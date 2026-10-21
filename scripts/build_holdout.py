"""Builds the independent holdout set (inputs/supplier_holdout.xlsx + labels).

Run:  python scripts/build_holdout.py
Writes inputs/supplier_holdout.xlsx (sheet News_Test, answer columns empty) and
inputs/supplier_holdout_labels.json (answers kept apart from the app).

Two labelling passes:
  1. LABELS: the label written by hand next to each article.
  2. derive(): an independent re-derivation from the README rules, the
     supplier catalog and the facts stated in the text (FACTS). Names and
     places are detected automatically from the catalog; the build fails if
     both passes do not agree on every field.
Only the catalog (Suppliers sheet) of supplier_training.xlsx is read.
News of training/validation are only compared by token overlap and by their
(supplier, Event_Type) labels; no text is printed. The build fails if any
(supplier, event type) pair repeats or the token Jaccard reaches 0.20.
"""
import json, re, sys
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "inputs/supplier_holdout.xlsx"
LABELS_JSON = ROOT / "inputs/supplier_holdout_labels.json"

# (news_id, date, source, headline, summary)
NEWS = [
    ("H001", "2026-10-07", "Auto Industry Brief",
     "European new car registrations up 6% in September",
     "New car registrations across the European Union rose 6% in September compared with a year earlier, led by hybrid models, an industry association said. Battery-electric cars took a slightly smaller share than in August."),
    ("H002", "2026-10-07", "BioProcess Today",
     "Alpine Filtration AG opens new sterile filter production hall in Zurich",
     "Swiss filtration maker Alpine Filtration AG has started production in a new cleanroom hall at its Zurich site, raising its sterile filter capacity by about 25%. The company said the expansion was completed on schedule and that delivery lead times for existing customers will shorten from early 2027."),
    ("H003", "2026-10-08", "Andes Daily News",
     "Magnitude 6.4 earthquake shakes San Juan province in western Argentina",
     "A strong earthquake struck San Juan province in Argentina on Wednesday, damaging roads and forcing several wineries and a cement plant near the city of San Juan to suspend work while engineers check buildings. Authorities reported no fatalities."),
    ("H004", "2026-10-08", "Chemicals Europe Weekly",
     "Rhenvale Excipients GmbH hit by one-day warning strike in Ludwigshafen",
     "Workers at Rhenvale Excipients GmbH staged a 24-hour warning strike at the company's Ludwigshafen site on Thursday as part of a regional wage dispute. The company said production resumed the next morning and that microcrystalline cellulose deliveries would be delayed by no more than two days."),
    ("H005", "2026-10-09", "South Asia Business Wire",
     "Backlot fire halts filming at Polaris Film Studios",
     "A fire damaged two outdoor sets at Polaris Film Studios, a film and television production company in Atlanta, Georgia, forcing it to pause filming for a week. No one was injured, and the studio said its streaming releases are not affected."),
    ("H006", "2026-10-09", "Latin America Freight News",
     "Emergency bridge repairs close Sao Paulo ring road for two days",
     "Authorities in Sao Paulo, Brazil, closed the main ring road around the city for two days for emergency repairs to a damaged bridge. Manufacturers in the city said outbound deliveries would run up to three days late; the road is due to reopen on Sunday night."),
    ("H007", "2026-10-10", "Nordic Lifestyle Journal",
     "Oslo hosts Nordic design week with record attendance",
     "More than 60,000 visitors attended this year's Nordic design week in Oslo, organisers said, with exhibitions on furniture, textiles and sustainable architecture spread across 40 venues in the city."),
    ("H008", "2026-10-10", "Lab Supply Insider",
     "Atlas Cleanroom Garments to exit cleanroom garments at end of 2027",
     "Atlas Cleanroom Garments said it will stop making cleanroom garments at its Tangier plant at the end of 2027 and convert the site to medical textiles. Orders will be supplied as normal until then, and customers have been asked to plan alternative sources."),
    ("H009", "2026-10-11", "Northern Italy Business",
     "Planned grid works cut power to Bergamo factories for 36 hours",
     "The regional grid operator will cut electricity to the industrial areas of Bergamo, Italy, for 36 hours this weekend to replace a substation transformer. Manufacturers in the city expect to lose about a day and a half of output; power returns on Monday morning."),
    ("H010", "2026-10-11", "Pharma Packaging Monitor",
     "Lumina Glassworks adds new vial forming line in Mainz",
     "Lumina Glassworks has commissioned a new forming line for Type I glass vials at its plant in Mainz, Germany, adding roughly 15% to its annual output. The company said the line passed customer acceptance runs ahead of plan and will be used to cut order backlogs in the first half of 2027."),
    ("H011", "2026-10-12", "UK Manufacturing Today",
     "UK boiler maker Celsius Heating Systems enters administration",
     "Celsius Heating Systems, a Birmingham-based maker of domestic gas boilers, has appointed administrators after a fall in new-build housing orders. About 400 jobs are at risk, and the administrators are seeking a buyer for its two factories in the West Midlands."),
    ("H012", "2026-10-12", "Asia Pharma Wire",
     "Regulators halt production at Taizhou Hengyuan Pharma metformin plant for at least six weeks",
     "Chinese environmental authorities have ordered Taizhou Hengyuan Pharma to stop all production at its metformin hydrochloride plant after an inspection found wastewater treatment failures. The company told customers that shipments are suspended and that the shutdown is expected to last at least six weeks while equipment is replaced."),
    ("H013", "2026-10-13", "North West England Courier",
     "Chemical warehouse fire forces evacuations in Lancaster, England",
     "Firefighters spent the night tackling a blaze at a chemical storage warehouse on an industrial estate in Lancaster, Lancashire, in north-west England. Nearby homes were evacuated as a precaution; the warehouse operator, a local paint distributor, said no one was injured."),
    ("H014", "2026-10-13", "Enterprise Software Ledger",
     "Vectra Serialisation Software acquired; new owner plans to retire its platform in 2028",
     "Vectra Serialisation Software of Madrid has been bought by a larger US software group, which said it will migrate Vectra customers to its own track-and-trace system and switch off the Vectra platform in mid-2028. Service and support for the current platform continue unchanged until then."),
    ("H015", "2026-10-14", "Healthcare Markets Brief",
     "Brennor Pharma launches once-weekly diabetes tablet in Europe",
     "Brennor Pharma said its new once-weekly tablet for type 2 diabetes is now available in Germany and France, following approval earlier this year. The company expects the drug to compete with older daily treatments."),
    ("H016", "2026-10-14", "Eurasia Rail Freight Review",
     "Derailment closes main China-Europe rail freight line out of Xi'an for four days",
     "A freight train derailment west of Xi'an, China, has closed the main line used by China-Europe container trains departing the city. Rail operators said services should resume within four days and that cargo already booked will reach Europe about a week later than planned."),
    ("H017", "2026-10-15", "BioProcess Today",
     "Celsius Bioprocess Systems halts bioreactor bag output and recalls recent lots",
     "Celsius Bioprocess Systems has stopped making bioreactor bags at its San Juan plant and is recalling all bags produced since August after finding a defect in the film used to make them. The company told customers that deliveries will not resume for at least ten weeks."),
    ("H018", "2026-10-15", "India Textile Chronicle",
     "Strike halts Kaveri Spinning Mills in Tamil Nadu",
     "Workers at Kaveri Spinning Mills, a cotton yarn producer in Coimbatore, Tamil Nadu, walked out over unpaid bonuses, halting all three of its mills. The textile company said talks with unions would continue next week."),
    ("H019", "2026-10-16", "Iberian Industry Report",
     "Medipack Iberica brings forward foil line maintenance; orders delayed about a week",
     "Medipack Iberica SL has brought forward a planned maintenance stop on one of its two aluminium blister foil lines in Barcelona after a mechanical fault. The company said the second line keeps running and that some October orders will ship about one week late."),
    ("H020", "2026-10-16", "Spain Economic Daily",
     "Flash floods shut all factories in and around Valencia for at least eight weeks",
     "Torrential rain caused severe flash flooding across Valencia province in eastern Spain. Regional authorities have ordered every factory in the city of Valencia and its surrounding industrial estates to stay closed for at least eight weeks while power and equipment are restored; the rest of Spain was not affected."),
    ("H021", "2026-10-17", "European Biopharma News",
     "Irish regulator suspends Celtic BioLogics' Cork manufacturing licence",
     "Ireland's medicines regulator has suspended the manufacturing licence of Celtic BioLogics Ltd at its Cork site after repeated sterility test failures, and has stopped all shipments of drug substance from the plant. The company expects the suspension to last at least four to six months while it rebuilds its cleanroom controls."),
    ("H022", "2026-10-17", "India Life Sciences Wire",
     "Cyprin Analytical Services opens second testing laboratory in Bengaluru",
     "Cyprin Analytical Services has opened a second batch release testing laboratory in Bengaluru, India, doubling its capacity. The company said average turnaround times for customers will fall from 14 to about 9 days starting in November."),
    ("H023", "2026-10-18", "Pakistan Business Daily",
     "Heatwave and power cuts shut factories in Hyderabad, Pakistan",
     "Factories in Hyderabad, in Pakistan's Sindh province, have suspended work for a week as a late heatwave and grid failures cause power cuts of up to 14 hours a day. Textile and food processing plants are the worst hit, local business groups said."),
    ("H024", "2026-10-18", "German Industry Monitor",
     "Darmstadt orders all chemical and lab products plants to stop for three months",
     "Authorities in Darmstadt, Germany, have ordered every chemical and laboratory products plant in the city to stop production for at least three months after groundwater contamination was traced to the city's industrial area. Plants must install new containment systems before they can restart."),
    ("H025", "2026-10-19", "Nordic Business Review",
     "Reactor failure halts Nordic Lipids' Oslo plant for at least ten weeks",
     "Nordic Lipids AS has stopped all production at its Oslo plant after the failure of the main reactor used to make lipid nanoparticle components. The company told customers that a replacement unit must be built and that shipments will not restart for at least ten weeks."),
    ("H026", "2026-10-19", "US Manufacturing Wire",
     "Explosion shuts Stellar Elastomers' rubber stopper plant in Lancaster, Pennsylvania",
     "An explosion in the compounding unit of Stellar Elastomers Inc. in Lancaster, Pennsylvania, injured three workers and forced the plant to shut down. The company said all rubber stopper shipments are on hold and it does not expect to resume deliveries for at least three months."),
    ("H027", "2026-10-20", "Japan Industrial Times",
     "Strong earthquake shuts all factories in Osaka for at least two months",
     "A magnitude 7.2 earthquake struck Osaka, Japan, early on Sunday, damaging buildings and cutting gas lines. Prefectural authorities said all factories in Osaka will stay closed for at least two months while structures and utilities are inspected and repaired."),
    ("H028", "2026-10-20", "China Packaging Digest",
     "Zhejiang Paper Leaflets to move printing to a new plant in 2027",
     "Zhejiang Paper Leaflets plans to move its printing operations from Hangzhou to a new plant in Jiaxing in the second half of 2027 and has warned customers to expect a production gap of several weeks during the move. Customers will also need to approve leaflets printed at the new site."),
    ("H029", "2026-10-14", "Danish Food Retail News",
     "Danish margarine maker Nordic Lipid Foods recalls three spreads",
     "Nordic Lipid Foods A/S, a margarine and cooking-oil producer based in Aarhus, Denmark, is recalling three spreads sold in Danish supermarkets after a labelling error left out an allergen warning. No other products are affected."),
    ("H030", "2026-10-16", "Lab Supply Insider",
     "Boston Assay Supplies warns of delays of up to ten days on QC assay kits",
     "Boston Assay Supplies told customers that shipments of some quality control assay kits will be delayed by up to ten days because a packaging component arrived late from its own supplier. The company said all orders will be filled in full by early November."),
]

