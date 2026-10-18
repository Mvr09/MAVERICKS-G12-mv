"""Private effective-payload evidence; no headers, credentials or new decisions."""
from copy import deepcopy
from app.importer import digest


class CapturingClient:
    def __init__(self, client):
        self.client = client
        self.payloads = {}
        self.responses = {}

    def __getattr__(self, name):
        return getattr(self.client, name)

    def ask(self, payload, stage, deadline):
        # Capture the exact body given to the configured client, including cache
        # lookups. Authorization headers are built deeper in JevClient only.
        self.payloads[stage] = deepcopy(payload)
        response = self.client.ask(payload, stage, deadline)
        self.responses[stage] = deepcopy(response)
        return response

    def audit(self):
        return {
            '_effective_payloads': self.payloads,
            '_effective_responses': self.responses,
            '_effective_payload_hashes': {k: digest(v) for k,v in self.payloads.items()},
            '_audit_format': 'effective-payload-1.0.0',
        }
