#!/usr/bin/env python3
"""Stay22: hotel rates, hotel maps and GetYourGuide links for Gently Yonder.

Stay22 (joined 2026-09-27, AID "gentlyyonder") passes a reader on to Booking.com,
Expedia, Hotels.com, Agoda, Vrbo, KAYAK or GetYourGuide and pays us a share of the
commission when they book. Nothing here is a secret: the AID sits in every link.

Links ("Allez") are plain redirects, https://www.stay22.com/allez/<provider>?aid=…
- "roam" lets Stay22 choose the booking site for each reader. It needs a place
  (lat/lng), so we use it only where our text names no booking site: "see hotels
  around Shinjuku Station".
- A named provider ("booking", "agoda", "getyourguide" …) wherever the text names
  that site. A link must never send a reader somewhere other than what it says.
- One hotel: link=<its booking.com URL>. Stay22 can also match by name
  (hotelname=), but that is fuzzy: it sent HOSHINOYA Tokyo to a different hotel and
  Aman Kyoto to a guesthouse. So every hotel in HOTELS was looked up by hand on
  Booking.com (2026-09-27); None means Booking.com doesn't list it, and it gets no
  rates link at all rather than a near miss.
- campaign= is not in the href. js/gy-reveal.js adds page + placement at click
  time (as it does Travelpayouts' sub_id), so an untagged click is a crawler.
  Stay22 wants "_" not "-" inside a campaign id.

add_aeo.py places everything built here (data-aeo, so every run rebuilds it).
"""
from __future__ import annotations

from urllib.parse import quote, urlencode

AID = "gentlyyonder"
BASE = "https://www.stay22.com"
REL = "nofollow sponsored noopener"
NAVY = "172033"                        # the map's accent, as hex without "#"


def allez(provider: str = "roam", **params) -> str:
    """A tracked link through Stay22 to one booking site (or "roam")."""
    q = {"aid": AID, **{k: v for k, v in params.items() if v is not None}}
    return f"{BASE}/allez/{provider}?" + urlencode(q, quote_via=quote, safe="")


def hotel_rates(booking_url: str) -> str:
    """One hotel's own page on Booking.com."""
    return allez("booking", link=booking_url)


def area_rates(lat: float, lng: float) -> str:
    """Hotels around a point, on whichever booking site Stay22 picks."""
    return allez("roam", lat=lat, lng=lng)


def map_src(address: str, zoom: int, campaign: str) -> str:
    """The embeddable hotel map. By address, not lat/lng: from coordinates the map
    labels its search box with whatever is there ("JR新宿駅;1階;9番線" in Tokyo).
    An iframe can't be tagged at click time, so its campaign is fixed: <page>_map.
    scroll=disabled: otherwise the wheel zooms the map and a reader scrolling down
    the guide gets stuck in it (the +/- buttons and dragging still work)."""
    q = dict(aid=AID, address=address, zoom=zoom, maincolor=NAVY, ljs="en", scroll="disabled",
             campaign=campaign.replace("-", "_"))
    return f"{BASE}/embed/gm?" + urlencode(q, quote_via=quote, safe="")


