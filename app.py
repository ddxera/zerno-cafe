# app.py — сайт кофейни на Flask: фото, состав напитков и корзина заказа
# Запуск: pip install flask  →  python app.py  →  открыть http://127.0.0.1:5000
#
# ФОТО: положи свои снимки в папку  static/img/  рядом с этим файлом
# (имена — как в поле "photo" ниже). Пока файла нет, сайт показывает рисунок.

import datetime
import json
import math
import os
import re
import threading

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# ---------- ДАННЫЕ ----------
# ingredients — список пар (ингредиент, количество); tint — цвет фона под фото
MENU = [
    {"name": "Эспрессо", "price": 2.50, "note": "Плотный и сладкий, с густой кремой",
     "photo": "espresso.jpg", "art": "espresso", "tint": "#F6D9A4", "size": "30 мл",
     "ingredients": [("Зёрна арабики", "9 г"), ("Вода", "30 мл")]},
    {"name": "Американо", "price": 3.00, "note": "Эспрессо, разбавленный горячей водой",
     "photo": "americano.jpg", "art": "americano", "tint": "#F1CF98", "size": "150 мл",
     "ingredients": [("Эспрессо", "30 мл"), ("Горячая вода", "120 мл")]},
    {"name": "Капучино", "price": 3.80, "note": "Молочная пена и тонкая пудра какао",
     "photo": "cappuccino.jpg", "art": "cappuccino", "tint": "#F8E0B3", "size": "180 мл",
     "ingredients": [("Эспрессо", "30 мл"), ("Молоко", "120 мл"), ("Молочная пена", "1 см"), ("Какао", "щепотка")]},
    {"name": "Флэт уайт", "price": 4.20, "note": "Двойной эспрессо и шёлковое молоко",
     "photo": "flatwhite.jpg", "art": "flatwhite", "tint": "#F3D7A0", "size": "170 мл",
     "ingredients": [("Двойной эспрессо", "60 мл"), ("Молоко", "110 мл")]},
    {"name": "Раф с лавандой", "price": 4.90, "note": "Сливки, ваниль и веточка лаванды",
     "photo": "raf.jpg", "art": "raf", "tint": "#E8D7E6", "size": "200 мл",
     "ingredients": [("Эспрессо", "30 мл"), ("Сливки 10%", "120 мл"), ("Лавандовый сироп", "15 мл"), ("Ваниль", "щепотка")]},
    {"name": "Фильтр-кофе", "price": 3.20, "note": "Сорт недели — спросите бариста",
     "photo": "filter.jpg", "art": "filter", "tint": "#EDCB92", "size": "250 мл",
     "ingredients": [("Молотый кофе", "15 г"), ("Вода 94 °C", "250 мл")]},
    {"name": "Круассан", "price": 2.80, "note": "Свежий, хрустящий, на сливочном масле",
     "photo": "croissant.jpg", "art": "croissant", "tint": "#FADB9A", "size": "90 г",
     "ingredients": [("Пшеничная мука", "тесто"), ("Сливочное масло 82%", "слои"), ("Молоко, дрожжи, соль", "тесто")]},
]

SHOP = {
    "name": "Зерно",
    "tagline": "Кофе, который успеваешь допить",
    "address": "Главная улица, 12",
    "hours": "Пн–Пт 7:30–18:00, Сб–Вс 9:00–17:00",
    "phone": "+31 00 000 0000",
}

# Какая часть фото видна в круглой плитке меню
POS = {"espresso": "50% 72%", "americano": "50% 55%", "cappuccino": "45% 58%", "flatwhite": "50% 25%",
       "raf": "50% 48%", "filter": "50% 45%", "croissant": "50% 72%"}

# ---------- РИСУНКИ НАПИТКОВ (вид сверху, SVG) ----------
def cup(r, liquid, art=""):
    """Рисует чашку на блюдце: r — размер чашки, liquid — цвет напитка, art — детали сверху."""
    big = r + 14
    return (
        '<svg viewBox="0 0 120 120" aria-hidden="true">'
        f'<circle cx="63" cy="65" r="{big}" fill="#1B2420" opacity=".12"/>'
        f'<circle cx="60" cy="60" r="{big}" fill="#fff" stroke="#D3D6D0" stroke-width="1.5"/>'
        f'<circle cx="60" cy="60" r="{big - 6}" fill="none" stroke="#E4E6E1"/>'
        f'<rect x="{57 + r}" y="53" width="20" height="14" rx="7" fill="#fff" stroke="#D3D6D0" stroke-width="1.5"/>'
        f'<circle cx="60" cy="60" r="{r}" fill="#fff" stroke="#D3D6D0" stroke-width="1.5"/>'
        f'<circle cx="60" cy="60" r="{r - 5}" fill="{liquid}"/>'
        f'{art}</svg>'
    )

SHINE = '<circle cx="51" cy="51" r="5" fill="#fff" opacity=".18"/>'
ARTS = {
    "espresso": cup(22, "#5B341D", '<circle cx="60" cy="60" r="11" fill="#9A5E34"/>' + SHINE),
    "americano": cup(30, "#6B3F24", '<circle cx="60" cy="60" r="19" fill="none" stroke="#A8744A" stroke-width="3" opacity=".6"/>' + SHINE),
    "cappuccino": cup(30, "#EADBC2", '<circle cx="60" cy="60" r="17" fill="#F7ECDA"/>'
                      '<circle cx="60" cy="60" r="22" fill="none" stroke="#6B3F24" stroke-width="1.6" stroke-dasharray="1 4" stroke-linecap="round"/>'),
    "flatwhite": cup(28, "#B98557", '<path d="M60 74C42 62 44 46 54 46c4 0 6 3 6 5 0-2 2-5 6-5 10 0 12 16-6 28z" fill="#F6EBDA"/>'
                     '<path d="M60 53v15" stroke="#B98557" stroke-width="1.5"/>'),
    "raf": cup(30, "#D9C8E4", '<circle cx="60" cy="60" r="14" fill="#F3ECF7"/>'
               '<path d="M26 97 46 80" stroke="#6E8B5B" stroke-width="2" stroke-linecap="round"/>'
               '<g fill="#8A6BB8"><ellipse cx="31" cy="92" rx="3" ry="5" transform="rotate(45 31 92)"/>'
               '<ellipse cx="37" cy="87" rx="3" ry="5" transform="rotate(45 37 87)"/>'
               '<ellipse cx="43" cy="82" rx="3" ry="5" transform="rotate(45 43 82)"/></g>'),
    "filter": cup(32, "#3E2415", '<circle cx="60" cy="60" r="24" fill="none" stroke="#6B3F24" stroke-width="2" opacity=".6"/>' + SHINE),
    "croissant": (
        '<svg viewBox="0 0 120 120" aria-hidden="true">'
        '<circle cx="63" cy="65" r="46" fill="#1B2420" opacity=".12"/>'
        '<circle cx="60" cy="60" r="46" fill="#fff" stroke="#D3D6D0" stroke-width="1.5"/>'
        '<circle cx="60" cy="60" r="40" fill="none" stroke="#E4E6E1"/>'
        '<g transform="translate(0 6)" fill="#D99A4E" stroke="#A9692A" stroke-width="1.5">'
        '<ellipse cx="29" cy="66" rx="11" ry="8" transform="rotate(-65 29 66)"/>'
        '<ellipse cx="91" cy="66" rx="11" ry="8" transform="rotate(65 91 66)"/>'
        '<ellipse cx="41" cy="52" rx="14" ry="10" transform="rotate(-35 41 52)"/>'
        '<ellipse cx="79" cy="52" rx="14" ry="10" transform="rotate(35 79 52)"/>'
        '<ellipse cx="60" cy="44" rx="17" ry="12"/></g>'
        '<g transform="translate(0 6)" stroke="#F2C27F" stroke-width="2" stroke-linecap="round" fill="none">'
        '<path d="M52 40q8-4 16 0"/><path d="M33 47q5-4 10-3"/><path d="M77 44q5-1 10 3"/></g></svg>'
    ),
}

