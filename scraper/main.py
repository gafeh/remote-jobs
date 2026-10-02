import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, sources
from .filters import screen
from .score import heuristic, llm_score

ROOT = Path(__file__).resolve().parent.parent
DATA, SITE = ROOT / "data", ROOT / "site"


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def collect():
    fetchers = [
        ("Remotive", sources.remotive),
        ("RemoteOK", sources.remoteok),
        ("WeWorkRemotely", sources.weworkremotely),
        ("Himalayas", sources.himalayas),
        ("Jobicy", sources.jobicy),
        ("WorkingNomads", sources.workingnomads),
    ]
    fetchers += [(f"greenhouse:{s}", lambda s=s: sources.greenhouse(s)) for s in config.GREENHOUSE]
    fetchers += [(f"lever:{s}", lambda s=s: sources.lever(s)) for s in config.LEVER]
    fetchers += [(f"ashby:{s}", lambda s=s: sources.ashby(s)) for s in config.ASHBY]

    jobs, stats = [], {}
    for name, fn in fetchers:
        try:
            got = list(fn())
            jobs += got
            stats[name] = len(got)
        except Exception as e:
            stats[name] = f"error: {e.__class__.__name__}"
        print(f"[fetch] {name}: {stats[name]}")
    return jobs, stats


def dedupe(jobs):
    best = {}
    for j in jobs:
        key = re.sub(r"[^a-z0-9]", "", (j["company"] + j["title"]).lower())
        if key not in best or (j["posted"] or "") > (best[key]["posted"] or ""):
            best[key] = j
    return list(best.values())


def load_resume():
    if os.environ.get("RESUME_TEXT"):
        return os.environ["RESUME_TEXT"]
    p = ROOT / "resume.txt"
    return p.read_text() if p.exists() else ""


def main():
    now = datetime.now(timezone.utc)
    DATA.mkdir(exist_ok=True)
    first_seen = load(DATA / "first_seen.json", {})
    cache = load(DATA / "llm_cache.json", {})

    raw, stats = collect()
    kept, rejected = [], []
    cutoff = now - timedelta(days=config.MAX_AGE_DAYS)

    for j in dedupe(raw):
        ok, why = screen(j)
        if not ok:
            rejected.append({**{k: j[k] for k in ("title", "company", "location", "source", "url")}, "reason": why})
            continue
        if j["posted"] and datetime.fromisoformat(j["posted"]) < cutoff:
            continue
        heuristic(j, now)
        kept.append(j)

    kept.sort(key=lambda j: j["h_score"], reverse=True)

    resume = load_resume()
    if os.environ.get("ANTHROPIC_API_KEY") and resume:
        llm_score(kept[:config.LLM_TOP_N], resume, cache)
    else:
        print("[llm] skipped (no ANTHROPIC_API_KEY or resume)")

    public = []
    for j in kept:
        llm = j.get("llm")
        if llm and llm.get("location_ok") is False:
            rejected.append({**{k: j[k] for k in ("title", "company", "location", "source", "url")},
                             "reason": "LLM: location not workable"})
            continue
        first_seen.setdefault(j["id"], now.isoformat())
        is_new = datetime.fromisoformat(first_seen[j["id"]]) > now - timedelta(hours=24)
        score = round(0.35 * j["h_score"] + 0.65 * int(llm.get("interview_odds", 0))) if llm else j["h_score"]
        public.append({
            "id": j["id"], "title": j["title"], "company": j["company"], "location": j["location"],
            "url": j["url"], "source": j["source"], "posted": j["posted"], "salary": j["salary"],
            "score": score, "h_score": j["h_score"], "skills_hit": j["skills_hit"],
            "penalties": j["penalties"], "llm": llm, "is_new": is_new,
        })

    public.sort(key=lambda j: (j["score"], j["posted"] or ""), reverse=True)

    keep_after = now - timedelta(days=60)
    first_seen = {k: v for k, v in first_seen.items() if datetime.fromisoformat(v) > keep_after}
    cache = {k: v for k, v in cache.items() if k in first_seen}

    SITE.mkdir(exist_ok=True)
    (SITE / "jobs.json").write_text(json.dumps({
        "generated_at": now.isoformat(), "stats": stats,
        "rejected_count": len(rejected), "jobs": public}, indent=1))
    (SITE / "rejected.json").write_text(json.dumps(rejected[:800], indent=1))
    (DATA / "first_seen.json").write_text(json.dumps(first_seen))
    (DATA / "llm_cache.json").write_text(json.dumps(cache))
    print(f"[done] {len(public)} published, {len(rejected)} rejected")


if __name__ == "__main__":
    main()