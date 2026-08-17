#!/usr/bin/env python3
"""Build the Stillair printable integration field-guide binder."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "stillair-integration-field-guides.pdf"

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
        ("5", "Proof, starts, and thermal"),
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
        "No blades during bare-motor characterization.",
        "No powered motor work before the no-motor board and safety-chain checks pass.",
        "Balance and hand-clearance checks pass before any powered full-rotor run.",
        "Use a guarded fixture and released procedure for the 216 RPM rotor proof.",
        "Never bypass the 180 RPM controller limit or 200 RPM analog trip without the written guarded two-person procedure.",
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
        "Reserve 110 x 80 x 25 mm for PCB-01 plus connector and service clearance.",
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
        "For release, `config check` must report config=verified; ok=true with config=unverified is not a pass.",
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
        "GL100 is rigidly guarded with NO BLADES installed.",
        "VM scope probe and manual cutoff are ready before power.",
    ], x + 14, y + 62, w - 28, 9)

    x, y, w, h = s.panel("BARE-MOTOR WORK ALLOWED NOW", 205)
    s.checkboxes([
        "Measure phase R and L independently with the method and connection convention recorded.",
        "Manually spin the GL100 and scope line-to-line BEMF; record amplitude and phase convention.",
        "Record the measured values beside provisional seeds 0xB1 / 0xAE / 0xCA. Do not call the seeds released.",
        "Confirm 20 pole pairs and inspect console, FG, Hall, watchdog, and stop behavior without raw live register writes.",
        "Scope only the motor operations already approved by the guarded procedure; VM target <=35 V and 40 V rejects.",
        "Keep blades and loose hub hardware off throughout this bare-motor stage.",
    ], x + 14, y + 158, w - 28, 8.9)

    x, y, w, h = s.panel("MPET AND GOLDEN IMAGE - HOLD", 190, AMBER_BG, AMBER, AMBER)
    s.checkboxes([
        "Do not run MPET unloaded. controls.md requires the representative final rotor because unloaded MPET can produce bad Ke/Kp/Ki.",
        "Resolve the representative-rotor MPET procedure, then cross-check it against independent R/L/BEMF measurements.",
        "Populate the required D-generation fields, including safety-critical speed, ALARM, and external-watchdog settings.",
        "Do not use `config apply` as a release step until EEPROM completion timing and readback are proven on hardware.",
        "Capture the complete image only after review. Never reuse A1/C-generation register dumps.",
        "Require `config check` to report config=verified; ok=true with config=unverified is not a release pass.",
    ], x + 14, y + 143, w - 28, 8.7)

    x, y, w, h = s.panel("CURRENT RECORD", 90)
    s.text("R: __________   L: __________   BEMF: __________   convention: __________________________", x + 14, y + 48, w - 28, 9.5, bold=True)
    s.text("Config verdict: unverified / verified    image commit: ________________________________", x + 14, y + 20, w - 28, 9.2)
    s.stop("Independent bare-motor measurements are recorded. MPET and the golden image remain HOLD until the loaded procedure is released.")
    s.footer("docs/controls.md, Measured-data gate and Stored configuration; docs/electrical.md, V1-to-V2 gates", "DRV-01, PCB-02, CTL-08/09/10")


def page_5a(c: Canvas, n: int) -> None:
    s = Sheet(c, "5A", "Rotor Balance and Runout", n)
    x, y, w, h = s.panel("MEASURE BEFORE POWER", 245)
    s.checkboxes([
        "Use a released level/indexed fixture, a dial indicator readable to 0.01 mm, and a calibrated scale readable to 0.01 g.",
        "Define the vibration measurement and rejection criterion before any powered motion.",
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
    s = Sheet(c, "5B", "Guarded Rotor Proof", n, "HOLD: PROCEDURE MISSING")
    x, y, w, h = s.panel("ENGINEER BEFORE TESTING", 260, RED_BG, RED, RED)
    s.checkboxes([
        "Release a fixture drawing with rated containment, external drive, remote cutoff/interlock, and instrument mounting.",
        "Write the two-person procedure: roles, callouts, abort criteria, maximum duration, safe positions, and restoration checks.",
        "Define the exact bypass hardware/state if a temporary electronic bypass is unavoidable.",
        "Provide independent RPM measurement and a measurable vibration/contact abort criterion.",
        "Record pre-run balance, runout, fastener witness marks, and hand-clearance condition.",
        "Approve the procedure before any high-energy run.",
    ], x + 14, y + 210, w - 28, 8.8)

    x, y, w, h = s.panel("PROOF REQUIREMENTS", 260, PURPLE_BG, PURPLE, PURPLE)
    s.checkboxes([
        "MEC-03 proof requirement: external guarded drive, 216 RPM, 2 minutes each direction.",
        "After any bypass, restore and independently reverify the 180 RPM MCF limit and 200 RPM analog trip before fixture removal.",
        "Never dynamically test the 270 RPM credible bypass load. It is calculation-only.",
        "Use the manual cutoff immediately for unexpected vibration, sound, contact, or speed deviation.",
        "Reject damage, opening, permanent set, deformation, balance shift, contact, or loosened witness marks.",
        "Repeat balance, runout, witness-mark, and hand-clearance checks after both directions pass.",
    ], x + 14, y + 210, w - 28, 8.8)

    s.stop("No test is authorized by this sheet. Release the fixture and procedures first; then issue an execution revision.")
    s.footer("testing/test-matrix.csv; docs/parts.md, design loads", "MEC-03, MEC-07")


def page_5c(c: Canvas, n: int) -> None:
    s = Sheet(c, "5C", "Representative Starts and Thermal", n, "HOLD: METHODS TO DEFINE")
    x, y, w, h = s.panel("START AND SPEED QUALIFICATION", 260)
    s.checkboxes([
        "With the representative final rotor guarded, run the released MPET procedure; cross-check R/L/BEMF, then complete and read back the golden image.",
        "Before starts, require config check to report config=verified and independently verify the 180 RPM MCF limit and 200 RPM analog trip.",
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
        "Run the complete fan for 8 hours at 170 RPM on the guarded fixture.",
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
        "Clear the room and establish a manual cutoff observer.",
        "Confirm plate seating, anchor washers, tether, catcher, Hall gap, wall gap, and housing clearance.",
        "Confirm firmware golden-image verdict is verified and power restoration remains off.",
        "Approve and write the speed ladder, dwell time, maximum, measurements, and abort thresholds before starting: __________________",
        "Start at the released minimum speed; do not improvise a higher installed test point.",
    ], x + 14, y + 130, w - 28, 8.9)

    x, y, w, h = s.panel("INCREASING LIMITED-SPEED CHECKS", 245, GREEN_BG, GREEN, GREEN)
    s.checkboxes([
        "At each step inspect plate movement, tether behavior, catcher clearance, Hall gap, wall gap, and new resonance.",
        "Verify commanded speed against independent tach and recorded telemetry.",
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


PAGES: list[Callable[[Canvas, int], None]] = [
    page_0a,
    page_1a,
    page_1b,
    page_1c,
    page_3a,
    page_3b,
    page_3c,
    page_4a,
    page_4b,
    page_5a,
    page_5b,
    page_5c,
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