# ---------- ДИЗАЙН (CSS) ----------
STYLE = """
/* Палитра и шрифты подобраны навыком UI/UX Pro Max: тёплый коричневый + кремовый, Playfair Display SC + Onest */
:root { --bg:#FEF3C7; --card:#FFFFFF; --primary:#92400E; --ink:#78350F; --muted:#7C5428; --line:rgba(120,53,15,.22);
  --serif:"Playfair Display SC",Georgia,"Times New Roman",serif; --sans:"Onest","Segoe UI",system-ui,sans-serif; }
* { box-sizing:border-box; }
html { scroll-padding-bottom:96px; scroll-behavior:smooth; }
body { margin:0; background:var(--bg); color:var(--ink); font:400 18px/1.6 var(--sans); }
.skip { position:absolute; left:-999px; top:8px; z-index:30; background:var(--card); color:var(--ink); padding:12px 16px; }
.skip:focus { left:8px; }
.wrap { max-width:840px; margin:0 auto; padding:0 24px; }

/* Шапка: большой цветной блок */
header { background:var(--primary); color:var(--bg); padding:56px 0 72px; }
.hero { display:grid; grid-template-columns:1fr 240px; gap:32px; align-items:center; }
header .name { font:700 24px var(--serif); letter-spacing:.04em; margin:0 0 40px; }
header h1 { font:700 clamp(36px,7vw,64px)/1.08 var(--serif); margin:0; }
header p.sub { margin:24px 0 0; font-size:20px; }
.hero-art { background:rgba(254,243,199,.16); border-radius:50%; padding:16px; aspect-ratio:1; }
.hero-art svg { width:100%; height:100%; }
.facts { background:var(--ink); color:var(--bg); }
.facts .wrap { display:grid; grid-template-columns:repeat(3,1fr); }
.facts p { margin:0; padding:20px 24px; font-size:16px; border-left:1px solid rgba(254,243,199,.25); }
.facts p:first-child { border-left:0; padding-left:0; }

section { padding:64px 0 8px; }
h2 { font:700 40px/1.15 var(--serif); margin:0 0 8px; }
.hint { margin:0 0 24px; color:var(--muted); font-size:16px; }

/* Меню: фото + название ..... цена + кнопка «Состав» */
.menu { list-style:none; margin:0; padding:0; border-top:2px solid var(--ink); }
.card { border-bottom:1px solid var(--line); padding:8px 0; }
.menu button.item { position:relative; display:grid; grid-template-columns:104px 1fr; gap:20px; align-items:center;
  width:100%; min-height:44px; text-align:left; cursor:pointer; background:transparent; color:var(--ink);
  border:0; padding:8px 60px 8px 8px; font:inherit; transition:background-color .2s; touch-action:manipulation; }
.menu button.item:hover { background:#FDE68A; }
.menu button.item:active { background:#FCD34D; }
.art { width:104px; height:104px; border-radius:8px; overflow:hidden; }
.art svg, .art img { width:100%; height:100%; object-fit:cover; display:block; }
.row { display:flex; align-items:baseline; gap:12px; }
.dots { flex:1; border-bottom:2px dotted var(--line); transform:translateY(-4px); }
.title { font:700 22px var(--serif); }
.price { font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }
.note { display:block; margin-top:4px; font-size:16px; color:var(--muted); }
.line { position:relative; }
.menu button.plus { position:absolute; right:8px; top:50%; margin-top:-22px; width:44px; height:44px; min-height:44px;
  padding:0; border-radius:50%; font-size:24px; line-height:1; }
.art { position:relative; }
.badge { position:absolute; left:6px; bottom:6px; z-index:1; background:var(--ink); color:var(--bg); font:700 12px var(--sans);
  letter-spacing:.06em; padding:2px 8px; border-radius:999px; }

/* Состав (стрелочка) */
details.comp { margin:0 0 8px 132px; }
details.comp summary { list-style:none; cursor:pointer; display:inline-flex; align-items:center; gap:8px;
  min-height:44px; font-weight:600; font-size:16px; color:var(--primary); }
details.comp summary::-webkit-details-marker { display:none; }
.chev { transition:transform .2s; }
details[open] .chev { transform:rotate(180deg); }
.ing { list-style:none; margin:0 0 8px; padding:12px 16px; background:var(--card); border-left:4px solid var(--primary); font-size:16px; }
.ing li { display:flex; justify-content:space-between; gap:12px; padding:4px 0; }
.ing li span:last-child { color:var(--muted); font-variant-numeric:tabular-nums; }
.ing .size { border-top:1px solid var(--line); margin-top:8px; padding-top:8px; font-weight:600; }

/* Заказ */
.cart-list { list-style:none; margin:0 0 16px; padding:0; }
.cart-list li { display:flex; align-items:center; gap:12px; padding:12px 0; border-bottom:2px solid var(--ink); }
.c-name { flex:1; font-weight:700; }
.c-sum { min-width:76px; text-align:right; font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }
.qty { display:flex; align-items:center; gap:4px; }
.qty button { min-width:44px; min-height:44px; padding:0; font-size:22px; line-height:1; }
.qty .n { min-width:28px; text-align:center; font-weight:700; font-variant-numeric:tabular-nums; }
.empty { color:var(--muted); margin:0 0 16px; }
.total { display:flex; justify-content:space-between; font:700 26px var(--serif); margin-bottom:24px; }
form { display:grid; gap:16px; max-width:440px; }
label { font-weight:600; font-size:16px; }
input { width:100%; min-height:48px; padding:12px 16px; font:inherit; border:2px solid var(--ink); background:var(--card); color:var(--ink); }
button { font:inherit; font-weight:700; min-height:48px; padding:12px 24px; cursor:pointer; background:var(--primary); color:#fff;
  border:2px solid var(--primary); transition:background-color .2s; touch-action:manipulation; }
button:hover { background:var(--ink); border-color:var(--ink); }
button:disabled { background:#CDBB9A; border-color:#CDBB9A; color:#5A4326; cursor:not-allowed; }
:focus-visible { outline:3px solid var(--primary); outline-offset:3px; }
a { color:var(--primary); font-weight:600; }

/* Плавающая кнопка «Заказ» */
.bar { position:fixed; left:50%; bottom:16px; transform:translateX(-50%); display:flex; align-items:center; gap:16px; z-index:20;
  min-height:48px; background:var(--ink); color:var(--bg); padding:12px 24px; border-radius:999px; text-decoration:none;
  box-shadow:0 6px 20px rgba(120,53,15,.4); font-variant-numeric:tabular-nums; }
.bar:focus-visible { outline-color:var(--bg); }
.bar[hidden] { display:none; }

footer { margin-top:80px; background:var(--ink); color:var(--bg); padding:48px 0 96px; font-size:16px; }
footer .wrap { display:grid; grid-template-columns:1fr 1fr; gap:24px; }
footer h3 { margin:0 0 8px; font:700 24px var(--serif); }
footer p { margin:4px 0; }

@media (max-width:640px) {
  .hero { grid-template-columns:1fr; } .hero-art { width:176px; order:-1; }
  .facts .wrap { grid-template-columns:1fr; } .facts p { border-left:0; padding:12px 0; }
  .menu button.item { grid-template-columns:88px 1fr; gap:16px; padding-right:56px; }
  .art { width:88px; height:88px; } details.comp { margin-left:112px; }
  footer .wrap { grid-template-columns:1fr; } h2 { font-size:32px; }
}
/* Окно 3D-просмотра */
body:has(dialog[open]) { overflow:hidden; }
dialog#viewer { width:min(92vw,720px); max-height:94vh; padding:0; border:0; background:var(--bg); color:var(--ink);
  box-shadow:0 24px 80px rgba(60,25,5,.5); overflow:auto; }
dialog#viewer::backdrop { background:rgba(60,25,5,.62); }
dialog#viewer[open] { animation:pop .38s cubic-bezier(.2,.9,.3,1.15); }
dialog#viewer[open]::backdrop { animation:fade .3s ease-out; }
@keyframes pop { from { opacity:0; transform:translateY(28px) scale(.94); } to { opacity:1; transform:none; } }
@keyframes fade { from { opacity:0; } to { opacity:1; } }
.v-head { display:flex; justify-content:space-between; align-items:center; gap:16px; padding:16px 16px 8px 24px; }
.v-head h3 { font:700 30px/1.15 var(--serif); margin:0; }
.v-close { width:44px; min-height:44px; padding:0; font-size:26px; line-height:1; }
.v-stage { position:relative; margin:0 16px; aspect-ratio:4/3; max-height:56vh; width:calc(100% - 32px); border-radius:8px; overflow:hidden;
  background:radial-gradient(circle at 50% 38%, #FFF8E1 0%, #F8E0B3 55%, #EDCB92 100%); }
#v-canvas { width:100%; height:100%; display:block; touch-action:none; cursor:grab; }
#v-canvas:active { cursor:grabbing; }
#v-fallback { position:absolute; inset:0; display:grid; place-items:center; }
#v-fallback[hidden], #v-canvas[hidden], .v-tools[hidden] { display:none; }
#v-fallback svg { width:58%; height:auto; }
#v-fallback img { width:100%; height:100%; object-fit:cover; }
.v-tools { position:absolute; right:12px; bottom:12px; display:flex; gap:8px; }
.v-tools button { width:44px; min-height:44px; padding:0; font-size:24px; line-height:1; }
.v-foot { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; padding:16px 24px 24px; }
.v-foot p { margin:0 0 4px; }
.v-help { color:var(--muted); font-size:15px; max-width:44ch; }
@media (prefers-reduced-motion:reduce) {
  html { scroll-behavior:auto; } * { transition:none !important; }
}

/* ===== Редизайн: тёмный эспрессо-фон, янтарный свет, редакторская типографика ===== */
:root { --bg:#0E0A08; --card:#1A120D; --primary:#F08A3C; --amber:#F2A24A; --ink:#F3E6D0; --muted:#BDA98F; --line:rgba(243,230,208,.16);
  --serif:"Cormorant Garamond","Playfair Display SC",Georgia,serif; --sans:"Onest","Segoe UI",system-ui,sans-serif; }
html { background:var(--bg); }
body { background:radial-gradient(120% 60% at 50% 0%,#2a170c 0%,var(--bg) 60%); overflow-x:hidden; }
body::after { content:""; position:fixed; inset:0; pointer-events:none; z-index:50; opacity:.07; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
button, .qty button, .v-close, .v-tools button { color:#1a0f08; }
button:disabled { color:#5A4326; }

/* Навигация-«стекло» */
.nav { position:fixed; top:16px; left:50%; transform:translateX(-50%); z-index:40; width:min(92vw,720px);
  display:flex; align-items:center; justify-content:space-between; gap:24px; padding:8px 8px 8px 24px;
  border:1px solid var(--line); border-radius:999px; background:rgba(20,13,9,.55); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); }
.logo { font:600 28px var(--serif); color:var(--ink); text-decoration:none; letter-spacing:.02em; }
.logo i { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--primary); margin-left:4px; }
.links { display:flex; gap:28px; }
.links a { color:var(--ink); text-decoration:none; font-weight:500; font-size:16px; opacity:.85; transition:color .2s,opacity .2s; }
.links a:hover { opacity:1; color:var(--amber); }
.pill { display:inline-flex; align-items:center; justify-content:center; min-height:44px; padding:0 26px; border-radius:999px;
  font-weight:600; text-decoration:none; transition:background-color .25s,color .25s,border-color .25s,transform .25s; }
.pill:hover { transform:translateY(-2px); }
.pill.solid, .nav .pill { background:var(--primary); color:#1a0f08; }
.pill.solid:hover, .nav .pill:hover { background:var(--ink); }
.pill.outline { border:1px solid var(--line); color:var(--ink); }
.pill.outline:hover { border-color:var(--ink); }

/* Первый экран: огромное слово-призрак, чашка поверх, свет горизонта */
.hero { position:relative; min-height:100svh; display:grid; align-content:center; padding:120px 0 64px; overflow:hidden; isolation:isolate; }
.hero::before { content:""; position:absolute; inset:0; z-index:-1; background:radial-gradient(520px circle at var(--mx,72%) var(--my,40%),rgba(240,138,60,.17),transparent 62%); }
.hero .wrap { max-width:1100px; width:100%; }
.ghost { position:absolute; left:50%; top:46%; transform:translate(-50%,-50%); z-index:-2; user-select:none; white-space:nowrap;
  font:700 clamp(150px,30vw,460px)/.8 var(--serif); letter-spacing:-.04em; color:rgba(243,230,208,.05); }
.arc { position:absolute; left:50%; bottom:-100vw; width:130vw; height:130vw; transform:translateX(-50%); border-radius:50%; z-index:-1;
  border-top:2px solid rgba(255,196,128,.75); background:radial-gradient(closest-side,#0a0604 80%,rgba(240,138,60,.5) 97%,transparent 100%);
  box-shadow:0 -40px 120px rgba(240,138,60,.35), inset 0 40px 80px rgba(240,138,60,.12); animation:glow 6s ease-in-out infinite alternate; }
@keyframes glow { to { box-shadow:0 -60px 160px rgba(240,138,60,.5), inset 0 60px 100px rgba(240,138,60,.2); } }
.hero-copy { position:relative; z-index:2; }
.kicker { font:500 14px var(--sans); letter-spacing:.14em; text-transform:uppercase; color:var(--amber); margin:0 0 20px; }
.hero h1 { font:300 clamp(52px,8.6vw,124px)/.94 var(--serif); letter-spacing:-.02em; margin:0; max-width:6.4em; }
h1 em, h2 em { font-style:italic; font-weight:400; color:var(--amber); }
.lead { max-width:34ch; font-size:19px; color:var(--muted); margin:28px 0 36px; }
.cta { display:flex; gap:12px; flex-wrap:wrap; }
.cup { position:absolute; right:max(2vw,calc((100vw - 1100px)/2)); top:50%; width:min(38vw,440px); aspect-ratio:1; margin-top:-24%; z-index:1;
  filter:drop-shadow(0 40px 60px rgba(0,0,0,.7)) drop-shadow(0 0 80px rgba(240,138,60,.25)); animation:float 7s ease-in-out infinite; }
.cup svg { width:100%; height:100%; }
@keyframes float { 50% { transform:translateY(-18px) rotate(3deg); } }
.hero .stats { list-style:none; display:flex; gap:56px; margin:0; padding:0; position:absolute; left:56px; right:auto; bottom:40px; z-index:2; }
.stats b { display:block; font:600 28px var(--sans); color:var(--ink); }
.stats span { color:var(--muted); font-size:15px; }

/* Бегущая строка с контурными буквами */
.marquee { overflow:hidden; border-block:1px solid var(--line); padding:18px 0; background:rgba(243,230,208,.02); }
.track { display:flex; width:max-content; animation:slide 45s linear infinite; }
.track span { font:italic 300 clamp(40px,6vw,76px)/1 var(--serif); padding:0 28px; white-space:nowrap; color:transparent; -webkit-text-stroke:1px rgba(243,230,208,.5); }
.track span::after { content:"✦"; font-style:normal; color:var(--amber); -webkit-text-stroke:0; margin-left:56px; font-size:.4em; vertical-align:middle; }
@keyframes slide { to { transform:translateX(-50%); } }

/* Заголовки и меню */
.wrap { max-width:960px; }
section { padding:96px 0 8px; }
h2 { font:300 clamp(44px,7vw,88px)/1 var(--serif); letter-spacing:-.02em; margin:0 0 12px; }
.menu button.item { grid-template-columns:144px 1fr; gap:28px; padding:20px 64px 20px 12px; }
.menu button.item:hover { background:transparent; }
.menu button.item:active { background:rgba(240,138,60,.12); }
.card { border-bottom:1px solid var(--line); transition:background .4s; }
.card:hover { background:linear-gradient(90deg,rgba(240,138,60,.09),transparent 70%); }
.art { width:144px; height:144px; border-radius:50% !important; background:radial-gradient(circle at 50% 40%,#3a2214,#140d09 70%) !important;
  box-shadow:0 0 0 1px var(--line),0 18px 40px rgba(0,0,0,.6); transition:transform .5s cubic-bezier(.2,.8,.2,1),box-shadow .5s; }
.card:hover .art { transform:scale(1.08) rotate(-6deg); box-shadow:0 0 0 1px var(--amber),0 24px 60px rgba(240,138,60,.28); }
.art svg { transform:scale(1.2); }
.badge { left:50%; bottom:8px; transform:translateX(-50%); }
.idx { display:block; font:600 12px var(--sans); letter-spacing:.16em; color:var(--amber); margin-bottom:4px; }
.title { font:400 clamp(28px,4vw,40px)/1.05 var(--serif); }
.price { font:600 20px var(--sans); color:var(--amber); }
.note { color:var(--muted); }
details.comp { margin:0 0 16px 184px; }
.ing { background:rgba(243,230,208,.05); border-left:2px solid var(--amber); }
.ing .size { border-top-color:var(--line); }

/* Заказ, подвал, окно 3D */
#order form { padding:28px; border:1px solid var(--line); border-radius:24px; background:rgba(243,230,208,.04); backdrop-filter:blur(10px); }
.cart-list li { border-bottom:1px solid var(--line); }
.c-sum { color:var(--amber); }
.total { font:400 38px var(--serif); }
input { background:rgba(243,230,208,.06); border:1px solid var(--line); border-radius:12px; }
input:focus-visible { outline-color:var(--amber); }
footer { margin-top:120px; background:#080504; color:var(--ink); border-top:1px solid var(--line); position:relative; overflow:hidden; padding:72px 0 120px; }
footer::before { content:"ЗЕРНО"; position:absolute; left:50%; bottom:-.22em; transform:translateX(-50%); pointer-events:none;
  font:700 clamp(120px,28vw,420px)/1 var(--serif); color:rgba(243,230,208,.04); }
footer .wrap { position:relative; }
footer h3 { font:400 30px var(--serif); }
footer p { color:var(--muted); }
dialog#viewer { border:1px solid var(--line); border-radius:20px; background:#140d09; box-shadow:0 30px 120px rgba(0,0,0,.8),0 0 80px rgba(240,138,60,.12); }
.v-stage { background:radial-gradient(circle at 50% 35%,#4a2a14 0%,#1c110a 60%,#100a07 100%); border-radius:14px; }
.v-head h3 { font:400 40px var(--serif); }


/* Бронь столов */
.dock { position:fixed; left:50%; bottom:16px; transform:translateX(-50%); z-index:20; display:flex; gap:10px; align-items:center; max-width:94vw; }
.dock .bar { position:static; transform:none; }
.book-btn { background:rgba(20,13,9,.75); color:var(--ink); border:1px solid var(--amber); border-radius:999px; min-height:48px; padding:12px 24px;
  backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); box-shadow:0 6px 20px rgba(0,0,0,.4); }
.book-btn:hover { background:var(--amber); color:#1a0f08; border-color:var(--amber); }
dialog#booking { width:min(94vw,860px); max-height:94vh; padding:0; border:1px solid var(--line); border-radius:20px; background:#140d09; color:var(--ink);
  box-shadow:0 30px 120px rgba(0,0,0,.8),0 0 80px rgba(240,138,60,.12); overflow:auto; }
dialog#booking::backdrop { background:rgba(60,25,5,.62); }
dialog#booking[open] { animation:pop .38s cubic-bezier(.2,.9,.3,1.15); }
select { width:100%; min-height:48px; padding:12px 16px; font:inherit; border:1px solid var(--line); border-radius:12px; background:rgba(243,230,208,.06); color:var(--ink); }
select option { background:#1a120d; color:var(--ink); }
input[type=date] { color-scheme:dark; }
.b-fields { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; padding:8px 24px 16px; }
.b-guests { display:flex; align-items:center; gap:12px; min-height:48px; font-weight:700; font-size:20px; }
.b-guests button { width:48px; padding:0; font-size:22px; }
.b-plan { padding:0 24px; }
.b-plan svg { width:100%; height:auto; display:block; background:rgba(243,230,208,.04); border:1px solid var(--line); border-radius:16px; }
.room { fill:none; stroke:rgba(243,230,208,.3); stroke-width:2; }
.win { fill:#8fb4c9; opacity:.7; } .door { fill:var(--amber); } .counter { fill:#2a1a10; stroke:rgba(243,230,208,.35); stroke-width:1.5; }
.deco { fill:var(--muted); font:600 11px var(--sans); letter-spacing:.14em; }
.tbl { cursor:pointer; outline:none; }
.tbl .hit { fill:transparent; stroke:none; }
.tbl .top { fill:#3a2214; stroke:var(--amber); stroke-width:2; transition:fill .2s; }
.tbl .chair, .tbl .bench { fill:#2a1a10; stroke:rgba(243,230,208,.45); stroke-width:1.5; }
.tbl .lbl { fill:var(--ink); font:700 14px var(--sans); pointer-events:none; }
.tbl:hover .top { fill:#6a3a1a; }
.tbl:focus-visible .hit { stroke:var(--amber); stroke-width:2; fill:rgba(240,138,60,.1); }
.tbl.sel .top { fill:var(--primary); } .tbl.sel .lbl { fill:#1a0f08; }
.tbl.taken, .tbl.small { cursor:not-allowed; opacity:.3; }
.tbl.taken .top { stroke:#999; stroke-dasharray:4 4; }
.b-info { margin:12px 24px; color:var(--muted); min-height:3em; }
#b-form { max-width:none; padding:0 24px; grid-template-columns:1fr 1fr; }
#b-form .wide { grid-column:1/-1; }
#b-form[hidden] { display:none; }
#b-msg { margin:0; padding:12px 24px 24px; min-height:1.5em; font-weight:600; }
#b-msg.ok { color:#9be28f; } #b-msg.err { color:#ff9a8a; }
@media (max-width:640px) { .b-fields, #b-form { grid-template-columns:1fr; } .dock { flex-wrap:wrap; justify-content:center; } }

/* Появление при прокрутке */
.js .reveal { opacity:0; transform:translateY(32px); transition:opacity .9s ease,transform .9s cubic-bezier(.2,.8,.2,1); }
.js .reveal.in { opacity:1; transform:none; }

@media (max-width:760px) {
  .links { display:none; } .nav { padding-left:20px; }
  .hero { padding-top:96px; } .cup { position:relative; right:auto; top:auto; margin:0 auto -24px; width:72vw; order:-1; }
  .hero .stats { position:relative; left:auto; bottom:auto; padding:0 24px; gap:24px; flex-wrap:wrap; margin-top:40px; }
  .art { width:88px; height:88px; } .menu button.item { grid-template-columns:88px 1fr; gap:16px; padding-right:56px; }
  details.comp { margin-left:116px; }
}
@media (prefers-reduced-motion:reduce) {
  .cup, .track, .arc { animation:none; } .js .reveal { opacity:1; transform:none; transition:none; }
}
"""

