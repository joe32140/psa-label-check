#!/usr/bin/env python3
"""
snkrdunk_refs.py - download reference photos of genuine PSA slabs of the same
card from SNKRDUNK (snkrdunk.com), for use as --ref in psa_label_check.py.

PSA's own cert page is usually behind a bot check, so agents often cannot get
PSA's image. SNKRDUNK lists many graded copies of the same card, its pages and
JSON are reachable with plain HTTP, and every sale goes through SNKRDUNK's own
authentication. Listings that are past that step (sold and shipped) are
preferred as references.

The references are a DIFFERENT cert, and often a different grade, of the same
card, so run the check with --description-only: it compares only the left
description block and skips the card number, grade and cert column. Use
several references, because PSA has re-typeset some labels between printing
eras; psa_label_check.py votes across them.

Usage:
  # find the SNKRDUNK card page (apparel id) from a keyword
  python snkrdunk_refs.py --search "144 s-p"
  # download 8 PSA-graded references for that card (any grade)
  python snkrdunk_refs.py --apparel-id 120250 --out refs/
  # only one grade
  python snkrdunk_refs.py --apparel-id 120250 --grade PSA10 --out refs/
  # or start from any SNKRDUNK card or listing URL
  python snkrdunk_refs.py --url https://snkrdunk.com/apparels/120250/used/42863548 --out refs/

Writes <out>/ref_<listing>.jpg and <out>/refs.json, and prints the ready-to-run
psa_label_check.py --ref arguments. Exit code: 0 ok, 3 error / nothing found.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://snkrdunk.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
# Listing statuses that come after SNKRDUNK's authentication step
# (seen on the site: 4 取引完了 = completed, 11 運営の発送待ち = authenticated,
# waiting to ship, 13 到着待ち = shipped to the buyer).
AUTHENTICATED = {4, 11, 13}


def get(url, as_json=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return json.loads(data) if as_json else data


def search(keywords, limit=8):
    """Card pages (apparel ids) that appear in SNKRDUNK's search results."""
    html = get(f"{BASE}/search?" + urllib.parse.urlencode({"keywords": keywords})).decode("utf-8", "replace")
    ids = []
    for m in re.finditer(r"apparels[\\/]+(\d+)", html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    out = []
    for aid in ids[:limit]:
        items = used_listings(aid, pages=1, per_page=50)
        name = items[0]["apparel"]["localizedName"] if items else ""
        grades = {}
        for it in items:
            g = it.get("displayShortConditionTitle", "")
            grades[g] = grades.get(g, 0) + 1
        out.append({"apparel_id": int(aid), "name": name, "url": f"{BASE}/apparels/{aid}",
                    "recent_listings_by_condition": grades})
    return out


def used_listings(apparel_id, pages=6, per_page=50):
    items = []
    for page in range(1, pages + 1):
        d = get(f"{BASE}/v1/apparels/{apparel_id}/used?page={page}&perPage={per_page}", as_json=True)
        batch = d.get("apparelUsedItems") or []
        items += batch
        if len(batch) < per_page:
            break
    return items


def front_photo(item):
    ph = item.get("photos") or {}
    front = (ph.get("trading_card_single_front") or {}).get("imageUrl")
    return front or (item.get("primaryPhoto") or {}).get("imageUrl") or (item.get("imageUrls") or [None])[0]


def grade_ok(item, grade):
    cond = item.get("displayShortConditionTitle", "").upper()
    return cond.startswith("PSA") if grade.upper() == "PSA" else cond == grade.upper()


def pick_refs(items, grade, n, exclude=()):
    cands = [it for it in items
             if grade_ok(it, grade) and str(it["id"]) not in exclude and front_photo(it)]
    # authenticated (sold and checked by SNKRDUNK) first, then newest
    cands.sort(key=lambda it: (it.get("status") not in AUTHENTICATED, -it["id"]))
    return cands[:n]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--search", help="keywords, e.g. card number '144 s-p' or the card name in Japanese")
    src.add_argument("--apparel-id", type=int, help="SNKRDUNK card id (the number in /apparels/<id>)")
    src.add_argument("--url", help="SNKRDUNK card or listing URL")
    ap.add_argument("--grade", default="PSA",
                    help="condition label to match: PSA (any PSA grade, default), PSA10, PSA9, ...")
    ap.add_argument("--n", type=int, default=8, help="number of reference photos (default 8)")
    ap.add_argument("--exclude-listing", action="append", default=[],
                    help="listing id to skip, e.g. the listing being tested (repeatable)")
    ap.add_argument("--out", default="refs", help="output directory (default refs/)")
    a = ap.parse_args(argv)

    try:
        if a.search:
            res = search(a.search)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0 if res else 3
        aid = a.apparel_id
        if a.url:
            m = re.search(r"/apparels/(\d+)(?:/used/(\d+))?", a.url)
            if not m:
                print("error: not a SNKRDUNK /apparels/ URL", file=sys.stderr)
                return 3
            aid = int(m.group(1))
        items = used_listings(aid)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 3

    refs = pick_refs(items, a.grade, a.n, set(a.exclude_listing))
    if not refs:
        print(f"error: no {a.grade} listings with photos for apparel {aid}", file=sys.stderr)
        return 3
    os.makedirs(a.out, exist_ok=True)
    meta = []
    for it in refs:
        url = front_photo(it)
        path = os.path.join(a.out, f"ref_{it['id']}.jpg")
        with open(path, "wb") as f:
            f.write(get(url))
        meta.append({"file": path, "listing_id": it["id"], "grade": it.get("displayShortConditionTitle"),
                     "status": it.get("status"), "status_text": it.get("statusText"),
                     "authenticated_by_snkrdunk": it.get("status") in AUTHENTICATED,
                     "listing_url": f"{BASE}/apparels/{aid}/used/{it['id']}", "image_url": url})
    name = items[0]["apparel"]["localizedName"] if items else ""
    with open(os.path.join(a.out, "refs.json"), "w", encoding="utf-8") as f:
        json.dump({"apparel_id": aid, "card": name, "grade": a.grade, "refs": meta}, f, indent=2, ensure_ascii=False)
    print(json.dumps({"apparel_id": aid, "card": name, "refs": [(m["listing_id"], m["status_text"]) for m in meta]},
                     ensure_ascii=False))
    print("--ref " + " ".join(m["file"] for m in meta) + " --description-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
