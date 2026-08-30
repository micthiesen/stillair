#!/usr/bin/env python3
"""Build the Stillair printable integration field-guide binder."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "stillair-integration-field-guides.pdf"
ASSETS = ROOT / "docs" / "field-guides" / "assets"

PAGE_W, PAGE_H = letter
MARGIN = 30
CONTENT_W = PAGE_W - 2 * MARGIN

INK = colors.HexColor("#191919")
MUTED = colors.HexColor("#5d6168")
LINE = colors.HexColor("#d4d7dc")
PAPER = colors.HexColor("#fbfaf6")
WHITE = colors.white
BLUE = colors.HexColor("#1769e0")
BLUE_BG = colors.HexColor("#eaf2ff")
GREEN = colors.HexColor("#24843a")
GREEN_BG = colors.HexColor("#eaf6ec")
RED = colors.HexColor("#d62828")
RED_BG = colors.HexColor("#fff0f0")
PURPLE = colors.HexColor("#7540b8")
PURPLE_BG = colors.HexColor("#f3edfb")
AMBER = colors.HexColor("#9a6200")
AMBER_BG = colors.HexColor("#fff5d8")
GRAY_BG = colors.HexColor("#f1f2f4")


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


class Sheet:
    def __init__(self, canvas: Canvas, sheet_id: str, title: str, page_no: int, status: str = "FIELD GUIDE"):
        self.c = canvas
        self.sheet_id = sheet_id
        self.title = title
        self.page_no = page_no
        self.status = status
        self.y = PAGE_H - 88
        self._header()

    def _header(self) -> None:
        c = self.c
        c.setFillColor(PAPER)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        badge_width = max(98, stringWidth(self.status, "Helvetica-Bold", 8) + 24)
        badge_width = min(150, badge_width)
        badge_x = PAGE_W - MARGIN - badge_width
        heading = f"{self.sheet_id}  {self.title}"
        heading_size = 22.0
        while heading_size > 15 and stringWidth(heading, "Helvetica-Bold", heading_size) > badge_x - MARGIN - 12:
            heading_size -= 0.5
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", heading_size)
        c.drawString(MARGIN, PAGE_H - 38, heading)
        badge_color = AMBER if "HOLD" in self.status else BLUE
        c.setFillColor(badge_color)
        c.roundRect(badge_x, PAGE_H - 54, badge_width, 24, 12, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(badge_x + badge_width / 2, PAGE_H - 46, self.status)
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(MARGIN, PAGE_H - 64, PAGE_W - MARGIN, PAGE_H - 64)

    def footer(self, sources: str, tests: str = "") -> None:
        c = self.c
        c.setStrokeColor(LINE)
        c.line(MARGIN, 35, PAGE_W - MARGIN, 35)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7.5)
        source_lines = wrap(f"SOURCE: {sources}", "Helvetica", 7.5, 350)
        c.drawString(MARGIN, 24, source_lines[0])
        if len(source_lines) > 1:
            c.drawString(MARGIN, 14, source_lines[1])
        if tests:
            test_text = f"TESTS: {tests}"
            test_size = 7.5
            while test_size > 5.5 and stringWidth(test_text, "Helvetica-Bold", test_size) > 190:
                test_size -= 0.25
            c.setFont("Helvetica-Bold", test_size)
            c.drawRightString(PAGE_W - MARGIN, 24, test_text)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(PAGE_W - MARGIN, 14, f"PAGE {self.page_no}")

    def panel(self, title: str, height: float, color=WHITE, border=LINE, title_color=INK) -> tuple[float, float, float, float]:
        x = MARGIN
        y = self.y - height
        self.c.setFillColor(color)
        self.c.setStrokeColor(border)
        self.c.setLineWidth(1)
        self.c.roundRect(x, y, CONTENT_W, height, 10, stroke=1, fill=1)
        self.c.setFillColor(title_color)
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(x + 14, y + height - 22, title)
        self.y = y - 10
        return x, y, CONTENT_W, height

    def text(self, text: str, x: float, y: float, width: float, size: float = 9.5, color=INK, bold=False, leading: float | None = None) -> float:
        font = "Helvetica-Bold" if bold else "Helvetica"
        leading = leading or size * 1.28
        self.c.setFillColor(color)
        self.c.setFont(font, size)
        for line in wrap(text, font, size, width):
            self.c.drawString(x, y, line)
            y -= leading
        return y

    def checkboxes(self, items: Iterable[str], x: float, y: float, width: float, size: float = 9.2, gap: float = 7) -> float:
        for item in items:
            lines = wrap(item, "Helvetica", size, width - 24)
            leading = size * 1.22
            box_y = y + size * 0.72 - 11
            self.c.setStrokeColor(INK)
            self.c.setLineWidth(1.2)
            self.c.rect(x, box_y, 11, 11, stroke=1, fill=0)
            self.c.setFillColor(INK)
            self.c.setFont("Helvetica", size)
            line_y = y
            for line in lines:
                self.c.drawString(x + 20, line_y, line)
                line_y -= leading
            text_height = size + (len(lines) - 1) * leading
            y -= max(11, text_height) + gap
        return y

    def checkbox_grid(self, rows: Iterable[tuple[str, str]], x: float, y: float, column_width: float, size: float = 9, gap: float = 8) -> float:
        """Draw two checkbox columns on shared row baselines."""
        leading = size * 1.22
        for left_text, right_text in rows:
            row_heights: list[float] = []
            for column, item in enumerate((left_text, right_text)):
                item_x = x + column * column_width
                lines = wrap(item, "Helvetica", size, column_width - 32)
                box_y = y + size * 0.72 - 11
                self.c.setStrokeColor(INK)
                self.c.setLineWidth(1.2)
                self.c.rect(item_x, box_y, 11, 11, stroke=1, fill=0)
                self.c.setFillColor(INK)
                self.c.setFont("Helvetica", size)
                line_y = y
                for line in lines:
                    self.c.drawString(item_x + 20, line_y, line)
                    line_y -= leading
                row_heights.append(max(11, size + (len(lines) - 1) * leading))
            y -= max(row_heights) + gap
        return y

    def warning(self, text: str, x: float, y: float, width: float, color=RED, bg=RED_BG) -> float:
        lines = wrap(text, "Helvetica-Bold", 9, width - 24)
        height = 18 + len(lines) * 11
        self.c.setFillColor(bg)
        self.c.setStrokeColor(color)
        self.c.setLineWidth(1)
        self.c.roundRect(x, y - height, width, height, 7, stroke=1, fill=1)
        self.c.setFillColor(color)
        self.c.setFont("Helvetica-Bold", 9)
        line_y = y - 17
        for line in lines:
            self.c.drawString(x + 12, line_y, line)
            line_y -= 11
        return y - height

    def stop(self, text: str) -> None:
        h = 42
        y = 48
        self.c.setFillColor(BLUE_BG)
        self.c.setStrokeColor(BLUE)
        self.c.setLineWidth(1)
        self.c.roundRect(MARGIN, y, CONTENT_W, h, 8, stroke=1, fill=1)
        self.c.setFillColor(BLUE)
        self.c.setFont("Helvetica-Bold", 9.5)
        self.c.drawString(MARGIN + 12, y + 25, "STOP / HANDOFF")
        self.text(text, MARGIN + 112, y + 25, CONTENT_W - 126, size=8.5, color=INK)


def arrow(c: Canvas, x1: float, y1: float, x2: float, y2: float, color=BLUE, width=3) -> None:
    import math

    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 8
    for delta in (2.55, -2.55):
        c.line(x2, y2, x2 + head * math.cos(angle + delta), y2 + head * math.sin(angle + delta))


def stack_boxes(c: Canvas, labels: list[str], x: float, y: float, width: float, box_h: float = 32, color=BLUE_BG) -> None:
    for index, label in enumerate(labels):
        box_y = y - index * (box_h + 10)
        c.setFillColor(color if index % 2 == 0 else WHITE)
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.2)
        c.roundRect(x, box_y, width, box_h, 6, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + width / 2, box_y + box_h / 2 - 2, label)
        if index < len(labels) - 1:
            arrow(c, x + width / 2, box_y - 1, x + width / 2, box_y - 9, BLUE, 2)


def fit_image(c: Canvas, path: Path, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    """Fit a transparent image inside a box and return its drawn bounds."""
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    c.drawImage(image, dx, dy, dw, dh, mask="auto")
    return dx, dy, dw, dh


def numbered(c: Canvas, n: int, x: float, y: float, color=AMBER) -> None:
    c.setFillColor(color)
    c.setStrokeColor(WHITE)
    c.setLineWidth(1)
    c.circle(x, y, 10, stroke=1, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x, y - 3, str(n))


def step_strip(c: Canvas, labels: list[str], x: float, y: float, w: float, color=BLUE) -> None:
    gap = 8
    bw = (w - gap * (len(labels) - 1)) / len(labels)
    for i, label in enumerate(labels):
        bx = x + i * (bw + gap)
        c.setFillColor(BLUE_BG if color == BLUE else GREEN_BG)
        c.setStrokeColor(color)
        c.roundRect(bx, y, bw, 34, 6, stroke=1, fill=1)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 7.4)
        lines = wrap(label, "Helvetica-Bold", 7.4, bw - 8)
        ty = y + 20 + (len(lines) - 1) * 4
        for line in lines:
            c.drawCentredString(bx + bw / 2, ty, line)
            ty -= 9
        if i < len(labels) - 1:
            arrow(c, bx + bw + 1, y + 17, bx + bw + gap - 1, y + 17, color, 1)


def mini_card(c: Canvas, title: str, body: str, x: float, y: float, w: float, h: float, color=BLUE, bg=WHITE) -> None:
    c.setFillColor(bg)
    c.setStrokeColor(color)
    c.roundRect(x, y, w, h, 7, stroke=1, fill=1)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 9, y + h - 16, title)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7.8)
    ty = y + h - 29
    for line in wrap(body, "Helvetica", 7.8, w - 18):
        c.drawString(x + 9, ty, line)
        ty -= 9.5


def page_0a(c: Canvas, n: int) -> None:
    s = Sheet(c, "0A", "Integration Roadmap", n)
    x, y, w, h = s.panel("HOW TO USE THIS BINDER", 75, BLUE_BG, BLUE, BLUE)
    s.text("Use one sheet at the bench. Check each box only after the action is complete. Record measurements in testing/test-matrix.csv. A HOLD badge means prerequisites are unresolved; do not improvise past it.", x + 14, y + 38, w - 28, 10)

    x, y, w, h = s.panel("DEPENDENCY SPINE", 250)
    stages = [
        ("1", "Complete boards and cables"),
        ("2", "Prove PCB-01 without motor"),
        ("3", "Measure bare GL100, no blades"),
        ("4", "Integrate and balance rotor"),
        ("5", "Workshop 216 RPM proof"),
        ("6", "Ceiling loaded commissioning"),
    ]
    box_w = 160
    box_h = 48
    for i, (num, label) in enumerate(stages):
        col = i % 3
        row = i // 3
        bx = x + 14 + col * 174
        by = y + 158 - row * 85
        c.setFillColor(BLUE_BG if i < 3 else PURPLE_BG)
        c.setStrokeColor(BLUE if i < 3 else PURPLE)
        c.setLineWidth(1.2)
        c.roundRect(bx, by, box_w, box_h, 8, stroke=1, fill=1)
        c.setFillColor(BLUE if i < 3 else PURPLE)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(bx + 10, by + 28, num)
        s.text(label, bx + 34, by + 29, box_w - 42, 8.5, INK, True, 10)
        if col < 2:
            arrow(c, bx + box_w + 2, by + 24, bx + box_w + 12, by + 24, MUTED, 1.5)

    x, y, w, h = s.panel("CURRENT CHECKPOINT", 112, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "PCB-01 and PCB-02 hand-population complete and inspected.",
        "Power, motor, Hall, and programming harnesses built and continuity-checked.",
        "PCB-01 passes PCB-01 through PCB-04 and TACH-01 without the motor.",
    ], x + 14, y + 70, w - 28, 9.5)

    x, y, w, h = s.panel("NON-NEGOTIABLE BOUNDARIES", 155, RED_BG, RED, RED)
    s.checkboxes([
        "Desk first: no-motor checks, then only released bare-motor work with no blades.",
        "Check retention, clearance, balance, and runout unpowered on the installed plate.",
        "First loaded motion starts at the lowest useful speed with continuous observation.",
        "Use normal safety firmware plus the persistent CLI; no general permissive build.",
        "Keep long USB J6 outside the sweep; cutoff reachable outside it; unplugging is not braking.",
    ], x + 14, y + 112, w - 28, 9.1)
    s.footer("docs/integration.md; docs/decisions.md; testing/test-matrix.csv")


def page_1a(c: Canvas, n: int) -> None:
    s = Sheet(c, "1A", "Complete PCB-01 and PCB-02", n)
    x, y, w, h = s.panel("TOOLS", 58, GRAY_BG)
    s.text("ESD mat - microscope - temperature-controlled iron/hot air - flux - solder wick - DMM", x + 14, y + 22, w - 28, 9.5, bold=True)

    x, y, w, h = s.panel("PCB-01 HAND-POPULATION", 245)
    s.checkbox_grid([
        ("Inspect the assembled board for shipping damage and solder bridges.", "Fit U8: LM2907M/NOPB. Match pin 1 to board marking."),
        ("Fit C1 and C2: Panasonic FR 470 uF / 50 V. Observe polarity and silkscreen.", "Bridge C34 with KEMET C1206C104K3GACTU, 100 nF C0G, across the 0603 site."),
        ("Fit J1: Molex 43045-0200 power header.", "Bridge F1 pads. The wall-side 3 A fuse is then mandatory."),
        ("Fit J2: Molex 43650-0300 phase header.", "Inspect every hand joint and verify no RAW24-to-ground short."),
    ], x + 14, y + 195, w / 2 - 2, 8.7)

    x, y, w, h = s.panel("PCB-02 HAND-ASSEMBLY", 165, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "Fit U1: DRV5033FAQDBZR, with package orientation matching PCB marking.",
        "Fit C1: 100 nF / 50 V X7R 0603 local bypass.",
        "Fit J1: S3B-PH-K-S side-entry JST-PH.",
        "Keep every component on the magnet-facing side; solder before mounting to BR-100.",
        "Inspect under magnification and continuity-check 3V3, HALL_TACH, and AGND.",
    ], x + 14, y + 120, w - 28, 9)

    s.warning("DO NOT POWER either board until 1B harness polarity and the unpowered continuity checks are complete.", MARGIN, 150, CONTENT_W)
    s.stop("Both boards are fully populated, photographed, and pass unpowered short/polarity inspection.")
    s.footer("docs/electrical.md, PCB-01 mechanical definition and SCH-06; bom/bom.csv, PCB fab rows")


def page_1b(c: Canvas, n: int) -> None:
    s = Sheet(c, "1B", "Build and Verify Harnesses", n)
    x, y, w, h = s.panel("CONNECTOR TRUTH", 220)
    rows = [
        ("J1 POWER", "1 RAW24", "2 0V"),
        ("J2 MOTOR", "1 W", "2 V   |   3 U"),
        ("J3 / PCB-02 J1", "1 3V3", "2 HALL_TACH   |   3 AGND"),
        ("J5 I2C", "GND, 3V3", "SDA, SCL"),
        ("J7 PROGRAM", "3V3, TX, RX", "EN, BOOT, GND"),
    ]
    col_x = [x + 14, x + 155, x + 330]
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED)
    c.drawString(col_x[0], y + 170, "CONNECTOR")
    c.drawString(col_x[1], y + 170, "FIRST PINS")
    c.drawString(col_x[2], y + 170, "REMAINDER")
    yy = y + 148
    for ref, a, b in rows:
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.line(x + 14, yy - 5, x + w - 14, yy - 5)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8.7)
        c.drawString(col_x[0], yy + 3, ref)
        c.setFont("Helvetica", 8.7)
        c.drawString(col_x[1], yy + 3, a)
        c.drawString(col_x[2], yy + 3, b)
        yy -= 25

    x, y, w, h = s.panel("BUILD CHECKLIST", 230)
    s.checkboxes([
        "Power harness: Belden 5300UE 18/2 to Micro-Fit; preserve +24 V and 0 V end-to-end.",
        "Motor harness: use 18 AWG contacts; label connector positions W, V, U even if motor flying leads are initially unlabeled.",
        "Hall harness: PHR-3 to PHR-3 straight-through, using molded No.1 marks at both ends.",
        "Programming lead: J7 pin 1 is board 3V3, not a power input.",
        "Pull-test every crimp, then continuity-check each contact and verify no cross-continuity.",
        "Record harness length, wire colors, and contact orientation before sleeving.",
    ], x + 14, y + 182, w - 28, 9.2)

    s.warning("J7 pin 1 ties directly to board 3V3. Never connect a programmer that actively drives 3.3 V while 24 V is connected.", MARGIN, 181, CONTENT_W)
    s.warning("A swapped Hall contact can leave the tach silently dead. Require 1-to-1, 2-to-2, 3-to-3 and no cross-continuity before first power.", MARGIN, 140, CONTENT_W)
    s.stop("Every harness is labeled, pull-tested, and has a signed continuity result. No device is powered yet.")
    s.footer("docs/electrical.md, SCH-07 connectors; testing/test-matrix.csv", "TACH-06")


def page_1c(c: Canvas, n: int) -> None:
    s = Sheet(c, "1C", "PCB-01 First Power and Safety Chain", n)
    x, y, w, h = s.panel("SAFE TEST SETUP", 145, RED_BG, RED, RED)
    s.checkboxes([
        "Disconnect motor phases and keep the rotor absent.",
        "Use the fused 24 V bench path with current limiting and a physical cutoff within reach.",
        "Connect console/programmer without driving board 3V3 from J7.",
        "Place probes before power; use spring ground for VM transient measurements.",
    ], x + 14, y + 102, w - 28, 9.2)

    x, y, w, h = s.panel("CHECK IN THIS ORDER", 295)
    items = [
        "PCB-01: power briefly; verify 24 V, 3.3 V, AVDD, DVDD, DRVOFF, current draw, and no abnormal heating.",
        "PCB-03: force PGOOD, WDO, manual clear, and OVERSPEED_N low one at a time. DRVOFF must rise without ESP help.",
        "PCB-03B: static WDI must time out in 1.44-1.76 s; WDO pulse about 200 ms. Falling edges at 2 Hz prevent timeout.",
        "PCB-03D: repeat cold and slow-ramp power-up 20 times; U6 /PRE must release after TACH_PGOOD_N.",
        "PCB-04: remove and restore 24 V. Fan remains disabled for at least 10 s and until a new command plus explicit arm.",
        "TACH-01: inject 0-3.3 V at HALL_TACH with bridge disabled, 1-3% duty, and at least 30 s settling.",
        "Record reset near 3.00 Hz and trip near 3.33 Hz; the persistent lock resets only on genuine power cycle.",
    ]
    s.checkboxes(items, x + 14, y + 246, w - 28, 8.9)

    x, y, w, h = s.panel("PASS LIMITS", 112, GREEN_BG, GREEN, GREEN)
    s.text("VM insertion target: <=35 V; coast/cutoff/stall/reversal checks occur later with the guarded motor. Watchdog: 1.44-1.76 s. Power-up: 20/20 correct presets. Tach: reset about 3.00 Hz, trip about 3.33 Hz. Any automatic re-arm blocks release.", x + 14, y + 68, w - 28, 9.0, bold=True)
    s.stop("PCB-01 through PCB-04 and TACH-01 have recorded pass/fail results. Do not connect the motor after a failure.")
    s.footer("testing/test-matrix.csv; docs/electrical.md, safety and tach sections", "PCB-01, PCB-03/03B/03D, PCB-04, TACH-01")


def page_2a(c: Canvas, n: int) -> None:
    import math

    s = Sheet(c, "2A", "Ceiling Orientation and Primary Holes", n)
    x, y, w, h = s.panel("TEMPLATE ORIENTATION - VIEWED FROM THE ROOM", 355)
    cx, cy, r = x + 205, y + 185, 140
    c.setFillColor(WHITE)
    c.setStrokeColor(INK)
    c.setLineWidth(3)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.circle(cx, cy, 9, stroke=1, fill=0)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, cy + 14, "CENTER")

    # Power line points to the midpoint of the cable-clamp holes.
    c.setStrokeColor(GREEN)
    c.setDash(6, 4)
    c.line(cx, cy, cx + r, cy)
    c.setDash()
    for off in (-15, 15):
        c.setFillColor(GREEN_BG)
        c.setStrokeColor(GREEN)
        c.circle(cx + r - 5, cy + off, 5, stroke=1, fill=1)
    arrow(c, x + w - 30, cy, cx + r + 18, cy, BLUE, 5)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(cx + r + 30, cy + 28, "POWER SURFACE RUN")
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(cx + r + 30, cy - 15, "Aim midpoint of small-hole pair")
    c.drawString(cx + r + 30, cy - 27, "toward the incoming power.")

    # Rotate the plate so the cable line is horizontal: primary axis is 15 deg clockwise on page.
    angle = math.radians(-15)
    primary = []
    for sign in (-1, 1):
        px = cx + sign * 103 * math.cos(angle)
        py = cy + sign * 103 * math.sin(angle)
        primary.append((px, py))
        c.saveState()
        c.translate(px, py)
        c.rotate(-15)
        c.setFillColor(RED_BG)
        c.setStrokeColor(RED)
        c.setLineWidth(2.5)
        c.roundRect(-17, -9, 34, 18, 9, stroke=1, fill=1)
        c.circle(0, 0, 3.5, stroke=0, fill=1)
        c.restoreState()
    c.setStrokeColor(MUTED)
    c.setDash(5, 4)
    c.line(primary[0][0], primary[0][1], primary[1][0], primary[1][1])
    c.setDash()
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(primary[0][0] - 70, primary[0][1] + 18, "PRIMARY 1")
    c.drawString(primary[1][0] - 10, primary[1][1] - 28, "PRIMARY 2")
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy + 105, "PRIMARY CENTERS 130 mm APART")

    # Tether ray is exactly 90 deg from each primary ray.
    tether_angle = math.radians(-105)
    tx = cx + 120 * math.cos(tether_angle)
    ty = cy + 120 * math.sin(tether_angle)
    c.setStrokeColor(MUTED)
    c.setDash(5, 4)
    c.line(cx, cy, tx, ty)
    c.setDash()
    c.saveState()
    c.translate(tx, ty)
    c.rotate(-105)
    c.setStrokeColor(MUTED)
    c.setFillColor(GRAY_BG)
    c.roundRect(-18, -9, 36, 18, 9, stroke=1, fill=1)
    c.restoreState()
    c.setStrokeColor(RED)
    c.setLineWidth(3)
    c.line(tx - 13, ty - 13, tx + 13, ty + 13)
    c.line(tx - 13, ty + 13, tx + 13, ty - 13)
    c.setFillColor(PURPLE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(cx - 72, cy - 48, "90 deg")
    c.drawString(cx + 18, cy - 58, "90 deg")
    c.setFillColor(RED)
    c.drawString(tx - 85, ty - 24, "TETHER: DO NOT DRILL")

    x, y, w, h = s.panel("DRILL AND CLEAN", 190)
    s.checkboxes([
        "Confirm the known fan center and orient the template as shown.",
        "Mark only the centers of the two red 11 x 20 mm primary slots.",
        "Remove the template. Use a straight-shank ANSI bit in the M12 3404, or an SDS-plus ANSI bit only in an SDS-plus rotary hammer.",
        "Drill with a 3/8 in ANSI B212.15 carbide bit; never substitute 10 mm.",
        "Depth-stop both primary holes at about 75 mm.",
        "Peck-drill to clear dust and cool the tip; stop and rent SDS-plus if progress is poor.",
        "Brush and blow both holes clean per Simpson instructions.",
    ], x + 14, y + 145, w - 220, 8.7)
    c.setFillColor(GRAY_BG)
    c.setStrokeColor(MUTED)
    c.setLineWidth(1)
    c.rect(x + w - 190, y + 38, 165, 105, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + w - 175, y + 115, "PRIMARY HOLES")
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(x + w - 175, y + 82, "3/8 in x ~75 mm")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + w - 175, y + 56, "NO ANCHORS YET")
    s.stop("Two cleaned primary holes are ready. Leave all Titen HD anchors out until permanent installation.")
    s.footer("docs/install.md; docs/parts.md, MP-100 and Cable entry", "INS-01 later")


def page_2b(c: Canvas, n: int) -> None:
    s = Sheet(c, "2B", "Bench-Prepare and Anchor MP-100", n, "HOLD: RELEASE GATES OPEN")
    x, y, w, h = s.panel("BENCH ASSEMBLY - CEILING FACE UP", 245)
    s.checkboxes([
        "Insert the received SUS304 SP-100 from the ceiling face; seat flange fully in the double-D recess, metal on the pocket shoulder.",
        "Place three tiny spaced dots of neutral-cure RTV across the perimeter seam. Put none under the flange.",
        "Install 3 x ST-100 with 3 x M6 x 16 A4 flat-head screws from the ceiling face.",
        "Verify all three screw heads are flush or slightly below the ceiling face.",
        "Keep ceiling-face-up until RTV cures; tap/shake and confirm no metallic click.",
        "Leave off motor/carrier, rotor, catcher stack, electronics, clamps, and housing.",
    ], x + 14, y + 198, w - 28, 9)

    x, y, w, h = s.panel("OVERHEAD LIFT - EACH PRIMARY STACK", 170, BLUE_BG, BLUE, BLUE)
    stack_boxes(c, ["CEILING", "HARD-SPACER WASHER", "MP-100, 6 mm", "HEAD WASHER", "THD37300H HEAD"], x + 36, y + 116, 180, 18, BLUE_BG)
    s.text("Parts for both anchors", x + 250, y + 118, 260, 10, BLUE, True)
    s.checkboxes([
        "2 x Simpson THD37300H, 3/8 x 3 in.",
        "4 x Prime-Line 9080006 washers, about 2.5 mm thick.",
        "9/16 in socket and approved driver.",
    ], x + 250, y + 90, 255, 8.7)

    x, y, w, h = s.panel("INSTALLATION CHECK", 145)
    s.checkboxes([
        "Place one loose hard-spacer washer above MP-100 at each anchor during the lift; do not glue spacers to plate.",
        "Drive each anchor through head washer, MP-100 slot, hard spacer, and into cleaned concrete.",
        "Follow Simpson installation instructions; the screw anchor has no wedge-anchor set torque.",
        "Record model, spacing, embedment basis, plate seating, and any shimming under INS-01.",
    ], x + 14, y + 100, w - 28, 8.9)
    s.warning("ONE-INSTALL INTERFACE: do not install, remove, and reinstall Titen HDs. Mounting remains blocked until off-ceiling proof, tether, motor-bearing, and installation-approval gates close.", MARGIN, 136, CONTENT_W)
    s.stop("MP-100 is permanently seated on hard spacers, SP-100/ST-100 are captive, and INS-01 is recorded.")
    s.footer("docs/install.md, Mounting sequence; docs/integration.md, Before MP-100 is anchored", "INS-01")


def page_3a(c: Canvas, n: int) -> None:
    s = Sheet(c, "3A", "Stationary Stack Dry-Fit", n)
    x, y, w, h = s.panel("STACK ORDER", 250)
    stack_boxes(c, ["MP-100 CEILING PLATE", "3 x ST-100, 62 mm", "MC-100 CARRIER", "GL100 STATIONARY FACE"], x + 48, y + 170, 200, 34, BLUE_BG)
    s.text("Fasteners", x + 300, y + 182, 220, 10, BLUE, True)
    s.checkboxes([
        "MP-100 to ST-100: 3 x M6 x 16 flat-head from ceiling face.",
        "MC-100 to ST-100: 3 x M6 x 20 A4-80 with wedge-lock pairs.",
        "MC-100 to GL100 rear face: 4 x M4 x 12 A4-80 on 60 mm PCD.",
    ], x + 300, y + 150, 220, 8.6)

    x, y, w, h = s.panel("DRY-FIT CHECKLIST", 260)
    s.checkboxes([
        "Confirm GL100 stationary rear face is the 60 mm M4 pattern; rotating output is the 50 mm pattern.",
        "Confirm the motor wire exit clears the MC-100 phase window without pinching.",
        "Hand-start every fastener. Stop if any screw bottoms before clamping.",
        "Verify the three ST-100s seat squarely and MC-100 is not rocked by finish or burrs.",
        "Verify M4 x 12 gives about 5.5 mm engagement and never exceeds the GL100 6.0 mm limit.",
        "Use the owner-selected assembly torque consistently with a calibrated driver.",
        "Apply compatible removable threadlocker and witness marks at final assembly.",
        "Record stack fit, wire clearance, and any washer/length adaptation before proceeding.",
    ], x + 14, y + 212, w - 28, 8.9)
    s.warning("Torque research is closed. Use the owner-selected value consistently, then witness-mark each fastener.", MARGIN, 132, CONTENT_W)
    s.stop("The stationary stack fits without force, rocking, wire pinch, or bottoming screws. Keep it non-powered.")
    s.footer("docs/parts.md, GL100/ST-100/MC-100 and Fastener release practice; bom/bom.csv")


def page_3b(c: Canvas, n: int) -> None:
    s = Sheet(c, "3B", "Rotor and Tach Inserts", n)
    x, y, w, h = s.panel("ROTOR ASSEMBLY", 235)
    s.checkboxes([
        "RH-100 pilot enters the GL100 bore by hand; never press or force it.",
        "Install RH-100 with 4 x M4 x 10 A4 flat-head screws from the underside into the 50 mm rotating pattern.",
        "Verify every hub screw head is 0.1-0.2 mm subflush.",
        "Fit one magnet and two mass-matched brass slugs in the three r76 pockets; epoxy is the retention.",
        "Match each complete insert-plus-epoxy station within 0.01 g.",
        "Install three BP-100 v3 blades using their printed locating pins and 4 x M5 x 22 bolts per blade into the captured M5 nuts.",
    ], x + 14, y + 188, w - 28, 8.9)

    x, y, w, h = s.panel("ROTOR FINAL CHECKS", 205, PURPLE_BG, PURPLE, PURPLE)
    s.checkboxes([
        "Confirm all three blade stations use the correct fasteners and captured nuts.",
        "Verify the magnet and both brass stations are fully retained after epoxy cure.",
        "Apply the owner-selected torque and witness marks to hub and blade fasteners.",
        "Hand-rotate several revolutions and confirm no rub, click, or changing clearance.",
        "Photograph the completed rotor before balance measurements begin.",
    ], x + 14, y + 158, w - 28, 9)

    x, y, w, h = s.panel("BEFORE ANY POWER", 105, RED_BG, RED, RED)
    s.checkboxes([
        "Hand-rotate through multiple revolutions; confirm no rub, click, or changing clearance.",
        "Verify all critical fasteners have consistent torque and witness marks.",
        "Do not use cad/BP-100.step for current fit; the committed export is stale v2 geometry.",
        "Proceed to balance and runout measurement before powered full-rotor testing.",
    ], x + 14, y + 65, w - 28, 8.7)
    s.stop("The complete rotor turns freely by hand with correct retention and no contact.")
    s.footer("docs/parts.md, RH-100 and tach inserts; docs/blade-v2.md")


def page_3c(c: Canvas, n: int) -> None:
    s = Sheet(c, "3C", "Hall and Electronics Bracket", n)
    x, y, w, h = s.panel("HALL SENSOR GEOMETRY - RELEASED", 240, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "PCB-02 components face the rotor magnet; J1 and cable exit outboard.",
        "Sensor element and magnet centerline are both at radius 76.0 +/- 0.5 mm.",
        "Set 2.5 mm nominal axial gap, adjustable 1.5-4.0 mm, measured from the marked SOT-23 outer face to magnet cap.",
        "Use PCB-02 M2 holes on 6 mm pitch. At H1 use a bare pan head or washer <=4.5 mm OD.",
        "Provide cable strain relief on BR-100; PCB material does not extend beyond J1.",
        "Hand-turn rotor: one clean pulse per revolution with magnet; no false pulses with magnet removed.",
    ], x + 14, y + 192, w - 28, 9)

    x, y, w, h = s.panel("EB-100 AFTER CONNECTORS", 200, BLUE_BG, BLUE, BLUE)
    s.checkboxes([
        "BR-100 remains owner hand-fabricated; validate around the physical motor, PCB-02, cable, and Hall gap.",
        "Populate PCB-01 connectors before defining EB-100 and real cable bends.",
        "Reserve 110 x 80 x 25 mm for PCB-01 V1; V2 requires 120 x 90 x 30 mm.",
        "Use four 6-8 mm M3 standoffs and keep isolated mounting holes clear of circuit ground.",
        "Provide independent PCB retention and clamp cables independently of the bracket.",
    ], x + 14, y + 154, w - 28, 8.9)

    x, y, w, h = s.panel("RELEASE CHECK", 115)
    s.checkboxes([
        "Connector bodies and cable bends clear the rotor and standoffs.",
        "PCB-01 has an independent retention lanyard and independent cable clamps.",
        "Hand rotation remains free after the bracket and all cables are fitted.",
    ], x + 14, y + 73, w - 28, 8.8)
    s.stop("Hall pulses are clean and the retained PCB/cables clear every moving part.")
    s.footer("docs/electrical.md, Hall daughterboard; docs/parts.md, BR-100 and EB-100", "TACH-03")


def page_4a(c: Canvas, n: int) -> None:
    s = Sheet(c, "4A", "Flash, Console, and CLI Session", n)
    x, y, w, h = s.panel("BUILD AND FLASH", 165)
    commands = [
        ["cd firmware && cargo build"],
        [
            "espflash flash --port /dev/cu.usbmodem2101 --non-interactive",
            "  app/target/riscv32imac-unknown-none-elf/debug/stillair",
        ],
        ["target/debug/stillair --port /dev/cu.usbmodem2101 state"],
    ]
    box_top = y + 132
    for command_lines in commands:
        box_height = 27 if len(command_lines) == 1 else 38
        box_y = box_top - box_height
        c.setFillColor(GRAY_BG)
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.roundRect(x + 14, box_y, w - 28, box_height, 5, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("Courier-Bold", 7.8)
        line_y = box_top - (14 if len(command_lines) > 1 else 18)
        for command_line in command_lines:
            c.drawString(x + 23, line_y, command_line)
            line_y -= 11
        box_top = box_y - 11

    x, y, w, h = s.panel("BARE DEV-BOARD INPUT SIMULATION", 160, AMBER_BG, AMBER, AMBER)
    s.checkboxes([
        "GPIO22 to 3V3: PGOOD good.",
        "GPIO21 to 3V3: nFAULT idle high.",
        "GPIO14 to GND: ALARM idle low.",
        "Without real FG edges, Starting must fault NoRotation after 15 s. This is expected.",
    ], x + 14, y + 112, w - 28, 9.2)

    x, y, w, h = s.panel("SESSION RULES", 225)
    s.checkboxes([
        "Use one serial reader at a time. Stop raw-log capture before espflash or the CLI opens the port.",
        "Use `script` for any multi-step sequence. Separate CLI invocations create separate simulator sessions.",
        "Use `wait <state> --for <seconds>` after asynchronous commands.",
        "Use `stream <hz> --for <seconds>` for CSV telemetry.",
        "Factory-unverified stays in SafeBoot. Use `config stage` for a volatile bench image; release requires config=verified.",
        "Use `config capture` only after a complete measured configuration exists.",
        "Treat simulator results as harness validation, never motor validation.",
    ], x + 14, y + 178, w - 28, 9)
    s.text("WARNING: The CLI only surfaces @-prefixed protocol lines. Capture raw logs for Wi-Fi/Matter failures. Never use raw reg write on a spinning motor except under an approved stopped/instrumented procedure.", x + 14, y + 20, w - 28, 8.3, RED, True, 10)
    s.stop("Firmware flashes, one CLI session communicates reliably, and scripted sequences preserve device state.")
    s.footer("AGENTS.md, Driving the fan; firmware/cli/src/main.rs")


def page_4b(c: Canvas, n: int) -> None:
    s = Sheet(c, "4B", "Bare-Motor Measurements and Config Gate", n, "HOLD: IMAGE UNVERIFIED")
    x, y, w, h = s.panel("PREREQUISITES", 100, RED_BG, RED, RED)
    s.checkboxes([
        "PCB-01 through PCB-04 and TACH-01 passed.",
        "GL100 is rigidly restrained with NO BLADES installed.",
        "VM scope probe and manual cutoff are ready before power.",
    ], x + 14, y + 62, w - 28, 9)

    x, y, w, h = s.panel("BARE-MOTOR WORK ALLOWED NOW", 205)
    s.checkboxes([
        "Measure phase R and L independently with the method and connection convention recorded.",
        "Manually spin the GL100 and scope line-to-line BEMF; record amplitude and phase convention.",
        "Record the measured values beside provisional seeds 0xB1 / 0xAE / 0xC0. Do not call the seeds released.",
        "Confirm 20 pole pairs and inspect console, FG, Hall, watchdog, and stop behavior without raw live register writes.",
        "Scope only the motor operations already approved by the bench procedure; VM target <=35 V and 40 V rejects.",
        "Keep blades and loose hub hardware off throughout this bare-motor stage.",
    ], x + 14, y + 158, w - 28, 8.9)

    x, y, w, h = s.panel("MPET AND GOLDEN IMAGE - HOLD", 190, AMBER_BG, AMBER, AMBER)
    s.checkboxes([
        "Do not run MPET unloaded. controls.md requires the representative final rotor because unloaded MPET can produce bad Ke/Kp/Ki.",
        "Resolve the representative-rotor MPET procedure, then cross-check it against independent R/L/BEMF measurements.",
        "Populate the required D-generation fields, including safety-critical speed, ALARM, and external-watchdog settings.",
        "Do not use `config apply` as a release step until EEPROM completion timing and readback are proven on hardware.",
        "Capture the complete image only after review. Never reuse A1/C-generation register dumps.",
        "Require `config check` to report config=verified after the final reviewed image is committed.",
    ], x + 14, y + 143, w - 28, 8.7)

    x, y, w, h = s.panel("CURRENT RECORD", 90)
    s.text("R: __________   L: __________   BEMF: __________   convention: __________________________", x + 14, y + 48, w - 28, 9.5, bold=True)
    s.text("Config verdict: unverified / provisional / verified    image: ________________________", x + 14, y + 20, w - 28, 9.2)
    s.stop("Independent bare-motor measurements are recorded. MPET and the golden image remain HOLD until the loaded procedure is released.")
    s.footer("docs/controls.md, Measured-data gate and Stored configuration; docs/electrical.md, V1-to-V2 gates", "DRV-01, PCB-02, CTL-08/09/10")


def page_5a(c: Canvas, n: int) -> None:
    s = Sheet(c, "5A", "Rotor Balance and Runout", n)
    x, y, w, h = s.panel("MEASURE BEFORE POWER", 245)
    s.checkboxes([
        "Use a released level/indexed fixture, a dial indicator readable to 0.01 mm, and a calibrated scale readable to 0.01 g.",
        "For first powered motion, start low and stop for visible wobble, increasing vibration, rubbing, or unusual sound.",
        "Record each blade mass and first moment; target first moments within 0.5%.",
        "Measure RH-100 OD runout; limit <=0.10 mm TIR.",
        "Measure all blade tips in one indexed setup; spread <=0.5 mm.",
        "Hand-rotate and verify no rotating-to-stationary contact.",
        "Correct only with the documented balance-slug method; re-measure after every change.",
        "Photograph witness marks and record final correction masses/locations.",
    ], x + 14, y + 198, w - 28, 9.1)

    x, y, w, h = s.panel("VISUAL RECORD", 190, BLUE_BG, BLUE, BLUE)
    c.setStrokeColor(INK)
    c.circle(x + 115, y + 86, 60, stroke=1, fill=0)
    for angle in (0, 120, 240):
        import math
        ax = x + 115 + 82 * math.cos(math.radians(angle))
        ay = y + 86 + 82 * math.sin(math.radians(angle))
        c.line(x + 115, y + 86, ax, ay)
        c.circle(ax, ay, 5, stroke=1, fill=0)
    labels = ["Hub TIR: ______ mm", "Tip spread: ______ mm", "First-moment spread: ______ %", "Correction: _____________________"]
    yy = y + 130
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    for label in labels:
        c.drawString(x + 280, yy, label)
        yy -= 30

    x, y, w, h = s.panel("PASS CONDITION", 105, GREEN_BG, GREEN, GREEN)
    s.text("Hub <=0.10 mm TIR, tips within 0.5 mm, first moments within 0.5%, no objectionable vibration, and no contact.", x + 14, y + 62, w - 28, 10, bold=True)
    s.stop("MEC-05 passes with measurements recorded. Do not advance a rotor that only 'looks balanced.'")
    s.footer("testing/test-matrix.csv; docs/parts.md, RH-100", "MEC-05")


def page_5b(c: Canvas, n: int) -> None:
    s = Sheet(c, "5B", "Workshop Rotor Proof", n)
    x, y, w, h = s.panel("SET UP THE TEST YOU WILL ACTUALLY RUN", 260, BLUE_BG, BLUE, BLUE)
    s.checkboxes([
        "Secure the rotor and external drive so the setup cannot walk or tip; clear the rotor plane and nearby loose objects.",
        "Disconnect GL100 phases from PCB-01. PCB-02 may stay powered for Hall speed; the analog lock may latch without stopping the external drive.",
        "Use PCB-02 Hall telemetry or the external drive's own credible speed readout; record which source was used.",
        "Keep the ordinary power switch, low-voltage cutoff, or plug reachable from outside the sweep.",
        "Start at the lowest useful speed and advance only while motion and sound remain normal.",
        "Record pre-run balance, runout, fastener witness marks, and hand-clearance condition.",
        "Watch and listen continuously; removing power makes the rotor coast rather than stop instantly. No safety bypass is used.",
    ], x + 14, y + 210, w - 28, 8.8)

    x, y, w, h = s.panel("PROOF RUN", 260, PURPLE_BG, PURPLE, PURPLE)
    s.checkboxes([
        "Run the secured external drive at 216 RPM for 2 minutes in each direction.",
        "Stop and inspect after the first direction before reversing the setup.",
        "Never dynamically test the 270 RPM credible bypass load. It is calculation-only.",
        "Cut power immediately for visible wobble, increasing vibration, unusual sound, rubbing, contact, looseness, or speed disagreement.",
        "Reject damage, opening, permanent set, deformation, balance shift, contact, or loosened witness marks.",
        "Repeat balance, runout, witness-mark, and hand-clearance checks after both directions pass.",
    ], x + 14, y + 210, w - 28, 8.8)

    s.stop("Both directions pass with stable reported speed and no abnormal motion, sound, contact, loosening, or damage.")
    s.footer("testing/test-matrix.csv; docs/parts.md, design loads", "MEC-03, MEC-07")


def page_5c(c: Canvas, n: int) -> None:
    s = Sheet(c, "5C", "Representative Starts and Thermal", n, "HOLD: METHODS TO DEFINE")
    x, y, w, h = s.panel("START AND SPEED QUALIFICATION", 260)
    s.checkboxes([
        "With the representative final rotor installed, run the released MPET procedure; cross-check R/L/BEMF, then complete and read back the golden image.",
        "Before starts, require config check to report config=verified and verify the 180 RPM MCF limit and 200 RPM analog trip from reported diagnostics.",
        "At the intended minimum, complete 20 randomized-rest starts per direction at 24.0 V.",
        "At the same minimum, complete 5 starts per direction at 23.3 V and 5 per direction at 24.7 V.",
        "Reject any retry, reverse kick, stall, hunting, or objectionable tonal sequence.",
        "Verify steady operation at 30, 40, 55, 70, 120, and 170 RPM.",
        "Verify MCF active-control ceiling never exceeds 180 RPM.",
        "Test reversal after verified stop, watchdog shutdown, power recovery, and cutoff at speed.",
    ], x + 14, y + 212, w - 28, 9)

    x, y, w, h = s.panel("THERMAL", 230, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "Record ambient condition, temperature-sensor locations, and logging cadence.",
        "Run the complete fan for 8 hours at 170 RPM on the installed ceiling plate.",
        "Record RMS phase current, MCF q-axis estimate, PWM peak, independent motor/PCB temperatures, ambient, and supply behavior.",
        "Normal RMS phase current <0.8 A; investigate at 1.0 A; 1.5 A limiter must not clip continuously.",
        "Motor <70 C, PCB <85 C, no supply dropout or overtemperature, input power <50 W.",
        "After cooldown, repeat hand-clearance and fastener witness-mark checks.",
    ], x + 14, y + 180, w - 28, 8.8)

    x, y, w, h = s.panel("RELEASE SUMMARY", 120)
    s.text("Released minimum RPM: ______     Max qualified RPM: ______", x + 14, y + 78, w - 28, 10, bold=True)
    s.text("Open anomalies / restrictions: __________________________________________________________", x + 14, y + 43, w - 28, 9.5)
    s.stop("Representative starts, stable speeds, essential shutdowns, and the thermal run pass.")
    s.footer("testing/test-matrix.csv; docs/build.md, Commissioning", "DRV-02/03/05/07/09, CTL-02/03/05/07")


def page_6a(c: Canvas, n: int) -> None:
    s = Sheet(c, "6A", "Final Stack From Below", n, "HOLD: RELEASE GATES OPEN")
    x, y, w, h = s.panel("PREREQUISITE GATE", 110, RED_BG, RED, RED)
    s.checkboxes([
        "2B plate installation complete and INS-01 recorded.",
        "5A-5C off-ceiling release complete; tether path resolved and separately verified.",
        "Motor axial-bearing gate and local installation approval/certification path are closed.",
        "No unresolved torque, Hall-gap, EB-100, ENC-100, or cable-routing hold remains.",
    ], x + 14, y + 70, w - 28, 8.9)

    x, y, w, h = s.panel("ASSEMBLY ORDER FROM BELOW", 280, BLUE_BG, BLUE, BLUE)
    stack_boxes(c, ["ANCHORED MP-100 + SP-100 + ST-100", "MC-100 + GL100, WIRES THROUGH WINDOW", "RH-100 + COMPLETE ROTOR", "KD-100 + CASTELLATED NUT + COTTER", "EB-100 + PCB-01 + CABLE CLAMPS", "ENC-100 HOUSING + RETENTION LANYARD"], x + 52, y + 205, 265, 25, BLUE_BG)
    s.text("Checks at every layer", x + 355, y + 210, 180, 10, BLUE, True)
    s.checkboxes([
        "No wire pinch or sharp-edge contact.",
        "Correct fastener, locking method, torque record, and witness mark.",
        "Hand rotation remains free after each rotating layer.",
        "Catcher gap remains 2.5 +/- 0.5 mm.",
        "Hall gap remains within 1.5-4.0 mm.",
    ], x + 355, y + 180, 180, 8.4)

    x, y, w, h = s.panel("FINAL PHYSICAL CHECK", 145)
    s.checkboxes([
        "Tether has 15-20 mm slack and cannot foul rotor, catcher, housing, or cable path.",
        "Power cable is clamped to MP-100, not the removable housing; notch remains open at top rim.",
        "PCB and removable housing half each have their required independent retention.",
        "All serviceable assemblies can be removed from below without touching the anchors.",
    ], x + 14, y + 100, w - 28, 8.8)
    s.stop("Complete assembly is secure, freely rotating by hand, correctly tethered, and ready only for limited-speed commissioning.")
    s.footer("docs/install.md, Mounting sequence; docs/parts.md, assembly sections", "INS-01, INS-02")


def page_6b(c: Canvas, n: int) -> None:
    s = Sheet(c, "6B", "Installed Commissioning and Sign-Off", n, "HOLD: LADDER TBD")
    x, y, w, h = s.panel("BEFORE FIRST INSTALLED ROTATION", 175)
    s.checkboxes([
        "Clear the room and keep the manual cutoff reachable from outside the rotor sweep.",
        "Confirm plate seating, anchor washers, tether, catcher, Hall gap, wall gap, and housing clearance.",
        "Confirm firmware golden-image verdict is verified and power restoration remains off.",
        "Approve and write the speed ladder, dwell time, maximum, measurements, and abort thresholds before starting: __________________",
        "Start at the released minimum speed; do not improvise a higher installed test point.",
    ], x + 14, y + 130, w - 28, 8.9)

    x, y, w, h = s.panel("INCREASING LIMITED-SPEED CHECKS", 245, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "At each step inspect plate movement, tether behavior, catcher clearance, Hall gap, wall gap, and new resonance.",
        "Verify commanded speed against recorded FG and Hall telemetry; stop if they disagree.",
        "Test normal stop and confirm coast behavior.",
        "Test direction reversal only through ramp-to-zero and verified stop.",
        "Interrupt and restore power; confirm it returns off and requires a fresh command plus explicit arm.",
        "Verify network loss preserves the last local speed while ESP/watchdog failure revokes drive.",
        "Exercise Apple Home 1%, 50%, and 100% mapping only within the installed release ceiling.",
    ], x + 14, y + 198, w - 28, 8.9)

    x, y, w, h = s.panel("INSTALLATION RECORD", 165)
    fields = [
        "Date: ____________________    Installer: ____________________",
        "Golden image revision / commit: ______________________________________________",
        "Installed speed ceiling: ______ RPM    Released sleep speed: ______ RPM",
        "INS-03 result: PASS / FAIL    Remaining restrictions: __________________________",
    ]
    yy = y + 120
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    for field in fields:
        c.drawString(x + 14, yy, field)
        yy -= 28
    s.stop("INS-03 passes with no movement, contact, resonance, or clearance loss. Keep every recorded restriction in force.")
    s.footer("testing/test-matrix.csv; docs/controls.md, Home integration; docs/install.md", "INS-03, PCB-04, CTL-01/02/03/11/12")


def page_1a_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "1A", "PCB-01 Population Map", n)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, 708, "TOP / COMPONENT SIDE  -  KiCad target appearance")
    dx, dy, dw, dh = fit_image(c, ASSETS / "pcb01-top.png", 35, 315, 542, 388)
    # Exact features on the KiCad target view.
    pts = [(0.16, .71), (0.29, .70), (.24, .61), (.03, .48), (.39, .06), (.86, .42), (.81, .45)]
    for i, (px, py) in enumerate(pts, 1):
        numbered(c, i, dx + px * dw, dy + py * dh)
    c.setFillColor(PAPER); c.setStrokeColor(LINE)
    c.roundRect(35, 278, 542, 32, 7, stroke=1, fill=1)
    labels = ["1 C1", "2 C2", "3 F1", "4 J1", "5 J2", "6 U8", "7 C34"]
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 8)
    for i, label in enumerate(labels): c.drawString(47 + (i % 4) * 128, 296 - (i // 4) * 12, label)
    c.setFillColor(RED); c.setFont("Helvetica-Bold", 7.5)
    c.drawString(47, 268, "SOLDER ORDER: U8 -> C34 -> J1/J2 -> C1/C2 -> INSPECT -> F1 LAST")

    mini_card(c, "1 + 2  C1 / C2", "EEU-FR1H471, 470 uF 50 V. Positive lead to board +; negative stripe to pin 2 / PGND. Seat square without crushing bung.", 35, 190, 258, 76, GREEN, GREEN_BG)
    mini_card(c, "3  F1 - INSTALL LAST", "Low-profile tinned copper link across the 1206 pads. Near-zero ohms after soldering. External wall-side 3 A fuse remains mandatory.", 305, 190, 272, 76, RED, RED_BG)
    mini_card(c, "4 + 5  CONNECTORS", "J1 43045-0200; J2 43650-0300. Larger chisel tip. Tack one electrical pin, square and fully seat housing, then finish. Locating pegs are not soldered.", 35, 104, 258, 76, BLUE, BLUE_BG)
    mini_card(c, "6  U8  /  7  C34", "U8 LM2907M/NOPB: notch/dimple to pin-1 marker, tack pin 1 then diagonal pin 8, flux and drag-solder. C34 C1206C104K3GACTU: 100 nF C0G 25 V +/-10%, spanning the smaller 0603 site, not shorting it.", 305, 104, 272, 76, PURPLE, PURPLE_BG)
    s.warning("PCB-01: USE THE IRON, NOT BROAD HOT AIR. Then clean and dry; inspect under the microscope; verify no hard short from RAW24, VM24, 3V3, or 12V_TACH to ground; photograph the board.", 35, 96, 542)
    s.footer("pcb/pcb-01/pcb-01.kicad_pcb; bom/bom.csv; docs/electrical.md, SCH-06")


def page_1b_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "1B", "PCB-02 Population + Soldering", n)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, 708, "TOP / MAGNET-FACING COMPONENT SIDE  -  KiCad target appearance")
    dx, dy, dw, dh = fit_image(c, ASSETS / "pcb02-top.png", 35, 496, 542, 190)
    for i, (px, py) in enumerate([(.17, .80), (.14, .45), (.79, .50)], 1): numbered(c, i, dx + px * dw, dy + py * dh)
    arrow(c, 488, 484, 560, 484, GREEN, 2)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 7.5); c.drawRightString(480, 482, "J1 / CABLE EXITS RIGHT")

    mini_card(c, "1  C1", "C0603C104K5RACTU, 100 nF 50 V X7R, 0603. Pin 1 / 3V3 is left; pin 2 / AGND is right.", 35, 399, 170, 70, GREEN, GREEN_BG)
    mini_card(c, "2  U1", "DRV5033FAQDBZR, SOT-23. Match package index to board triangle. Pin 1 upper-left = 3V3; pin 2 lower-left = HALL_TACH; pin 3 right = AGND.", 216, 399, 181, 70, PURPLE, PURPLE_BG)
    mini_card(c, "3  J1", "S3B-PH-K-S side-entry JST-PH. Top to bottom in this view: 3 AGND, 2 HALL_TACH, 1 3V3. Iron-solder last.", 408, 399, 169, 70, BLUE, BLUE_BG)

    c.setFillColor(INK); c.setFont("Helvetica-Bold", 11); c.drawString(35, 377, "IRON METHOD: THIN SOLDER WIRE + FLUX")
    step_strip(c, ["Flux + tin one pad", "Place under microscope", "Reheat to tack", "Solder remaining pads", "Inspect + wick bridges", "Iron-solder J1"], 35, 329, 542, PURPLE)
    mini_card(c, "C1 - ONE-PAD TACK", "Tin one pad lightly. Reheat it while placing C1, align the body, then solder the other end. Refresh the tack only if needed.", 35, 239, 170, 76, GREEN, GREEN_BG)
    mini_card(c, "U1 - THREE LEADS", "Flux, tack pin 3, correct alignment, then solder pins 1 and 2. Reflow the tack last if it needs a cleaner fillet.", 216, 239, 181, 76, PURPLE, PURPLE_BG)
    mini_card(c, "J1 - LAST", "Tack one pin, reheat while seating the body square and flush, finish the other pins, then revisit the tack.", 408, 239, 169, 76, BLUE, BLUE_BG)
    s.y = 225
    x, y, w, h = s.panel("FINAL INSPECTION", 125, GREEN_BG, GREEN, GREEN)
    s.checkbox_grid([
        ("All parts on magnet-facing side; sensor marked face will face magnet. Do not use magnet polarity as the orientation cue.", "No short: 3V3 to HALL_TACH, 3V3 to AGND, or HALL_TACH to AGND."),
        ("Flux cleaned using its specified method; board completely dry.", "Microscope: wet fillets, no lifted lead, whisker, ball, or disturbed part; photograph board."),
    ], x + 14, y + 82, w / 2 - 2, 8.2)
    s.stop("PCB-02 passes magnified inspection and unpowered three-net short checks. Do not power yet.")
    s.footer("pcb/pcb-02/pcb-02.kicad_pcb; bom/bom.csv; docs/electrical.md, Hall daughterboard")


def connector_face(c: Canvas, x: float, y: float, pins: list[tuple[str, colors.Color]], title: str, note: str) -> None:
    c.setFillColor(WHITE); c.setStrokeColor(INK); c.roundRect(x, y, 210, 88, 8, stroke=1, fill=1)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 9); c.drawString(x + 10, y + 69, title)
    pw = min(42, 150 / len(pins))
    start = x + 10
    for i, (name, color) in enumerate(pins):
        px = start + i * (pw + 5)
        c.setFillColor(color); c.setStrokeColor(INK); c.roundRect(px, y + 29, pw, 28, 4, stroke=1, fill=1)
        c.setFillColor(WHITE if color != colors.yellow else INK); c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(px + pw / 2, y + 40, name)
        c.setFillColor(MUTED); c.setFont("Helvetica", 6.8); c.drawCentredString(px + pw / 2, y + 19, str(i + 1))
    c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawRightString(x + 200, y + 8, note)


def page_1c_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "1C", "Harness Build + Pin Proof", n)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 10); c.drawString(35, 706, "LOOK INTO THE MATING FACE; USE MOLDED PIN-1 MARKS, NOT WIRE COLOR MEMORY")
    connector_face(c, 35, 590, [("RAW24", RED), ("0V", INK)], "POWER  J1 - 18 AWG", "Micro-Fit 2-way")
    connector_face(c, 367, 590, [("W", PURPLE), ("V", BLUE), ("U", GREEN)], "MOTOR  J2 - 18 AWG", "Micro-Fit 3-way")
    arrow(c, 245, 634, 357, 634, MUTED, 2)
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 7); c.drawCentredString(301, 644, "DMM END-TO-END")
    connector_face(c, 35, 462, [("3V3", RED), ("TACH", colors.yellow), ("AGND", INK)], "HALL  J3 / PCB-02 J1", "PHR-3, straight-through")
    connector_face(c, 367, 462, [("3V3", RED), ("TX", BLUE), ("RX", GREEN), ("EN", AMBER), ("BOOT", PURPLE), ("GND", INK)], "PROGRAM  J7", "do not drive 3V3")
    arrow(c, 245, 506, 357, 506, GREEN, 2)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 7); c.drawCentredString(301, 516, "1-1 / 2-2 / 3-3")
    s.y = 440
    x, y, w, h = s.panel("EACH HARNESS: BUILD -> PROVE -> LABEL", 215, BLUE_BG, BLUE, BLUE)
    step_strip(c, ["Confirm housing view", "Crimp + tug each contact", "Insert to click", "Continuity each pin", "No cross-continuity", "Label both ends"], x + 14, y + 143, w - 28)
    s.checkbox_grid([
        ("Power: +24 V and 0 V preserved end-to-end.", "Motor: label positions W / V / U even if flying leads are not yet identified."),
        ("Hall: exactly 1-to-1, 2-to-2, 3-to-3.", "Record length, gauge, wire colors, contact orientation, and result before sleeving."),
    ], x + 14, y + 113, w / 2 - 2, 8.5)
    s.warning("J7 PIN 1 IS BOARD 3V3, NOT A POWER INPUT. Never let the programmer drive it while 24 V is connected.", 35, 220, 542)
    s.stop("Every harness is labeled, pull-tested, and signed off for pin continuity and no cross-continuity.")
    s.footer("docs/electrical.md, SCH-07 connectors; testing/test-matrix.csv", "TACH-06")


def page_1d_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "1D", "PCB-01 First Power, No Motor", n)
    # Bench hookup schematic.
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 10); c.drawString(35, 704, "WIRE THIS FIRST; PLACE PROBES BEFORE POWER")
    mini_card(c, "24 V BENCH SUPPLY", "current limited", 35, 615, 120, 64, RED, RED_BG)
    mini_card(c, "3 A FUSE + CUTOFF", "within reach", 185, 615, 120, 64, RED, RED_BG)
    mini_card(c, "PCB-01 J1", "RAW24 / 0V", 335, 615, 105, 64, BLUE, BLUE_BG)
    mini_card(c, "J2 MOTOR", "DISCONNECTED", 470, 615, 107, 64, RED, RED_BG)
    arrow(c, 155, 647, 185, 647, RED, 3); arrow(c, 305, 647, 335, 647, RED, 3)
    c.setStrokeColor(RED); c.setLineWidth(3); c.line(468, 612, 575, 681); c.line(468, 681, 575, 612)
    mini_card(c, "PROGRAMMER", "TX / RX / EN / BOOT / GND; 3V3 crossed out", 35, 530, 175, 62, AMBER, AMBER_BG)
    arrow(c, 210, 561, 335, 561, AMBER, 2)
    mini_card(c, "PROBES", "DMM rails + scope VM with spring ground", 335, 530, 242, 62, GREEN, GREEN_BG)
    s.y = 505
    x, y, w, h = s.panel("NUMBERED TEST FLOW", 330)
    flows = [
        ("1  RAILS", "Brief power: 24 V, 3.3 V, AVDD, DVDD, DRVOFF; record current and heat."),
        ("2  HARDWARE CUTS", "Force PGOOD, WDO, manual clear, OVERSPEED_N low one at a time -> DRVOFF rises without ESP help."),
        ("3  WATCHDOG", "Static WDI: timeout 1.44-1.76 s, WDO pulse about 200 ms. 2 Hz falling edges prevent timeout."),
        ("4  STARTUP", "Cold + slow-ramp power-up 20 times: U6 /PRE releases only after TACH_PGOOD_N."),
        ("5  RECOVERY", "Remove/restore 24 V: disabled >=10 s; requires new command plus explicit arm."),
        ("6  TACH", "Bridge disabled. Inject 0-3.3 V, 1-3% duty, settle >=30 s: reset ~3.00 Hz, trip ~3.33 Hz."),
    ]
    for i, (title, body) in enumerate(flows):
        col, row = i % 2, i // 2
        mini_card(c, title, body, x + 14 + col * 260, y + 213 - row * 82, 248, 70, BLUE if i < 5 else PURPLE, WHITE)
    s.warning("PASS LIMITS: VM <=35 V target; 40 V rejects. Persistent tach lock clears only on a genuine low-voltage power cycle. Any automatic re-arm blocks release.", 35, 198, 542)
    s.stop("All listed board/safety tests have recorded passes. Do not connect the motor after any failure.")
    s.footer("testing/test-matrix.csv; docs/electrical.md, safety and tach", "PCB-01, PCB-03/03B/03D, PCB-04, TACH-01")


def page_0a_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "0A", "Active Integration Map", n)
    c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 13); c.drawString(35, 698, "YOU ARE HERE")
    arrow(c, 92, 688, 92, 650, BLUE, 4)
    stages = [
        ("1A-1B", "POPULATE", "two boards", BLUE), ("1C", "HARNESS", "pin proof", BLUE),
        ("1D", "NO MOTOR", "board proof", PURPLE), ("4B", "BARE MOTOR", "R / L / BEMF", PURPLE),
        ("3A-3C", "ASSEMBLE", "fit + Hall", GREEN), ("5A", "BALANCE", "measure", GREEN),
        ("5B", "WORKSHOP PROOF", "first full rotor", AMBER),
        ("5C", "LOADED TEST", "MPET + scripts", PURPLE),
    ]
    for i, (sid, title, sub, color) in enumerate(stages):
        col, row = i % 4, i // 4
        x = 35 + col * 138; y = 566 - row * 112
        c.setFillColor(WHITE); c.setStrokeColor(color); c.setLineWidth(2); c.roundRect(x, y, 118, 76, 9, stroke=1, fill=1)
        c.setFillColor(color); c.setFont("Helvetica-Bold", 9); c.drawString(x + 9, y + 57, sid)
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 10); c.drawString(x + 9, y + 38, title)
        c.setFillColor(MUTED); c.setFont("Helvetica", 8); c.drawString(x + 9, y + 21, sub)
        if i not in (3, 7): arrow(c, x + 120, y + 38, x + 136, y + 38, color, 1.5)
    arrow(c, 569, 604, 569, 548, MUTED, 2); arrow(c, 569, 548, 35, 548, MUTED, 2); arrow(c, 35, 548, 35, 528, MUTED, 2)
    s.y = 430
    x, y, w, h = s.panel("WHAT COUNTS AS DONE", 145, GREEN_BG, GREEN, GREEN)
    s.checkbox_grid([
        ("A result is measured and recorded, not just observed.", "A failed gate stops the next powered stage."),
        ("Connector polarity and pin order are proved end-to-end.", "After loaded MPET, verify config before start/speed qualification."),
        ("Installed unpowered checks precede gradual loaded work.", "Normal safety firmware + long USB J6; cutoff outside sweep."),
    ], x + 14, y + 100, w / 2 - 2, 8.4)
    x, y, w, h = s.panel("BOUNDARIES KEPT OUT OF THIS ACTIVE BINDER", 120, GRAY_BG)
    s.text("Michael performs installed work with one-step-at-a-time project guidance. Completed plate, tether, and catcher work stays closed. Deferred scope remains omitted unless explicitly reopened.", x + 14, y + 75, w - 28, 9.2, bold=True)
    s.stop("Start at 1A. Carry only the current sheet, board, and required tools to the bench.")
    s.footer("docs/STATE.md; docs/integration.md; testing/test-matrix.csv")


def page_3a_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "3A", "Stationary Stack Dry-Fit", n)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 10); c.drawString(35, 704, "EXPLODED SIDE VIEW - NON-POWERED")
    cx = 205
    parts = [("MP-100 PLATE", 620, 270, 25, BLUE), ("3 x ST-100", 535, 165, 44, PURPLE), ("MC-100 CARRIER", 438, 270, 32, BLUE), ("GL100 STATIONARY FACE", 335, 205, 62, GREEN)]
    for label, yy, ww, hh, color in parts:
        c.setFillColor(WHITE); c.setStrokeColor(color); c.setLineWidth(2); c.roundRect(cx - ww/2, yy, ww, hh, 6, stroke=1, fill=1)
        c.setFillColor(color); c.setFont("Helvetica-Bold", 9); c.drawCentredString(cx, yy + hh/2 - 3, label)
    for a, b in [(620,579),(535,470),(438,397)]: arrow(c, cx, a-4, cx, b+4, MUTED, 2)
    c.setFillColor(RED_BG); c.setStrokeColor(RED); c.setLineWidth(2); c.rect(318, 445, 22, 15, stroke=1, fill=1)
    arrow(c, 329, 463, 370, 493, RED, 2)
    c.setFillColor(RED); c.setFont("Helvetica-Bold", 8); c.drawRightString(368, 508, "MOTOR WIRES")
    c.drawRightString(368, 498, "THROUGH RED WINDOW")
    mini_card(c, "MP-100 -> ST-100", "3 x M6 x 16 flat-head from plate ceiling face; heads flush or below.", 420, 595, 157, 72, BLUE, BLUE_BG)
    mini_card(c, "ST-100 -> MC-100", "3 x M6 x 20 A4-80 + Nord-Lock pairs. Hand-start, square seating.", 420, 503, 157, 72, PURPLE, PURPLE_BG)
    mini_card(c, "MC-100 -> GL100", "4 x M4 x 12 A4-80 into the 60 mm stationary pattern. The 50 mm face rotates.", 420, 411, 157, 72, GREEN, GREEN_BG)
    mini_card(c, "THREAD DEPTH", "Target about 5.5 mm engagement; 6.0 mm motor-thread maximum. A bottoming screw is felt at hand torque: stop and correct.", 420, 319, 157, 72, RED, RED_BG)
    s.y = 300
    x, y, w, h = s.panel("RELEASE CHECK", 155)
    s.checkbox_grid([
        ("All fasteners hand-start; no rocking or forced alignment.", "Motor wire is unpinched and clear of sharp edges."),
        ("Owner-selected torque applied consistently; witness marks present.", "Threadlocker only where specified; no screw bottoms."),
        ("Stationary 60 mm and rotating 50 mm faces confirmed.", "Stack remains non-powered until later gates pass."),
    ], x + 14, y + 108, w / 2 - 2, 8.5)
    s.stop("Dry stack sits square without force, rocking, wire pinch, or bottoming screws.")
    s.footer("docs/parts.md, GL100/ST-100/MC-100; bom/bom.csv")


def page_3b_visual(c: Canvas, n: int) -> None:
    import math
    s = Sheet(c, "3B", "Rotor + Tach Inserts", n)
    cx, cy = 220, 505
    c.setStrokeColor(INK); c.setLineWidth(2); c.circle(cx, cy, 95, stroke=1, fill=0); c.circle(cx, cy, 24, stroke=1, fill=0)
    for i, (ang, name, color) in enumerate([(90,"MAGNET",RED),(210,"BRASS",AMBER),(330,"BRASS",AMBER)]):
        px, py = cx + 67*math.cos(math.radians(ang)), cy + 67*math.sin(math.radians(ang))
        c.setFillColor(color); c.circle(px, py, 13, stroke=0, fill=1); c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 6.8); c.drawCentredString(px, py-2, name)
    for ang, label in [(0,"A"),(120,"B"),(240,"C")]:
        x2, y2 = cx+155*math.cos(math.radians(ang)), cy+155*math.sin(math.radians(ang)); c.setStrokeColor(BLUE); c.setLineWidth(8); c.line(cx,cy,x2,y2); c.setFillColor(BLUE); c.setFont("Helvetica-Bold",12); c.drawCentredString(x2,y2+10,label)
    mini_card(c, "HUB TO MOTOR", "4 x M4 x 10 A4 flat-head from underside into 50 mm rotating pattern; heads 0.1-0.2 mm subflush. Pilot enters bore by hand only.", 405, 574, 172, 105, BLUE, BLUE_BG)
    mini_card(c, "EACH BLADE", "BP-100 v3 locating pins + captured M5 nuts; 4 x M5 x 22 per blade. Torque consistently and witness-mark.", 405, 455, 172, 105, PURPLE, PURPLE_BG)
    mini_card(c, "THREE INSERT STATIONS", "Epoxy retains one magnet + two brass slugs. Match complete insert-plus-epoxy station masses within 0.01 g after cure.", 405, 336, 172, 105, AMBER, AMBER_BG)
    s.y = 315
    x, y, w, h = s.panel("MASS + FINAL RECORD", 175)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 9)
    c.drawString(x+18,y+126,"MAGNET ______ g     BRASS B ______ g     BRASS C ______ g     MAX SPREAD ______ g")
    s.checkbox_grid([
        ("Pilot hand-fit; all four hub heads subflush.", "All three blade stations have four correct bolts and captured nuts."),
        ("Epoxy fully cured; inserts cannot move.", "Hand-rotate several revolutions: no rub, click, or changing clearance."),
        ("Critical fasteners torqued and witness-marked.", "Photograph rotor before balance measurements."),
    ], x + 14, y + 98, w / 2 - 2, 8.3)
    s.warning("Do not use cad/BP-100.step for current fit; it is stale v2 geometry.", 35, 152, 542)
    s.stop("Complete rotor turns freely with correct retention; continue to 5A before powered motion.")
    s.footer("docs/parts.md, RH-100/tach inserts; docs/blade-v2.md")


def page_3c_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "3C", "Hall Gap + Electronics Bracket", n)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 10); c.drawString(35, 704, "SECTION THROUGH MAGNET AND SENSOR")
    c.setFillColor(RED); c.roundRect(85, 585, 90, 32, 5, stroke=0, fill=1); c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8); c.drawCentredString(130,597,"MAGNET CAP")
    c.setFillColor(GREEN_BG); c.setStrokeColor(GREEN); c.roundRect(85, 474, 220, 52, 5, stroke=1, fill=1)
    c.setFillColor(PURPLE); c.roundRect(112, 512, 36, 16, 3, stroke=0, fill=1); c.setFillColor(INK); c.setFont("Helvetica-Bold",8); c.drawString(155,516,"U1 SOT-23 MARKED FACE")
    arrow(c, 130, 581, 130, 531, RED, 2); arrow(c, 130, 531, 130, 581, RED, 2)
    c.setFillColor(RED); c.setFont("Helvetica-Bold",9); c.drawString(155,554,"2.5 mm NOMINAL")
    c.setFont("Helvetica",8); c.drawString(155,542,"allowed 1.5-4.0 mm")
    arrow(c, 282, 486, 328, 458, GREEN, 2)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8); c.drawRightString(328,445,"J1 / CABLE OUTBOARD")
    mini_card(c, "COMMON CENTERLINE", "Magnet and sensor element at radius 76.0 +/-0.5 mm.", 350, 588, 227, 72, BLUE, BLUE_BG)
    mini_card(c, "PCB-02 MOUNTING", "M2 holes on 6 mm pitch. At H1 use bare pan head or washer <=4.5 mm OD. Components face magnet.", 350, 504, 227, 72, GREEN, GREEN_BG)
    mini_card(c, "BR-100", "Strain-relieve Hall cable. Validate bracket around physical motor, board, magnet, and real gap.", 350, 420, 227, 72, PURPLE, PURPLE_BG)
    s.y = 395
    x, y, w, h = s.panel("PCB-01 BRACKET ENVELOPE", 140, BLUE_BG, BLUE, BLUE)
    c.setFillColor(WHITE); c.setStrokeColor(BLUE); c.rect(x+18,y+34,220,72,stroke=1,fill=1)
    c.setFillColor(BLUE); c.setFont("Helvetica-Bold",8); c.drawCentredString(x+128,y+73,"V1: 110 x 80 x 25 mm")
    c.drawCentredString(x+128,y+63,"V2: 120 x 90 x 30 mm SERVICE ENVELOPE")
    s.text("Four 6-8 mm M3 standoffs. Keep isolated mounting holes clear of circuit ground. Independent PCB retention and cable clamps. Preserve connector and cable-bend keepouts.", x+260,y+92,w-280,8.6,bold=True)
    x, y, w, h = s.panel("HAND-ROTATION RELEASE", 115, GREEN_BG, GREEN, GREEN)
    s.checkbox_grid([
        ("One clean pulse/revolution with magnet.", "No false pulse with magnet removed."),
        ("All cables and connector bodies clear rotor.", "Gap remains in range through full hand rotation."),
    ], x+14,y+72,w/2-2,8.7)
    s.stop("Hall pulse is clean; retained PCB and clamped cables clear all moving parts.")
    s.footer("docs/electrical.md, Hall daughterboard; docs/parts.md, BR-100/EB-100", "TACH-03")


def page_4a_visual(c: Canvas, n: int) -> None:
    s = Sheet(c, "4A", "Flash + One Persistent CLI Session", n)
    x, y, w, h = s.panel("BUILD / FLASH / TALK", 165)
    commands = [
        ["cargo build --manifest-path firmware/Cargo.toml"],
        ["espflash flash --port /dev/cu.usbmodem101 --non-interactive", "  firmware/app/target/riscv32imac-unknown-none-elf/debug/stillair"],
        ["firmware/target/debug/stillair --port /dev/cu.usbmodem101 state"],
    ]
    box_top = y + 132
    for command_lines in commands:
        box_height = 27 if len(command_lines) == 1 else 38
        box_y = box_top - box_height
        c.setFillColor(GRAY_BG); c.setStrokeColor(LINE); c.roundRect(x+14, box_y, w-28, box_height, 5, stroke=1, fill=1)
        c.setFillColor(INK); c.setFont("Courier-Bold", 7.5)
        line_y = box_top - (14 if len(command_lines) > 1 else 18)
        for command_line in command_lines:
            c.drawString(x+23, line_y, command_line)
            line_y -= 11
        box_top = box_y - 11
    c.setFillColor(INK); c.setFont("Helvetica-Bold",10); c.drawString(35, 507, "BARE DEV-BOARD INPUT JUMPERS")
    mini_card(c,"GPIO22 -> 3V3","PGOOD good",35,424,160,65,GREEN,GREEN_BG)
    mini_card(c,"GPIO21 -> 3V3","nFAULT idle high",226,424,160,65,GREEN,GREEN_BG)
    mini_card(c,"GPIO14 -> GND","ALARM idle low",417,424,160,65,BLUE,BLUE_BG)
    step_strip(c,["config stage","Starting","15 s, no FG","NoRotation fault"],35,366,542,RED)
    c.setFillColor(RED); c.setFont("Helvetica-Bold",8); c.drawCentredString(306,350,"EXPECTED ON A BARE BOARD; IT DOES NOT GENERATE FG EDGES")
    s.y = 340
    x, y, w, h = s.panel("SESSION RULES", 205)
    mini_card(c,"ONE READER","Stop raw-log capture before espflash or CLI opens the port.",x+14,y+111,160,70,BLUE,BLUE_BG)
    mini_card(c,"USE SCRIPT","Multi-step simulator work must stay in one session; separate invocations reset it.",x+188,y+111,160,70,PURPLE,PURPLE_BG)
    mini_card(c,"CONFIG GATE","unverified = blocked; provisional = volatile bench; verified = release.",x+362,y+111,160,70,RED,RED_BG)
    s.text("wait <state> --for <seconds>  |  wait speed <rpm> --within <rpm> --for <seconds>",x+14,y+91,w-28,8.5,bold=True)
    s.text("stream <hz> --for <seconds> for CSV  |  config capture after complete measured configuration",x+14,y+76,w-28,8.5,bold=True)
    s.warning("Firmware refuses raw register/config writes unless stopped. Use controlled mpet run, not live raw commands. Simulator passes validate the harness, not the motor.",35,166,542)
    s.stop("Firmware flashes; one persistent CLI session communicates and preserves scripted state.")
    s.footer("AGENTS.md, Driving the fan; firmware/cli/src/main.rs")


def motor_meter(c: Canvas, x: float, y: float, title: str, symbol: str, color, result: str) -> None:
    c.setFillColor(WHITE); c.setStrokeColor(color); c.roundRect(x,y,165,150,8,stroke=1,fill=1)
    c.setFillColor(color); c.setFont("Helvetica-Bold",9); c.drawString(x+10,y+132,title)
    c.setStrokeColor(INK); c.setLineWidth(2); c.circle(x+82,y+78,30,stroke=1,fill=0)
    c.setFillColor(INK); c.setFont("Helvetica-Bold",13); c.drawCentredString(x+82,y+73,"M")
    c.line(x+15,y+95,x+52,y+89); c.line(x+15,y+61,x+52,y+70)
    c.setFillColor(color); c.setFont("Helvetica-Bold",12); c.drawString(x+17,y+105,symbol)
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold",7); c.drawString(x+10,y+42,result)
    for row, pair in enumerate(("U-V", "V-W", "W-U")):
        c.drawString(x+10, y+30-row*10, f"{pair}: __________________")


def page_4b_visual(c: Canvas, n: int) -> None:
    s = Sheet(c,"4B","Unloaded First Spin",n,"VOLATILE BENCH IMAGE")
    c.setFillColor(RED); c.setFont("Helvetica-Bold",13); c.drawString(35,702,"NO BLADES")
    c.setFillColor(INK); c.setFont("Helvetica-Bold",9); c.drawString(160,702,"Motor secured; reachable power cutoff; board and Hall tests passed")
    motor_meter(c,35,518,"1  POWER CYCLE","19.4 V",BLUE,"supply: 19.4 V / 2 A limit")
    motor_meter(c,223,518,"2  CONFIG STAGE","CLI",PURPLE,"expect: provisional")
    motor_meter(c,411,518,"3  OBSERVED RUN","35",GREEN,"watch: smooth rotation")
    c.setFillColor(MUTED); c.setFont("Helvetica",8); c.drawCentredString(306,501,"Double-align may make one or two small positioning ticks before smooth rotation.")
    s.y = 495
    x,y,w,h=s.panel("GREEN LANE - DO NOW",145,GREEN_BG,GREEN,GREEN)
    s.checkbox_grid([
        ("Power at 19.4 V with a 2 A supply limit; confirm normal idle draw.","Run config stage after each motor-power cycle; require provisional."),
        ("Issue a fresh run only after staging.","Use script 03 at 35 RPM; watch continuously and keep the cutoff reachable."),
    ],x+14,y+98,w/2-2,8.4)
    x,y,w,h=s.panel("LOADED-STAGE HANDOFF",145,AMBER_BG,AMBER,AMBER)
    s.checkbox_grid([
        ("No unloaded MPET; script 02 requires the representative loaded rotor.","The provisional image is for this unloaded first-spin test only."),
        ("Never config apply the provisional image; it is volatile by design.","After final apply and power cycle require config check: verified."),
    ],x+14,y+98,w/2-2,8.3)
    s.warning("Factory-unverified is blocked: a normal run would invoke implicit MPET with zero gains. Stage first. VM <=35 V target; 40 V rejects.",35,157,542)
    s.stop("35 RPM starts, turns smoothly, reports FG, and stops cleanly. Loaded tuning remains separate.")
    s.footer("docs/controls.md, measured-data gate; docs/electrical.md", "DRV-01, PCB-02, CTL-08/09/10")


def page_5a_visual(c: Canvas, n: int) -> None:
    import math
    s=Sheet(c,"5A","Rotor Balance + Runout Record",n)
    cx,cy=160,535; c.setStrokeColor(INK); c.circle(cx,cy,58,stroke=1,fill=0)
    for i,(ang,label) in enumerate([(0,"A"),(120,"B"),(240,"C")]):
        tx,ty=cx+120*math.cos(math.radians(ang)),cy+120*math.sin(math.radians(ang)); c.setStrokeColor(BLUE); c.setLineWidth(6); c.line(cx,cy,tx,ty); c.setFillColor(BLUE); c.setFont("Helvetica-Bold",12); c.drawCentredString(tx,ty+8,label)
    c.setStrokeColor(RED); c.setLineWidth(2); c.line(cx-70,cy-78,cx-48,cy-42); c.setFillColor(RED); c.setFont("Helvetica-Bold",8); c.drawString(35,435,"DIAL INDICATOR AT RH-100 OD")
    mini_card(c,"HUB RUNOUT","<=0.10 mm TIR",340,603,237,64,RED,RED_BG)
    mini_card(c,"BLADE TIP HEIGHT","all three in one indexed setup; spread <=0.5 mm",340,527,237,64,BLUE,BLUE_BG)
    mini_card(c,"FIRST MOMENT","each blade; spread <=0.5%",340,451,237,64,PURPLE,PURPLE_BG)
    s.y = 415
    x,y,w,h=s.panel("A / B / C MEASUREMENT TABLE",185)
    cols=["STATION","MASS (g)","FIRST MOMENT","TIP (mm)","CORRECTION"]
    widths=[70,85,110,85,145]; xx=x+14
    c.setFillColor(GRAY_BG); c.rect(xx,y+126,sum(widths),27,stroke=0,fill=1)
    for title,ww in zip(cols,widths): c.setFillColor(INK); c.setFont("Helvetica-Bold",7.5); c.drawCentredString(xx+ww/2,y+136,title); xx+=ww
    for r,label in enumerate(["A","B","C"]):
        yy=y+95-r*31; xx=x+14
        for ww in widths: c.setStrokeColor(LINE); c.rect(xx,yy,ww,28,stroke=1,fill=0); xx+=ww
        c.setFillColor(INK); c.setFont("Helvetica-Bold",9); c.drawCentredString(x+49,yy+9,label)
    x,y,w,h=s.panel("METHOD CHECK",125,GREEN_BG,GREEN,GREEN)
    s.checkbox_grid([
        ("0.01 mm indicator + 0.01 g calibrated scale.","First powered check starts low; stop for wobble, vibration, rubbing, or unusual sound."),
        ("Correct only by documented slug method; remeasure.","Hand-clearance pass and witness-mark photo saved."),
    ],x+14,y+82,w/2-2,8.5)
    s.stop("MEC-05 passes numerically; do not advance a rotor that only looks balanced.")
    s.footer("testing/test-matrix.csv; docs/parts.md, RH-100", "MEC-05")


def page_5b_visual(c: Canvas, n: int) -> None:
    s=Sheet(c,"5B","Workshop Rotor Proof",n)
    c.setFillColor(RED_BG); c.setStrokeColor(RED); c.setLineWidth(3); c.roundRect(75,410,462,260,16,stroke=1,fill=1)
    c.setFillColor(WHITE); c.setStrokeColor(INK); c.circle(306,540,70,stroke=1,fill=1); c.setFillColor(INK); c.setFont("Helvetica-Bold",12); c.drawCentredString(306,536,"ROTOR + DRIVE")
    mini_card(c,"REPORTED SPEED","PCB-02 Hall or drive readout",90,580,140,58,BLUE,BLUE_BG)
    mini_card(c,"WATCH + LISTEN","stop if motion or sound changes",382,580,140,58,PURPLE,PURPLE_BG)
    mini_card(c,"POWER OFF","reachable; rotor will coast",90,438,140,58,RED,WHITE)
    mini_card(c,"CLEAR AREA","stay outside rotor plane",382,438,140,58,GREEN,WHITE)
    c.setFillColor(RED); c.setFont("Helvetica-Bold",7.6); c.drawCentredString(306,392,"GL100 PHASES DISCONNECTED FROM PCB-01  |  NO SAFETY BYPASS")
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold",7.2); c.drawCentredString(306,380,"PCB-02 MAY REPORT HALL SPEED; ANALOG TRIP MAY LATCH BUT WILL NOT STOP THE EXTERNAL DRIVE")
    step_strip(c,["START LOW","216 RPM","2 min CW","STOP + INSPECT","2 min CCW","STOP + INSPECT"],35,321,542,PURPLE)
    c.setFillColor(RED); c.setFont("Helvetica-Bold",11); c.drawCentredString(306,298,"270 RPM = CALCULATION ONLY  x  NEVER DYNAMICALLY TEST")
    s.y = 285
    x,y,w,h=s.panel("BEFORE, DURING, AND RECORD",170)
    s.checkbox_grid([
        ("Setup secured; rotor plane and nearby area clear.","Speed source responds and is recorded."),
        ("Start low; advance only while smooth and quiet.","Watch continuously; cutoff remains reachable."),
        ("Balance, runout, clearance, witness marks recorded.","Inspect after each direction; stop on any change."),
    ],x+14,y+125,w/2-2,8.2)
    c.setFillColor(INK); c.setFont("Helvetica",7.8)
    c.drawString(x+14,y+56,"Speed source: ____________________________     Setup: __________________________________________")
    c.drawString(x+14,y+39,"CW actual: ______ RPM   result: __________     CCW actual: ______ RPM   result: __________")
    c.drawString(x+14,y+22,"Notes: __________________________________________________________________________________")
    c.drawString(x+14,y+7,"Date / initials: __________________________________")
    s.stop("Both directions pass with no abnormal motion, sound, contact, loosening, or damage.")
    s.footer("testing/test-matrix.csv; docs/parts.md, design loads", "MEC-03, MEC-07")


def page_5c_visual(c: Canvas, n: int) -> None:
    s=Sheet(c,"5C","Loaded Commissioning Script Card",n,"HARDWARE VALUES PENDING")
    x,y,w,h=s.panel("FINAL TEST CONNECTION",90,BLUE_BG,BLUE,BLUE)
    step_strip(c,["LAPTOP + CLI","LONG USB J6","PCB-01","MOTOR + ROTOR"],x+14,y+31,w-28,BLUE)
    c.setFillColor(INK); c.setFont("Helvetica-Bold",7.5); c.drawString(x+14,y+14,"NORMAL SAFETY FIRMWARE  |  24 V VIA REACHABLE CUTOFF  |  CABLES OUTSIDE SWEEP")
    x,y,w,h=s.panel("CONTROLLED MPET + GOLDEN IMAGE",220,BLUE_BG,BLUE,BLUE)
    s.checkbox_grid([
        ("Run scripts/02-mpet-and-capture.txt only with the representative loaded rotor.", "Review MTR_PARAMS, CURRENT_PI, and SPEED_PI against independent R / L / BEMF."),
        ("Put only reviewed D-generation values into the golden IMAGE.", "While stopped, config apply performs one commit, waits 750 ms, polls self-clear, then verifies readback."),
        ("Power-cycle after apply; config check must report verified.", "If MPET faults or times out, firmware aborts it and revokes drive permission."),
    ],x+14,y+172,w/2-2,8.15)
    c.setFillColor(INK); c.setFont("Helvetica-Bold",8.2)
    c.drawString(x+14,y+24,"MPET result / image revision: _________________________________________________________________")

    x,y,w,h=s.panel("RUN THE NUMBERED FILES",140,GREEN_BG,GREEN,GREEN)
    script_rows = [
        ("02", "mpet-and-capture.txt", "loaded MPET + config capture"),
        ("04", "loaded-speed-ladder.txt", "35 / 60 / 90 / 120 / 150 / 170 RPM ladder"),
        ("05", "direction-check.txt", "low-speed direction check through verified stop"),
        ("06", "observed-run.txt", "30-minute continuously observed run"),
    ]
    for row,(number,filename,label) in enumerate(script_rows):
        yy=y+92-row*24
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold",9); c.drawString(x+16,yy,number)
        c.setFillColor(INK); c.setFont("Courier-Bold",7.4); c.drawString(x+43,yy,f"scripts/{number}-{filename}")
        c.setFont("Helvetica",7.7); c.drawString(x+300,yy,label)

    x,y,w,h=s.panel("WATCHED STOP RULES",120,AMBER_BG,AMBER,AMBER)
    s.checkbox_grid([
        ("Keep the ordinary plug/cutoff reachable and watch continuously.", "Stop for visible wobble, increasing vibration, rubbing, or unusual sound."),
        ("Use reported FG diagnostics and your own observation; no external tachometer is required.", "No permissive firmware or safety bypass. A stopped run may be repeated after inspection."),
    ],x+14,y+77,w/2-2,8.1)
    s.stop("Loaded MPET, verified config, speed ladder, direction check, and observed run have recorded results.")
    s.footer("firmware/scripts/README.md; docs/controls.md, commissioning", "CTL-13/14; DRV-02/03/05/07/09")


PAGES: list[Callable[[Canvas, int], None]] = [
    page_0a_visual,
    page_1a_visual,
    page_1b_visual,
    page_1c_visual,
    page_1d_visual,
    page_3a_visual,
    page_3b_visual,
    page_3c_visual,
    page_4a_visual,
    page_4b_visual,
    page_5a_visual,
    page_5b_visual,
    page_5c_visual,
]


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(OUTPUT), pagesize=letter, pageCompression=1)
    canvas.setTitle("Stillair Integration Field Guides")
    canvas.setAuthor("Stillair project")
    canvas.setSubject("Printable active integration and bench-test field guides")
    for page_no, page in enumerate(PAGES, start=1):
        page(canvas, page_no)
        canvas.showPage()
    canvas.save()
    return OUTPUT


if __name__ == "__main__":
    print(build())
