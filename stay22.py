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
    "where-to-stay-in-hong-kong": dict(area="Tsim Sha Tsui", lat=22.2966, lng=114.1722, zoom=15,
                                       address="1881 Heritage, Hong Kong"),
    "where-to-stay-in-kyoto-cherry-blossom": dict(area="Okazaki", lat=35.0128, lng=135.7838, zoom=15,
                                                  address="Heian Shrine, Kyoto, Japan"),
    "where-to-stay-in-singapore": dict(area="Marina Bay", lat=1.2898, lng=103.8555, zoom=15,
                                       address="Esplanade - Theatres on the Bay, Singapore"),
    "where-to-stay-in-taipei": dict(area="Taipei Main Station", lat=25.0478, lng=121.5170, zoom=15,
                                    address="Taipei Main Station, Taipei, Taiwan"),
    "where-to-stay-in-kuala-lumpur": dict(area="KLCC", lat=3.1555, lng=101.7140, zoom=15,
                                          address="KLCC Park, Kuala Lumpur, Malaysia"),
    "where-to-stay-in-tokyo-cherry-blossom": dict(area="Asakusa", lat=35.7118, lng=139.7967, zoom=15,
                                                  address="Kaminarimon, Tokyo, Japan"),
    "where-to-stay-in-sydney-new-years-eve": dict(area="Circular Quay", lat=-33.8611, lng=151.2108, zoom=15,
                                                  address="Circular Quay, Sydney NSW, Australia"),
    "where-to-stay-in-sapporo-snow-festival": dict(area="Odori Park", lat=43.0598, lng=141.3480, zoom=15,
                                                   address="Odori Park, Sapporo, Japan"),
    "where-to-stay-in-niseko": dict(area="Grand Hirafu", lat=42.8605, lng=140.6966, zoom=12,
                                    address="Kutchan, Hokkaido, Japan"),
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
    # Sydney on New Year's Eve (Booking.com pages confirmed by search, 2026-10-05)
    "Shangri-La Sydney": _B + "au/shangrila-sydney.html",
    "Four Seasons Hotel Sydney": _B + "au/four-seasons-sydney.html",
    "Sofitel Sydney Darling Harbour": _B + "au/sofitel-sydney-darling-harbour.html",
    "Hyatt Regency Sydney": _B + "au/hyatt-regency-sydney.html",
    # Sapporo (Booking.com pages confirmed by search, 2026-10-06; OMO3's listing was not taking bookings)
    "The Royal Park Canvas Sapporo Odori Park": _B + "jp/the-royal-park-canvas-sapporo-odori-park.html",
    "Sapporo Grand Hotel": _B + "jp/sapporo-grand.html",
    "JR Inn Sapporo-eki Minamiguchi": _B + "jp/jr-inn-sapporo-eki-minami-guchi.html",
    "JR Tower Hotel Nikko Sapporo": _B + "jp/jr-tower-nikko-sapporo.html",
    "Hotel Gracery Sapporo": _B + "jp/gracery-sapporo.html",
    "Keio Plaza Hotel Sapporo": _B + "jp/keio-plaza-sapporo.html",
    "Cross Hotel Sapporo": _B + "jp/cross-sapporo.html",
    "Mercure Sapporo": _B + "jp/mercure-sapporo.html",
    "OMO3 Sapporo Susukino by Hoshino Resorts": None,
    "Sapporo Park Hotel": _B + "jp/sapporo-park-hokkaido.html",
    # Niseko (Booking.com pages confirmed by search, 2026-10-06; the Mercure is still listed as Midtown Niseko)
    "Skye Niseko": _B + "jp/skye-niseko.html",
    "Ki Niseko": _B + "jp/kiniseko.html",
    "Mercure Niseko Resort": _B + "jp/midtown-niseko.html",
    "Park Hyatt Niseko Hanazono": _B + "jp/park-hyatt-niseko-hanazono.html",
    "Nikko Style Niseko HANAZONO": _B + "jp/nitukosutairunisekohanazono.html",
    "Higashiyama Niseko Village, a Ritz-Carlton Reserve": _B + "jp/the-ritz-carlton-reserve-niseko.html",
    "Hilton Niseko Village": _B + "jp/hilton-niseko-village.html",
    "The Green Leaf Niseko Village, Tapestry Collection by Hilton": _B + "jp/green-leaf-niseko-village.html",
    "Niseko Northern Resort Annupuri": _B + "jp/niseko-northern-resort-an-nupuri.html",
    "Torifito Hotel & Pod Niseko": _B + "jp/torihuitohoteru-kiyabinnisekoponnotang.html",
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
    # Hong Kong (each Booking.com page checked by hand, October 2026)
    "The Peninsula Hong Kong": _B + "hk/the-peninsula-hong-kong.html",
    "Hotel ICON": _B + "hk/icon-hong-kong.html",
    "The Salisbury – YMCA of Hong Kong": _B + "hk/salisbury.html",
    "Mandarin Oriental, Hong Kong": _B + "hk/mandarin-oriental-hong-kong.html",
    "The Murray, Hong Kong": _B + "hk/the-murray-hong-kong-a-niccolo.html",
    # a Pullman until it joined Marriott's Autograph Collection in Jan 2025; same Booking.com page
    "The Park Lane Hong Kong, Autograph Collection": _B + "hk/the-park-lane-hong-kong.html",
    "Hotel Indigo Hong Kong Island": _B + "hk/indigo.html",
    "99 Bonham": _B + "hk/bonham.html",
    "Lan Kwai Fong Hotel @ Kau U Fong": _B + "hk/lan-kwai-fong.html",
    # not iclub-sheung-wan-ii, which is iclub AMTD Sheung Wan, a different hotel
    "iclub Sheung Wan Hotel": _B + "hk/iclub-sheung-wan.html",
    "Cordis, Hong Kong": _B + "hk/langhamplace.html",
    "Eaton HK": _B + "hk/eaton.html",
    # Kyoto in cherry-blossom season (each Booking.com page checked by hand, October 2026)
    "The Westin Miyako Kyoto": _B + "jp/the-westin-miyako-kyoto.html",
    "Hotel Okura Kyoto Okazaki Bettei": _B + "jp/hoteruokurajing-du-gang-qi-bie-di.html",
    "Suiran, a Luxury Collection Hotel, Kyoto": _B + "jp/suiran-luxury-collection-kyoto.html",
    # Singapore (each Booking.com page checked by hand, October 2026)
    "Marina Bay Sands": _B + "sg/marina-bay-sands.html",
    "Raffles Singapore": _B + "sg/raffles.html",
    "Pan Pacific Singapore": _B + "sg/panpacificsingapore.html",
    "The Fullerton Hotel Singapore": _B + "sg/the-fullerton-singapore.html",
    "The Warehouse Hotel": _B + "sg/the-warehouse.html",
    "Pan Pacific Orchard": _B + "sg/pan-pacific-orchard.html",
    # the former Mandarin Orchard; Booking.com's review pages still use the old "mandarin" slug
    "Hilton Singapore Orchard": _B + "sg/hilton-singapore-orchard.html",
    "YOTEL Singapore Orchard Road": _B + "sg/yotel-singapore-orchard-road.html",
    "PARKROYAL COLLECTION Pickering": _B + "sg/parkroyal-on-pickering.html",
    "The Clan Hotel Singapore": _B + "sg/the-clan-singapore.html",
    "Shangri-La Rasa Sentosa": _B + "sg/rasa-sentosa-resort-by-the-shangri-la.html",
    "Capella Singapore": _B + "sg/capella-singapore.html",
    # Taipei (each Booking.com page checked by hand, October 2026)
    "Regent Taipei": _B + "tw/the-regent-taipei.html",
    "The Okura Prestige Taipei": _B + "tw/the-okura-prestige-taipei.html",
    "Palais de Chine Hotel": _B + "tw/palais-de-chine.html",
    "citizenM Taipei North Gate": _B + "tw/citizenm-taipei-north-gate.html",
    "amba Taipei Ximending": _B + "tw/taipei-amba-ximending.html",
    # Booking.com titles it "Just Sleep - Ximending"
    "Just Sleep Taipei Ximending": _B + "tw/just-sleep-ximending.html",
    "Grand Hyatt Taipei": _B + "tw/grand-hyatt-taipei-taipei50.html",
    "W Taipei": _B + "tw/w-taipei.html",
    "Shangri-La Far Eastern, Taipei": _B + "tw/shangri-la-s-far-eastern-plaza-taipei.html",
    "Hotel Proverbs Taipei": _B + "tw/hotel-proverbs-taipei.html",
    "Grand View Resort Beitou": _B + "tw/grand-view-resort-beitou.html",
    "Hotel Royal Beitou": _B + "tw/royal-hotel-beitou.html",
    # Kuala Lumpur (each Booking.com page checked by hand, October 2026)
    "Mandarin Oriental, Kuala Lumpur": _B + "my/mandarin-oriental-kuala-lumpur.html",
    "Four Seasons Hotel Kuala Lumpur": _B + "my/four-seasons-kuala-lumpur.html",
    "Traders Hotel, Kuala Lumpur": _B + "my/traders-kuala-lumpur.html",
    "EQ Kuala Lumpur": _B + "my/eq.html",
    "Pavilion Hotel Kuala Lumpur Managed by Banyan Tree": _B + "my/pavilion-kuala-lumpur-managed-by-banyan-tree.html",
    "JW Marriott Hotel Kuala Lumpur": _B + "my/jw-marriott-kuala-lumpur.html",
    "Holiday Inn Express Kuala Lumpur City Centre": _B + "my/holiday-inn-express-kuala-lumpur-city-centre.html",
    "The Majestic Hotel Kuala Lumpur, Autograph Collection": _B + "my/the-majestic-kuala-lumpur.html",
    # opened 7 Aug 2025 in Merdeka 118
    "Park Hyatt Kuala Lumpur": _B + "my/park-hyatt-kuala-lumpur.html",
    "AnCasa Hotel Kuala Lumpur, Chinatown": _B + "my/ancasa-spa-kuala-lumpur.html",
    "Hilton Kuala Lumpur": _B + "my/hilton-kuala-lumpur.html",
    "Aloft Kuala Lumpur Sentral": _B + "my/aloft-kuala-lumpur-sentral.html",
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
