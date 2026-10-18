# Spark link check (daily, in the built-in browser)

Open a live stay guide, wait ~8 s, then run in javascript_tool:

```js
var ours=[].map.call(document.querySelectorAll('li > strong > a, a.gy-hotel-name, li > strong'),function(e){return e.textContent.trim()});
var sp=[].map.call(document.querySelectorAll('a[href*="product=lma"]'),function(a){var u=new URL(a.href);return {t:a.textContent.trim(), h:u.searchParams.get('hotelname'), addr:u.searchParams.get('address')}});
[sp.length, sp.filter(function(x){return x.h}).map(function(x){return x.t+' => '+x.addr+(ours.some(function(o){return o.indexOf(x.h)===0||x.h.indexOf(o)===0})?'  [ours]':'  [NOT OURS]')})]
```

Spark links carry `product=lma`; hotel links carry `hotelname=` and `address=<name>, <city>`.
`[ours]` = a hotel we verified (Rome's Hotel Panda resolved to booking.com/hotel/it/panda.html, correct).
`[NOT OURS]` = Spark matched a name we did not check: open it once and confirm the Booking.com page is
that property in that city; if wrong, ask Stay22 to exclude it, or link that mention ourselves.