# Pass 1: hand labels. (Is_Risk, Urgent, suppliers, case_type, explanation)
LABELS = {
    "H001": ("N", "N", [], "noise", "Car market statistics; no Helixa supplier or material involved."),
    "H002": ("N", "N", ["S026"], "supplier_positive", "Alpine Filtration AG (S026) adds sterile filter capacity: positive news about a supplier, no threat to supply."),
    "H003": ("N", "N", [], "location_trap", "San Juan in Argentina, not San Juan, Puerto Rico (S025). No Helixa supplier in the affected area."),
    "H004": ("Y", "N", ["S009"], "direct", "Named supplier S009 (Rhenvale) loses one day; deliveries at most two days late. Minor and short; approved alternate S010 and 40 days cover."),
    "H005": ("N", "N", [], "name_trap", "Polaris Film Studios is a US film company in Atlanta, not Polaris Films Sp. z o.o. (S019, Lodz)."),
    "H006": ("Y", "N", ["S036"], "regional", "Ring-road closure delays Sao Paulo deliveries up to three days: affects Aurum Gelatin Capsules (S036, Sao Paulo) without naming it. Minor and short; alternate S037 and 40 days cover."),
    "H007": ("N", "N", [], "noise", "Cultural event in Oslo; no supply impact for Nordic Lipids (S012) or anyone else."),
    "H008": ("Y", "N", ["S040"], "strategic", "Single-source S040 will stop cleanroom garments at end of 2027: supply risk that needs a new source, but slow-moving (over a year) and supply continues."),
    "H009": ("Y", "N", ["S016"], "regional", "36-hour power cut in Bergamo affects Vitrum Medica (S016, Bergamo) without naming it. Short; alternate S015 and 35 days cover."),
    "H010": ("N", "N", ["S015"], "supplier_positive", "Lumina Glassworks (S015) adds vial output: positive supplier news, no risk."),
    "H011": ("N", "N", [], "name_trap", "Celsius Heating Systems is a UK boiler maker, not Celsius Bioprocess Systems (S025, San Juan)."),
    "H012": ("Y", "Y", ["S003"], "direct", "Regulator stops all production at single-source, High-criticality S003 for at least six weeks; only 30 days of cover."),
    "H013": ("N", "N", [], "location_trap", "Lancaster in England, not Lancaster, USA (S017). The warehouse belongs to a local paint distributor."),
    "H014": ("Y", "N", ["S035"], "strategic", "Single-source platform S035 will be switched off in mid-2028: supply risk that needs a replacement plan, not an immediate stop."),
    "H015": ("N", "N", [], "noise", "Competitor product launch; commercial news with no effect on Helixa's suppliers."),
    "H016": ("Y", "N", ["S033"], "regional", "Main Xi'an China-Europe rail line closed four days: affects Silkroute Rail Freight (S033, Xi'an) without naming it. About one week of delay; alternate S032."),
    "H017": ("Y", "Y", ["S025"], "direct", "Single-source, High-criticality S025 stops bag output and recalls lots; no deliveries for at least ten weeks, beyond its 40 days of cover."),
    "H018": ("N", "N", [], "name_trap", "Kaveri Spinning Mills is a cotton yarn maker in Tamil Nadu, not Kaveri Fine Chemicals (S002, Ahmedabad)."),
    "H019": ("Y", "N", ["S018"], "direct", "Named supplier S018 runs on one of two foil lines; some orders one week late. Minor; alternate S019."),
    "H020": ("Y", "Y", ["S011"], "regional", "All factories in Valencia closed for at least eight weeks: stops single-source S011 (Valencia) beyond its 35 days of cover."),
    "H021": ("Y", "Y", ["S008"], "direct", "Regulator stops all shipments from single-source, High-criticality S008 for 4-6 months, beyond its 90 days of cover."),
    "H022": ("N", "N", ["S034"], "supplier_positive", "Cyprin Analytical Services (S034) doubles testing capacity: positive supplier news."),
    "H023": ("N", "N", [], "location_trap", "Hyderabad in Pakistan, not Hyderabad, India (S001)."),
    "H024": ("Y", "Y", ["S028"], "regional", "Every chemical and lab products plant in Darmstadt stopped for at least three months: stops single-source S028 (Darmstadt) beyond its 60 days of cover."),
    "H025": ("Y", "Y", ["S012"], "direct", "Reactor failure stops all production at single-source, High-criticality S012 for at least ten weeks; only 30 days of cover."),
    "H026": ("Y", "Y", ["S017"], "direct", "Explosion shuts single-source, High-criticality S017 (Lancaster, USA); no deliveries for at least three months, beyond 40 days of cover."),
    "H027": ("Y", "Y", ["S020"], "regional", "All Osaka factories closed for at least two months: stops single-source S020 (Osaka) beyond its 45 days of cover."),
    "H028": ("Y", "N", ["S024"], "strategic", "Single-source S024 plans a move in H2 2027 with a gap of several weeks and requalification: slow-moving supply risk."),
    "H029": ("N", "N", [], "name_trap", "Nordic Lipid Foods is a Danish margarine maker, not Nordic Lipids AS (S012, Oslo)."),
    "H030": ("Y", "N", ["S029"], "direct", "Named supplier S029 delays some kits by up to ten days; Low criticality and 30 days cover: minor."),
}