FONTS = '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=Onest:wght@400;500;600&display=swap" rel="stylesheet">'

# ---------- ГЛАВНАЯ СТРАНИЦА ----------
HOME_PAGE = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ shop.name }} — кофейня</title>
  {{ fonts|safe }}
  <style>{{ style|safe }}</style>
</head>
<body>
  <a class="skip" href="#menu">Перейти к меню</a>
  <nav class="nav" aria-label="Основная навигация">
    <a class="logo" href="#top">{{ shop.name }}<i></i></a>
    <div class="links"><a href="#menu">Меню</a><a href="#order">Заказ</a><a href="#" data-book>Бронь</a><a href="#contacts">Контакты</a></div>
    <a class="pill" href="#order">Заказать</a>
  </nav>
  <section class="hero" id="top">
    <div class="ghost" aria-hidden="true">ЗЕРНО</div>
    <div class="arc" aria-hidden="true"></div>
    <div class="hero-copy wrap">
      <p class="kicker">Кофейня · {{ shop.address }}</p>
      <h1>Кофе, который <em>успеваешь</em> допить</h1>
      <p class="lead">Обжариваем свежо, варим при вас. Выберите напиток, рассмотрите его в 3D и закажите к приходу.</p>
      <div class="cta"><a class="pill solid" href="#menu">Смотреть меню</a><a class="pill outline" href="#order">Мой заказ</a></div>
    </div>
    <div class="cup" aria-hidden="true">{{ arts.flatwhite|safe }}</div>
    <ul class="stats wrap">
      <li><b>7:30</b><span>открываемся</span></li>
      <li><b>{{ menu|length }}</b><span>позиций в меню</span></li>
      <li><b>3D</b><span>рассмотри напиток</span></li>
    </ul>
  </section>
  <div class="marquee" aria-hidden="true"><div class="track"><span>Эспрессо</span><span>Капучино</span><span>Флэт уайт</span><span>Раф</span><span>Фильтр</span><span>Круассан</span><span>Эспрессо</span><span>Капучино</span><span>Флэт уайт</span><span>Раф</span><span>Фильтр</span><span>Круассан</span></div></div>

  <main class="wrap">
    <section id="menu">
      <h2>Меню <em>на сегодня</em></h2>
      <p class="hint">Нажмите на напиток, чтобы рассмотреть его в 3D. Кнопка «+» добавляет в заказ, стрелка «Состав» показывает ингредиенты.</p>
      <ul class="menu">
        {% for item in menu %}
        <li class="card">
          <div class="line">
          <button type="button" class="item" data-name="{{ item.name }}" data-price="{{ item.price }}" data-art="{{ item.art }}" data-note="{{ item.note }}" data-size="{{ item.size }}"
            data-top="{{ url_for('static', filename='img/top_' ~ item.art ~ '.png') if item.has_top else '' }}"
            data-glb="{{ url_for('static', filename='models/' ~ item.art ~ '.glb') if item.has_model else '' }}">
            <span class="art" style="background:{{ item.tint }}">
              <span class="badge" aria-hidden="true">3D</span>
              {% if item.has_photo %}
                <img src="{{ url_for('static', filename='img/' ~ item.photo) }}" alt="{{ item.name }}" style="object-position:{{ item.pos }}" loading="lazy">
              {% else %}
                {{ arts[item.art]|safe }}
              {% endif %}
            </span>
            <span>
              <span class="idx" aria-hidden="true">{{ '%02d'|format(loop.index) }}</span>
              <span class="row">
                <span class="title">{{ item.name }}</span><span class="dots"></span>
                <span class="price">{{ '%.2f'|format(item.price) }} €</span>
              </span>
              <span class="note">{{ item.note }}</span>
            </span>
            </button>
          <button type="button" class="plus" data-name="{{ item.name }}" data-price="{{ item.price }}" aria-label="Добавить в заказ: {{ item.name }}">+</button>
          </div>
          <details class="comp">
            <summary>Состав
              <svg class="chev" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </summary>
            <ul class="ing">
              {% for ing, amount in item.ingredients %}
              <li><span>{{ ing }}</span><span>{{ amount }}</span></li>
              {% endfor %}
              <li class="size"><span>Порция</span><span>{{ item.size }}</span></li>
            </ul>
          </details>
        </li>
        {% endfor %}
      </ul>
    </section>

    <section id="order">
      <h2>Ваш заказ</h2>
      <div aria-live="polite">
        <p class="empty" id="cart-empty">Пока пусто. Выберите что-нибудь в меню.</p>
        <ul class="cart-list" id="cart-list"></ul>
        <div class="total" id="cart-total" hidden><span>Итого</span><span id="cart-total-sum">0.00 €</span></div>
      </div>
      <form action="/order" method="post" id="order-form">
        <input type="hidden" name="cart" id="cart-json">
        <div><label for="name">Ваше имя</label><input id="name" name="name" type="text" required></div>
        <button type="submit" id="submit-btn" disabled>Отправить заказ</button>
      </form>
    </section>
  </main>

  <div class="dock">
    <button type="button" class="book-btn" id="book-open">Бронь стола</button>
    <a class="bar" href="#order" id="bar" hidden><span id="bar-n"></span><span id="bar-sum"></span></a>
  </div>

  <dialog id="viewer" aria-labelledby="v-title">
    <div class="v-head">
      <h3 id="v-title"></h3>
      <button type="button" class="v-close" id="v-close" aria-label="Закрыть">×</button>
    </div>
    <div class="v-stage">
      <canvas id="v-canvas" tabindex="0" role="img"></canvas>
      <div id="v-fallback" hidden></div>
      <div class="v-tools">
        <button type="button" id="v-zin" aria-label="Приблизить">+</button>
        <button type="button" id="v-zout" aria-label="Отдалить">−</button>
      </div>
    </div>
    <div class="v-foot">
      <div>
        <p id="v-note"></p>
        <p class="v-help" id="v-help">Потяните, чтобы вращать. Колесо мыши или щипок пальцами приближают. Стрелки и «+»/«−» работают с клавиатуры.</p>
      </div>
      <button type="button" id="v-add"></button>
    </div>
  </dialog>

  <dialog id="booking" aria-labelledby="b-title">
    <div class="v-head">
      <h3 id="b-title">Бронь стола</h3>
      <button type="button" class="v-close" id="b-close" aria-label="Закрыть">×</button>
    </div>
    <div class="b-fields">
      <div><label for="b-date">Дата</label><input type="date" id="b-date"></div>
      <div><label for="b-time">Время</label><select id="b-time"></select></div>
      <div><label for="g-minus">Гостей</label>
        <div class="b-guests"><button type="button" id="g-minus" aria-label="Меньше гостей">−</button><span id="b-guests" aria-live="polite">2</span><button type="button" id="g-plus" aria-label="Больше гостей">+</button></div></div>
    </div>
    <div class="b-plan">{{ floor|safe }}</div>
    <p class="b-info" id="b-info" aria-live="polite"></p>
    <form id="b-form">
      <div><label for="b-name">Имя</label><input id="b-name" type="text" maxlength="60" required autocomplete="name"></div>
      <div><label for="b-phone">Телефон</label><input id="b-phone" type="tel" required autocomplete="tel" placeholder="+358 40 123 4567"></div>
      <div class="wide"><label for="b-comment">Пожелания (необязательно)</label><input id="b-comment" type="text" maxlength="200"></div>
      <button class="wide" type="submit" id="b-submit" disabled>Забронировать</button>
    </form>
    <p id="b-msg" role="status"></p>
  </dialog>

  <footer id="contacts">
    <div class="wrap">
      <div><h3>{{ shop.name }}</h3><p>{{ shop.address }}</p><p>{{ shop.phone }}</p></div>
      <div><h3>Часы работы</h3><p>{{ shop.hours }}</p></div>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
  <script>
    // (библиотека Three.js для 3D подгружается ниже, перед скриптом страницы)
    // Корзина хранится в браузере: { "Капучино": {price: 3.8, qty: 2}, ... }
    const cart = {};
    const $ = (id) => document.getElementById(id);
    const money = (n) => n.toFixed(2) + " €";

    function changeQty(name, delta) {
      cart[name].qty += delta;
      if (cart[name].qty <= 0) delete cart[name];
      render();
    }

    function makeButton(text, label, onClick) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = text;
      b.setAttribute("aria-label", label);
      b.addEventListener("click", onClick);
      return b;
    }

    // Перерисовываем список заказа из объекта cart
    function render() {
      $("cart-list").innerHTML = "";
      let total = 0, count = 0;

      for (const name in cart) {
        const { price, qty } = cart[name];
        total += price * qty;
        count += qty;

        const li = document.createElement("li");
        const nameEl = document.createElement("span");
        nameEl.className = "c-name";
        nameEl.textContent = name;

        const qtyEl = document.createElement("span");
        qtyEl.className = "qty";
        const nEl = document.createElement("span");
        nEl.className = "n";
        nEl.textContent = qty;
        qtyEl.append(
          makeButton("−", "Убрать одну порцию: " + name, () => changeQty(name, -1)),
          nEl,
          makeButton("+", "Добавить ещё одну порцию: " + name, () => changeQty(name, 1))
        );

        const sumEl = document.createElement("span");
        sumEl.className = "c-sum";
        sumEl.textContent = money(price * qty);

        li.append(nameEl, qtyEl, sumEl);
        $("cart-list").append(li);
      }

      const isEmpty = count === 0;
      $("cart-empty").hidden = !isEmpty;
      $("cart-total").hidden = isEmpty;
      $("submit-btn").disabled = isEmpty;
      $("cart-total-sum").textContent = money(total);
      $("bar").hidden = isEmpty;
      $("bar-n").textContent = "Заказ: " + count;
      $("bar-sum").textContent = money(total);
    }

    function addToCart(name, price) {
      if (!cart[name]) cart[name] = { price: price, qty: 0 };
      cart[name].qty += 1;
      render();
    }

    // Кнопка «+» рядом с напитком — сразу в заказ
    document.querySelectorAll("button.plus").forEach((btn) => {
      btn.addEventListener("click", () => addToCart(btn.dataset.name, parseFloat(btn.dataset.price)));
    });

    // Клик по самой позиции — открываем 3D-просмотр
    document.querySelectorAll("button.item").forEach((btn) => {
      btn.addEventListener("click", () => openViewer(btn));
    });

    // Перед отправкой кладём заказ в скрытое поле как текст JSON
    $("order-form").addEventListener("submit", () => {
      const items = Object.keys(cart).map((name) => ({ name: name, qty: cart[name].qty }));
      $("cart-json").value = JSON.stringify(items);
    });

    // ---------- 3D-просмотр напитка (Three.js: физические материалы, студийный свет, тени) ----------
    const dlg = $("viewer");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
    const rnd = (a, b) => a + Math.random() * (b - a);
    const lin = (hex) => new THREE.Color(hex).convertSRGBToLinear();   // цвет из привычного hex в «правильный» для освещения
    let V = null;   // сцена создаётся один раз при первом открытии

    // r — радиус чашки, h — высота, liquid больше не нужен: рисунок напитка создаётся в topTexture()
    const LOOKS = {
      espresso:   { r: 0.72, h: 0.78 },
      americano:  { r: 0.98, h: 0.92 },
      cappuccino: { r: 1.05, h: 0.86 },
      flatwhite:  { r: 0.98, h: 0.82 },
      raf:        { r: 1.0,  h: 0.95 },
      filter:     { r: 0.95, h: 1.3, mug: true },
    };

    function makeCanvas(s) { const c = document.createElement("canvas"); c.width = c.height = s; return c; }
    function canvasTex(c, srgb) {
      const t = new THREE.CanvasTexture(c);
      if (srgb) t.encoding = THREE.sRGBEncoding;
      t.anisotropy = 8;
      return t;
    }

    // Поверхность напитка: крема, пена, какао, латте-арт
    function topTexture(kind) {
      const s = 1024, m = s / 2, c = makeCanvas(s), g = c.getContext("2d");
      g.beginPath(); g.arc(m, m, m - 1, 0, 7); g.clip();   // вне круга — прозрачно
      const radial = (stops) => {
        const gr = g.createRadialGradient(m, m, 0, m, m, m);
        stops.forEach((st) => gr.addColorStop(st[0], st[1]));
        g.fillStyle = gr; g.fillRect(0, 0, s, s);
      };
      const dots = (n, d0, d1, r0, r1, col, a) => {
        g.fillStyle = col; g.globalAlpha = a;
        for (let i = 0; i < n; i++) {
          const ang = rnd(0, 6.283), d = Math.sqrt(Math.random()) * (d1 - d0) * m + d0 * m;
          g.beginPath(); g.arc(m + Math.cos(ang) * d, m + Math.sin(ang) * d, rnd(r0, r1), 0, 7); g.fill();
        }
        g.globalAlpha = 1;
      };
      if (kind === "espresso") {
        radial([[0, "#4a2310"], [.45, "#7a4422"], [.8, "#9b6234"], [.93, "#5a3017"], [1, "#2a1308"]]);
        g.lineWidth = 26; g.lineCap = "round";
        for (let i = 0; i < 14; i++) {   // «тигровые» разводы крема
          g.strokeStyle = "rgba(190,130,70," + rnd(.08, .2) + ")";
          g.beginPath(); g.arc(m + rnd(-40, 40), m + rnd(-40, 40), rnd(60, 400), rnd(0, 6), rnd(0, 6) + 2.2); g.stroke();
        }
        dots(900, 0, .9, 1, 4, "#d9a56a", .22);
      } else if (kind === "americano" || kind === "filter") {
        radial([[0, "#1d0e06"], [.6, "#33190b"], [.88, "#5a3216"], [.95, "#8a5a30"], [1, "#2a1308"]]);
        g.strokeStyle = "rgba(196,140,84,.55)"; g.lineWidth = 34;   // светлая кромка у стенки
        g.beginPath(); g.arc(m, m, m - 40, 0, 7); g.stroke();
        dots(500, .55, .95, 1, 5, "#c9935a", .25);
      } else if (kind === "cappuccino") {
        radial([[0, "#f8eedc"], [.7, "#f0dfc2"], [.86, "#e2c8a0"], [.93, "#b98557"], [1, "#5a3017"]]);
        g.strokeStyle = "rgba(185,133,87,.28)"; g.lineWidth = 22; g.beginPath();   // спираль взбитого молока
        for (let a = 0; a < 17; a += .1) g.lineTo(m + Math.cos(a) * a * 24, m + Math.sin(a) * a * 24);
        g.stroke();
        dots(1500, 0, .86, 2, 7, "#fff7e8", .55);     // пузырьки пены
        dots(1900, .1, .85, 1.5, 3.5, "#6b3f24", .5);  // какао
      } else if (kind === "flatwhite") {
        radial([[0, "#a06a40"], [.7, "#8b5632"], [.9, "#7a4a28"], [1, "#2a1308"]]);
        g.shadowColor = "#f6ead6"; g.shadowBlur = 12; g.fillStyle = "#f6ead6";
        for (let i = 0; i < 5; i++) {   // тюльпан из стопки «капель» молока
          g.beginPath(); g.ellipse(m, m + s * (.26 - i * .12), s * (.27 - i * .035), s * .075, 0, 0, 7); g.fill();
        }
        g.shadowColor = "#8b5632"; g.shadowBlur = 4; g.strokeStyle = "#8b5632"; g.lineWidth = 6; g.lineCap = "round";
        g.beginPath(); g.moveTo(m, m + s * .37); g.lineTo(m, m - s * .3); g.stroke();
        g.shadowBlur = 0;
        dots(600, 0, .9, 1, 3, "#d2a070", .15);
      } else {   // raf
        radial([[0, "#f7eff7"], [.7, "#ecdcec"], [.88, "#d9c3e0"], [.95, "#b79bc6"], [1, "#5a3a6b"]]);
        dots(1200, 0, .85, 2, 6, "#ffffff", .5);
        dots(70, 0, .4, 3, 6, "#7b5aa6", .9);   // сухие бутоны лаванды
      }
      return canvasTex(c, true);
    }

    // Карта рельефа: пузырьки пены и микро-неровности крема
    function bumpTexture(kind) {
      const s = 512, m = s / 2, c = makeCanvas(s), g = c.getContext("2d");
      g.fillStyle = "#808080"; g.fillRect(0, 0, s, s);
      const foam = kind === "cappuccino" || kind === "raf";
      for (let i = 0; i < (foam ? 900 : 700); i++) {
        const a = rnd(0, 6.283), d = Math.sqrt(Math.random()) * m * .95, r = foam ? rnd(2, 9) : rnd(1, 3);
        const x = m + Math.cos(a) * d, y = m + Math.sin(a) * d, gr = g.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, foam ? "#ffffff" : "#c0c0c0"); gr.addColorStop(1, "#808080");
        g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
      }
      return canvasTex(c, false);
    }

    // Поверхность напитка: пена — «шапкой» над краем, кофе — с лёгким мениском у стенки
    function liquidMesh(kind, lr, topUrl) {
      const geo = new THREE.PlaneGeometry(lr * 2, lr * 2, 48, 48);
      const p = geo.attributes.position, foam = kind === "cappuccino";
      for (let i = 0; i < p.count; i++) {
        const d = Math.min(1, Math.hypot(p.getX(i), p.getY(i)) / lr);
        p.setZ(i, foam ? .1 * (1 - d * d) : .035 * Math.pow(d, 4));
      }
      geo.rotateX(-Math.PI / 2); geo.computeVertexNormals();
      const soft = foam || kind === "raf";
      const mat = new THREE.MeshPhysicalMaterial({
        map: topTexture(kind), bumpMap: bumpTexture(kind), bumpScale: soft ? .9 : .25, alphaTest: .5,
        roughness: soft ? .55 : .1, clearcoat: soft ? 0 : 1, clearcoatRoughness: .05, envMapIntensity: soft ? .5 : 1.3 });
      if (topUrl) new THREE.TextureLoader().load(topUrl, (t) => {   // настоящее фото поверхности вместо нарисованной
        t.encoding = THREE.sRGBEncoding; t.anisotropy = 8;
        mat.map = t; mat.bumpMap = null; mat.roughness = soft ? .5 : .2; mat.needsUpdate = true;
      });
      return new THREE.Mesh(geo, mat);
    }

    function steamTexture() {
      const c = makeCanvas(128), g = c.getContext("2d");
      for (let i = 0; i < 14; i++) {
        const x = rnd(40, 88), y = rnd(40, 88), r = rnd(18, 40), gr = g.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, "rgba(255,255,255,.22)"); gr.addColorStop(1, "rgba(255,255,255,0)");
        g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
      }
      return canvasTex(c, false);
    }

    function woodTexture() {
      const s = 1024, c = makeCanvas(s), g = c.getContext("2d");
      g.fillStyle = "#8a5a33"; g.fillRect(0, 0, s, s);
      for (let x = 0; x < s; x += rnd(6, 18)) {
        g.fillStyle = "rgba(" + (Math.random() < .5 ? "60,32,14" : "170,118,70") + "," + rnd(.05, .22) + ")";
        g.fillRect(x, 0, rnd(2, 10), s);
      }
      g.strokeStyle = "rgba(50,26,10,.25)"; g.lineWidth = 2;
      for (let i = 0; i < 90; i++) {
        const x = rnd(0, s);
        g.beginPath(); g.moveTo(x, 0); g.bezierCurveTo(x + rnd(-30, 30), s * .3, x + rnd(-30, 30), s * .6, x + rnd(-20, 20), s); g.stroke();
      }
      return canvasTex(c, true);
    }

    // Слоёное тесто круассана: золотая корочка, полосы слоёв, блики масла
    function flakyTexture() {
      const c = makeCanvas(512), g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, 512);
      gr.addColorStop(0, "#e6a94f"); gr.addColorStop(.5, "#d4893a"); gr.addColorStop(1, "#a95f25");
      g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
      for (let i = 0; i < 260; i++) {
        g.strokeStyle = Math.random() < .5 ? "rgba(255,214,140," + rnd(.1, .3) + ")" : "rgba(110,55,15," + rnd(.12, .3) + ")";
        g.lineWidth = rnd(1, 5);
        const y = rnd(0, 512);
        g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(170, y + rnd(-25, 25), 340, y + rnd(-25, 25), 512, y + rnd(-12, 12)); g.stroke();
      }
      for (let i = 0; i < 300; i++) {
        g.fillStyle = "rgba(255,225,160," + rnd(.08, .25) + ")";
        g.beginPath(); g.arc(rnd(0, 512), rnd(0, 512), rnd(1, 4), 0, 7); g.fill();
      }
      return canvasTex(c, true);
    }

    // Студийное окружение: тёплый купол и яркие «софтбоксы» — они дают живые блики на фарфоре и кофе
    function makeEnvironment(renderer) {
      const env = new THREE.Scene();
      const dome = new THREE.SphereGeometry(30, 32, 16), cols = [];
      const pos = dome.attributes.position, top = lin("#f1dfc2"), bot = lin("#3a2212");
      for (let i = 0; i < pos.count; i++) {
        const cc = bot.clone().lerp(top, clamp(pos.getY(i) / 60 + .5, 0, 1));
        cols.push(cc.r, cc.g, cc.b);
      }
      dome.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
      env.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
      const panel = (w, h, x, y, z, k) => {
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
          new THREE.MeshBasicMaterial({ color: new THREE.Color(k, k * .96, k * .88), side: THREE.DoubleSide }));
        mesh.position.set(x, y, z); mesh.lookAt(0, 0, 0); env.add(mesh);
      };
      panel(14, 8, -12, 14, 12, 7); panel(10, 5, 16, 8, -6, 4); panel(18, 3, 0, 22, -4, 3); panel(8, 8, -18, 4, -8, 2.2);
      const pm = new THREE.PMREMGenerator(renderer);
      const tex = pm.fromScene(env, .02).texture;
      pm.dispose();
      return tex;
    }

    function initViewer() {
      if (V) return V;
      if (!window.THREE) return null;
      try {
        const canvas = $("v-canvas");
        const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
        renderer.outputEncoding = THREE.sRGBEncoding;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.1;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(32, 4 / 3, 0.1, 80);
        let hasEnv = false;
        try { scene.environment = makeEnvironment(renderer); hasEnv = true; } catch (err) { /* без отражений */ }
        scene.add(new THREE.HemisphereLight(0xfff1dc, 0x7a4a24, hasEnv ? .25 : .9));
        const key = new THREE.DirectionalLight(0xfff0dc, hasEnv ? 1.5 : 1.8);
        key.position.set(3.5, 6.5, 3.5); key.castShadow = true;
        key.shadow.mapSize.set(2048, 2048);
        Object.assign(key.shadow.camera, { left: -4, right: 4, top: 4, bottom: -4, near: .5, far: 20 });
        key.shadow.camera.updateProjectionMatrix();
        key.shadow.bias = -.0004; key.shadow.normalBias = .02;
        scene.add(key);
        const rim = new THREE.DirectionalLight(0xffd3a0, .5); rim.position.set(-4, 3, -3.5); scene.add(rim);
        const table = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 5.5, .14, 96),
          new THREE.MeshStandardMaterial({ map: woodTexture(), roughness: .6, envMapIntensity: .5 }));
        table.position.y = -.07; table.receiveShadow = true; scene.add(table);
        V = { renderer, scene, camera, canvas, holder: null, steam: [], steamY: 1, ptrs: new Map(), raf: 0, last: 0, time: 0, intro: 1,
              ctrl: { theta: .5, phi: 1, r: 6.2, tTheta: .5, tPhi: 1, tR: 6.2, auto: true, lastTouch: 0 },
              steamTex: steamTexture() };
        bindControls();
        return V;
      } catch (err) {
        return null;   // нет WebGL — покажем обычную картинку
      }
    }

    function buildModel(art, topUrl) {
      const g = new THREE.Group();
      const ceramic = new THREE.MeshPhysicalMaterial({ color: lin("#fbf7ef"), roughness: .2, clearcoat: .9, clearcoatRoughness: .08, side: THREE.DoubleSide });
      const metal = new THREE.MeshStandardMaterial({ color: lin("#d5d8db"), metalness: 1, roughness: .22 });
      const profile = (pts) => new THREE.SplineCurve(pts.map((p) => new THREE.Vector2(p[0], p[1])))
        .getPoints(96).map((p) => new THREE.Vector2(Math.max(p.x, 0), p.y));
      const lathe = (pts) => new THREE.Mesh(new THREE.LatheGeometry(profile(pts), 128), ceramic);
      const saucer = (S) => lathe([[0, .02], [.5 * S, .02], [.78 * S, .06], [S, .17], [.99 * S, .21], [.94 * S, .2],
                                   [.8 * S, .125], [.6 * S, .092], [.45 * S, .085], [0, .085]]);

      const beans = (S, n) => {   // кофейные зёрна на столе
        const mat = new THREE.MeshStandardMaterial({ color: lin("#2e180b"), roughness: .42 });
        const line = new THREE.MeshStandardMaterial({ color: lin("#120804"), roughness: .6 });
        for (let i = 0; i < n; i++) {
          const a = 2.4 + i * .42 + rnd(-.1, .1), d = S + rnd(.25, .65), b = new THREE.Group();
          const body = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 14), mat); body.scale.set(.12, .075, .085);
          const groove = new THREE.Mesh(new THREE.BoxGeometry(.2, .012, .014), line); groove.position.y = .066; groove.rotation.y = .15;
          b.add(body, groove);
          b.position.set(Math.sin(a) * d, .07, Math.cos(a) * d);
          b.rotation.set(rnd(-.15, .15), rnd(0, 6.28), rnd(-.15, .15));
          g.add(b);
        }
      };
      const spoon = () => {   // металлическая ложечка на блюдце
        const sp = new THREE.Group();
        const bowl = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), metal);
        bowl.material.side = THREE.DoubleSide; bowl.scale.set(.27, .09, .18); bowl.position.set(-.5, .09, 0);
        const handle = new THREE.Mesh(new THREE.BoxGeometry(.75, .016, .045), metal);
        handle.position.set(.1, .055, 0); handle.rotation.z = -.1;
        sp.add(bowl, handle);
        return sp;
      };

      let steamY = 1, camR = 6.2, hot = true;

      if (art === "croissant") {
        hot = false; camR = 7.4;
        g.add(saucer(1.9));
        const dough = new THREE.MeshPhysicalMaterial({ map: flakyTexture(), roughness: .5, clearcoat: .35, clearcoatRoughness: .4 });
        const n = 11;
        for (let i = 0; i < n; i++) {
          const k = i / (n - 1), a = (k - .5) * Math.PI * .95, w = .2 + .36 * Math.pow(Math.sin(Math.PI * k), .9);
          const geo = new THREE.SphereGeometry(1, 48, 32), p = geo.attributes.position;
          for (let j = 0; j < p.count; j++) {   // неровная поверхность и кольцевые «складки» слоёв
            const x = p.getX(j), y = p.getY(j), z = p.getZ(j);
            const f = 1 + Math.sin(x * 7 + i * 3) * Math.sin(z * 6) * .05 + .035 * Math.sin(Math.acos(Math.max(-1, Math.min(1, y))) * 9);
            p.setXYZ(j, x * f, y * f, z * f);
          }
          geo.computeVertexNormals();
          const seg = new THREE.Mesh(geo, dough);
          seg.scale.set(w * 1.25, w * .9, w);
          seg.position.set(Math.sin(a) * 1.05, .085 + w * .8, -Math.cos(a) * 1.05 + .55);
          seg.rotation.y = -a; seg.rotateZ(.08 * (i % 2 ? 1 : -1));
          g.add(seg);
        }
        for (let i = 0; i < 12; i++) {   // крошки на тарелке
          const cr = new THREE.Mesh(new THREE.SphereGeometry(1, 8, 6), dough);
          cr.scale.set(rnd(.02, .045), rnd(.012, .025), rnd(.02, .045));
          const a = rnd(0, 6.28), d = rnd(1.1, 1.7);
          cr.position.set(Math.sin(a) * d, .1, Math.cos(a) * d);
          g.add(cr);
        }
      } else {
        const L = LOOKS[art], R = L.r, H = L.h, S = R * 1.6;
        g.add(saucer(S));
        const cup = new THREE.Group(); cup.position.y = .085; g.add(cup);
        cup.add(L.mug
          ? lathe([[0, 0], [.9 * R, 0], [R, .05 * H], [R, .96 * H], [.98 * R, H], [.94 * R, H], [.9 * R, .96 * H], [.9 * R, .1 * H], [0, .1 * H]])
          : lathe([[0, 0], [.38 * R, 0], [.44 * R, .04 * H], [.6 * R, .2 * H], [.84 * R, .55 * H], [.97 * R, .92 * H], [R, .985 * H],
                   [.985 * R, H], [.955 * R, .99 * H], [.935 * R, .95 * H], [.8 * R, .55 * H], [.55 * R, .2 * H], [.3 * R, .14 * H], [0, .13 * H]]));
        const liq = liquidMesh(art, (L.mug ? .915 : .93) * R, topUrl);
        liq.position.y = (L.mug ? .8 : .82) * H; cup.add(liq);
        const hr = H * (L.mug ? .26 : .3), tube = H * (L.mug ? .06 : .07);
        const handle = new THREE.Mesh(new THREE.TorusGeometry(hr, tube, 16, 32, Math.PI), ceramic);
        handle.rotation.z = -Math.PI / 2; handle.position.set(R * .97, H * .55, 0); cup.add(handle);

        const sp = spoon(); sp.position.set(0, .11, S * .76); sp.scale.setScalar(R * .95); g.add(sp);
        beans(S, 7);
        if (art === "raf") {   // веточка лаванды на блюдце
          const lav = new THREE.Group(); lav.position.set(-R * 1.05, .17, R * .85); lav.rotation.y = .9;
          const stem = new THREE.Mesh(new THREE.CylinderGeometry(.014, .014, .6, 6), new THREE.MeshStandardMaterial({ color: lin("#6E8B5B") }));
          stem.rotation.z = Math.PI / 2; lav.add(stem);
          [-.2, -.05, .1, .25].forEach((x) => {
            const f = new THREE.Mesh(new THREE.SphereGeometry(.06, 12, 10), new THREE.MeshStandardMaterial({ color: lin("#8A6BB8"), roughness: .6 }));
            f.scale.set(1.7, .75, .75); f.position.set(x, .03, 0); lav.add(f);
          });
          g.add(lav);
        }
        steamY = .085 + H + .12;
      }

      g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

      V.steam = [];
      if (hot) for (let i = 0; i < 8; i++) {
        const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: V.steamTex, transparent: true, opacity: 0, depthWrite: false }));
        g.add(s); V.steam.push(s);
      }
      V.steamY = steamY;
      return { group: g, camR: camR };
    }

    function disposeModel(group) {
      group.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        const mat = o.material;
        if (!mat) return;
        ["map", "bumpMap"].forEach((k) => { if (mat[k] && mat[k] !== V.steamTex) mat[k].dispose(); });
        mat.dispose();
      });
    }

    // Управление: вращение пальцем/мышью, колесо и щипок — масштаб, стрелки и +/- с клавиатуры
    function bindControls() {
      const cv = V.canvas, c = V.ctrl;
      const touched = () => { c.auto = false; c.lastTouch = performance.now(); };
      cv.addEventListener("pointerdown", (e) => { cv.setPointerCapture(e.pointerId); V.ptrs.set(e.pointerId, e); touched(); });
      cv.addEventListener("pointermove", (e) => {
        if (!V.ptrs.has(e.pointerId)) return;
        const prev = V.ptrs.get(e.pointerId);
        if (V.ptrs.size === 1) {
          c.tTheta -= (e.clientX - prev.clientX) * .008;
          c.tPhi = clamp(c.tPhi - (e.clientY - prev.clientY) * .006, .3, 1.5);
        } else if (V.ptrs.size === 2) {
          const other = [...V.ptrs.values()].find((p) => p.pointerId !== e.pointerId);
          const d0 = Math.hypot(prev.clientX - other.clientX, prev.clientY - other.clientY);
          const d1 = Math.hypot(e.clientX - other.clientX, e.clientY - other.clientY);
          if (d1 > 0) c.tR = clamp(c.tR * d0 / d1, 3.2, 11);
        }
        V.ptrs.set(e.pointerId, e); touched();
      });
      const up = (e) => V.ptrs.delete(e.pointerId);
      cv.addEventListener("pointerup", up);
      cv.addEventListener("pointercancel", up);
      cv.addEventListener("wheel", (e) => { e.preventDefault(); c.tR = clamp(c.tR * (1 + e.deltaY * .001), 3.2, 11); touched(); }, { passive: false });
      cv.addEventListener("keydown", (e) => {
        const map = { ArrowLeft: () => c.tTheta -= .2, ArrowRight: () => c.tTheta += .2,
                      ArrowUp: () => c.tPhi = clamp(c.tPhi - .12, .3, 1.5), ArrowDown: () => c.tPhi = clamp(c.tPhi + .12, .3, 1.5),
                      "+": () => c.tR = clamp(c.tR * .85, 3.2, 11), "=": () => c.tR = clamp(c.tR * .85, 3.2, 11),
                      "-": () => c.tR = clamp(c.tR * 1.18, 3.2, 11) };
        if (map[e.key]) { e.preventDefault(); map[e.key](); touched(); }
      });
      $("v-zin").addEventListener("click", () => { c.tR = clamp(c.tR * .8, 3.2, 11); touched(); });
      $("v-zout").addEventListener("click", () => { c.tR = clamp(c.tR * 1.25, 3.2, 11); touched(); });
      window.addEventListener("resize", () => { if (dlg.open) resizeViewer(); });
    }

    function resizeViewer() {
      const w = V.canvas.clientWidth, h = V.canvas.clientHeight;
      if (!w || !h) return;
      V.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      V.renderer.setSize(w, h, false);
      V.camera.aspect = w / h; V.camera.updateProjectionMatrix();
    }

    function loop(now) {
      V.raf = requestAnimationFrame(loop);
      const dt = Math.min((now - V.last) / 1000 || 0, .05);
      V.last = now; V.time += dt;
      const c = V.ctrl;
      if (!c.auto && V.ptrs.size === 0 && now - c.lastTouch > 2500 && !reduceMotion) c.auto = true;   // после паузы снова медленно крутим
      if (c.auto && !reduceMotion) c.tTheta += dt * .45;
      const k = 1 - Math.exp(-dt * 9);
      c.theta += (c.tTheta - c.theta) * k; c.phi += (c.tPhi - c.phi) * k; c.r += (c.tR - c.r) * k;
      V.camera.position.set(c.r * Math.sin(c.phi) * Math.sin(c.theta), .5 + c.r * Math.cos(c.phi), c.r * Math.sin(c.phi) * Math.cos(c.theta));
      V.camera.lookAt(0, .5, 0);
      if (V.intro < 1) {   // появление: модель «вылетает», вращаясь и увеличиваясь
        V.intro = Math.min(1, V.intro + dt / .9);
        const e = 1 - Math.pow(1 - V.intro, 3);
        V.holder.scale.setScalar(.5 + .5 * e); V.holder.rotation.y = (1 - e) * -2.4;
      }
      V.steam.forEach((s, i) => {   // пар поднимается и тает
        const t = (V.time * .16 + i / V.steam.length) % 1;
        s.position.set(Math.sin(V.time + i * 1.7) * .12 * (t + .2) + (i - 2) * .07, V.steamY + t * 1.5, Math.cos(V.time * .8 + i) * .1);
        s.scale.setScalar(.5 + t * 1.1);
        s.material.opacity = reduceMotion ? 0 : Math.sin(Math.PI * t) * .2;
      });
      V.renderer.render(V.scene, V.camera);
    }

    function openViewer(btn) {
      const name = btn.dataset.name, price = parseFloat(btn.dataset.price), art = btn.dataset.art;
      $("v-title").textContent = name;
      $("v-note").textContent = btn.dataset.note + " · " + btn.dataset.size;
      const add = $("v-add");
      add.dataset.name = name; add.dataset.price = price;
      add.textContent = "Добавить в заказ · " + money(price);
      $("v-canvas").setAttribute("aria-label", "3D-модель: " + name);
      dlg.showModal();

      const v = initViewer();
      $("v-canvas").hidden = !v; $("v-fallback").hidden = !!v;
      document.querySelector(".v-tools").hidden = !v;
      if (!v) {   // нет интернета для Three.js или WebGL — показываем обычную картинку
        $("v-fallback").innerHTML = btn.querySelector(".art").innerHTML;
        $("v-help").textContent = "3D сейчас недоступно (нужен интернет и поддержка WebGL), поэтому показана картинка.";
        return;
      }
      $("v-help").textContent = "Потяните, чтобы вращать. Колесо мыши или щипок пальцами приближают. Стрелки и «+»/«−» работают с клавиатуры.";
      if (v.holder) { v.scene.remove(v.holder); disposeModel(v.holder); }
      const m = buildModel(art, btn.dataset.top);
      v.holder = m.group; v.scene.add(m.group);
      const c = v.ctrl;
      c.tR = c.r = m.camR; c.tPhi = c.phi = 1; c.tTheta = c.theta = .5; c.auto = true; c.lastTouch = 0;
      v.intro = reduceMotion ? 1 : 0;
      if (reduceMotion) { v.holder.scale.setScalar(1); v.holder.rotation.y = 0; } else { v.holder.scale.setScalar(.5); }
      resizeViewer();
      cancelAnimationFrame(v.raf); v.last = performance.now();
      v.raf = requestAnimationFrame(loop);
      if (btn.dataset.glb && THREE.GLTFLoader) loadGlb(btn.dataset.glb, v);   // есть готовая модель — показываем её
    }

    // Готовая 3D-модель из файла .glb (например, сделанная по фото) заменяет модель, собранную кодом
    function loadGlb(url, v) {
      new THREE.GLTFLoader().load(url, (gltf) => {
        if (!dlg.open) return;
        const obj = gltf.scene, box = new THREE.Box3().setFromObject(obj);
        const size = box.getSize(new THREE.Vector3()), mid = box.getCenter(new THREE.Vector3());
        const k = 3 / Math.max(size.x, size.y, size.z);
        obj.scale.setScalar(k); obj.position.set(-mid.x * k, -box.min.y * k, -mid.z * k);
        obj.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
        const g = new THREE.Group(); g.add(obj);
        v.steam = []; v.scene.remove(v.holder); disposeModel(v.holder);
        v.holder = g; v.scene.add(g);
        v.intro = reduceMotion ? 1 : 0; g.scale.setScalar(reduceMotion ? 1 : .5);
      }, undefined, () => { /* файла нет или он повреждён — остаётся модель из кода */ });
    }

    $("v-add").addEventListener("click", (e) => {
      const b = e.currentTarget, label = b.textContent;
      addToCart(b.dataset.name, parseFloat(b.dataset.price));
      b.textContent = "Добавлено";
      setTimeout(() => { b.textContent = label; }, 1200);
    });
    $("v-close").addEventListener("click", () => dlg.close());
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });   // клик по затемнению закрывает окно
    dlg.addEventListener("close", () => { if (V) cancelAnimationFrame(V.raf); });

    // ---------- Анимации страницы ----------
    document.documentElement.classList.add("js");
    const revealEls = document.querySelectorAll(".card, section h2, .hint, #order form, .stats li");
    revealEls.forEach((el) => el.classList.add("reveal"));
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((list) => list.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      }), { threshold: .12 });
      revealEls.forEach((el) => io.observe(el));
    } else {
      revealEls.forEach((el) => el.classList.add("in"));
    }
    const heroEl = document.querySelector(".hero"), ghostEl = document.querySelector(".ghost");
    if (!reduceMotion && heroEl) {
      heroEl.addEventListener("pointermove", (e) => {   // янтарный свет следует за курсором
        heroEl.style.setProperty("--mx", e.clientX + "px");
        heroEl.style.setProperty("--my", (e.clientY - heroEl.getBoundingClientRect().top) + "px");
      });
      window.addEventListener("scroll", () => {          // слово-призрак уезжает медленнее страницы
        ghostEl.style.transform = "translate(-50%, calc(-50% + " + window.scrollY * .25 + "px))";
      }, { passive: true });
    }

    // ---------- Бронь столов ----------
    const bdlg = $("booking");
    const tbls = [...bdlg.querySelectorAll(".tbl")];
    const B = { table: null, guests: 2 };
    const todayStr = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

    function selectTable(id) {
      B.table = id;
      tbls.forEach((t) => { t.classList.toggle("sel", t.dataset.id === id); t.setAttribute("aria-pressed", t.dataset.id === id); });
      const t = tbls.find((x) => x.dataset.id === id);
      $("b-info").textContent = t ? t.dataset.name + ", мест: " + t.dataset.seats + ". " + t.dataset.desc
        : "Выберите стол на плане. Серые заняты на это время, бледные не подходят по числу гостей. Число на столе — количество мест.";
      $("b-submit").disabled = !t;
    }

    function markTables(taken) {
      tbls.forEach((t) => {
        const busy = taken.includes(t.dataset.id), small = B.guests > +t.dataset.seats;
        t.classList.toggle("taken", busy);
        t.classList.toggle("small", small && !busy);
        t.setAttribute("aria-disabled", busy || small);
        if ((busy || small) && B.table === t.dataset.id) selectTable(null);
      });
    }

    async function loadTaken() {
      const date = $("b-date").value, time = $("b-time").value;
      if (!date || !time) { markTables([]); return; }
      const data = await (await fetch("/api/booking?date=" + date + "&time=" + encodeURIComponent(time))).json();
      markTables(data.taken || []);
    }

    async function loadSlots() {
      const sel = $("b-time"), keep = sel.value;
      const data = await (await fetch("/api/booking?date=" + $("b-date").value)).json();
      sel.innerHTML = "";
      (data.slots || []).forEach((s) => sel.add(new Option(s, s)));
      if ((data.slots || []).includes(keep)) sel.value = keep;
      if (!(data.slots || []).length) $("b-info").textContent = data.error || "На эту дату свободного времени нет, выберите другую.";
      else if (!B.table) selectTable(null);
      loadTaken();
    }

    function openBooking() {
      $("b-msg").textContent = ""; $("b-msg").className = "";
      $("b-date").min = todayStr(); if (!$("b-date").value) $("b-date").value = todayStr();
      $("b-form").hidden = false; selectTable(null);
      bdlg.showModal(); loadSlots();
    }

    tbls.forEach((t) => {
      const pick = () => { if (!t.classList.contains("taken") && !t.classList.contains("small")) selectTable(t.dataset.id); };
      t.addEventListener("click", pick);
      t.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
    $("b-date").addEventListener("change", loadSlots);
    $("b-time").addEventListener("change", loadTaken);
    [["g-minus", -1], ["g-plus", 1]].forEach((p) => $(p[0]).addEventListener("click", () => {
      B.guests = clamp(B.guests + p[1], 1, 8); $("b-guests").textContent = B.guests; loadTaken();
    }));
    $("book-open").addEventListener("click", openBooking);
    document.querySelectorAll("[data-book]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); openBooking(); }));
    $("b-close").addEventListener("click", () => bdlg.close());
    bdlg.addEventListener("click", (e) => { if (e.target === bdlg) bdlg.close(); });

    $("b-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = $("b-msg"); msg.className = ""; msg.textContent = "Отправляем…";
      const body = { table: B.table, date: $("b-date").value, time: $("b-time").value, guests: B.guests,
                     name: $("b-name").value, phone: $("b-phone").value, comment: $("b-comment").value };
      try {
        const res = await fetch("/book", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await res.json();
        if (data.ok) {
          const day = new Date(data.date + "T00:00").toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
          msg.className = "ok"; msg.textContent = "Готово! «" + data.table + "» забронирован на " + day + " в " + data.time + ". Ждём вас, " + body.name + ".";
          $("b-form").hidden = true;
        } else { msg.className = "err"; msg.textContent = data.error; }
        loadTaken();
      } catch (err) { msg.className = "err"; msg.textContent = "Нет связи с сайтом. Попробуйте ещё раз."; }
    });

    render();
  </script>
</body>
</html>
"""

# ---------- СТРАНИЦА «СПАСИБО» ----------
THANKS_PAGE = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Заказ принят — {{ shop.name }}</title>
  {{ fonts|safe }}
  <style>{{ style|safe }}</style>
</head>
<body>
  <nav class="nav"><a class="logo" href="/">{{ shop.name }}<i></i></a><span></span><a class="pill" href="/">В меню</a></nav>
  <section class="hero" style="min-height:80svh">
    <div class="ghost" aria-hidden="true">СПАСИБО</div>
    <div class="arc" aria-hidden="true"></div>
    <div class="hero-copy wrap">
      <p class="kicker">Заказ принят</p>
      <h1>Спасибо, <em>{{ customer }}</em></h1>
      <p class="lead">Всё будет готово, когда вы зайдёте.</p>
    </div>
    <div class="cup" aria-hidden="true">{{ arts.espresso|safe }}</div>
  </section>
  <main class="wrap">
    <section>
      <h2>Что вы <em>заказали</em></h2>
      <ul class="cart-list">
        {% for line in lines %}
        <li><span class="c-name">{{ line.name }} × {{ line.qty }}</span><span class="c-sum">{{ '%.2f'|format(line.sum) }} €</span></li>
        {% endfor %}
      </ul>
      <div class="total"><span>Итого</span><span>{{ '%.2f'|format(total) }} €</span></div>
      <a class="pill solid" href="/">Вернуться в меню</a>
    </section>
  </main>
</body>
</html>
"""


# ---------- СТОЛЫ И БРОНЬ ----------
# kind: round — круглый, square — квадратный, long — общий, booth — диванчик, bar — высокие стулья у стойки
# x, y — центр на плане (план 640x420), w, h — размер столешницы
TABLES = [
    {"id": "T1", "name": "Бистро у окна", "kind": "round", "x": 100, "y": 90, "w": 56, "h": 56, "seats": 2, "desc": "Круглый столик для двоих рядом с окном."},
    {"id": "T2", "name": "Бистро у окна", "kind": "round", "x": 210, "y": 90, "w": 56, "h": 56, "seats": 2, "desc": "Круглый столик для двоих рядом с окном."},
    {"id": "T3", "name": "Квадратный стол у окна", "kind": "square", "x": 330, "y": 90, "w": 64, "h": 64, "seats": 4, "desc": "Светлое место на четверых у окна."},
    {"id": "T4", "name": "Квадратный стол", "kind": "square", "x": 100, "y": 225, "w": 64, "h": 64, "seats": 4, "desc": "В глубине зала, здесь тише."},
    {"id": "T5", "name": "Квадратный стол", "kind": "square", "x": 230, "y": 225, "w": 64, "h": 64, "seats": 4, "desc": "В центре зала, удобно для встречи вчетвером."},
    {"id": "T6", "name": "Общий стол", "kind": "long", "x": 200, "y": 350, "w": 168, "h": 52, "seats": 8, "desc": "Длинный стол для компании до 8 человек."},
    {"id": "T7", "name": "Диванчик", "kind": "booth", "x": 440, "y": 340, "w": 96, "h": 46, "seats": 4, "desc": "Мягкие диваны, удобно для долгих разговоров."},
    {"id": "T8", "name": "Барная стойка, место 1", "kind": "bar", "x": 528, "y": 100, "w": 0, "h": 0, "seats": 2, "desc": "Высокие стулья у стойки, видно, как варят кофе."},
    {"id": "T9", "name": "Барная стойка, место 2", "kind": "bar", "x": 528, "y": 250, "w": 0, "h": 0, "seats": 2, "desc": "Высокие стулья у стойки, видно, как варят кофе."},
]

def table_svg(t):
    """Рисует один стол со стульями. Весь стол кликабельный (невидимая область hit)."""
    x, y, w, h, n, k = t["x"], t["y"], t["w"], t["h"], t["seats"], t["kind"]
    chair = lambda cx, cy: f'<circle class="chair" cx="{cx:.1f}" cy="{cy:.1f}" r="9"/>'
    lx, ly = x, y + 5
    if k == "round":
        r = w / 2
        body = "".join(chair(x + (r + 14) * math.cos(6.2832 * i / n - 1.5708), y + (r + 14) * math.sin(6.2832 * i / n - 1.5708)) for i in range(n))
        body += f'<circle class="top" cx="{x}" cy="{y}" r="{r}"/>'
        box = (x - r - 26, y - r - 26, 2 * r + 52, 2 * r + 52)
    elif k == "square":
        body = chair(x, y - h / 2 - 14) + chair(x, y + h / 2 + 14) + chair(x - w / 2 - 14, y) + chair(x + w / 2 + 14, y)
        body += f'<rect class="top" x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="8"/>'
        box = (x - w / 2 - 28, y - h / 2 - 28, w + 56, h + 56)
    elif k == "long":
        per = n // 2
        body = "".join(chair(x - w / 2 + w * (i + .5) / per, y - h / 2 - 12) + chair(x - w / 2 + w * (i + .5) / per, y + h / 2 + 12) for i in range(per))
        body += f'<rect class="top" x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="10"/>'
        box = (x - w / 2 - 14, y - h / 2 - 28, w + 28, h + 56)
    elif k == "booth":
        body = (f'<rect class="bench" x="{x - w / 2}" y="{y - h / 2 - 26}" width="{w}" height="16" rx="8"/>'
                f'<rect class="bench" x="{x - w / 2}" y="{y + h / 2 + 10}" width="{w}" height="16" rx="8"/>'
                f'<rect class="top" x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="8"/>')
        box = (x - w / 2 - 14, y - h / 2 - 36, w + 28, h + 72)
    else:   # bar
        body = "".join(chair(x, y + 36 * i) for i in range(n))
        body += f'<rect class="top" x="{x + 23}" y="{y - 14}" width="46" height="{36 * n - 8}" rx="8"/>'
        lx, ly, box = x + 46, y + 36 * (n - 1) / 2 + 5, (x - 20, y - 22, 92, 36 * n + 8)
    return (f'<g class="tbl" data-id="{t["id"]}" data-seats="{n}" data-name="{t["name"]}" data-desc="{t["desc"]}" '
            f'tabindex="0" role="button" aria-pressed="false" aria-label="{t["name"]}, мест: {n}">'
            f'<rect class="hit" x="{box[0]:.0f}" y="{box[1]:.0f}" width="{box[2]:.0f}" height="{box[3]:.0f}" rx="12"/>'
            f'{body}<text class="lbl" x="{lx}" y="{ly}" text-anchor="middle">{n}</text></g>')

FLOOR = (
    '<svg viewBox="0 0 640 420" role="group" aria-label="План зала">'
    '<rect class="room" x="8" y="8" width="624" height="404" rx="14"/>'
    '<rect class="win" x="60" y="5" width="330" height="7" rx="3"/><text class="deco" x="225" y="34" text-anchor="middle">ОКНО</text>'
    '<rect class="door" x="40" y="408" width="72" height="6" rx="3"/><text class="deco" x="76" y="398" text-anchor="middle">ВХОД</text>'
    '<rect class="counter" x="548" y="60" width="52" height="300" rx="10"/>'
    '<text class="deco" transform="translate(574 215) rotate(-90)" text-anchor="middle">БАР</text>'
    + "".join(table_svg(t) for t in TABLES) + '</svg>')

BOOK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bookings.json")
BOOK_MIN = 90   # сколько минут стол занят
HOURS = {"week": ("07:30", "18:00"), "weekend": ("09:00", "17:00")}
_lock = threading.Lock()

def load_bookings():
    try:
        with open(BOOK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def to_min(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)

def slots_for(day):
    """Время начала брони каждые 30 минут, чтобы 90 минут уместились до закрытия."""
    open_, close = HOURS["weekend" if day.weekday() >= 5 else "week"]
    res, t = [], to_min(open_)
    while t + BOOK_MIN <= to_min(close):
        res.append(f"{t // 60:02d}:{t % 60:02d}")
        t += 30
    if day == datetime.date.today():   # сегодняшнее прошедшее время недоступно
        now = datetime.datetime.now()
        res = [s for s in res if to_min(s) > now.hour * 60 + now.minute]
    return res

def taken_tables(day_str, time_str, bookings):
    a = to_min(time_str)
    return sorted({b["table"] for b in bookings
                   if b["date"] == day_str and to_min(b["time"]) < a + BOOK_MIN and a < to_min(b["time"]) + BOOK_MIN})

def parse_day(s):
    try:
        d = datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    today = datetime.date.today()
    return d if today <= d <= today + datetime.timedelta(days=60) else None

# ---------- МАРШРУТЫ ----------
@app.route("/")
def home():
    # Проверяем, лежит ли фото напитка в static/img/ — если да, покажем его вместо рисунка
    # Что лежит в static/: фото, плоская текстура поверхности напитка, готовая 3D-модель .glb
    def has(sub, name):
        return os.path.exists(os.path.join(app.static_folder, sub, name))
    menu = [{**item, "has_photo": has("img", item["photo"]), "has_top": has("img", f"top_{item['art']}.png"),
             "has_model": has("models", f"{item['art']}.glb"), "pos": POS.get(item["art"], "50% 50%")} for item in MENU]
    return render_template_string(HOME_PAGE, shop=SHOP, menu=menu, arts=ARTS, style=STYLE, fonts=FONTS, floor=FLOOR)


@app.route("/order", methods=["POST"])
def order():
    customer = request.form.get("name", "").strip() or "гость"

    # Браузер прислал заказ как текст JSON — превращаем обратно в список
    try:
        items = json.loads(request.form.get("cart", "[]"))
    except json.JSONDecodeError:
        return "Некорректный заказ", 400
    if not isinstance(items, list):
        return "Некорректный заказ", 400

    # Цены берём ТОЛЬКО из нашего меню: данным из браузера доверять нельзя
    prices = {item["name"]: item["price"] for item in MENU}

    lines = []
    total = 0
    for entry in items:
        if not isinstance(entry, dict):
            return "Некорректный заказ", 400
        name = entry.get("name")
        qty = entry.get("qty")
        if name not in prices or not isinstance(qty, int) or not 1 <= qty <= 20:
            return "Некорректный заказ", 400
        line_sum = prices[name] * qty
        lines.append({"name": name, "qty": qty, "sum": line_sum})
        total += line_sum

    if not lines:
        return "Заказ пустой", 400

    # Здесь позже можно сохранять заказ в файл или базу данных
    print(f"Новый заказ от {customer}: {lines}, итого {total:.2f} €")

    return render_template_string(
        THANKS_PAGE, shop=SHOP, customer=customer, lines=lines, total=total,
        arts=ARTS, style=STYLE, fonts=FONTS,
    )


@app.route("/api/booking")
def api_booking():
    day = parse_day(request.args.get("date"))
    if not day:
        return jsonify(slots=[], taken=[], error="Выберите дату в ближайшие 60 дней"), 400
    slots = slots_for(day)
    t = request.args.get("time")
    taken = taken_tables(day.isoformat(), t, load_bookings()) if t in slots else []
    return jsonify(slots=slots, taken=taken)


@app.route("/book", methods=["POST"])
def book():
    d = request.get_json(silent=True) or {}

    def fail(msg, code=400):
        return jsonify(ok=False, error=msg), code

    table = next((t for t in TABLES if t["id"] == d.get("table")), None)
    day = parse_day(d.get("date"))
    time_s = d.get("time")
    guests = d.get("guests")
    name = str(d.get("name", "")).strip()
    phone = str(d.get("phone", "")).strip()
    if not table:
        return fail("Выберите стол на плане")
    if not day:
        return fail("Выберите дату в ближайшие 60 дней")
    if time_s not in slots_for(day):
        return fail("Это время недоступно, выберите другое")
    if not isinstance(guests, int) or not 1 <= guests <= table["seats"]:
        return fail(f"За этот стол помещается до {table['seats']} гостей")
    if not name or len(name) > 60:
        return fail("Укажите имя")
    if not re.fullmatch(r"[\d+\-() ]{6,20}", phone):
        return fail("Укажите телефон, например +358 40 123 4567")

    with _lock:   # чтобы два человека не заняли один стол одновременно
        bookings = load_bookings()
        if table["id"] in taken_tables(day.isoformat(), time_s, bookings):
            return fail("Этот стол уже занят на выбранное время. Выберите другой.", 409)
        bookings.append({"table": table["id"], "date": day.isoformat(), "time": time_s, "guests": guests,
                         "name": name, "phone": phone, "comment": str(d.get("comment", "")).strip()[:200],
                         "created": datetime.datetime.now().isoformat(timespec="seconds")})
        with open(BOOK_FILE, "w", encoding="utf-8") as f:
            json.dump(bookings, f, ensure_ascii=False, indent=2)

    print(f"Новая бронь: {table['name']} ({table['id']}), {day} {time_s}, {guests} гостей, {name}")
    return jsonify(ok=True, table=table["name"], date=day.isoformat(), time=time_s)


if __name__ == "__main__":
    app.run(debug=True)