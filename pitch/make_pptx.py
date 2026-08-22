"""
Build the Street Signal deck as a real PowerPoint file.

A .pptx is a zip of XML documents, so this needs no libraries at all — just
zipfile from the standard library. Everything it writes is a genuine text box,
so the deck opens editable in PowerPoint, Keynote and Google Slides rather than
as flat images the way a PDF import would.

Fonts: Arial / Arial Black, deliberately. Barlow Condensed would match the PDF
exactly, but a font the opener doesn't have gets substituted and the layout
shifts. Arial is on every machine. Swap it later in one pass with
Home > Replace Fonts if you want the original face.

Run:  python3 pitch/make_pptx.py
"""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent / "street-signal-pitch.pptx"

EMU = 914400                      # EMU per inch
W, H = int(13.333 * EMU), int(7.5 * EMU)     # 16:9
MARGIN = int(0.62 * EMU)
CONTENT_W = W - 2 * MARGIN

# Same palette as the PDF, minus the leading '#'
BG      = "071620"
INK     = "EAF2F7"
INK2    = "A8BFCE"
DIM     = "6E8899"
BLUE    = "37A2F0"
RED     = "E0574A"
GOLD    = "C1811F"
GREEN   = "4FA85C"
PANEL   = "0D2432"
LINE    = "1B4056"

DISPLAY, BODY, MONO = "Arial Black", "Arial", "Courier New"


# ---------------------------------------------------------------- shapes ----
def _run(text, size, color, font=BODY, bold=False, italic=False):
    return (f'<a:r><a:rPr lang="en-US" sz="{int(size*100)}" b="{1 if bold else 0}" '
            f'i="{1 if italic else 0}" dirty="0"><a:solidFill><a:srgbClr val="{color}"/>'
            f'</a:solidFill><a:latin typeface="{font}"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r>')


def textbox(sid, x, y, cx, cy, paras, anchor="t", spacing=100):
    """paras: list of lists of run-tuples, one list per paragraph."""
    body = ""
    for runs in paras:
        if runs is None:                      # blank spacer line
            body += '<a:p><a:endParaRPr lang="en-US" sz="800"/></a:p>'
            continue
        body += (f'<a:p><a:pPr><a:lnSpc><a:spcPct val="{spacing}000"/></a:lnSpc></a:pPr>'
                 + "".join(_run(*r) for r in runs) + '</a:p>')
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="tb{sid}"/>'
            f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" anchor="{anchor}"><a:normAutofit/></a:bodyPr>'
            f'<a:lstStyle/>{body}</p:txBody></p:sp>')


def rect(sid, x, y, cx, cy, fill, line=None, lw=12700):
    ln = (f'<a:ln w="{lw}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
          if line else '<a:ln><a:noFill/></a:ln>')
    fl = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="r{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fl}{ln}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>')


def slide_xml(shapes):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="' + BG + '"/></a:solidFill>'
            '<a:effectLst/></p:bgPr></p:bg><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            + "".join(shapes) +
            '</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" '
            'bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
            'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
            'folHlink="folHlink"/></p:clrMapOvr></p:sld>')