# Pass 2 inputs: what the text states about the event, written per article.
# effect: none | positive | minor_delay (<= 10 days) | future (>= 12 months away)
#         | halt (production or shipments stopped) | insolvency
# halt_days: minimum stop stated in the text.
# material: material keyword stated in the text (used for country-wide events).
FACTS = {
    "H001": dict(effect="none"), "H002": dict(effect="positive"),
    "H003": dict(effect="halt", halt_days=1), "H004": dict(effect="minor_delay"),
    "H005": dict(effect="halt", halt_days=7), "H006": dict(effect="minor_delay"),
    "H007": dict(effect="none"), "H008": dict(effect="future"),
    "H009": dict(effect="minor_delay"), "H010": dict(effect="positive"),
    "H011": dict(effect="insolvency"), "H012": dict(effect="halt", halt_days=42),
    "H013": dict(effect="halt", halt_days=1), "H014": dict(effect="future"),
    "H015": dict(effect="none"), "H016": dict(effect="minor_delay"),
    "H017": dict(effect="halt", halt_days=70), "H018": dict(effect="halt", halt_days=7),
    "H019": dict(effect="minor_delay"), "H020": dict(effect="halt", halt_days=56),
    "H021": dict(effect="halt", halt_days=120), "H022": dict(effect="positive"),
    "H023": dict(effect="halt", halt_days=7),
    "H024": dict(effect="halt", halt_days=90),
    "H025": dict(effect="halt", halt_days=70), "H026": dict(effect="halt", halt_days=90),
    "H027": dict(effect="halt", halt_days=60), "H028": dict(effect="future"),
    "H029": dict(effect="none"), "H030": dict(effect="minor_delay"),
}
# Event type per article (training vocabulary where it exists). Used only to
# check that no (supplier, event type) pair repeats a training/validation case.
EVENT_TYPE = {
    "H002": "Positive news", "H004": "Labour strike", "H006": "Logistics disruption",
    "H008": "Business exit", "H009": "Utility outage", "H010": "Positive news",
    "H012": "Regulatory action", "H014": "Acquisition by competitor",
    "H016": "Logistics disruption", "H017": "Quality recall",
    "H019": "Fire / plant incident", "H020": "Natural disaster",
    "H021": "Regulatory action", "H022": "Positive news", "H024": "Regulatory action",
    "H025": "Fire / plant incident", "H026": "Fire / plant incident",
    "H027": "Natural disaster", "H028": "Site relocation", "H030": "Supply shortage",
}
CASE_RULES = {  # expected shape of each case type
    "direct": lambda r, u, ids, named, area: r == "Y" and named,
    "regional": lambda r, u, ids, named, area: r == "Y" and not named and area,
    "name_trap": lambda r, u, ids, named, area: r == "N" and not ids,
    "location_trap": lambda r, u, ids, named, area: r == "N" and not ids,
    "supplier_positive": lambda r, u, ids, named, area: r == "N" and u == "N" and ids and named,
    "strategic": lambda r, u, ids, named, area: r == "Y" and u == "N" and named,
    "noise": lambda r, u, ids, named, area: r == "N" and not ids,
}


