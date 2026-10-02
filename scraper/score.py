import json
import re
from datetime import datetime

from . import config

SKILLS = [(label, re.compile(rf"(?<![a-z0-9])(?:{pat})(?![a-z0-9])", re.I), w)
          for label, pat, w in config.SKILLS]
SENIOR = re.compile(r"\b(senior|sr\.?|lead)\b", re.I)
YEARS = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:(?:-|to|\u2013)\s*\d{1,2}\s*)?\+?\s*years?(?:\s+of)?(?:\s+\w+){0,3}\s+experience",
    re.I)
TZ_OVERLAP = re.compile(
    r"\b(us|est|edt|pst|pdt|cst|eastern|pacific|central)\s+(time\s*zones?|hours|business hours)\b", re.I)
TITLE_BOOST = re.compile(r"back[\s-]?end|full[\s-]?stack|python|node|\bai\b|llm|platform", re.I)


def required_years(text):
    nums = [int(n) for n in YEARS.findall(text) if 1 <= int(n) <= 15]
    return max(nums) if nums else None


def heuristic(job, now):
    text = " ".join([job["title"], " ".join(job["tags"]), job["description"]])
    hits = [label for label, rx, _ in SKILLS if rx.search(text)]
    raw = sum(w for label, _, w in SKILLS if label in hits)

    score = min(raw, config.SKILL_CAP) / config.SKILL_CAP * 60
    score += 10 if TITLE_BOOST.search(job["title"]) else 0

    if job["posted"]:
        age_h = (now - datetime.fromisoformat(job["posted"])).total_seconds() / 3600
        score += 30 if age_h <= 24 else 20 if age_h <= 72 else 10 if age_h <= 168 else 0

    penalties = []
    if SENIOR.search(job["title"]):
        score -= 8
        penalties.append("senior title")
    yrs = required_years(job["description"])
    if yrs and yrs > config.YEARS_EXPERIENCE:
        score -= min(30, (yrs - config.YEARS_EXPERIENCE) * 10)
        penalties.append(f"asks {yrs}+ yrs")
    if TZ_OVERLAP.search(job["description"]):
        score -= 5
        penalties.append("US hours overlap")
    if len(hits) < 3:
        score -= 10
        penalties.append("weak skill overlap")

    job.update(h_score=round(max(0, min(100, score))), skills_hit=hits, penalties=penalties)


PROMPT = """You are screening one job for one specific candidate. Be strict and realistic.
Estimate the probability this candidate passes the initial resume screen (recruiter or ATS) and gets an interview invite.

<resume>
{resume}
</resume>

<job>
Title: {title}
Company: {company}
Location: {location}
{description}
</job>

Consider: must-have requirements the resume lacks, seniority mismatch, how many core skills appear on the resume,
and location limits. The candidate lives in Lagos, Nigeria (UTC+1), is authorized to work only in Nigeria,
and can only be hired as a contractor or through an employer-of-record.

Respond with JSON only, no prose, no code fences:
{{"interview_odds": <integer 0-100>, "verdict": "apply" | "stretch" | "skip", "why": "<one sentence>", "gaps": ["<missing must-have>"], "location_ok": true | false}}"""


def llm_score(jobs, resume, cache):
    from anthropic import Anthropic

    client = Anthropic()
    for job in jobs:
        if job["id"] in cache:
            job["llm"] = cache[job["id"]]
            continue
        try:
            msg = client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": PROMPT.format(
                    resume=resume[:8000], title=job["title"], company=job["company"],
                    location=job["location"], description=job["description"][:5000])}],
            )
            text = "".join(b.text for b in msg.content if b.type == "text").strip()
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
            data = json.loads(text)
            cache[job["id"]] = data
            job["llm"] = data
        except Exception as e:
            print(f"[llm] {job['id']}: {e.__class__.__name__}: {e}")