# ---------------------------------------------------------------- helpers ---
class Slide:
    """Builds one slide, handing out unique shape ids as it goes."""

    def __init__(self, number):
        self.shapes, self.n, self.number = [], 1, number

    def _id(self):
        self.n += 1
        return self.n

    def kicker(self, text, y=int(0.55 * EMU)):
        self.shapes.append(textbox(self._id(), MARGIN, y, CONTENT_W, int(0.3 * EMU),
                                   [[(text.upper(), 10, BLUE, MONO, True)]]))
        return self

    def title(self, parts, y=int(0.95 * EMU), size=40):
        """parts: list of (text, color) — lets one phrase pick up the accent."""
        runs = [(t, size, c, DISPLAY, True) for t, c in parts]
        self.shapes.append(textbox(self._id(), MARGIN, y, CONTENT_W,
                                   int(1.5 * EMU), [runs], spacing=95))
        return self

    def body(self, paras, x=None, y=None, cx=None, cy=None, size=13):
        self.shapes.append(textbox(self._id(), x or MARGIN, y or int(2.6 * EMU),
                                   cx or CONTENT_W, cy or int(3.2 * EMU),
                                   paras, spacing=125))
        return self

    def panel(self, x, y, cx, cy, accent=None):
        self.shapes.append(rect(self._id(), x, y, cx, cy, PANEL, LINE))
        if accent:
            self.shapes.append(rect(self._id(), x, y, cx, int(0.045 * EMU), accent))
        return self

    def page(self):
        self.shapes.append(textbox(self._id(), W - MARGIN - int(1 * EMU),
                                   H - int(0.62 * EMU), int(1 * EMU), int(0.3 * EMU),
                                   [[(f"{self.number:02d}", 9, DIM, MONO)]]))
        return self

    def xml(self):
        self.page()
        return slide_xml(self.shapes)


def col(i, n=4, gap=0.22):
    """Left edge and width for column i of n across the content area."""
    g = int(gap * EMU)
    cw = (CONTENT_W - g * (n - 1)) // n
    return MARGIN + i * (cw + g), cw