def catalog():
    wb = load_workbook(ROOT / "inputs/supplier_training.xlsx", read_only=True, data_only=True)
    rows = list(wb["Suppliers"].iter_rows(values_only=True))
    wb.close()
    head = rows[0]
    return {r[0]: dict(zip(head, r)) for r in rows[1:] if r[0]}


def has(text, word):
    return re.search(r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)", text.lower()) is not None


def country_names(s):
    c = s["Country"]
    return {"Puerto Rico (USA)": ["Puerto Rico"], "USA": ["USA", "United States", "Pennsylvania"]}.get(c, [c])


def derive(news, cat):
    """Pass 2: labels from README rules + catalog + stated facts only."""
    nid, _, _, head, summary = news
    text = head + " " + summary
    f = FACTS[nid]
    named = sorted(sid for sid, s in cat.items() if has(text, s["Supplier_Name"]))
    # Area match: catalog city AND its country in the text, or a country-wide
    # event naming the supplier's material.
    area = sorted(sid for sid, s in cat.items()
                  if (has(text, s["City"]) and any(has(text, c) for c in country_names(s)))
                  or (f.get("material") and any(has(text, c) for c in country_names(s))
                      and f["material"] in s["Material_Supplied"].lower()))
    if f["effect"] == "none":
        return "N", "N", [], named, area
    if f["effect"] == "positive":
        return "N", "N", named, named, area
    affected = sorted(set(named) | set(area)) if named else area
    if not affected:
        return "N", "N", [], named, area
    if f["effect"] in ("minor_delay", "future"):
        return "Y", "N", affected, named, area
    # halt / insolvency: urgent only if no unaffected approved alternate and
    # the stop is longer than inventory cover (insolvency always counts).
    def stops(sid):
        s = cat[sid]
        alt = s["Approved_Alternate_ID"]
        backup = alt and alt not in affected
        cover = s["Inventory_Cover_Days"] or 0
        long_enough = f["effect"] == "insolvency" or f.get("halt_days", 0) > cover
        return not backup and long_enough
    urgent = "Y" if all(stops(sid) for sid in affected) else None
    if urgent is None and any(stops(sid) for sid in affected):
        raise SystemExit(f"{nid}: urgency mixed across suppliers; rewrite or drop")
    if urgent is None and f["effect"] in ("halt", "insolvency") and f.get("halt_days", 99) > 10:
        raise SystemExit(f"{nid}: serious stop with backup is debatable; rewrite or drop")
    return "Y", urgent or "N", affected, named, area


