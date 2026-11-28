#!/usr/bin/env python3
# Copyright (C) 2026 The Dodobian authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build dodobian.org into site/public/.

The page is a Dodo Desktop: a dark glass panel, light windows in the Dodo Labwc theme and the lagoon
wallpaper behind them. Texts live in text/en.json and ru/text.json; images come from brand/.
Needs python3, ImageMagick 7 (magick) and rsvg-convert.
"""
import html, json, os, re, shutil, subprocess, sys

SITE = "https://dodobian.org"
GITHUB = "https://github.com/dodobian/dodobian"
HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.join(os.path.dirname(HERE), "brand")
OUT = os.path.join(HERE, "public")

T = {}
for _lang, _path in (("en", "text/en.json"), ("ru", "ru/text.json")):
    with open(os.path.join(HERE, _path), encoding="utf-8") as _f:
        T[_lang] = json.load(_f)
        T[_lang]["inside"] = [tuple(x) for x in T[_lang]["inside"]]

GH_ICON = '<svg aria-hidden="true" viewBox="0 0 16 16" width="20" height="20"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'

# Russian typography: a one- or two-letter word sticks to the next one, a dash to the word before it.
SHORT = re.compile("(?<![\\w<])([\u0410-\u044f\u0401\u0451]{1,2}) ")


def nb(x):
    if isinstance(x, str):
        return SHORT.sub("\\1\u00a0", x).replace(" \u2014", "\u00a0\u2014")
    if isinstance(x, (list, tuple)):
        return type(x)(nb(i) for i in x)
    return x


CSS = """
@font-face{font-family:"Nunito";font-style:normal;font-weight:400 900;font-display:swap;src:url(%(pre)sassets/fonts/nunito-latin.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:"Nunito";font-style:normal;font-weight:400 900;font-display:swap;src:url(%(pre)sassets/fonts/nunito-cyrillic.woff2) format("woff2");unicode-range:U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116}
/* Window colours are the Dodo theme roles (brand/palette.json, light variant); the bars follow a dark glass panel. */
:root{--jungle:#0E2620;--panel-fg:#E6EEE5;--panel-hover:rgba(230,238,229,.12);--win:#FBFCF8;--title:#EEF2EC;--title-on:#DCEBE5;--text:#0E2620;--muted:#56695E;--faint:#7B8A80;--border:#C9D5CB;--line:#D2DDD2;--primary:#0E6E73;--sel:#CBEAE5;--flame:#E8553A;--flame-hover:#D4472D;--lagoon:#1FB5A8;--palm:#1F6B45;--mango:#FFB347;--lime:#A6D608;--sage:#9DB8A0;--sand:#F3E7C9;--bar:#0D1919;--bar-glass:rgba(13,25,25,.78);--bar-glass-bottom:rgba(19,19,22,.75);--bar-fg:#C4DDD2;--bar-soft:#98C2AF;--bar-line:rgba(255,255,255,.07);--bar-module:rgba(255,255,255,.05);--bar-hover:rgba(255,255,255,.08);--bar-active:rgba(127,184,158,.2);
--display:"Nunito",ui-rounded,"SF Pro Rounded",system-ui,sans-serif;--body:"Nunito",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"JetBrains Mono","DejaVu Sans Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%%}
body{margin:0;background:var(--bar);color:var(--text);font:16.5px/1.55 var(--body)}
a{color:var(--primary)}img{max-width:100%%;display:block}
code{font:.9em var(--mono);background:rgba(14,110,115,.1);padding:.08em .35em;border-radius:5px}
:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
/* panel */
.panel{position:relative;z-index:1000;height:38px;display:flex;align-items:center;gap:4px;padding:0 8px;background:var(--bar);color:var(--bar-fg);font-size:14px;border-bottom:1px solid var(--bar-line)}
.panel a,.panel button{color:inherit;text-decoration:none;font:inherit;background:none;border:0;cursor:pointer;display:inline-flex;align-items:center;gap:8px;height:30px;padding:0 10px;border-radius:8px}
.panel a:hover,.panel button:hover{background:var(--bar-hover)}
.panel .menu{font-weight:800;letter-spacing:.01em}.panel .menu img{width:22px;height:22px}
.tasks{display:none;gap:4px;margin-left:8px}
.tasks button{max-width:180px;background:var(--bar-module)!important;border:1px solid var(--bar-line)!important;font-size:13px}.tasks button:hover{background:var(--bar-hover)!important}
.tasks button[aria-pressed="true"]{background:var(--bar-active)!important;border-color:rgba(127,184,158,.35)!important}
.panel .lang{display:inline-flex;margin:0 4px;border:1px solid var(--bar-line);border-radius:8px;overflow:hidden;background:var(--bar-module)}.panel .lang a{height:26px;padding:0 9px;border-radius:0;font-size:12.5px;font-weight:800;letter-spacing:.04em}.panel .lang a[aria-current]{background:var(--bar-active);color:#fff}.wallmark{position:absolute;z-index:1;right:14px;top:calc(38px + 56vw * 941 / 1672 - 52px);width:150px;pointer-events:none;filter:drop-shadow(0 1px 2px rgba(0,0,0,.55)) drop-shadow(0 3px 12px rgba(0,0,0,.45))}.wallmark img{width:100%%;height:auto}.panel .spacer{flex:1}.panel .clock{font-variant-numeric:tabular-nums;padding:0 10px;opacity:.9}
/* desktop */
.desk{position:relative;overflow:hidden;background:var(--bar)}
.wall{width:100%%;height:auto}
.wins{display:flex;flex-direction:column;gap:16px;padding:16px max(16px,env(safe-area-inset-left,0px)) 28px}.col{display:contents}#w-about{order:1}#w-inside{order:2}#w-progress{order:3}#w-term{order:4}
/* windows: Dodo Labwc theme */
.win{background:var(--win);border:1px solid var(--border);border-radius:12px;box-shadow:0 2px 12px rgba(14,38,32,.14);overflow:hidden;min-width:0}
.win.on{border-color:var(--primary);box-shadow:0 4px 20px rgba(14,38,32,.22)}
.win:not(.on){background:rgba(251,252,248,.88)}.win:not(.on) .tb{background:rgba(238,242,236,.88)}.term:not(.on) .wb{background:rgba(14,38,32,.9)}
.tb{height:34px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 4px 0 10px;background:var(--title);color:var(--muted);font-size:13.5px;font-weight:700;user-select:none}
.win.on .tb{background:var(--title-on);color:var(--text)}
.tb .ic{width:16px;height:16px}.tb .lb{text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tb .bt{display:none;justify-self:end;gap:2px}
.tb .bt button{width:26px;height:26px;border:0;border-radius:13px;background:none;color:var(--faint);display:grid;place-items:center;cursor:pointer;padding:0}
.win.on .tb .bt button{color:var(--text)}
.tb .bt button:hover{background:rgba(14,110,115,.15)}
.tb svg{width:12px;height:12px}
.wb{padding:22px 24px 24px}
.eyebrow{display:inline-block;font-size:12.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:3px 11px;border-radius:999px;background:rgba(255,179,71,.28);color:#7A4A00}
h1{font-family:var(--display);font-weight:900;font-size:clamp(32px,3.6vw,46px);line-height:1.08;letter-spacing:-.01em;margin:14px 0 12px;text-wrap:balance}
.lead{margin:0 0 6px;max-width:34em}.hint{display:none;margin:0;color:var(--muted);font-size:15px}
.btns{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.btn{display:inline-flex;align-items:center;gap:9px;font-weight:800;font-size:15.5px;text-decoration:none;padding:11px 18px;border-radius:10px;border:1px solid transparent;cursor:pointer;font-family:inherit}
.btn-primary{background:var(--flame);color:#fff}.btn-primary:hover{background:var(--flame-hover)}
.btn-secondary{background:#fff;color:var(--text);border-color:var(--border)}.btn-secondary:hover{border-color:var(--primary)}
.list{list-style:none;margin:0;padding:0;display:grid;gap:14px}
.list h2{font-size:16px;margin:0 0 2px;font-weight:800;display:flex;align-items:center;gap:9px}
.list p{margin:0;color:var(--muted);font-size:15px}
.dot{width:9px;height:9px;border-radius:50%%;flex:none}
.cols{display:grid;gap:14px}
.cols h2{font-size:12.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
.cols ul{list-style:none;margin:0;padding:0}.cols li{display:flex;gap:9px;padding:7px 0;border-bottom:1px solid var(--line);font-size:15px}
.cols li:last-child{border-bottom:0}.ok{color:var(--palm);font-weight:900}.nx{color:#C77700;font-weight:900}
.term .wb{background:var(--jungle);color:var(--panel-fg);font:14px/1.7 var(--mono);padding:16px 18px;overflow-x:auto}
.term p{margin:0;white-space:pre}.term .pr{color:var(--lime)}.term .er{color:#FF8A73}.term .cm{color:var(--sage)}.term a{color:#7FE0D6}
footer{color:var(--bar-soft);font-size:13px;padding:14px max(16px,env(safe-area-inset-left,0px));border-top:1px solid var(--bar-line);background:var(--bar)}
footer p{margin:2px 0}footer a{color:var(--bar-fg)}footer{text-align:center}footer .tm{font-size:11.5px;opacity:.8}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
/* wide screens: a real desktop */
@media (min-width:1100px){
 .desk{height:max(100vh,720px);height:max(100dvh,720px)}
 .panel{position:absolute;top:0;left:0;right:0;background:var(--bar-glass)}
 footer{position:absolute;left:0;right:0;bottom:0;z-index:1000;padding:6px 14px 7px;font-size:12.5px;line-height:1.45;background:var(--bar-glass-bottom)}footer p{margin:0}
 .wallmark{top:auto;bottom:62px;width:280px;right:3vw}
 .wallmark.alt{right:auto;left:calc(27vw + min(570px,39.5vw) - 280px)}
 .wall{position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover;object-position:0 100%%}
 .wins{position:absolute;inset:0;flex-direction:row;align-items:flex-start;gap:20px;padding:calc(38px + 3.5vh) 0 0 27vw}
 .col{display:flex;flex-direction:column;gap:16px;flex:none}
 .col-1{width:min(570px,39.5vw);align-items:flex-end}.col-2{width:min(384px,26.5vw)}
 #w-about{width:100%%}#w-term{width:min(400px,100%%)}#w-inside,#w-progress{width:100%%}
 #w-term .wb{font-size:13px}
 .js .tb{cursor:grab;touch-action:none}.js .dragging .tb{cursor:grabbing}
 .js .tb .bt,.js .tasks{display:flex}.js .hint{display:block}
 .win.max{left:0!important;top:38px!important;width:100%%!important;height:calc(100%% - 86px)!important;border-radius:0;display:flex;flex-direction:column}.win.max .wb{flex:1;overflow:auto}
}
@media (min-width:1700px){.wallmark{width:320px}.wallmark.alt{left:calc(27vw + min(570px,39.5vw) - 320px)}}
@media (min-width:2000px) and (min-height:1150px){.wins{zoom:1.3;padding-left:calc(27vw / 1.3);padding-top:calc((38px + 3.5vh) / 1.3)}}
@media (min-width:1100px) and (max-height:900px){
 h1{font-size:clamp(30px,3.1vw,40px);margin:10px 0 8px}.wb{padding:16px 20px 18px}.lead{font-size:15.5px}
 .btns{margin-top:14px}.list{gap:8px}.list p,.cols li{font-size:14.5px}.cols li{padding:3px 0}.cols{gap:6px}.cols h2{margin-bottom:4px}
 .wins{padding-top:calc(38px + 2.2vh)}.col{gap:12px}
}
@media (max-width:480px){.panel .clock{display:none}}
@media (max-width:1099px){.term p{white-space:pre-wrap;word-break:break-all}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

LANG_JS = """<script>try{var p=localStorage.getItem("lang"),l=(navigator.languages&&navigator.languages[0])||navigator.language||"";if(!p&&/^ru\\b/i.test(l)&&!/bot|crawl|spider|slurp|lighthouse|preview/i.test(navigator.userAgent))location.replace("ru/"+location.hash)}catch(e){}</script>"""
ICON_MIN = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 9.5h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
ICON_MAX = '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.2" y="2.2" width="7.6" height="7.6" rx="1.6" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
ICON_CLOSE = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'

JS = """
(function(){
  var d=document, root=d.documentElement; root.classList.add('js');
  var area=d.querySelector('.wins'), z=10, wide=matchMedia('(min-width:1100px)'), moved=false, frozen=false;
  var wins=[].slice.call(d.querySelectorAll('.win'));
  function focusWin(w){ wins.forEach(function(x){x.classList.toggle('on',x===w);}); w.style.zIndex=++z; sync(); }
  function sync(){ d.querySelectorAll('.tasks button').forEach(function(b){ var w=d.getElementById(b.dataset.win); b.setAttribute('aria-pressed', String(!w.hidden && w.classList.contains('on'))); }); }
  // The columns place the windows; then each window is pinned where it stands so it can be dragged alone.
  function freeze(){
    if(frozen||!wide.matches) return;
    var ar=area.getBoundingClientRect();
    var k=zk(); var pos=wins.map(function(w){ var r=w.getBoundingClientRect(); return [(r.left-ar.left)/k, (r.top-ar.top)/k, r.width/k]; });
    wins.forEach(function(w,i){ if(w.hidden) return; w.style.position='absolute'; w.style.left=pos[i][0]+'px'; w.style.top=pos[i][1]+'px'; w.style.width=pos[i][2]+'px'; });
    frozen=true; fit();
  }
  function fit(){ var desk=d.querySelector('.desk'), ar=area.getBoundingClientRect(), need=0;
    wins.forEach(function(w){ if(!w.hidden){ var r=w.getBoundingClientRect(); need=Math.max(need, r.bottom-ar.top); } });
    desk.style.minHeight=need+52>innerHeight ? (need+52)+'px' : '';
    var wm=d.querySelector('.wallmark'); wm.classList.remove('alt'); var m=wm.getBoundingClientRect();
    var hit=wins.some(function(w){ if(w.hidden) return false; var r=w.getBoundingClientRect(); return r.left<m.right+8&&r.right>m.left-8&&r.top<m.bottom+8&&r.bottom>m.top-8; });
    wm.classList.toggle('alt',hit); }
  function zk(){ var k=parseFloat(getComputedStyle(area).zoom); if(!k||k===1) return 1; var t=area.getBoundingClientRect().width/area.offsetWidth; return Math.abs(t-1)<.01 ? k : t; }
  function unfreeze(){ wins.forEach(function(w){ var zi=w.style.zIndex; w.removeAttribute('style'); w.style.zIndex=zi; w.classList.remove('max'); }); frozen=false; }
  wins.forEach(function(w){
    var tb=w.querySelector('.tb');
    w.addEventListener('pointerdown',function(){ focusWin(w); });
    tb.addEventListener('pointerdown',function(e){
      if(!wide.matches||e.button!==0||e.target.closest('button')||w.classList.contains('max')) return;
      freeze(); moved=true;
      var k=zk(), r=w.getBoundingClientRect(), ar=area.getBoundingClientRect(), dx=(e.clientX-r.left)/k, dy=(e.clientY-r.top)/k, W=ar.width/k, H=ar.height/k, rw=r.width/k;
      w.classList.add('dragging'); tb.setPointerCapture(e.pointerId);
      function mv(ev){ var x=(ev.clientX-ar.left)/k-dx, y=(ev.clientY-ar.top)/k-dy;
        x=Math.max(-rw+80,Math.min(W-80,x)); y=Math.max(38/k,Math.min(H-70/k,y));
        w.style.left=x+'px'; w.style.top=y+'px'; }
      function up(){ w.classList.remove('dragging'); tb.removeEventListener('pointermove',mv); tb.removeEventListener('pointerup',up); tb.removeEventListener('pointercancel',up); }
      tb.addEventListener('pointermove',mv); tb.addEventListener('pointerup',up); tb.addEventListener('pointercancel',up);
    });
    tb.addEventListener('dblclick',function(e){ if(wide.matches&&!e.target.closest('button')){ freeze(); w.classList.toggle('max'); } });
    w.querySelectorAll('[data-act]').forEach(function(b){ b.addEventListener('click',function(){
      freeze();
      if(b.dataset.act==='max'){ w.classList.toggle('max'); } else { w.hidden=true; w.classList.remove('on'); sync(); }
    }); });
  });
  d.querySelectorAll('.tasks button').forEach(function(b){ b.addEventListener('click',function(){
    var w=d.getElementById(b.dataset.win); freeze();
    if(!w.hidden && w.classList.contains('on')){ w.hidden=true; w.classList.remove('on'); sync(); }
    else { w.hidden=false; focusWin(w); }
  }); });
  d.querySelectorAll('[data-raise]').forEach(function(a){ a.addEventListener('click',function(e){
    var w=d.getElementById(a.dataset.raise); if(!w) return; w.hidden=false; focusWin(w);
    if(wide.matches) e.preventDefault();
  }); });
  wide.addEventListener('change',function(){ wins.forEach(function(w){ w.hidden=false; }); unfreeze(); moved=false; if(wide.matches) freeze(); });
  addEventListener('resize',function(){ if(!moved&&wide.matches){ unfreeze(); freeze(); } });
  d.querySelectorAll('.lang a').forEach(function(a){ a.addEventListener('click',function(){ try{ localStorage.setItem('lang',a.dataset.lang); }catch(e){} }); });
  var c=d.querySelector('.clock');
  function tick(){ c.textContent=new Date().toLocaleTimeString(root.lang,{hour:'2-digit',minute:'2-digit'}); }
  if(c){ c.hidden=false; tick(); setInterval(tick,15000); }
  focusWin(d.getElementById('w-about'));
  if(d.fonts&&d.fonts.ready){ d.fonts.ready.then(freeze); } else { freeze(); }
})();
"""


# The wallpaper: AVIF first, WebP for older browsers; the source art is 1672 px wide, so nothing larger.
WALL_WIDTHS = (1672, 960, 640)


def srcset(pre, ext):
    return ", ".join(f"{pre}assets/lagoon-{w}.{ext} {w}w" for w in sorted(WALL_WIDTHS))


def win(id_, title, body, t, pre, cls=""):
    return (f'<section class="win {cls}" id="{id_}" aria-labelledby="{id_}-t">'
            f'<div class="tb"><img class="ic" src="{pre}assets/favicon.svg" alt="" width="16" height="16">'
            f'<span class="lb" id="{id_}-t">{title}</span>'
            f'<span class="bt"><button type="button" data-act="min" title="{t["min"]}" aria-label="{t["min"]}">{ICON_MIN}</button>'
            f'<button type="button" data-act="max" title="{t["max"]}" aria-label="{t["max"]}">{ICON_MAX}</button>'
            f'<button type="button" data-act="close" title="{t["close"]}" aria-label="{t["close"]}">{ICON_CLOSE}</button></span></div>'
            f'<div class="wb">{body}</div></section>')


def page(lang):
    t = T[lang]
    if lang == "ru":
        t = {k: nb(v) for k, v in t.items()}
    o = T[t["other"]]
    pre = "" if lang == "en" else "../"
    url = SITE + t["path"]
    ld = [{"@context": "https://schema.org", "@type": "Organization", "name": "Dodobian", "url": SITE + "/",
           "logo": SITE + "/assets/apple-touch-icon.png", "sameAs": ["https://github.com/dodobian"]},
          {"@context": "https://schema.org", "@type": "WebSite", "name": "Dodobian", "url": SITE + "/", "inLanguage": ["en", "ru"]}]
    about = (f'<span class="eyebrow">{t["eyebrow"]}</span><h1>{t["h1"]}</h1><p class="lead">{t["lead"]}</p><p class="hint">{t["hint"]}</p>'
             f'<div class="btns"><a class="btn btn-primary" href="{GITHUB}">{GH_ICON}{t["gh"]}</a>'
             f'<a class="btn btn-secondary" href="#w-progress" data-raise="w-progress">{t["prog_btn"]}</a></div>')
    colours = ["var(--lagoon)", "var(--palm)", "var(--mango)", "var(--flame)"]
    inside = '<ul class="list">' + "".join(
        f'<li><h2><span class="dot" style="background:{c}"></span>{h}</h2><p>{p}</p></li>' for (h, p), c in zip(t["inside"], colours)) + '</ul>'
    progress = ('<div class="cols"><div><h2>' + t["done_h"] + '</h2><ul>' + "".join(f'<li><span class="ok">✓</span>{x}</li>' for x in t["done"]) +
                '</ul></div><div><h2>' + t["next_h"] + '</h2><ul>' + "".join(f'<li><span class="nx">→</span>{x}</li>' for x in t["next"]) + '</ul></div></div>')
    term = (f'<p><span class="pr">~$</span> sudo apt install dodobian-desktop</p><p class="er">{t["term_err"]}</p>'
            f'<p><span class="pr">~$</span> <span class="cm">{t["term_note"]}</span></p>'
            f'<p><span class="pr">~$</span> xdg-open <a href="{GITHUB}">{GITHUB}</a></p>')
    tasks = "".join(f'<button type="button" data-win="{w}">{n}</button>' for w, n in
                    (("w-about", t["about_t"]), ("w-inside", t["inside_t"]), ("w-progress", t["progress_t"]), ("w-term", t["term_t"])))
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t["title"]}</title>
<meta name="description" content="{html.escape(t["desc"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{SITE}/">
<link rel="alternate" hreflang="ru" href="{SITE}/ru/">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0E2620">
<link rel="icon" href="{pre}assets/favicon.ico" sizes="32x32">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{pre}assets/apple-touch-icon.png">
<link rel="preload" href="{pre}assets/fonts/nunito-{"latin" if lang == "en" else "cyrillic"}.woff2" as="font" type="font/woff2" crossorigin>
<meta property="og:type" content="website">
<meta property="og:site_name" content="Dodobian">
<meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["desc"])}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{t["locale"]}">
<meta property="og:locale:alternate" content="{o["locale"]}">
<meta property="og:image" content="{SITE}/assets/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Dodobian">
<meta name="twitter:card" content="summary_large_image">
{LANG_JS if lang == "en" else ""}<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS % {"pre": pre}}</style>
</head>
<body>
<div class="desk">
<header class="panel">
<a class="menu" href="{pre or './'}"><img src="{pre}assets/dmark-swirl.svg" alt="" width="22" height="22">{t["menu"]}</a>
<nav class="tasks" aria-label="{t["tasks"]}">{tasks}</nav>
<span class="spacer"></span>
<a href="{GITHUB}">{GH_ICON}<span>GitHub</span></a>
<span class="lang" role="group" aria-label="{t["lang_label"]}"><a href="{"./" if lang == "en" else "../"}" lang="en" hreflang="en" data-lang="en"{" aria-current=\"page\"" if lang == "en" else ""}>EN</a><a href="{"ru/" if lang == "en" else "./"}" lang="ru" hreflang="ru" data-lang="ru"{" aria-current=\"page\"" if lang == "ru" else ""}>RU</a></span>
<span class="clock" aria-label="{t["clock_label"]}" hidden></span>
</header>
<picture><source type="image/avif" srcset="{srcset(pre, "avif")}" sizes="100vw"><source type="image/webp" srcset="{srcset(pre, "webp")}" sizes="100vw">
<img class="wall" src="{pre}assets/lagoon-1672.webp" width="1672" height="941" alt="{html.escape(t["alt"])}" fetchpriority="high"></picture>
<div class="wallmark"><img src="{pre}assets/wordmark-wallpaper.svg" width="440" height="73" alt="Dodobian"></div>
<main class="wins">
<div class="col col-1">
{win("w-about", t["about_t"], about, t, pre, "on")}
{win("w-term", t["term_t"], term, t, pre, "term")}
</div>
<div class="col col-2">
{win("w-inside", t["inside_t"], inside, t, pre)}
{win("w-progress", t["progress_t"], progress, t, pre)}
</div>
</main>
<footer><p>{t["copy"]} <a href="{GITHUB}">{GITHUB.replace("https://", "")}</a></p><p class="tm">{t["tm"]}</p></footer>
</div>
<script>{JS}</script>
</body>
</html>
"""



def recolour_wordmark(text, d_body):
    """The wordmark for the wallpaper: light text and a bright D body; the D keeps its dark outline and its dodo."""
    s = open(os.path.join(BRAND, "svg", "wordmark-light.svg"), encoding="utf-8").read()
    i = s.index('<path fill="#1F6B45" d="M1247')            # the outlines of "odobian"
    s = s[:i] + s[i:].replace('fill="#1F6B45"', f'fill="{text}"', 1)
    p1 = s.index("<path d=", s.index('<svg x="0"'))            # D outline: stays dark, it edges the bright D
    e1 = s.index(">", p1)
    p2 = s.index("<path d=", e1)                               # D body
    e2 = s.index(">", p2)
    return s[:p2] + s[p2:e2].replace("#1F6B45", d_body) + s[e2:]


def run(*cmd):
    subprocess.run(cmd, check=True)


def build_assets(a):
    os.makedirs(os.path.join(a, "fonts"))
    for f in os.listdir(os.path.join(HERE, "assets", "fonts")):
        shutil.copy(os.path.join(HERE, "assets", "fonts", f), os.path.join(a, "fonts", f))
    shutil.copy(os.path.join(BRAND, "svg", "dmark-small.svg"), os.path.join(a, "favicon.svg"))
    shutil.copy(os.path.join(BRAND, "svg", "dmark-swirl.svg"), os.path.join(a, "dmark-swirl.svg"))
    with open(os.path.join(a, "wordmark-wallpaper.svg"), "w", encoding="utf-8") as f:
        f.write(recolour_wordmark("#F3E7C9", "#FFB347"))    # sand text, mango D
    art = os.path.join(BRAND, "art", "wallpaper-lagoon-dodo-mouse.png")
    for w in WALL_WIDTHS:
        run("magick", art, "-resize", f"{w}x", "-quality", "78", os.path.join(a, f"lagoon-{w}.webp"))
        run("magick", art, "-resize", f"{w}x", "-quality", "55", os.path.join(a, f"lagoon-{w}.avif"))
    run("magick", os.path.join(BRAND, "png", "dmark-small-16.png"), os.path.join(BRAND, "png", "dmark-32.png"), os.path.join(a, "favicon.ico"))
    tmp = os.path.join(a, ".tmp.png")
    run("rsvg-convert", "-w", "140", os.path.join(BRAND, "svg", "emblem.svg"), "-o", tmp)
    run("magick", "-size", "180x180", "xc:#F3E7C9", tmp, "-gravity", "center", "-composite", os.path.join(a, "apple-touch-icon.png"))
    # link preview, 1200x630: the wallpaper, a jungle gradient on the left, the light wordmark and the line
    run("rsvg-convert", "-w", "520", os.path.join(a, "wordmark-wallpaper.svg"), "-o", tmp)
    font = os.path.join(BRAND, "fonts", "Baloo2-ExtraBold.ttf")
    run("magick", art, "-resize", "1200x", "-gravity", "center", "-crop", "1200x630+0+0", "+repage",
        "(", "-size", "630x1200", "gradient:rgba(14,38,32,0.92)-rgba(14,38,32,0)", "-rotate", "-90", ")", "-gravity", "west", "-composite",
        tmp, "-gravity", "northwest", "-geometry", "+64+70", "-composite",
        "-font", font, "-pointsize", "46", "-fill", "#F3E7C9", "-annotate", "+68+200", "The dodo is back.",
        "-pointsize", "30", "-fill", "#9DB8A0", "-annotate", "+70+256", "dodobian.org",
        "-strip", "-quality", "85", os.path.join(a, "og.jpg"))
    os.remove(tmp)


ROBOTS = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
SITEMAP = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "".join(f"  <url>\n    <loc>{SITE}{p}</loc>\n"
                     f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/"/>\n'
                     f'    <xhtml:link rel="alternate" hreflang="ru" href="{SITE}/ru/"/>\n'
                     f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>\n  </url>\n' for p in ("/", "/ru/"))
           + "</urlset>\n")


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(OUT, "ru"))
    build_assets(os.path.join(OUT, "assets"))
    for lang in ("en", "ru"):
        with open(os.path.join(OUT, "index.html" if lang == "en" else "ru/index.html"), "w", encoding="utf-8") as f:
            f.write(page(lang))
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write(ROBOTS)
    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write(SITEMAP)
    print("built", OUT)


if __name__ == "__main__":
    main()
