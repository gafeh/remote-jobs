"""Check candidate company boards before adding them to config.

Usage: python -m scraper.check_boards greenhouse:gitlab ashby:supabase lever:somecompany
"""
import collections
import sys

import requests

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
}


def locations(kind, data):
    if kind == "greenhouse":
        return [(j.get("location") or {}).get("name", "") for j in data.get("jobs", [])]
    if kind == "lever":
        return [(j.get("categories") or {}).get("location", "") for j in data]
    return [j.get("location", "") for j in data.get("jobs", [])]


for arg in sys.argv[1:]:
    kind, _, slug = arg.partition(":")
    r = requests.get(URLS[kind].format(slug), timeout=30)
    if r.status_code != 200:
        print(f"{arg}: NOT FOUND ({r.status_code})")
        continue
    locs = locations(kind, r.json())
    print(f"{arg}: {len(locs)} jobs")
    for loc, n in collections.Counter(locs).most_common(8):
        print(f"    {n:4}  {loc}")