def overlap_with_training(news):
    """Max token Jaccard against training/validation news, plus (supplier,
    event type) collisions. Texts are never printed."""
    def toks(s):
        return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 3}
    others, seen_pairs = [], set()
    for name, sheet in (("supplier_training.xlsx", "News"), ("supplier_validation.xlsx", "News_Validation")):
        wb = load_workbook(ROOT / "inputs" / name, read_only=True, data_only=True)
        rows = list(wb[sheet].iter_rows(values_only=True))
        wb.close()
        h = rows[0]
        for r in rows[1:]:
            d = dict(zip(h, r))
            if d.get("Headline"):
                others.append(toks(f"{d['Headline']} {d.get('Summary') or ''}"))
                for sid in str(d.get("Affected_Supplier_IDs") or "").replace(",", ";").split(";"):
                    if sid.strip():
                        seen_pairs.add((sid.strip(), d.get("Event_Type")))
    out = {}
    for n in news:
        mine = toks(n[3] + " " + n[4])
        out[n[0]] = round(max(len(mine & o) / len(mine | o) for o in others), 3)
    collisions = sorted(f"{nid}:{sid}:{EVENT_TYPE.get(nid)}" for nid, lab in LABELS.items()
                        for sid in lab[2] if (sid, EVENT_TYPE.get(nid)) in seen_pairs)
    return out, len(others), collisions


