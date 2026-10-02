import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (personal job board)"}
TIMEOUT = 30


def _get(url, **kw):
    r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def strip_html(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(v):
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000 if v > 1e12 else v, tz=timezone.utc)
        s = str(v).strip()
        if s.isdigit():
            return parse_date(int(s))
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T", 1))
        except ValueError:
            dt = parsedate_to_datetime(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def make(source, id, title, company, location, url, posted, description,
         tags=None, salary="", worldwide_hint=False):
    dt = parse_date(posted)
    return {
        "source": source,
        "id": str(id),
        "title": strip_html(title),
        "company": strip_html(company) or "Unknown",
        "location": strip_html(location),
        "url": url or "",
        "posted": dt.isoformat() if dt else None,
        "description": strip_html(description)[:12000],
        "tags": [str(t) for t in (tags or [])],
        "salary": str(salary or ""),
        "worldwide_hint": worldwide_hint,
    }


def remotive():
    data = _get("https://remotive.com/api/remote-jobs", params={"category": "software-dev"}).json()
    for j in data.get("jobs", []):
        yield make("Remotive", f"remotive-{j.get('id')}", j.get("title"), j.get("company_name"),
                   j.get("candidate_required_location", ""), j.get("url"), j.get("publication_date"),
                   j.get("description"), j.get("tags"), j.get("salary"))


def remoteok():
    data = _get("https://remoteok.com/api").json()
    for j in data:
        if not isinstance(j, dict) or "id" not in j or "position" not in j:
            continue  # first element is a legal notice
        lo, hi = j.get("salary_min"), j.get("salary_max")
        salary = f"${lo:,}-${hi:,}" if lo and hi else ""
        yield make("RemoteOK", f"remoteok-{j['id']}", j.get("position"), j.get("company"),
                   j.get("location", ""), j.get("url") or j.get("apply_url"),
                   j.get("epoch") or j.get("date"), j.get("description"), j.get("tags"), salary)


WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]


def weworkremotely():
    for feed in WWR_FEEDS:
        d = feedparser.parse(_get(feed).content)
        for e in d.entries:
            company, _, title = e.get("title", "").partition(": ")
            if not title:
                title, company = company, ""
            yield make("WeWorkRemotely", "wwr-" + (e.get("id") or e.get("link", "")), title, company,
                       e.get("region", ""), e.get("link"), e.get("published"), e.get("summary", ""))


def himalayas(pages=15):
    for p in range(pages):
        data = _get("https://himalayas.app/jobs/api", params={"limit": 20, "offset": p * 20}).json()
        jobs = data.get("jobs", [])
        if not jobs:
            break
        for j in jobs:
            restr = j.get("locationRestrictions") or []
            names = [r if isinstance(r, str) else (r.get("name") or "") for r in restr]
            yield make("Himalayas", "himalayas-" + str(j.get("guid") or j.get("applicationLink")),
                       j.get("title"), j.get("companyName"),
                       "Worldwide" if not names else ", ".join(names),
                       j.get("applicationLink") or j.get("guid"), j.get("pubDate"),
                       j.get("description") or j.get("excerpt"), j.get("categories"),
                       worldwide_hint=not names)
        time.sleep(1)


def jobicy():
    data = _get("https://jobicy.com/api/v2/remote-jobs", params={"count": 100}).json()
    for j in data.get("jobs", []):
        lo, hi = j.get("annualSalaryMin"), j.get("annualSalaryMax")
        salary = f"{lo}-{hi} {j.get('salaryCurrency', '')}".strip() if lo and hi else ""
        yield make("Jobicy", f"jobicy-{j.get('id')}", j.get("jobTitle"), j.get("companyName"),
                   j.get("jobGeo", ""), j.get("url"), j.get("pubDate"),
                   j.get("jobDescription") or j.get("jobExcerpt"), j.get("jobIndustry"), salary)


def workingnomads():
    data = _get("https://www.workingnomads.com/api/exposed_jobs/").json()
    for j in data:
        tags = j.get("tags") or ""
        tags = tags.split(",") if isinstance(tags, str) else tags
        yield make("WorkingNomads", "wn-" + str(j.get("url")), j.get("title"), j.get("company_name"),
                   j.get("location", ""), j.get("url"), j.get("pub_date"), j.get("description"), tags)


def greenhouse(slug):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"}).json()
    for j in data.get("jobs", []):
        yield make(f"Greenhouse:{slug}", f"gh-{slug}-{j.get('id')}", j.get("title"), slug,
                   (j.get("location") or {}).get("name", ""), j.get("absolute_url"),
                   j.get("updated_at"), j.get("content"))


def lever(slug):
    data = _get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}).json()
    for j in data:
        cats = j.get("categories") or {}
        loc = ", ".join(cats.get("allLocations") or []) or cats.get("location", "")
        desc = f"{j.get('descriptionPlain', '')} {j.get('additionalPlain', '')}"
        yield make(f"Lever:{slug}", f"lever-{slug}-{j.get('id')}", j.get("text"), slug, loc,
                   j.get("hostedUrl"), j.get("createdAt"), desc)


def ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").json()
    for j in data.get("jobs", []):
        yield make(f"Ashby:{slug}", f"ashby-{slug}-{j.get('id') or j.get('jobUrl')}", j.get("title"), slug,
                   j.get("location", ""), j.get("jobUrl"), j.get("publishedAt"),
                   j.get("descriptionPlain") or j.get("descriptionHtml"))