# ---------------------------------------------------------------- slides ----
def build():
    S = []

    # 1 — cover
    s = Slide(1)
    s.kicker("Boston · 311 open data · 2025", int(2.1 * EMU))
    s.title([("STREET ", INK), ("SIGNAL", RED)], int(2.5 * EMU), 60)
    s.shapes.append(rect(s._id(), MARGIN, int(4.15 * EMU), int(1.5 * EMU), 38100, RED))
    s.body([[("A resident asks whether their street is being ignored, and gets a straight "
              "answer from the city's own records — in one sentence, with receipts.",
              15, INK2)]], y=int(4.5 * EMU), cx=int(8.6 * EMU), cy=int(1.4 * EMU))
    S.append(s)

    # 2 — the problem
    s = Slide(2)
    s.kicker("The problem")
    s.title([('"Is it just me, or is my street being ignored?"', INK)], size=30)
    lx, lw = MARGIN, int(5.6 * EMU)
    rx = MARGIN + int(6.1 * EMU)
    s.body([[("— the question nobody can answer today", 11, DIM, MONO)]],
           x=lx, y=int(3.2 * EMU), cx=lw, cy=int(0.5 * EMU))
    s.body([
        [("You report the rats. Weeks later an email says ", 14, INK2),
         ("Closed", 14, INK, BODY, True), (". Nothing has changed.", 14, INK2)],
        None,
        [("Two doubts follow, and both land as self-blame: is this normal for a city, "
          "and did anything actually happen?", 12.5, INK2)],
        None,
        [("You are the only party in the transaction operating blind — and you are the "
          "one it is happening to.", 12.5, INK, BODY, True)],
    ], x=rx, y=int(2.5 * EMU), cx=int(6.0 * EMU), cy=int(4.0 * EMU))
    S.append(s)

    # 3 — the evidence
    s = Slide(3)
    s.kicker("The doubt is well founded")
    s.body([[("58,005", 66, RED, DISPLAY, True)]],
           y=int(1.15 * EMU), cx=int(4.2 * EMU), cy=int(1.5 * EMU))
    s.body([
        [("CASES BOSTON CLOSED IN 2025 AS", 10, INK2, MONO)],
        [('"NOTED ONLY"', 12, RED, MONO, True)],
        [("— recorded, with no fix logged", 10, INK2, MONO)],
    ], x=MARGIN + int(4.4 * EMU), y=int(1.5 * EMU), cx=int(5.5 * EMU), cy=int(1.4 * EMU))
    s.body([[("That is the recorded moment a person was managed rather than helped. "
              "It sits in a public file, and no resident has ever been shown it.",
              15, INK)]], y=int(3.1 * EMU), cx=int(10.5 * EMU), cy=int(1.1 * EMU))
    stats = [("31.8%", "MISSED THE CITY'S OWN DEADLINE", RED),
             ("40.2%", "OF VOLUME IS A REPEAT", RED),
             ("4.8h", "MEDIAN CLOSE — THE FLATTERING NUMBER", INK),
             ("90.8d", "99TH PERCENTILE — WHERE PEOPLE LIVE", RED)]
    for i, (big, lab, c) in enumerate(stats):
        x, cw = col(i)
        s.panel(x, int(4.6 * EMU), cw, int(1.5 * EMU))
        s.body([[(big, 26, c, DISPLAY, True)]], x=x + int(0.18 * EMU), y=int(4.75 * EMU),
               cx=cw, cy=int(0.6 * EMU))
        s.body([[(lab, 8.5, DIM, MONO)]], x=x + int(0.18 * EMU), y=int(5.45 * EMU),
               cx=cw - int(0.3 * EMU), cy=int(0.6 * EMU))
    S.append(s)

    # 4 — why nobody built it
    s = Slide(4)
    s.kicker("Why nobody has built this")
    s.title([("THE DATA IS OPEN, AND ALMOST ", INK), ("UNUSABLE", RED)], size=30)
    s.body([
        [("There is no prose in it.", 15, INK, BODY, True)], None,
        [("267,187 rows carry no description field — only short category codes. "
          "2,982 titles exist, but the top thirty cover 84.9% of every row, and one "
          "is 60,641 identical strings.", 12.5, INK2)], None,
        [("Index the rows and retrieval becomes a coin flip.", 12.5, INK2)],
    ], y=int(2.7 * EMU), cx=int(5.7 * EMU), cy=int(3.4 * EMU))
    s.body([
        [("And most of it isn't residents.", 15, INK, BODY, True)], None,
        [("57% of the file is city staff logging their own rounds. Skip that filter and "
          "the app says “eleven neighbours reported this too” when seven were "
          "an inspector.", 12.5, INK2)], None,
        [("That is the difference between solidarity and a warm lie.", 12, GOLD, MONO)],
    ], x=MARGIN + int(6.1 * EMU), y=int(2.7 * EMU), cx=int(6.0 * EMU), cy=int(3.4 * EMU))
    S.append(s)

    # 5 — the answer
    s = Slide(5)
    s.kicker("The answer")
    cardx, cardw = MARGIN, int(6.9 * EMU)
    s.panel(cardx, int(1.4 * EMU), cardw, int(3.9 * EMU))
    s.shapes.append(rect(s._id(), cardx, int(1.4 * EMU), cardw, int(0.42 * EMU), "2A2417"))
    s.body([[("WORTH PUSHING ON", 9, GOLD, MONO, True)]],
           x=cardx + int(0.25 * EMU), y=int(1.5 * EMU), cx=int(4 * EMU), cy=int(0.3 * EMU))
    s.body([[("No — ", 22, INK, DISPLAY, True), ("9 residents", 22, BLUE, DISPLAY, True),
             (" reported rodent activity on 328 Dartmouth St in 2025.", 22, INK, DISPLAY, True)]],
           x=cardx + int(0.25 * EMU), y=int(2.0 * EMU), cx=cardw - int(0.5 * EMU),
           cy=int(1.3 * EMU))
    s.body([
        [("The city logged 4 more itself, on top of the resident reports.", 12, INK2)],
        [("ISD is the department that handles these.", 12, INK2)],
        [("12 of the cases there closed as “noted only” — recorded, with no fix "
          "logged.", 12, GOLD)],
    ], x=cardx + int(0.25 * EMU), y=int(3.5 * EMU), cx=cardw - int(0.5 * EMU),
       cy=int(1.6 * EMU))
    rx = MARGIN + int(7.3 * EMU)
    s.title([("LEGITIMACY FIRST. ", INK), ("LOGISTICS SECOND.", RED)], int(1.5 * EMU), 26)
    s.shapes[-1] = textbox(99, rx, int(1.5 * EMU), int(4.7 * EMU), int(2.0 * EMU),
                           [[("LEGITIMACY FIRST. ", 26, INK, DISPLAY, True),
                             ("LOGISTICS SECOND.", 26, RED, DISPLAY, True)]], spacing=95)
    s.body([
        [("The opening sentence is the one that dissolves the shame. The department name, "
          "the timeline, the parcel history — all of it comes after.", 12.5, INK2)], None,
        [("Every figure traces to a real case ID that opens the city's own record. "
          "Citations are bound from retrieved rows, so the model cannot invent one.",
          11, DIM, MONO)],
    ], x=rx, y=int(3.5 * EMU), cx=int(4.7 * EMU), cy=int(2.6 * EMU))
    S.append(s)

    # 6 — how it works
    s = Slide(6)
    s.kicker("How it works")
    s.title([("THREE GUARDRAILS, ", INK), ("VISIBLE ON SCREEN", BLUE)], size=26)
    steps = [("(1)", "Classify intent — out of scope or personal? refuse, never search", True),
             ("->", "Hard filters — street, category, residents only, from THIS turn only", False),
             ("->", "Stage 1 — citywide category card", False),
             ("->", "Stage 2 — street-level card inside that category", False),
             ("(2)", "Sensitivity gate — address detail withheld unless asked for", True),
             ("->", "Score floor — no match, say “I don't have a source I trust”", False),
             ("(3)", "Output — every claim bound to a field, or it isn't written", True)]
    y = int(2.35 * EMU)
    for mark, text, hot in steps:
        s.panel(MARGIN, y, int(7.1 * EMU), int(0.52 * EMU))
        if hot:
            s.shapes.append(rect(s._id(), MARGIN, y, int(0.045 * EMU),
                                 int(0.52 * EMU), BLUE))
        s.body([[(f"{mark}  {text}", 10.5, BLUE if hot else INK2, MONO)]],
               x=MARGIN + int(0.2 * EMU), y=y + int(0.13 * EMU),
               cx=int(6.9 * EMU), cy=int(0.35 * EMU))
        y += int(0.63 * EMU)
    rx = MARGIN + int(7.5 * EMU)
    s.body([
        [("Ask for a landlord's phone number and the input guard blocks it before any "
          "search runs.", 13, INK2)], None,
        [("(1) Input      BLOCKED", 11, RED, MONO, True)],
        [("(2) Retrieval  NEVER RAN", 11, RED, MONO, True)],
        [("(3) Output     REFUSED", 11, RED, MONO, True)], None,
        [("Being told nothing is honest beats being told something plausible.",
          11, DIM, MONO)],
    ], x=rx, y=int(2.4 * EMU), cx=int(4.5 * EMU), cy=int(3.8 * EMU))
    S.append(s)

    # 7 — priority board
    s = Slide(7)
    s.kicker("The priority board")
    s.title([("BOSTON'S QUEUE HAS ", INK), ("NO SEVERITY FIELD.", RED)], size=26)
    s.body([
        [("A rat infestation and a misplaced trash barrel enter the same queue, with the "
          "same clock.", 14, INK)], None,
        [("Our first ranking let parking enforcement — 22% of the file — bury everything "
          "that can actually hurt someone. Crowd size now goes through a log, so tier does "
          "the work.", 12, INK2)], None,
        [("Top 40 is now 24 safety + 16 habitability. Zero parking.", 12.5, INK, BODY, True)],
    ], y=int(2.6 * EMU), cx=int(5.7 * EMU), cy=int(3.4 * EMU))
    rows = [("P1 Safety", "14.2%", "19.8%", "Human, now", INK),
            ("P2 Home", "7.0%", "63.5%", "Human, scheduled", RED),
            ("P3 Routine", "74.6%", "30.0%", "System proposes", INK),
            ("P4 Admin", "4.2%", "7.8%", "Fully automated", INK)]
    tx = MARGIN + int(6.1 * EMU)
    s.body([[("TIER            SHARE    NOTED ONLY   WHO HANDLES IT", 9, DIM, MONO)]],
           x=tx, y=int(2.6 * EMU), cx=int(6.0 * EMU), cy=int(0.3 * EMU))
    y = int(3.0 * EMU)
    for name, share, noted, who, c in rows:
        s.body([[(f"{name:<15} {share:<8} ", 11, BLUE, MONO),
                 (f"{noted:<12}", 11, c, MONO, c == RED),
                 (who, 11, INK2, MONO)]],
               x=tx, y=y, cx=int(6.0 * EMU), cy=int(0.35 * EMU))
        y += int(0.45 * EMU)
    s.body([[("78.8% of the queue is routine or transactional — and it is choking the 21% "
              "that needs a person.", 10.5, DIM, MONO)]],
           x=tx, y=int(5.1 * EMU), cx=int(6.0 * EMU), cy=int(0.8 * EMU))
    S.append(s)

    # 8 — the four tiers
    s = Slide(8)
    s.kicker("The four priority tiers")
    s.title([("THEY ANSWER ONE QUESTION: ", INK), ("WHO SHOULD TOUCH THIS?", RED)], size=24)
    s.body([[("Not is this real — all 267,187 rows are real people. Nothing is discarded, "
              "only routed.", 11.5, INK2)]],
           y=int(2.1 * EMU), cx=int(11 * EMU), cy=int(0.4 * EMU))
    tiers = [("P1 · SAFETY", "Human, now", RED,
              "Someone can be physically hurt and the harm is irreversible.",
              "83%", "OVERDUE ON “MAKE SAFE” — WORST IN THE FILE", "14.2% of volume"),
             ("P2 · HOME", "Human, scheduled — return visit", GOLD,
              "It makes a home unlivable, it recurs, one visit doesn't end it.",
              "63.5%", "CLOSED “NOTED ONLY” vs A 30% BASELINE", "7.0% of volume"),
             ("P3 · ROUTINE", "System proposes, human approves", BLUE,
              "Real, needs a decision — but repetitive enough to batch.",
              "74.6%", "OF THE WHOLE QUEUE · PARKING IS 60,641", "32.4% still open"),
             ("P4 · ADMIN", "Fully automated, no human", DIM,
              "Zero judgment. You either qualify for a bin or you don't.",
              "10.5d", "MEDIAN FOR A BIN · 0.1% OPEN, 38.5% LATE", "4.2% of volume")]
    for i, (name, who, c, crit, big, biglab, vol) in enumerate(tiers):
        x, cw = col(i)
        s.panel(x, int(2.7 * EMU), cw, int(3.3 * EMU), accent=c)
        pad = x + int(0.16 * EMU)
        iw = cw - int(0.32 * EMU)
        s.body([[(name, 15, c, DISPLAY, True)]], x=pad, y=int(2.9 * EMU), cx=iw, cy=int(0.35 * EMU))
        s.body([[(who.upper(), 8, INK, MONO, True)]], x=pad, y=int(3.28 * EMU), cx=iw, cy=int(0.4 * EMU))
        s.body([[(crit, 9.5, INK2)]], x=pad, y=int(3.75 * EMU), cx=iw, cy=int(1.0 * EMU))
        s.body([[(big, 22, c, DISPLAY, True)]], x=pad, y=int(4.75 * EMU), cx=iw, cy=int(0.5 * EMU))
        s.body([[(biglab, 7.5, DIM, MONO)]], x=pad, y=int(5.25 * EMU), cx=iw, cy=int(0.5 * EMU))
        s.body([[(vol, 8, DIM, MONO)]], x=pad, y=int(5.72 * EMU), cx=iw, cy=int(0.25 * EMU))
    s.body([[("These assignments are ours, not the city's — the schema carries no severity "
              "field, and that absence is the finding. Encampments in particular sits "
              "awkwardly in P2.", 9, DIM, MONO)]],
           y=int(6.2 * EMU), cx=int(11.5 * EMU), cy=int(0.6 * EMU))
    S.append(s)

    # 9 — the map
    s = Slide(9)
    s.kicker("The map is the argument")
    s.title([("YOU SEE WHAT'S BEING IGNORED ", INK), ("BEFORE YOU READ A WORD", BLUE)], size=25)
    s.body([
        [("Pin height is priority. The skyline shows you the backlog.", 12.5, INK2)], None,
        [("Ground ring is how many neighbours reported the same thing.", 12.5, INK2)], None,
        [("Colour is what kind of problem — six categories, not 155 city codes.",
          12.5, INK2)], None,
        [("Click any pin and it opens the answer for that street.", 12.5, INK2)],
    ], y=int(2.7 * EMU), cx=int(6.0 * EMU), cy=int(3.2 * EMU))
    cats = [("Pests & rodents", RED), ("Streets & sidewalks", "4B87E8"),
            ("Trash & dumping", GREEN), ("Lights & signals", "B76BD9"),
            ("Housing conditions", GOLD), ("Vehicles & parking", "E85A93")]
    cx0 = MARGIN + int(6.5 * EMU)
    for i, (name, c) in enumerate(cats):
        yy = int(2.7 * EMU) + i * int(0.42 * EMU)
        s.shapes.append(rect(s._id(), cx0, yy + int(0.06 * EMU),
                             int(0.13 * EMU), int(0.13 * EMU), c))
        s.body([[(name, 12, INK2)]], x=cx0 + int(0.28 * EMU), y=yy,
               cx=int(4.5 * EMU), cy=int(0.32 * EMU))
    s.body([[("Three.js, extruded from the city's own neighbourhood GeoJSON. "
              "No tile server, no map vendor, no network.", 10.5, DIM, MONO)]],
           x=cx0, y=int(5.4 * EMU), cx=int(5.2 * EMU), cy=int(0.8 * EMU))
    S.append(s)

    # 10 — what it costs
    s = Slide(10)
    s.kicker("What it costs to run")
    s.title([("ONE HTML FILE. ", INK), ("NOTHING ELSE.", RED)], size=32)
    layers = [("Data", "8,898 cards from 267,187 rows, 58 streets of parcel facts, 26 polygons"),
              ("Retrieval", "Plain JavaScript. Filters, two stages, gate, floor"),
              ("Answer", "Assembled from counted fields, never generated"),
              ("Map", "Three.js from city GeoJSON — no tile server"),
              ("State", "localStorage — votes, reports, points"),
              ("LLM", "Granite 3.1 8B on local Ollama, optional, keyword fallback")]
    y = int(2.7 * EMU)
    for k, v in layers:
        s.body([[(f"{k:<11}", 10.5, BLUE, MONO, True), (v, 10.5, INK2, MONO)]],
               y=y, cx=int(7.2 * EMU), cy=int(0.35 * EMU))
        y += int(0.45 * EMU)
    rx = MARGIN + int(7.6 * EMU)
    s.body([
        [("The build step is offline: a Python script rolls 267,000 coded rows into "
          "readable cards in about four seconds, with zero model calls.", 13, INK)], None,
        [("No server. No API keys. No per-query cost. On dead conference wifi, on a bus, "
          "in a basement apartment — it still answers.", 10.5, DIM, MONO)], None,
        [("SERVING COST: A STATIC FILE.", 17, BLUE, DISPLAY, True)],
    ], x=rx, y=int(2.6 * EMU), cx=int(4.4 * EMU), cy=int(3.6 * EMU))
    S.append(s)

    # 11 — limits + close
    s = Slide(11)
    s.kicker("The honest limits")
    s.body([
        [("The local model is optional. Granite classifies free-text reports when "
          "reachable; otherwise a keyword router takes over and the interface says which "
          "decided.", 11.5, INK2)], None,
        [("Property Assessment covers 58 streets, not all of Boston — the city's API caps "
          "at 32,000 rows.", 11.5, INK2)], None,
        [("Approximate street matches say so, rather than passing another street's numbers "
          "off as yours.", 11.5, INK2)], None,
        [("Reports stay on the device. A community signal, not a filing — real reports "
          "still go to 311.", 11.5, INK2)],
    ], y=int(1.5 * EMU), cx=int(6.2 * EMU), cy=int(4.6 * EMU))
    rx = MARGIN + int(6.9 * EMU)
    s.shapes.append(textbox(90, rx, int(2.3 * EMU), int(5.1 * EMU), int(2.6 * EMU),
                            [[("Stop shouting into a void.", 28, INK, DISPLAY, True)],
                             [("Start being someone ", 28, INK, DISPLAY, True),
                              ("with a case.", 28, BLUE, DISPLAY, True)]], spacing=100))
    s.body([[("Street Signal · built on Analyze Boston open data", 10.5, DIM, MONO)]],
           x=rx, y=int(5.1 * EMU), cx=int(5.1 * EMU), cy=int(0.4 * EMU))
    S.append(s)

    return [x.xml() for x in S]


