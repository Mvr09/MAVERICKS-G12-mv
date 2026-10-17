import math, time, random, threading
from contextlib import contextmanager
from sqlalchemy import text
from app.db import engine
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt
from sqlalchemy import select, func
from app.settings import settings, POLICY
from app.models import RequestCache, ApiCall, GrantArticle, Grant, now
from app.importer import digest


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    model: str
    answers: dict[str, dict]
    usage: dict


slots = threading.BoundedSemaphore(4)


def finite(value, lo, hi):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not lo <= value <= hi
    ):
        raise ProviderError("CONTRACT_RANGE")
    return value


def validate_response(payload, data):
    try:
        r = ProviderResponse.model_validate(data)
    except Exception:
        raise ProviderError("CONTRACT_SHAPE")
    if r.model != payload["model"]:
        raise ProviderError("MODEL_MISMATCH")
    if set(r.answers) != set(payload["questions"]):
        raise ProviderError("CONTRACT_MISSING_ANSWERS")
    for key, q in payload["questions"].items():
        a = r.answers[key]
        if a.get("type") != q["type"]:
            raise ProviderError("CONTRACT_TYPE")
        if q["type"] == "noul":
            finite(a.get("noul"), 0, 1)
            continue
        finite(a.get("confidence"), 0, 1)
        probabilities = a.get("probabilities")
        keys = (
            set(q["criteria"])
            if q["type"] == "choice"
            else {str(i) for i in range(len(q["criteria"]))}
        )
        if not isinstance(probabilities, dict) or set(probabilities) != keys:
            raise ProviderError("CONTRACT_DISTRIBUTION")
        for p in probabilities.values():
            finite(p, 0, 1)
        if abs(sum(probabilities.values()) - 1) > 0.015:
            raise ProviderError("CONTRACT_DISTRIBUTION")
        if q["type"] == "choice":
            if a.get("choice") not in keys:
                raise ProviderError("CONTRACT_CHOICE")
            if probabilities[a["choice"]] + 0.015 < max(probabilities.values()):
                raise ProviderError("CONTRACT_CHOICE")
        else:
            finite(a.get("score"), 0, len(q["criteria"]) - 1)
            if (
                abs(a["score"] - sum(int(k) * v for k, v in probabilities.items()))
                > 0.03
            ):
                raise ProviderError("CONTRACT_SCORE")
            if not isinstance(a.get("legend"), dict) or set(a["legend"]) != keys:
                raise ProviderError("CONTRACT_LEGEND")
    return r.model_dump()


def retry_after(value):
    try:
        return max(0, float(value))
    except (ValueError, TypeError):
        try:
            return max(
                0,
                (
                    parsedate_to_datetime(value) - datetime.now(timezone.utc)
                ).total_seconds(),
            )
        except Exception:
            return 0


@contextmanager
def global_slot(deadline):
    # Session advisory locks bound outbound calls to four across all processes.
    with engine.connect() as connection:
        acquired = None
        while acquired is None:
            if time.monotonic() >= deadline:
                raise ProviderError("ARTICLE_DEADLINE")
            for index in range(4):
                if connection.execute(
                    text("SELECT pg_try_advisory_lock(72641, :slot)"), {"slot": index}
                ).scalar():
                    acquired = index
                    break
            if acquired is None:
                time.sleep(0.05)
        try:
            yield
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(72641, :slot)"), {"slot": acquired}
            )


