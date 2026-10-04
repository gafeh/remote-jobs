import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (personal job board)"}
TIMEOUT = 30


def _get(url, timeout=TIMEOUT, **kw):
    r = requests.get(url, headers=UA, timeout=timeout, **kw)
    r.raise_for_status()
    return r


def strip_html(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<(br|p|li|/p|/li|/div)[^>]*>", " | ", s)  # keep block boundaries as separators
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip(" |")


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
         tags=None, salary="", worldwide_hint=False, visa_hint=False):
    dt = parse_date(posted)
    return {
        "source": source,
        "id": str(id),
        "title": strip_html(title).strip(" |"),
        "company": strip_html(company) or "Unknown",
        "location": strip_html(location),
        "url": url or "",
        "posted": dt.isoformat() if dt else None,
        "description": strip_html(description)[:12000],
        "tags": [str(t) for t in (tags or [])],
        "salary": str(salary or ""),
        "worldwide_hint": worldwide_hint,
        "visa_hint": visa_hint,
    }


def _bare_remote(slug, loc):
    return slug in config.TRUST_BARE_REMOTE and loc.strip().lower() in ("remote", "remote, remote", "fully remote")


# ---------------- Aggregators ----------------

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


def arbeitnow(pages=5):
    """Germany-focused board, many English-language roles. Only useful via the visa path."""
    for p in range(1, pages + 1):
        data = _get("https://www.arbeitnow.com/api/job-board-api", params={"page": p}).json()
        for j in data.get("data", []):
            yield make("Arbeitnow", f"arbeitnow-{j.get('slug')}", j.get("title"), j.get("company_name"),
                       j.get("location", ""), j.get("url"), j.get("created_at"),
                       j.get("description"), j.get("tags"))
        if not (data.get("links") or {}).get("next"):
            break
        time.sleep(1)


HN_SEP = re.compile(r"\s+\|\s+")


def hn_whos_hiring(threads=2):
    """HN 'Who is hiring?' threads. Posters tag REMOTE (Worldwide) or VISA in the header line."""
    s = _get("https://hn.algolia.com/api/v1/search_by_date",
             params={"tags": "story,author_whoishiring", "query": "who is hiring"}).json()
    stories = [h for h in s.get("hits", []) if h.get("title", "").lower().startswith("ask hn: who is hiring")]
    title_rx = re.compile(config.TITLE_ROLE, re.I)
    for story in stories[:threads]:
        item = _get(f"https://hn.algolia.com/api/v1/items/{story['objectID']}", timeout=90).json()
        for c in item.get("children", []):
            raw = c.get("text") or ""
            if not raw:
                continue
            header = strip_html(raw.split("<p>")[0])
            segs = [x.strip() for x in HN_SEP.split(header) if x.strip()]
            if len(segs) < 2:
                continue
            company = segs[0][:80]
            cands = [x for x in segs[1:] if not x.lower().startswith("http") and len(x) < 120]
            title = next((x for x in cands if title_rx.search(x)), cands[0] if cands else segs[1][:120])
            loc = ", ".join(x for x in segs if re.search(r"remote|onsite|on-site|hybrid|worldwide|global|anywhere", x, re.I))
            visa = any(re.match(r"^\s*visa\b", x, re.I) and not re.search(r"\bno\b|not", x, re.I) for x in segs)
            yield make("HN Who's Hiring", f"hn-{c['id']}", title, company, loc,
                       f"https://news.ycombinator.com/item?id={c['id']}", c.get("created_at"), raw,
                       visa_hint=visa)


# ---------------- Company ATS boards ----------------

def greenhouse(slug):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"}).json()
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        yield make(f"Greenhouse:{slug}", f"gh-{slug}-{j.get('id')}", j.get("title"), slug, loc,
                   j.get("absolute_url"), j.get("updated_at"), j.get("content"),
                   worldwide_hint=_bare_remote(slug, loc))


def lever(slug):
    data = _get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}).json()
    for j in data:
        cats = j.get("categories") or {}
        loc = ", ".join(cats.get("allLocations") or []) or cats.get("location", "")
        desc = f"{j.get('descriptionPlain', '')} {j.get('additionalPlain', '')}"
        yield make(f"Lever:{slug}", f"lever-{slug}-{j.get('id')}", j.get("text"), slug, loc,
                   j.get("hostedUrl"), j.get("createdAt"), desc,
                   worldwide_hint=_bare_remote(slug, loc))


def ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").json()
    for j in data.get("jobs", []):
        loc = j.get("location", "") or ""
        yield make(f"Ashby:{slug}", f"ashby-{slug}-{j.get('id') or j.get('jobUrl')}", j.get("title"), slug,
                   loc, j.get("jobUrl"), j.get("publishedAt"),
                   j.get("descriptionHtml") or j.get("descriptionPlain"),
                   worldwide_hint=_bare_remote(slug, loc))