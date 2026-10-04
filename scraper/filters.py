import re

from . import config

WORLDWIDE = re.compile(
    r"\b(worldwide|world[\s-]?wide|anywhere|global(ly)?|work from anywhere|all countries|any location|"
    r"no location restrictions?)\b", re.I)

REGION_BLOCK = re.compile(
    r"\b(us|usa|u\.s|united states|america|americas|amer|north america|namer|canada|uk|united kingdom|britain|"
    r"europe|european|eu|latam|latin america|south america|apac|asia|australia|new zealand|india|"
    r"germany|france|spain|portugal|poland|netherlands|ireland|brazil|mexico|argentina|colombia|"
    r"philippines|japan|singapore|est|pst|cst|cet)\b", re.I)

# Always disqualifying, remote or visa path.
ALWAYS_BLOCK = [
    (r"\b(u\.?s\.?|united states|american) citizen(ship)?\b", "requires US citizenship"),
    (r"\bsecurity clearance\b|\bclearance required\b|\bts/sci\b", "security clearance"),
]
# Disqualifying for remote roles; irrelevant if the employer sponsors a visa.
REMOTE_BLOCK = [
    (r"\b(legally )?(authori[sz]ed|eligible|right) to work in (the )?(u\.?s|usa|united states|canada|uk|"
     r"united kingdom|eu|european union|europe)\b", "country work authorization"),
    (r"\b(must|need to|required to)\s+(be\s+)?(reside|live|be based|be located|located|based)\s+"
     r"(in|within)\s+(the\s+)?(u\.?s|usa|united states|canada|uk|united kingdom|europe|eu|latam|"
     r"latin america|north america)\b", "must live in a specific region"),
    (r"\b(us|usa|u\.s\.|north america|canada|uk|europe|eu|latam|apac)[\s-]+only\b", "region-only role"),
    (r"\bw-?2\b", "W-2 (US employment)"),
]
ALWAYS_BLOCK = [(re.compile(p, re.I), why) for p, why in ALWAYS_BLOCK]
REMOTE_BLOCK = [(re.compile(p, re.I), why) for p, why in REMOTE_BLOCK]

TITLE_ROLE = re.compile(config.TITLE_ROLE, re.I)
TITLE_REJECT = re.compile(config.TITLE_REJECT, re.I)
ACCEPT = [re.compile(rf"\b{re.escape(r)}\b", re.I) for r in config.ALSO_ACCEPT_REGIONS]

# ---------- Visa sponsorship detection ----------
VISA_CTX = re.compile(r"visa|immigration|work permit|h-?1b|blue card|skilled worker|relocat|right to work|work authori", re.I)
NEGATION = re.compile(r"\b(no|not|unable|cannot|can't|won't|will not|does not|doesn't|do not|don't|nor|none|without|n't)\b", re.I)
POSITIVE = re.compile(r"\b(offer|offers|offered|offering|provide|provides|provided|available|support|supported|"
                      r"will sponsor|can sponsor|we sponsor|happy to sponsor|able to sponsor|includ\w*)\b", re.I)
# Sentence boundary: . ! ? not part of an abbreviation like "U.S.", or a "|" block separator.
BOUNDARY = re.compile(r"(?<!\b[A-Z])[.!?](?=\s|$)|\|")


def sponsorship(text):
    """'yes' only when a sentence clearly offers visa sponsorship; 'no' if any sentence refuses it."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")  # curly apostrophes in "don't"
    bounds = [(b.start(), b.group()) for b in BOUNDARY.finditer(text)]
    verdict = None
    for m in re.finditer(r"sponsor", text, re.I):
        before = [b for b in bounds if b[0] < m.start()]
        after = [b for b in bounds if b[0] >= m.end()]
        s0 = before[-1][0] + 1 if before else 0
        s1 = after[0][0] if after else len(text)
        sent = text[s0:s1]
        if not VISA_CTX.search(sent):
            continue
        if NEGATION.search(sent):
            return "no"
        is_header_cell = (not before or before[-1][1] == "|") and (not after or after[0][1] == "|")
        if POSITIVE.search(sent) or (is_header_cell and len(sent.strip()) < 40):
            verdict = "yes"
    return verdict


def location_ok(job):
    loc = job["location"]
    accepted = any(p.search(loc) for p in ACCEPT)
    if REGION_BLOCK.search(loc) and not accepted:
        return False, f"location restricted: {loc}"
    if job.get("worldwide_hint") or WORLDWIDE.search(loc) or accepted:
        return True, ""
    return False, f"location not worldwide: {loc or 'unspecified'}"


def screen(job):
    """Returns (ok, reason). Sets job['path'] to 'remote' or 'visa' and job['visa'] to yes/no/None."""
    title = job["title"]
    if not TITLE_ROLE.search(title):
        return False, "not an engineering title"
    if TITLE_REJECT.search(title):
        return False, "title excluded (seniority or role type)"

    desc = job["description"]
    job["visa"] = sponsorship(desc) or ("yes" if job.get("visa_hint") else None)
    sponsored = job["visa"] == "yes" and config.INCLUDE_VISA_SPONSORED

    for rx, why in ALWAYS_BLOCK:
        if rx.search(desc):
            return False, why

    loc_ok, loc_why = location_ok(job)
    if loc_ok:
        blocker = next((why for rx, why in REMOTE_BLOCK if rx.search(desc)), None)
        if not blocker:
            job["path"] = "remote"
            return True, ""
        if sponsored:
            job["path"] = "visa"
            return True, ""
        return False, blocker

    if sponsored:
        job["path"] = "visa"
        return True, ""
    return False, loc_why + ("; no sponsorship" if job["visa"] == "no" else "")