class JevClient:
    def __init__(
        self, db, article_id, transport=None, sleep=time.sleep, diagnostic_ack_at=None
    ):
        self.diagnostic_ack_at = diagnostic_ack_at
        self.db = db
        self.article_id = article_id
        self.transport = transport
        self.sleep = sleep
        self.cached_stages = []
        self.network_requests = 0

    def ask(self, payload, stage, deadline):
        # Cache includes the entire effective payload plus question version.
        key = digest({"payload": payload, "questions": POLICY["question_version"]})
        cached = self.db.get(RequestCache, key)
        if cached:
            self.cached_stages.append(stage)
            return validate_response(payload, cached.response)
        if self.transport is None:
            reservation = self.db.get(GrantArticle, self.article_id)
            grant = self.db.get(Grant, reservation.grant_id) if reservation else None
            if not grant:
                raise ProviderError("CONSUMPTION_NOT_AUTHORIZED")
            if grant.expires_at:
                remaining_authorization = (grant.expires_at - now()).total_seconds()
                if remaining_authorization <= 0:
                    raise ProviderError("AUTHORIZATION_EXPIRED")
                deadline = min(deadline, time.monotonic() + remaining_authorization)
        if not settings.typesafe_api_key.get_secret_value():
            raise ProviderError("ENGINE_NOT_CONFIGURED")
        attempts = self.db.scalar(
            select(func.count())
            .select_from(ApiCall)
            .where(ApiCall.article_id == self.article_id, ApiCall.stage == stage)
        )
        previous = self.db.scalar(
            select(ApiCall)
            .where(ApiCall.article_id == self.article_id, ApiCall.stage == stage)
            .order_by(ApiCall.created_at.desc())
        )
        ack = (
            datetime.fromisoformat(self.diagnostic_ack_at)
            if self.diagnostic_ack_at
            else None
        )
        if (
            previous
            and previous.status in (400, 401, 403, 422)
            and (not ack or ack <= previous.created_at)
        ):
            raise ProviderError(f"JEV_HTTP_{previous.status}")
        if attempts >= 3:
            raise ProviderError("ATTEMPTS_EXHAUSTED")
        while attempts < 3:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError("ARTICLE_DEADLINE")
            attempts += 1
            self.network_requests += 1
            start = time.monotonic()
            status = None
            usage = {}
            failure = None
            response = None
            # Reserve the attempt durably before any outbound request. Crash cannot reset it.
            record = ApiCall(
                article_id=self.article_id,
                stage=stage,
                attempt=attempts,
                model=payload["model"],
                duration=0,
                usage={},
            )
            self.db.add(record)
            self.db.commit()
            try:
                with (
                    slots,
                    global_slot(deadline),
                    httpx.Client(
                        transport=self.transport,
                        timeout=min(15, remaining),
                        follow_redirects=False,
                    ) as client,
                ):
                    response = client.post(
                        "https://api.typesafe.ai/v1/systemone",
                        headers={
                            "Authorization": "Bearer "
                            + settings.typesafe_api_key.get_secret_value()
                        },
                        json=payload,
                    )
                    status = response.status_code
                    if status != 200:
                        raise ProviderError(f"JEV_HTTP_{status}")
                    try:
                        data = response.json()
                    except Exception:
                        raise ProviderError("CONTRACT_JSON")
                    result = validate_response(payload, data)
                    usage = result["usage"]
                    self.db.merge(RequestCache(id=key, response=result))
            except httpx.RequestError:
                failure = ProviderError("JEV_CONNECTION")
            except ProviderError as exc:
                failure = exc
            finally:
                record.status = status
                record.duration = time.monotonic() - start
                record.usage = usage
                self.db.commit()
            if not failure:
                return result
            if (
                failure.code.startswith("CONTRACT")
                or failure.code == "MODEL_MISMATCH"
                or status in (400, 401, 403, 422)
                or (status is not None and status not in (429, 529) and status < 500)
            ):
                raise failure
            if attempts >= 3:
                raise failure
            delay = max(
                2 ** (attempts - 1) + random.uniform(0, 0.25),
                retry_after(response.headers.get("retry-after")) if response else 0,
            )
            if time.monotonic() + delay >= deadline:
                raise ProviderError("ARTICLE_DEADLINE")
            self.sleep(delay)
        raise ProviderError("ATTEMPTS_EXHAUSTED")
