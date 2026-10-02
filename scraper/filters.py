import re

from . import config

WORLDWIDE = re.compile(
    r"\b(worldwide|world[\s-]?wide|anywhere|global(ly)?|work from anywhere|all countries|"
    r"no location restrictions?)\b", re.I)

REGION_BLOCK = re.compile(
    r"\b(us|usa|u\.s|united states|america|americas|north america|canada|uk|united kingdom|britain|"
    r"europe|european|eu|latam|latin america|south america|apac|asia|australia|new zealand|india|"
    r"germany|france|spain|portugal|poland|netherlands|ireland|brazil|mexico|argentina|colombia|"
    r"philippines|japan|singapore|est|pst|cst|cet)\b", re.I)

HARD_BLOCKERS = [
    (r"\b(u\.?s\.?|united states|american) citizen(ship)?\b", "requires US citizenship"),
    (r"\bsecurity clearance\b|\bclearance required\b|\bts/sci\b", "security clearance"),
    (r"\b(legally )?authori[sz]ed to work in (the )?(u\.?s|usa|united states|canada|uk|united kingdom|"
     r"eu|european union)\b", "country work authorization"),
    (r"\b(must|need to|required to)\s+(be\s+)?(reside|live|be based|be located|located|based)\s+"
     r"(in|within)\s+(the\s+)?(u\.?s|usa|united states|canada|uk|united kingdom|europe|eu|latam|"
     r"latin america|north america)\b", "must live in a specific region"),
    (r"\b(us|usa|u\.s\.|north america|canada|uk|europe|eu|latam|apac)[\s-]+only\b", "region-only role"),
    (r"\bw-?2\b", "W-2 (US employment)"),
]
HARD_BLOCKERS = [(re.compile(p, re.I), why) for p, why in HARD_BLOCKERS]

TITLE_ROLE = re.compile(config.TITLE_ROLE, re.I)
TITLE_REJECT = re.compile(config.TITLE_REJECT, re.I)
ACCEPT = [re.compile(rf"\b{re.escape(r)}\b", re.I) for r in config.ALSO_ACCEPT_REGIONS]


def location_ok(job):
    loc = job["location"]
    accepted = any(p.search(loc) for p in ACCEPT)
    if REGION_BLOCK.search(loc) and not accepted:
        return False, f"location restricted: {loc}"
    if job.get("worldwide_hint") or WORLDWIDE.search(loc) or accepted:
        return True, ""
    return False, f"location not worldwide: {loc or 'unspecified'}"


def screen(job):
    title = job["title"]
    if not TITLE_ROLE.search(title):
        return False, "not an engineering title"
    if TITLE_REJECT.search(title):
        return False, "title excluded (seniority or role type)"
    ok, why = location_ok(job)
    if not ok:
        return False, why
    for rx, why in HARD_BLOCKERS:
        if rx.search(job["description"]):
            return False, why
    return True, ""