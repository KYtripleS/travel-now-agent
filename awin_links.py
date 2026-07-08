#!/usr/bin/env python3
"""Awin affiliate link config + builder for Gently Yonder.
Publisher (awinaffid) and approved merchant ids are public (they appear in
every live link), so they live in the repo for reproducible builds.
"""
from urllib.parse import quote

AWINAFFID = "2926361"
MERCHANTS = {          # name -> numeric awinmid
    "VELTRA": "89081",
    "NOMATIC": "90033",
    "USIMS": "121892",
    "SAMBOAT_UK": "32677",
    "SAMBOAT_IT": "32681",
    "EVENTFLOSS_DE": "27722",
}
REL = 'nofollow sponsored noopener'

def link(merchant: str, dest: str) -> str:
    mid = MERCHANTS[merchant]
    ued = quote(dest, safe="")
    return (f"https://www.awin1.com/cread.php?awinmid={mid}"
            f"&awinaffid={AWINAFFID}&ued={ued}")

def anchor(merchant: str, dest: str, text: str, cls: str = "product-link") -> str:
    href = link(merchant, dest).replace("&", "&amp;")
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{href}" rel="{REL}" target="_blank">{text}</a>'