# ------------------------------------------------------------- packaging ----
def write(slides):
    n = len(slides)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          + "".join(f'<Override PartName="/ppt/slides/slide{i+1}.xml" '
                    f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                    for i in range(n)) + '</Types>')

    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
                 '</Relationships>')

    sldIds = "".join(f'<p:sldId id="{256+i}" r:id="rId{i+2}"/>' for i in range(n))
    pres = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            f'<p:sldIdLst>{sldIds}</p:sldIdLst>'
            f'<p:sldSz cx="{W}" cy="{H}"/><p:notesSz cx="{H}" cy="{W}"/></p:presentation>')

    pres_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
                 + "".join(f'<Relationship Id="rId{i+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>'
                           for i in range(n))
                 + f'<Relationship Id="rId{n+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
                 '</Relationships>')

    empty_tree = ('<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/>'
                  '<p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
                  '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>'
                  '</a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
                  '<p:clrMap bg1="dk1" tx1="lt1" bg2="dk2" tx2="lt2" accent1="accent1" '
                  'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
                  'accent6="accent6" hlink="hlink" folHlink="folHlink"/>')

    master = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
              'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
              + empty_tree +
              '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
              '</p:sldMaster>')
    master_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
                   '</Relationships>')

    layout = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
              'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">'
              '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/>'
              '<p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
              '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>'
              '</a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
              '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    layout_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
                   '</Relationships>')

    def scheme():
        cols = [("dk1", "000000"), ("lt1", "FFFFFF"), ("dk2", BG), ("lt2", INK),
                ("accent1", BLUE), ("accent2", RED), ("accent3", GOLD),
                ("accent4", GREEN), ("accent5", "B76BD9"), ("accent6", "E85A93"),
                ("hlink", BLUE), ("folHlink", DIM)]
        return "".join(f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in cols)

    theme = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="StreetSignal">'
             '<a:themeElements><a:clrScheme name="StreetSignal">' + scheme() + '</a:clrScheme>'
             f'<a:fontScheme name="StreetSignal"><a:majorFont><a:latin typeface="{DISPLAY}"/>'
             '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
             f'<a:minorFont><a:latin typeface="{BODY}"/><a:ea typeface=""/><a:cs typeface=""/>'
             '</a:minorFont></a:fontScheme>'
             '<a:fmtScheme name="StreetSignal">'
             '<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
             '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
             '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
             '<a:lnStyleLst><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
             '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
             '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
             '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>'
             '<a:effectStyle><a:effectLst/></a:effectStyle>'
             '<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
             '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
             '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
             '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
             '</a:fmtScheme></a:themeElements></a:theme>')

    slide_rel = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                 '</Relationships>')

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        z.writestr("ppt/theme/theme1.xml", theme)
        for i, xml in enumerate(slides):
            z.writestr(f"ppt/slides/slide{i+1}.xml", xml)
            z.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", slide_rel)

    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {n} slides)")


if __name__ == "__main__":
    write(build())
