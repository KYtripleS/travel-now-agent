"""Ready Score Pro: build the paid workbook, one offline HTML file (2026-11-20 rebuild).

The earlier workbook file was lost, so this rebuilds a simpler one. Destination data comes from the
free Ready Score on the homepage (site/index.html, `var DEST = {...}`), so the paid file never covers
fewer places than the free tool. A few dated entry notes come from the facts ledger's claims, quoted
with the month they were checked.

Writes products/ready-score-pro.html. products/ is gitignored and never copied to site/ or docs/: the
file is sold, so it is uploaded to the checkout service by hand.

usage: .venv/bin/python ops/build_pro_workbook.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "products" / "ready-score-pro.html"
CHECKED = "2026-11"          # month the destination notes were last read
VERSION = "2026.11"

# Standard plug types (IEC letters), for the packing item. Dubai uses G (C and D also found).
PLUGS = {
    "Japan": "A/B", "South Korea": "C/F", "Taiwan": "A/B", "Hong Kong": "G", "Thailand": "A/B/C/O",
    "Vietnam": "A/C/F", "Singapore": "G", "Malaysia": "G", "Indonesia": "C/F", "Philippines": "A/B/C",
    "Australia": "I", "New Zealand": "I", "China": "A/C/I", "India": "C/D/M", "Cambodia": "A/C/G",
    "Sri Lanka": "D/G/M", "Nepal": "C/D/M", "Maldives": "D/G", "France": "C/E", "Italy": "C/F/L",
    "Spain": "C/F", "United Kingdom": "G", "Germany": "C/F", "Switzerland": "C/J", "Greece": "C/F",
    "Portugal": "C/F", "Netherlands": "C/F", "Turkey": "C/F", "USA": "A/B", "Canada": "A/B",
    "Mexico": "A/B", "Brazil": "C/N", "Peru": "A/C", "Dubai": "G", "Egypt": "C/F", "Morocco": "C/E",
}
SCHENGEN = {"France", "Italy", "Spain", "Germany", "Switzerland", "Greece", "Portugal", "Netherlands"}


def dest_data() -> dict:
    s = (REPO / "site" / "index.html").read_text(encoding="utf-8")
    i = s.index("var DEST = ") + len("var DEST = ")
    j = s.index("};", i) + 1
    return json.loads(s[i:j])


def facts() -> dict[str, dict]:
    out = {}
    for f in (REPO / "data" / "facts").glob("*.json"):
        d = json.loads(f.read_text())
        for x in (d if isinstance(d, list) else d.get("facts", [])):
            out[x["id"]] = x
    return out


def notes(F: dict) -> dict[str, list[str]]:
    """Dated notes per destination, each a fact from the ledger in plain words."""
    def month(fid):
        c = F.get(fid, {}).get("checked", "")
        return {"10": "October", "11": "November", "09": "September"}.get(c[5:7], "") + " " + c[:4]
    n: dict[str, list[str]] = {}
    if "kr.keta.exemption-2026" in F:
        n["South Korea"] = [f"Korea has extended its temporary K-ETA exemption for 22 countries and regions, including the "
                            f"United States, Canada, the UK, Australia, New Zealand and Japan, to 31 December 2026; without a "
                            f"K-ETA you fill in an arrival card. (Checked {month('kr.keta.exemption-2026')}.)"]
    if "gb.eta" in F:
        n["United Kingdom"] = [f"A UK ETA costs £20 and lasts 2 years or until the passport expires. Decisions usually come "
                               f"within a day but can take up to 3 working days, and every traveller, children too, needs one. "
                               f"British and Irish passport holders do not. (Checked {month('gb.eta')}.)"]
    if "ca.eta" in F:
        n["Canada"] = [f"Visa-exempt visitors flying to or through Canada need an eTA: CAN$7, most approved within minutes. "
                       f"US citizens need neither a visa nor an eTA. (Checked {month('ca.eta')}.)"]
    eu = []
    if "eu.ees.registration" in F:
        eu.append(f"The EU's Entry/Exit System registers non-EU short-stay visitors with fingerprints and a photo at the "
                  f"border, gradually replacing passport stamps. (Checked {month('eu.ees.registration')}.)")
    if "eu.etias.status" in F:
        eu.append(f"ETIAS, the EU travel authorisation, was not in operation and took no applications; the EU says it "
                  f"will announce the start date several months ahead, and the fee will be €20. "
                  f"(Checked {month('eu.etias.status')}.)")
    for c in SCHENGEN:
        n[c] = eu
    return n


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Ready Score Pro · Gently Yonder</title>
<style>
:root{--navy:#172033;--gold:#C9A84C;--paper:#F8F4E9;--ink:#1d2433;--muted:#5b6476;--red:#b3261e;--green:#2e7d4f;--line:rgba(23,32,51,.14)}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 Georgia,serif}
header{background:var(--navy);color:#fff;padding:18px 16px}header .in,main{max-width:860px;margin:0 auto}
header h1{margin:0;font-size:1.35rem;letter-spacing:-.01em}header p{margin:4px 0 0;color:#d8d2c0;font:13px/1.4 system-ui,sans-serif}
main{padding:12px 16px 60px}h2{font-size:1.15rem;margin:26px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
label,button,input,select,.ui{font:14px/1.3 system-ui,-apple-system,sans-serif}
input,select{padding:7px 8px;border:1px solid var(--line);border-radius:4px;background:#fff;max-width:100%}
button{padding:7px 12px;border:1px solid var(--navy);background:#fff;color:var(--navy);border-radius:4px;cursor:pointer}
button.primary{background:var(--navy);color:#fff}button.link{border:0;background:none;color:var(--muted);padding:2px 4px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0}.row>label{display:flex;flex-direction:column;gap:3px}
.banner{padding:10px 12px;border-left:3px solid var(--gold);background:#fff;margin:10px 0;font:14px/1.45 system-ui,sans-serif}
.banner.bad{border-color:var(--red)}
.score{display:flex;gap:16px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px;margin:12px 0}
.dial{width:92px;height:92px;border-radius:50%;display:grid;place-items:center;font:700 22px system-ui,sans-serif;flex:none}
.score .msg{font:14px/1.45 system-ui,sans-serif}.score .msg b{display:block;font-size:16px}
.cat h3{font:600 15px system-ui,sans-serif;margin:16px 0 4px;color:var(--navy)}
.item{display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px dashed var(--line)}
.item input{margin-top:4px}.item .t{flex:1}.item .due{font:12px system-ui,sans-serif;color:var(--muted);white-space:nowrap}
.item .due.late{color:var(--red);font-weight:600}.item a{color:#0B63D6}.blk{font:11px system-ui,sans-serif;color:var(--red);border:1px solid var(--red);border-radius:3px;padding:0 4px;margin-left:4px}
.done .t{color:var(--muted);text-decoration:line-through}
table{width:100%;border-collapse:collapse;font:14px system-ui,sans-serif}td,th{padding:6px;border-bottom:1px solid var(--line);text-align:left}
.note{font:13px/1.45 system-ui,sans-serif;color:var(--muted)}.warn{color:var(--red);font-weight:600}.ok{color:var(--green)}
@media print{header,button,.noprint,input[type=file]{display:none!important}body{background:#fff}.item{break-inside:avoid}}
</style>
</head>
<body>
<header><div class="in"><h1>Ready Score Pro</h1><p>Gently Yonder · version __VERSION__ · destination notes checked __CHECKED_TEXT__ · saved only in this browser</p></div></header>
<main>
<div id="storageWarn" class="banner bad" hidden>Your browser is not saving this workbook (a private window, or storage that is full). Use "Download backup" before you close it, or open the file in a normal window.</div>
<div id="staleWarn" class="banner bad" hidden></div>

<div class="row noprint ui">
  <label>Trip <select id="tripSel"></select></label>
  <button id="newTrip">New trip</button><button id="renameTrip">Rename</button><button id="delTrip">Delete trip</button>
</div>

<h2>Your trip</h2>
<div class="row">
  <label>Destination <select id="dest"></select></label>
  <label>Trip style <select id="style"><option value="city">City</option><option value="beach">Beach</option><option value="nature">Nature</option><option value="family">Family</option><option value="business">Business</option></select></label>
  <label>Leaving <input type="date" id="depart"></label>
  <label>Back home <input type="date" id="ret"></label>
</div>
<div id="destNotes"></div>

<div class="score" id="score"></div>

<h2>What is due</h2>
<div id="dueList" class="ui"></div>

<h2>Checklist</h2>
<p class="note">Each item says when to do it, counted back from the day you leave. Items marked <span class="blk">stops a trip</span> are the ones that can stop you boarding or entering: the score stays red until they are done.</p>
<div id="checklist"></div>
<div class="row noprint">
  <input id="cText" placeholder="Add your own check" style="flex:1;min-width:200px">
  <label>days before <input id="cDays" type="number" value="7" min="0" style="width:70px"></label>
  <button id="cAdd">Add</button>
</div>

<h2>Passports</h2>
<p class="note">Many countries want your passport valid for six months after you leave them. Each passport is checked against your return date.</p>
<div id="passports"></div>
<div class="row noprint"><input id="pName" placeholder="Traveller"><input id="pExp" type="date"><button id="pAdd">Add passport</button></div>

<h2>Bookings and references</h2>
<div id="bookings"></div>
<div class="row noprint">
  <select id="bKind"><option>Flight</option><option>Hotel</option><option>Train</option><option>Tour</option><option>Insurance</option><option>Other</option></select>
  <input id="bWhat" placeholder="What"><input id="bDate" type="date"><input id="bRef" placeholder="Reference"><button id="bAdd">Add booking</button>
</div>

<h2>Money: estimate and what you spent</h2>
<div class="row"><label>Currency <input id="cur" value="USD" style="width:80px"></label><label>Estimate for the trip <input id="est" type="number" min="0" style="width:140px"></label></div>
<div id="spent"></div>
<div class="row noprint"><input id="sWhat" placeholder="Spent on"><input id="sAmt" type="number" min="0" step="0.01" placeholder="Amount" style="width:120px"><button id="sAdd">Add</button></div>

<h2>Packing</h2>
<div class="row noprint"><button id="starter">Load the starter list for this trip</button><span class="note">Adds only what is missing; never removes your own items.</span></div>
<div id="packing"></div>
<div class="row noprint"><input id="kText" placeholder="Add an item"><button id="kAdd">Add</button></div>

<h2 class="noprint">Keep it safe</h2>
<div class="row noprint"><button id="backup" class="primary">Download backup</button><label class="ui">Restore a backup <input type="file" id="restore" accept="application/json"></label><button id="print">Print or save as PDF</button></div>
<p class="note">Ready Score Pro is preparation guidance, not legal or immigration advice, and it does not guarantee entry anywhere. Rules change: confirm entry requirements for your nationality with the official source before you travel. Guides linked here are on gentlyyonder.com.</p>
</main>
<script>
(function(){
"use strict";
var SITE="https://gentlyyonder.com/";
var DEST=__DEST__;
var PLUGS=__PLUGS__;
var NOTES=__NOTES__;
var CHECKED="__CHECKED__";
var KEY="gy_rsp_v1";
function $(id){return document.getElementById(id);}
function el(tag,attrs,text){var e=document.createElement(tag);if(attrs)for(var k in attrs){if(k==="class")e.className=attrs[k];else e.setAttribute(k,attrs[k]);}if(text!=null)e.textContent=text;return e;}
function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,7);}
function today(){var d=new Date();d.setHours(0,0,0,0);return d;}
function parse(s){if(!s)return null;var p=s.split("-");return new Date(+p[0],+p[1]-1,+p[2]);}
function days(a,b){return Math.round((b-a)/864e5);}
function fmt(d){return d.toLocaleDateString(undefined,{day:"numeric",month:"short",year:"numeric"});}

/* staleness: the notes carry the month they were checked */
(function(){var p=CHECKED.split("-"),c=new Date(+p[0],+p[1]-1,1);var age=days(c,today());
  if(age>180){var w=$("staleWarn");w.hidden=false;w.textContent="These destination notes were checked in "+c.toLocaleDateString(undefined,{month:"long",year:"numeric"})+", more than six months ago. A downloaded file cannot update itself: check each entry rule with the official source before you travel.";}})();

var state;
function blankTrip(name){return{id:uid(),name:name||"My trip",dest:"Japan",style:"city",depart:"",ret:"",done:{},custom:[],people:[],bookings:[],cur:"USD",est:"",spent:[],packing:[]};}
function load(){try{var s=JSON.parse(localStorage.getItem(KEY)||"null");if(s&&s.trips&&s.trips.length)return s;}catch(e){}
  var t=blankTrip();return{trips:[t],current:t.id};}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state));$("storageWarn").hidden=true;}catch(e){$("storageWarn").hidden=false;}}
state=load();
function trip(){for(var i=0;i<state.trips.length;i++)if(state.trips[i].id===state.current)return state.trips[i];state.current=state.trips[0].id;return state.trips[0];}

function items(t){
  var d=DEST[t.dest]||{};var L=[];
  function add(id,cat,text,daysB,link,blocker){L.push({id:id,cat:cat,text:text,days:daysB,link:link||null,blocker:!!blocker});}
  add("passport","Documents","Passport valid for the whole trip, and for six months after it where the country asks",90,null,true);
  add("visa","Documents","Visa need checked for your nationality",60,null,true);
  add("entry","Documents",d.eta||"Entry rules checked for your passport",21,d.etaUrl||null,true);
  add("copies","Documents","Passport photo page saved offline and on paper",7);
  add("insurance","Health and cover","Travel insurance bought, with medical cover abroad",45,SITE+"articles/best-travel-insurance-2026.html",true);
  add("meds","Health and cover","Prescriptions packed in their original boxes",7);
  add("flights","Bookings","Flights booked",60);
  add("firstnight","Bookings","First night's bed booked",30,SITE+"stay/index.html",true);
  add("transfer","Bookings","Way from the airport to the first bed decided",7,d.trans?SITE+d.trans:null);
  add("card","Money","A card that works abroad, and your bank told if it needs to be",14);
  add("cash","Money","A little local cash, or a plan for the first cash machine",3);
  add("esim","Connectivity","eSIM or SIM bought and installed before you fly",7,SITE+"articles/best-travel-esim-2026.html");
  add("maps","Connectivity","Offline map of where you land",2);
  add("plug","Packing","Plug adapter: type "+(PLUGS[t.dest]||"check for your destination"),5);
  add("packlist","Packing","Packing list done",2,d.pack?SITE+d.pack:null);
  add("address","Arrival day","First address saved offline, for the arrival card and the taxi",2);
  if(d.transit)add("transit","Arrival day",d.transit,1,d.trans?SITE+d.trans:null);
  add("guide","Arrival day","Read our guide for "+(d.name||t.dest),14,d.guide?SITE+d.guide:null);
  if(t.style==="family"){add("kids-docs","Documents","Children's passports and any consent letter checked",60,null,true);add("kids-seat","Bookings","Seats together and child fares checked",30);}
  if(t.style==="business"){add("biz-visa","Documents","Business-visit rules checked (some visas do not allow work)",45,null,true);add("biz-power","Packing","Laptop charger and a spare adapter",3);}
  if(t.style==="beach"){add("sun","Packing","Reef-safe sunscreen and a hat",5);}
  if(t.style==="nature"){add("boots","Packing","Shoes worn in before the trip",14);add("weather","Arrival day","Weather and trail conditions checked",1);}
  t.custom.forEach(function(c){add(c.id,"Your own checks",c.text,c.days,null,false);});
  return L;
}

function render(){
  var t=trip();
  var sel=$("tripSel");sel.innerHTML="";state.trips.forEach(function(x){var o=el("option",{value:x.id},x.name);if(x.id===t.id)o.selected=true;sel.appendChild(o);});
  var ds=$("dest");if(!ds.options.length){Object.keys(DEST).forEach(function(k){ds.appendChild(el("option",{value:k},DEST[k].name||k));});}
  ds.value=t.dest;$("style").value=t.style;$("depart").value=t.depart;$("ret").value=t.ret;$("cur").value=t.cur;$("est").value=t.est;
  var dn=$("destNotes");dn.innerHTML="";(NOTES[t.dest]||[]).forEach(function(n){dn.appendChild(el("div",{class:"banner"},n));});
  var L=items(t),dep=parse(t.depart),ret=parse(t.ret),now=today();
  var phase=!dep?"plan":(now<dep?"before":(ret&&now>ret?"after":"during"));
  /* checklist */
  var cl=$("checklist");cl.innerHTML="";var cats={};
  L.forEach(function(it){(cats[it.cat]=cats[it.cat]||[]).push(it);});
  Object.keys(cats).forEach(function(c){var box=el("div",{class:"cat"});box.appendChild(el("h3",null,c));
    cats[c].forEach(function(it){var done=!!t.done[it.id];var row=el("div",{class:"item"+(done?" done":"")});
      var cb=el("input",{type:"checkbox"});cb.checked=done;cb.addEventListener("change",function(){if(cb.checked)t.done[it.id]=1;else delete t.done[it.id];save();render();});
      row.appendChild(cb);var tx=el("span",{class:"t"});
      if(it.link){var a=el("a",{href:it.link,target:"_blank",rel:"noopener"},it.text);tx.appendChild(a);}else tx.textContent=it.text;
      if(it.blocker)tx.appendChild(el("span",{class:"blk"},"stops a trip"));row.appendChild(tx);
      var due=el("span",{class:"due"},it.days+" days before");
      if(dep){var dd=new Date(dep);dd.setDate(dd.getDate()-it.days);due.textContent="by "+fmt(dd);if(!done&&dd<now&&phase==="before")due.className="due late";}
      row.appendChild(due);
      if(it.cat==="Your own checks"){var x=el("button",{class:"link noprint"},"remove");x.addEventListener("click",function(){t.custom=t.custom.filter(function(c){return c.id!==it.id;});delete t.done[it.id];save();render();});row.appendChild(x);}
      box.appendChild(row);});cl.appendChild(box);});
  /* score */
  var total=L.length,nd=L.filter(function(i){return t.done[i.id];}).length,pct=total?Math.round(nd/total*100):0;
  var open=L.filter(function(i){return i.blocker&&!t.done[i.id];});
  var pw=passportProblems(t);
  var sc=$("score");sc.innerHTML="";var bad=open.length||pw.length;
  var dial=el("div",{class:"dial"},pct+"%");var col=bad?"var(--red)":(pct===100?"var(--green)":"var(--gold)");
  dial.style.background="radial-gradient(#fff 60%, transparent 61%), conic-gradient("+col+" "+pct*3.6+"deg, rgba(23,32,51,.08) 0)";
  var msg=el("div",{class:"msg"});
  if(phase==="after"){msg.appendChild(el("b",null,"Trip done"));msg.appendChild(document.createTextNode("Welcome home. Start a new trip for the next one."));}
  else if(bad){msg.appendChild(el("b",{class:"warn"},"Not ready yet"));msg.appendChild(document.createTextNode("Still open: "+open.map(function(i){return i.text;}).concat(pw).join("; ")+"."));}
  else if(pct===100){msg.appendChild(el("b",{class:"ok"},"Ready"));msg.appendChild(document.createTextNode("Everything on your list is done."));}
  else{msg.appendChild(el("b",null,"On track"));msg.appendChild(document.createTextNode("The checks that can stop a trip are done; "+(total-nd)+" smaller items left."));}
  sc.appendChild(dial);sc.appendChild(msg);
  /* due */
  var dl=$("dueList");dl.innerHTML="";
  if(phase==="plan")dl.appendChild(el("p",{class:"note"},"Set the day you leave and this becomes a plan: only what is due, most overdue first."));
  else if(phase==="after")dl.appendChild(el("p",{class:"note"},"This trip is over, so nothing is due."));
  else{var openI=L.filter(function(i){return !t.done[i.id];});
    if(phase==="during")openI=openI.filter(function(i){return i.days<=2||i.blocker;});
    openI.sort(function(a,b){return b.days-a.days;});
    var shown=openI.filter(function(i){var dd=new Date(dep);dd.setDate(dd.getDate()-i.days);return phase==="during"||days(now,dd)<=14;});
    if(!shown.length)dl.appendChild(el("p",{class:"note"},"Nothing due in the next two weeks."));
    var ul=el("ul");shown.forEach(function(i){var dd=new Date(dep);dd.setDate(dd.getDate()-i.days);var late=dd<now&&phase==="before";
      var li=el("li",null,i.text+" ");li.appendChild(el("span",{class:late?"warn":"note"},late?"(overdue since "+fmt(dd)+")":"(by "+fmt(dd)+")"));ul.appendChild(li);});
    dl.appendChild(ul);
    if(phase==="before")dl.insertBefore(el("p",{class:"note"},days(now,dep)+" days until you leave."),dl.firstChild);}
  /* passports */
  var pp=$("passports");pp.innerHTML="";
  if(!t.people.length)pp.appendChild(el("p",{class:"note"},"No passports added yet."));
  t.people.forEach(function(p){var r=el("div",{class:"item"});var e=parse(p.exp);var s=el("span",{class:"t"},p.name+": expires "+(e?fmt(e):"?")+" ");
    var st=passportStatus(p,t);s.appendChild(el("span",{class:st[0]},st[1]));r.appendChild(s);
    var x=el("button",{class:"link noprint"},"remove");x.addEventListener("click",function(){t.people=t.people.filter(function(q){return q!==p;});save();render();});r.appendChild(x);pp.appendChild(r);});
  /* bookings */
  var bk=$("bookings");bk.innerHTML="";var bs=t.bookings.slice().sort(function(a,b){return (a.date||"9").localeCompare(b.date||"9");});
  if(!bs.length)bk.appendChild(el("p",{class:"note"},"No bookings yet."));else{var tb=el("table");var h=el("tr");["Date","Type","What","Reference",""].forEach(function(c){h.appendChild(el("th",null,c));});tb.appendChild(h);
    bs.forEach(function(b){var r=el("tr");r.appendChild(el("td",null,b.date?fmt(parse(b.date)):""));r.appendChild(el("td",null,b.kind));r.appendChild(el("td",null,b.what));r.appendChild(el("td",null,b.ref));
      var c=el("td");var x=el("button",{class:"link noprint"},"remove");x.addEventListener("click",function(){t.bookings=t.bookings.filter(function(q){return q!==b;});save();render();});c.appendChild(x);r.appendChild(c);tb.appendChild(r);});bk.appendChild(tb);}
  /* money */
  var sp=$("spent");sp.innerHTML="";var sum=t.spent.reduce(function(a,s){return a+(+s.amt||0);},0);var est=+t.est||0;
  var tb2=el("table");t.spent.forEach(function(s){var r=el("tr");r.appendChild(el("td",null,s.what));r.appendChild(el("td",null,(+s.amt).toFixed(2)+" "+t.cur));
    var c=el("td");var x=el("button",{class:"link noprint"},"remove");x.addEventListener("click",function(){t.spent=t.spent.filter(function(q){return q!==s;});save();render();});c.appendChild(x);r.appendChild(c);tb2.appendChild(r);});
  if(t.spent.length)sp.appendChild(tb2);
  var line=el("p",{class:"ui"},"Spent "+sum.toFixed(2)+" "+t.cur+(est?" of "+est.toFixed(2)+": ":"."));
  if(est)line.appendChild(el("span",{class:sum>est?"warn":"ok"},sum>est?(sum-est).toFixed(2)+" over":(est-sum).toFixed(2)+" left"));sp.appendChild(line);
  /* packing */
  var pk=$("packing");pk.innerHTML="";if(!t.packing.length)pk.appendChild(el("p",{class:"note"},"Empty. Load the starter list or add your own."));
  t.packing.forEach(function(k){var r=el("div",{class:"item"+(k.done?" done":"")});var cb=el("input",{type:"checkbox"});cb.checked=!!k.done;
    cb.addEventListener("change",function(){k.done=cb.checked;save();render();});r.appendChild(cb);r.appendChild(el("span",{class:"t"},k.text));
    var x=el("button",{class:"link noprint"},"remove");x.addEventListener("click",function(){t.packing=t.packing.filter(function(q){return q!==k;});save();render();});r.appendChild(x);pk.appendChild(r);});
}
function passportStatus(p,t){var e=parse(p.exp),r=parse(t.ret)||parse(t.depart);if(!e)return["note","add the expiry date"];if(!r)return["note","add your dates to check it"];
  var six=new Date(r);six.setMonth(six.getMonth()+6);if(e<r)return["warn","expires before you come home"];if(e<six)return["warn","less than six months left after your return"];return["ok","fine for this trip"];}
function passportProblems(t){return t.people.filter(function(p){return passportStatus(p,t)[0]==="warn";}).map(function(p){return p.name+"'s passport";});}

function starter(t){var L=["Passport","Phone and charger","Plug adapter (type "+(PLUGS[t.dest]||"?")+")","Cards and a little cash","Medicines","Toiletries in a clear bag for security","Change of clothes in your hand luggage"];
  if(t.style==="beach")L=L.concat(["Swimwear","Reef-safe sunscreen","Hat","Light layer for air conditioning"]);
  if(t.style==="nature")L=L.concat(["Shoes worn in","Rain layer","Water bottle","Head torch"]);
  if(t.style==="city")L=L.concat(["Comfortable walking shoes","Day bag","Light layer"]);
  if(t.style==="family")L=L.concat(["Children's documents","Snacks for the flight","Small games or downloads"]);
  if(t.style==="business")L=L.concat(["Laptop and charger","Smart outfit","Business cards"]);
  if(t.dest==="Indonesia")L.push("Sarong for temple visits");
  if(t.dest==="USA")L.push("Small notes for tipping");
  return L;}

function bind(id,ev,fn){$(id).addEventListener(ev,fn);}
bind("tripSel","change",function(e){state.current=e.target.value;save();render();});
bind("newTrip","click",function(){var n=prompt("Name of the new trip","Next trip");if(n===null)return;var t=blankTrip(n.trim()||"Next trip");state.trips.push(t);state.current=t.id;save();render();});
bind("renameTrip","click",function(){var t=trip();var n=prompt("Rename this trip",t.name);if(n){t.name=n.trim()||t.name;save();render();}});
bind("delTrip","click",function(){if(state.trips.length===1){alert("This is your only trip. Start a new one first, then delete this.");return;}if(!confirm("Delete \""+trip().name+"\"? This cannot be undone unless you have a backup."))return;
  state.trips=state.trips.filter(function(x){return x.id!==state.current;});state.current=state.trips[0].id;save();render();});
["dest","style","depart","ret","cur","est"].forEach(function(k){bind(k,"change",function(e){trip()[k]=e.target.value;save();render();});});
bind("cAdd","click",function(){var v=$("cText").value.trim();if(!v)return;trip().custom.push({id:"c-"+uid(),text:v,days:Math.max(0,+$("cDays").value||0)});$("cText").value="";save();render();});
bind("pAdd","click",function(){var n=$("pName").value.trim()||"Traveller "+(trip().people.length+1);trip().people.push({name:n,exp:$("pExp").value});$("pName").value="";$("pExp").value="";save();render();});
bind("bAdd","click",function(){var w=$("bWhat").value.trim();if(!w)return;trip().bookings.push({kind:$("bKind").value,what:w,date:$("bDate").value,ref:$("bRef").value.trim()});$("bWhat").value="";$("bRef").value="";$("bDate").value="";save();render();});
bind("sAdd","click",function(){var a=+$("sAmt").value;if(!a)return;trip().spent.push({what:$("sWhat").value.trim()||"Spending",amt:a});$("sWhat").value="";$("sAmt").value="";save();render();});
bind("kAdd","click",function(){var v=$("kText").value.trim();if(!v)return;trip().packing.push({text:v,done:false});$("kText").value="";save();render();});
bind("starter","click",function(){var t=trip();var have={};t.packing.forEach(function(k){have[k.text.toLowerCase()]=1;});starter(t).forEach(function(s){if(!have[s.toLowerCase()])t.packing.push({text:s,done:false});});save();render();});
bind("backup","click",function(){var b=new Blob([JSON.stringify(state,null,1)],{type:"application/json"});var a=el("a",{href:URL.createObjectURL(b),download:"ready-score-pro-backup.json"});document.body.appendChild(a);a.click();a.remove();});
bind("restore","change",function(e){var f=e.target.files[0];if(!f)return;var r=new FileReader();r.onload=function(){try{var s=JSON.parse(r.result);if(!s.trips||!s.trips.length)throw 0;
  s.trips.forEach(function(t){var b=blankTrip();for(var k in b)if(t[k]===undefined)t[k]=b[k];});state=s;if(!state.current)state.current=s.trips[0].id;save();render();alert("Backup restored.");}catch(err){alert("That file is not a Ready Score Pro backup.");}};r.readAsText(f);});
bind("print","click",function(){window.print();});
save();render();
})();
</script>
</body>
</html>
"""


def main() -> None:
    D = dest_data()
    missing = [k for k in D if k not in PLUGS]
    if missing:
        raise SystemExit(f"no plug type for: {missing}")
    F = facts()
    y, m = CHECKED.split("-")
    month = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"][int(m) - 1]
    page = (TEMPLATE.replace("__DEST__", json.dumps(D, ensure_ascii=False))
            .replace("__PLUGS__", json.dumps(PLUGS))
            .replace("__NOTES__", json.dumps(notes(F), ensure_ascii=False))
            .replace("__CHECKED_TEXT__", f"{month} {y}")
            .replace("__CHECKED__", CHECKED)
            .replace("__VERSION__", VERSION))
    assert "</script" not in json.dumps(D)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"ready score pro: {OUT.relative_to(REPO)} ({len(D)} destinations, {len(page)//1024} KB)")


if __name__ == "__main__":
    main()