def main():
    cat = catalog()
    assert len(cat) == 40
    news = sorted(NEWS, key=lambda n: (n[1], n[0]))
    ids = [n[0] for n in NEWS]
    assert ids == [f"H{i:03}" for i in range(1, 31)] and set(LABELS) == set(ids) == set(FACTS)
    problems = []
    for n in news:
        nid = n[0]
        r, u, sup, case, _ = LABELS[nid]
        assert all(s in cat for s in sup), nid
        assert u == "N" or r == "Y", nid
        assert "2026-10-07" <= n[1] <= "2026-10-20", nid
        dr, du, dsup, named, area = derive(n, cat)
        if (dr, du, sorted(dsup)) != (r, u, sorted(sup)):
            problems.append(f"{nid}: pass1={r}/{u}/{sup} pass2={dr}/{du}/{dsup}")
        if not CASE_RULES[case](r, u, sup, named, area):
            problems.append(f"{nid}: case_type {case} does not fit (named={named}, area={area})")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    overlap, n_other, collisions = overlap_with_training(news)
    missing = [nid for nid, lab in LABELS.items() if lab[2] and nid not in EVENT_TYPE]
    if collisions or missing or max(overlap.values()) >= 0.2:
        print("too close to training/validation:", collisions, missing,
              sorted(overlap.items(), key=lambda x: -x[1])[:3])
        sys.exit(1)

    wb = Workbook()
    ws = wb.active
    ws.title = "News_Test"
    ws.append(["News_ID", "Published_Date", "Source", "Headline", "Summary",
               "Is_Risk", "Urgent", "Affected_Supplier_IDs"])
    for nid, day, source, head, summary in sorted(NEWS):
        ws.append([nid, datetime.fromisoformat(day), source, head, summary, None, None, None])
        ws.cell(ws.max_row, 2).number_format = "yyyy-mm-dd"
    for col, width in zip("ABCDEFGH", (9, 14, 28, 70, 110, 8, 8, 22)):
        ws.column_dimensions[col].width = width
    wb.save(XLSX)

    from collections import Counter
    labels = [{"News_ID": nid, "Is_Risk": LABELS[nid][0], "Urgent": LABELS[nid][1],
               "Affected_Supplier_IDs": "; ".join(LABELS[nid][2]),
               "case_type": LABELS[nid][3], "explanation": LABELS[nid][4]} for nid in sorted(LABELS)]
    LABELS_JSON.write_text(json.dumps({
        "dataset": "supplier_holdout.xlsx", "sheet": "News_Test",
        "generated": "2026-10-21", "generator": "scripts/build_holdout.py (AI-written fictional news)",
        "catalog": "inputs/supplier_training.xlsx (Suppliers)",
        "second_pass": "derive() agrees with every hand label",
        "max_token_jaccard_vs_training_validation": max(overlap.values()),
        "supplier_event_type_collisions_vs_training_validation": 0,
        "compared_against_news": n_other,
        "labels": labels}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    c = Counter(l["case_type"] for l in labels)
    print("ok", len(labels), "rows; risk Y", sum(l["Is_Risk"] == "Y" for l in labels),
          "urgent Y", sum(l["Urgent"] == "Y" for l in labels), dict(c))
    print("max token Jaccard vs", n_other, "training/validation news:", max(overlap.values()),
          "| top:", sorted(overlap.items(), key=lambda x: -x[1])[:3])


if __name__ == "__main__":
    main()