# --- where-to-stay guides ----------------------------------------------------------
# The first-trip area each verdict recommends: lat/lng for the verdict's link
# (exact), and the address the map centres on (for its English label).
PAGES = {
    "where-to-stay-in-tokyo": dict(area="Shinjuku Station", lat=35.6896, lng=139.7006, zoom=15,
                                   address="Shinjuku Station, Tokyo, Japan"),
    "where-to-stay-in-kyoto": dict(area="downtown Kyoto", lat=35.0050, lng=135.7648, zoom=15,
                                   address="Nishiki Market, Kyoto, Japan"),
    "where-to-stay-in-osaka": dict(area="Namba and Shinsaibashi", lat=34.6687, lng=135.5013, zoom=15,
                                   address="Dotonbori, Osaka, Japan"),
    "where-to-stay-in-sydney": dict(area="Hyde Park", lat=-33.8731, lng=151.2111, zoom=15,
                                    address="Hyde Park, Sydney NSW, Australia"),
    "where-to-stay-in-melbourne": dict(area="the CBD", lat=-37.8136, lng=144.9631, zoom=15,
                                       address="Bourke Street Mall, Melbourne VIC, Australia"),
    "where-to-stay-in-hakone": dict(area="Gora", lat=35.2494, lng=139.0489, zoom=14,
                                    address="Gora Station, Hakone, Japan"),
    "where-to-stay-in-seoul": dict(area="Myeongdong", lat=37.5609, lng=126.9863, zoom=15,
                                   address="Myeongdong Station, Seoul, South Korea"),
    "where-to-stay-in-bangkok": dict(area="Asok", lat=13.7370, lng=100.5604, zoom=15,
                                     address="Terminal 21, Bangkok, Thailand"),
}

