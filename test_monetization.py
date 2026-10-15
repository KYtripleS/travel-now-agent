"""Checks for the offer and finder rules that must never regress: an expired,
unchecked or unverified offer is never shown; a coupon appears only when
verified; affiliate CTAs carry rel="nofollow sponsored noopener"; offers stay
off historical pages; the finder data is complete.

usage: python test_monetization.py      (exit 1 on the first failure)
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path

import content_classes
import promotions as P

REPO = Path(__file__).resolve().parent
NOW, TODAY = datetime(2026, 10, 15, 3, tzinfo=timezone.utc), date(2026, 10, 15)
BASE = {
    "id": "t", "kind": "public_scheme", "title": "T", "benefit": "B", "url": "https://example.org/",
    "starts_at": "2026-06-01T00:00:00+10:00", "ends_at": "2027-01-01T00:00:00+11:00", "precision": "day",
    "coupon_code": None, "code_verified": False, "affiliate": None, "pages": [],
    "verification": {"status": "verified", "checked": "2026-10-15", "recheck_days": 30, "sources": ["https://example.org/"]},
}


def offer(**kw):
    p = copy.deepcopy(BASE)
    for k, v in kw.items():
        (p["verification"] if k in ("checked", "status") else p)[k] = v
    return p


def test_guards():
    assert P.problems(offer(), NOW, TODAY) == []
    assert P.problems(offer(ends_at="2026-10-14T00:00:00+11:00"), NOW, TODAY)        # expired
    assert P.problems(offer(ends_at="2027-01-01T00:00:00"), NOW, TODAY)              # no offset
    assert P.problems(offer(ends_at=None), NOW, TODAY)                               # no deadline
    assert P.problems(offer(checked="2026-09-01"), NOW, TODAY)                       # unchecked too long
    assert P.problems(offer(status="unverified"), NOW, TODAY)
    assert P.problems(offer(affiliate={"url": "https://example.com/x"}), NOW, TODAY)  # unknown partner
    assert not P.problems(offer(affiliate={"url": "https://airalo.tpx.lu/x"}), NOW, TODAY)


def test_render():
    assert "SAVE10" not in P.render(offer(coupon_code="SAVE10", code_verified=False))
    assert "SAVE10" in P.render(offer(coupon_code="SAVE10", code_verified=True))
    assert 'rel="nofollow sponsored noopener"' in P.render(offer(affiliate={"url": "https://airalo.tpx.lu/x"}))
    html = P.render(offer())
    assert 'data-ends="2027-01-01T00:00:00+11:00"' in html and "sponsored" not in html
    assert "data-countdown" not in html                                              # only when asked for


def test_live_data():
    classes = content_classes.load()
    for p in json.loads((REPO / "data/promotions.json").read_text())["promotions"]:
        for rel in p["pages"]:
            assert classes.get(rel) == "eligible", (p["id"], rel, classes.get(rel))
    for root in ("site", "docs"):
        for rel, cls in classes.items():
            f = REPO / root / rel
            if cls != "eligible" and f.exists():
                assert 'class="gy-promo"' not in f.read_text(encoding="utf-8"), rel
    data = json.loads((REPO / "site/data/stay-finder.json").read_text())
    assert len(data["cities"]) >= 40
    for c in data["cities"]:
        assert c["areas"] and (REPO / "site" / c["url"]).exists(), c["slug"]
        for a in c["areas"]:
            for h in a["hotels"]:
                assert h["rates"] is None or "aid=gentlyyonder" in h["rates"], h["name"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
