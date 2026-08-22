/* ============================================================================
   Six kinds of problem, not one hundred and fifty-five.

   Boston files complaints under 155 codes, most of them near-duplicates — a
   resident reporting a hole in the road doesn't know whether that's "Pothole"
   or "Request for Pothole Repair", and shouldn't have to. These six are what
   people actually mean. Every 311 code maps into one of them.

   The colours were checked with a colour-blindness validator in both light and
   dark: every neighbouring pair stays distinguishable for protanopia,
   deuteranopia and tritanopia, and each one holds at least 3:1 against the
   background it sits on. Colour is never the only signal though — every marker
   and every row also carries its name.
========================================================================== */

const CATS = [
  { k:"pests", short:"Pests", shortEs:"Plagas",  en:"Pests & rodents",     es:"Plagas y roedores",
    dark:"#E0574A", light:"#C0392B", icon:"◆" },
  { k:"street", short:"Streets", shortEs:"Calles", en:"Streets & sidewalks", es:"Calles y aceras",
    dark:"#4B87E8", light:"#2A62B8", icon:"▲" },
  { k:"waste", short:"Trash", shortEs:"Basura",  en:"Trash & dumping",     es:"Basura y vertidos",
    dark:"#4FA85C", light:"#2E7D46", icon:"■" },
  { k:"signal", short:"Lights", shortEs:"Luces", en:"Lights & signals",    es:"Luces y semáforos",
    dark:"#B76BD9", light:"#8E44AD", icon:"●" },
  { k:"home", short:"Housing", shortEs:"Vivienda",   en:"Housing conditions",  es:"Condiciones de vivienda",
    dark:"#C1811F", light:"#96620F", icon:"⬟" },
  { k:"车", short:"Vehicles", shortEs:"Vehículos",     en:"Vehicles & parking",  es:"Vehículos y estacionamiento",
    dark:"#E85A93", light:"#B32A63", icon:"▬" },
];
CATS[5].k = "vehicle";

const CAT_BY_KEY = Object.fromEntries(CATS.map(c => [c.k, c]));

/* Which of the six a 311 code belongs to. Checked in order — the first rule
   that matches wins, so the specific patterns sit above the general ones. */
const CAT_RULES = [
  [/rodent|pest|rat\b|mice|mouse|animal|bed ?bug/i,                 "pests"],
  [/sidewalk|pothole|street ?(repair|defect)|road|curb|pavement|snow|ice|shovel|crosswalk/i, "street"],
  [/trash|rubbish|barrel|recycl|dump|litter|graffiti|clean|collection|cart|sticker/i,        "waste"],
  [/sign|signal|light|lamp|traffic/i,                               "signal"],
  [/property|building|electrical|plumb|heat|mold|contractor|encampment|inspection|housing/i, "home"],
  [/parking|vehicle|abandoned|towing|enforcement/i,                 "vehicle"],
];

function catOf(title) {
  for (const [re, k] of CAT_RULES) if (re.test(title || "")) return k;
  return "waste";                       // the residual bucket, not a guess
}

function catColor(key) {
  const c = CAT_BY_KEY[key] || CAT_BY_KEY.waste;
  const el = document.documentElement;
  const light = el.getAttribute("data-theme") === "light" ||
    (!el.getAttribute("data-theme") && matchMedia("(prefers-color-scheme:light)").matches);
  return light ? c.light : c.dark;
}

function catLabel(key, lang) {
  const c = CAT_BY_KEY[key] || CAT_BY_KEY.waste;
  return lang === "es" ? c.es : c.en;
}