# Hotel name exactly as the guide prints it -> its Booking.com page (checked by
# hand, 2026-09-27), or None when Booking.com doesn't list it.
_B = "https://www.booking.com/hotel/"
HOTELS = {
    # Tokyo
    "Park Hyatt Tokyo": _B + "jp/park-hyatt-tokyo.html",
    "JR Kyushu Hotel Blossom Shinjuku": _B + "jp/jr-kyushu-blossom-shinjuku.html",
    "Hotel Gracery Shinjuku": _B + "jp/gracery-shinjuku.html",
    "TRUNK(HOTEL) CAT STREET": _B + "jp/trunk.html",
    "SHIBUYA STREAM HOTEL": _B + "jp/shibuya-stream-excel-tokyu.html",
    "sequence MIYASHITA PARK": _B + "jp/sequence-miyashita-park-tokyo.html",
    "The Tokyo Station Hotel": _B + "jp/tokyo-station.html",
    "HOSHINOYA Tokyo": None,
    "Hotel Ryumeikan Tokyo": _B + "jp/ryumeikan-tokyo.html",
    "The Peninsula Tokyo": _B + "jp/the-peninsula-tokyo.html",
    "MUJI HOTEL GINZA": _B + "jp/muji-ginza.html",
    "Mitsui Garden Hotel Ginza Premier": _B + "jp/mitsui-garden-ginza-premier-chuo.html",
    "The Gate Hotel Kaminarimon by Hulic": _B + "jp/the-gate-asakusa-kaminarimon-by-hulic.html",
    "OMO3 Asakusa by Hoshino Resorts": _B + "jp/omo3-asakusa-by-hoshino-resorts.html",
    "Nui. HOSTEL & BAR LOUNGE": _B + "jp/nui-hostel-and-bar-lounge.html",
    "NOHGA HOTEL UENO TOKYO": _B + "jp/nohga-ueno.html",
    "Ryokan Sawanoya": None,
    # Kyoto
    "HOTEL THE MITSUI KYOTO": _B + "jp/the-mitsui-kyoto-a-luxury-collection-spa.html",
    "Ace Hotel Kyoto": _B + "jp/ace-hotel-kyoto.html",
    "Mitsui Garden Hotel Kyoto Sanjo PREMIER": _B + "jp/san-jing-gadenhoterujing-du-san-tiao-puremia.html",
    "Cross Hotel Kyoto": _B + "jp/cross-hotel-kyoto.html",
    "Len Kyoto Kawaramachi": _B + "jp/len-kyoto-kawaramachi.html",
    "THE THOUSAND KYOTO": _B + "jp/the-thousand-kyoto.html",
    "Hotel Granvia Kyoto": _B + "jp/granvia-kyoto-kyoto.html",
    "Park Hyatt Kyoto": _B + "jp/park-hyatt-kyoto.html",
    "Four Seasons Hotel Kyoto": _B + "jp/four-seasons-kyoto.html",
    "The Hotel Seiryu Kyoto Kiyomizu": _B + "jp/thehotelseiryukyotokiyomizu.html",
    "HOSHINOYA Kyoto": None,
    "Aman Kyoto": None,
    # Osaka
    "W Osaka": _B + "jp/w-osaka.html",
    "Swissôtel Nankai Osaka": _B + "jp/swissotel-nankai-osaka-osaka.html",
    "Cross Hotel Osaka": _B + "jp/cross-osaka.html",
    "THE OSAKA STATION HOTEL, Autograph Collection": _B + "jp/osaka-autograph-collection.html",
    "Waldorf Astoria Osaka": _B + "jp/waldorf-astoria-osaka.html",
    "Hotel Hankyu RESPIRE OSAKA": _B + "jp/hankyu-respire-osaka.html",
    "Conrad Osaka": _B + "jp/conrad-osaka.html",
    "Osaka Marriott Miyako Hotel": _B + "jp/osaka-marriott-miyako.html",
    "OMO7 Osaka by Hoshino Resorts": _B + "jp/omo7-osaka-by-hoshino-resorts.html",
    "The Park Front Hotel at Universal Studios Japan": _B + "jp/the-park-front-hotel.html",
    # Sydney
    "Sheraton Grand Sydney Hyde Park": _B + "au/sheraton-on-the-park-sydney.html",
    "Kimpton Margot Sydney": _B + "au/kimpton-margot-sydney.html",
    "Capella Sydney": _B + "au/capella-sydney.html",
    "Great Southern Hotel Sydney": _B + "au/great-southern.html",
    "Park Hyatt Sydney": _B + "au/park-hyatt-sydney.html",
    "Pullman Quay Grand Sydney Harbour": _B + "au/quay-grand-suites-sydney.html",
    "YHA Sydney Harbour": _B + "au/sydney-harbour-yha.html",
    "Crown Towers Sydney": _B + "au/crown-towers-sydney.html",
    "W Sydney": _B + "au/w-sydney.html",
    "Paramount House Hotel": _B + "au/paramount-house.html",
    "Ovolo Sydney, Woolloomooloo": _B + "au/blue-sydney-sydney.html",
    "Hotel Ravesis": _B + "au/ravesis.html",
    "Q Station": _B + "au/q-station-retreat.html",
    # Melbourne
    "Park Hyatt Melbourne": _B + "au/park-hyatt-melbourne.html",
    "The Ritz-Carlton, Melbourne": _B + "au/the-ritz-carlton-melbourne.html",
    "QT Melbourne": _B + "au/qt-melbourne.html",
    "Laneways by Ovolo": None,
    "The Hotel Windsor": _B + "au/the-windsor.html",
    "The Victoria Hotel": _B + "au/the-victoria-melbourne-an-all-seasons.html",
    "The Langham, Melbourne": _B + "au/the-langham-melbourne.html",
    "Crown Towers Melbourne": _B + "au/crown-towers.html",
    "The StandardX, Melbourne": _B + "au/the-standard-melbourne.html",
    "The Prince": _B + "au/the-prince.html",
    "The Como Melbourne – MGallery": _B + "au/como-melbourne.html",
    "The Olsen Melbourne – Art Series": _B + "au/art-series-the-olsen.html",
    # Hakone (Booking.com pages confirmed by title, 2026-09-29)
    "Yumoto Fujiya Hotel": _B + "jp/yumoto-fujiya.html",
    "Fujiya Hotel": _B + "jp/fujiya.html",
    "Hakone Ginyu": None,
    "Hakone Kowakien Ten-yu": _B + "jp/hakone-kowakien-tenyu.html",
    "Gora Kadan": _B + "jp/gora-kadan.html",
    "Hyatt Regency Hakone Resort and Spa": _B + "jp/hyatt-regency-hakone-resort-and-spa.html",
    "Hotel Indigo Hakone Gora": _B + "jp/indigo-hakone-gora.html",
    "Hakone Tent": _B + "jp/hakone-tent.html",
    "Kinnotake Sengokuhara": _B + "jp/kinnotake.html",
    "Fuji-Hakone Guest House": _B + "jp/fuji-hakone-guest-house.html",
    "Odakyu Hotel de Yama": _B + "jp/odakyu-de-yama.html",
    "The Prince Hakone Lake Ashinoko": _B + "jp/the-prince-hakone.html",
    # Seoul (Booking.com pages confirmed by title, 2026-09-30; two listed under old names)
    "The Grand Lotte Seoul": _B + "kr/lotte-seoul-seoul.html",
    "The Westin Josun Seoul": _B + "kr/westin-chosun-seoul.html",
    "L7 Myeongdong by Lotte": _B + "kr/l7-myeongdong-by-lotte.html",
    "Four Seasons Hotel Seoul": _B + "kr/four-seasons-seoul.html",
    "Nine Tree by Parnas Seoul Insadong": _B + "kr/nine-tree-premier-insadong.html",
    "Rakkojae Seoul": _B + "kr/raggojae.html",
    "RYSE, Autograph Collection": _B + "kr/ryse-autograph-collection-korea.html",
    "L7 Hongdae by Lotte": _B + "kr/l7-hongdae.html",
    "Four Points by Sheraton Josun, Seoul Station": _B + "kr/four-points-by-sheraton-seoul-namsan.html",
    "Mondrian Seoul Itaewon": _B + "kr/mondrian-seoul-itaewon.html",
    "Josun Palace, a Luxury Collection Hotel, Seoul Gangnam": _B + "kr/josun-palace-a-luxury-collection-seoul-gangnam.html",
    "Signiel Seoul": _B + "kr/signiel-seoul.html",
    # Bangkok (each Booking.com page checked by hand, October 2026)
    "Hyatt Regency Bangkok Sukhumvit": _B + "th/hyatt-regency-bangkok-sukhumvit.html",
    "Bangkok Marriott Marquis Queen’s Park": _B + "th/bangkok-marriott-marquis-queens-park.html",
    "Holiday Inn Express Bangkok Sukhumvit 11": _B + "th/holiday-inn-express-bangkok-sukhumvit-11.html",
    "Siam Kempinski Hotel Bangkok": _B + "th/siam-kempinski-bangkok.html",
    "Pathumwan Princess Hotel": _B + "th/pathumwan-princess.html",
    "Mandarin Oriental, Bangkok": _B + "th/mandarin-oriental-bangkok.html",
    "Capella Bangkok": _B + "th/capella-bangkok.html",
    "Avani+ Riverside Bangkok Hotel": _B + "th/avani-riverside-bangkok-bangkok.html",
    "The Sukhothai Bangkok": _B + "th/the-sukhothai.html",
    # the rebuilt hotel (opened 27 Sep 2024); Booking.com also keeps the old hotel's page
    "Dusit Thani Bangkok": _B + "th/dusit-thani-bangkok-bangkok1.html",
    "Riva Surya Bangkok": _B + "th/riva-surya-bangkok.html",
    "Lamphu Tree House": _B + "th/lamphu-tree-house-boutique.html",
}

RATES_LABEL = "Check rates on Booking.com"
RATES_NOTE = ("How the hotel links work: a hotel’s name goes to its own website. "
              "“Check rates” opens it on Booking.com through our partner Stay22, which pays "
              "us a commission if you book, at no extra cost to you.")


def map_copy(area: str) -> tuple[str, str]:
    """Heading and blurb for the map box. Every clause must stay literally true."""
    return (f"Hotels around {area}, with prices",
            f"The map shows the hotels and apartments around {area} that booking sites such as "
            f"Booking.com and Expedia list, with nightly prices; our own picks follow further down. "
            f"It comes from our partner Stay22, which pays us a commission if you book through it.")
