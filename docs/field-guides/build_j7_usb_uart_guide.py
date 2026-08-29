#!/usr/bin/env python3
"""Build the single-page PCB-01 J7 to SH-U09C2 wiring guide."""

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "pcb-01-j7-usb-uart.pdf"

NAVY = HexColor("#18314F")
INK = HexColor("#18202A")
MUTED = HexColor("#5B6673")
LIGHT = HexColor("#E9EEF3")
BOARD = HexColor("#174B3D")
COPPER = HexColor("#D9A441")
RED = HexColor("#B42318")
WIRE = {
    "A": HexColor("#1261A0"),
    "B": HexColor("#00877A"),
    "C": HexColor("#30343B"),
    "D": HexColor("#A45A00"),
    "E": HexColor("#7B3FA1"),
}


def label(c: Canvas, text: str, x: float, y: float, size=9, color=INK, font="Helvetica"):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, text)


def centered(c: Canvas, text: str, x: float, y: float, size=9, color=INK, font="Helvetica"):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, text)


def wire_badge(c: Canvas, key: str, x: float, y: float, radius=9):
    c.setFillColor(WIRE[key])
    c.setStrokeColor(white)
    c.setLineWidth(1)
    c.circle(x, y, radius, fill=1, stroke=1)
    centered(c, key, x, y - 3.2, 9, white, "Helvetica-Bold")


def rounded_box(c: Canvas, x, y, w, h, title, title_color=NAVY):
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#C9D2DC"))
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    label(c, title, x + 12, y + h - 19, 11, title_color, "Helvetica-Bold")


def checkbox(c: Canvas, x, y, size=9):
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.8)
    c.rect(x, y, size, size, fill=0, stroke=1)


def draw_board(c: Canvas, x: float, y: float):
    """Enlarged component-side J7 footprint, matching docs/probing.md."""
    w, h = 282, 236
    c.setFillColor(BOARD)
    c.setStrokeColor(HexColor("#0E342A"))
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    # Three Tag-Connect alignment holes establish the footprint's asymmetry.
    for hx, hy in [(x + 31, y + 112), (x + 250, y + 151), (x + 250, y + 73)]:
        c.setFillColor(HexColor("#111820"))
        c.setStrokeColor(HexColor("#AAB5BF"))
        c.circle(hx, hy, 10, fill=1, stroke=1)
    centered(c, "alignment holes", x + 141, y + 21, 8, HexColor("#C8DDD6"))

    cols = [x + 84, x + 141, x + 198]
    rows = [y + 145, y + 82]
    pads = {
        (0, 0): ("2", "UART_TX", "A"),
        (1, 0): ("4", "ESP_EN", "E"),
        (2, 0): ("6", "AGND", "C"),
        (0, 1): ("1", "3V3", None),
        (1, 1): ("3", "UART_RX", "B"),
        (2, 1): ("5", "ESP_BOOT", "D"),
    }
    pad_points = {}
    for (ci, ri), (number, name, key) in pads.items():
        px, py = cols[ci], rows[ri]
        pad_points[number] = (px, py)
        c.setFillColor(COPPER)
        c.setStrokeColor(HexColor("#F5D58B"))
        c.setLineWidth(1.4)
        c.circle(px, py, 15, fill=1, stroke=1)
        centered(c, number, px, py - 4, 11, INK, "Helvetica-Bold")
        centered(c, name, px, py + (23 if ri == 0 else -30), 8, white, "Helvetica-Bold")
        if key:
            wire_badge(c, key, px - 21, py + (0 if ci != 2 else -22), 8)

    # Strong no-connect marker over pin 1.
    p1x, p1y = pad_points["1"]
    c.setStrokeColor(RED)
    c.setLineWidth(4)
    c.line(p1x - 13, p1y - 13, p1x + 13, p1y + 13)
    c.line(p1x - 13, p1y + 13, p1x + 13, p1y - 13)
    centered(c, "NO WIRE", p1x, p1y - 47, 8, HexColor("#FFD0CC"), "Helvetica-Bold")
    return pad_points


def draw_adapter(c: Canvas, x: float, y: float):
    w, h = 254, 236
    c.setFillColor(HexColor("#F7F9FB"))
    c.setStrokeColor(HexColor("#8D99A6"))
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, 15, fill=1, stroke=1)
    label(c, "DSD TECH SH-U09C2", x + 18, y + h - 28, 14, NAVY, "Helvetica-Bold")
    label(c, "USB-UART ADAPTER", x + 18, y + h - 45, 8, MUTED, "Helvetica-Bold")

    # USB-A plug silhouette.
    c.setFillColor(HexColor("#AAB4BF"))
    c.setStrokeColor(HexColor("#6A7480"))
    c.rect(x + w - 17, y + 66, 33, 88, fill=1, stroke=1)
    c.setFillColor(HexColor("#DCE2E8"))
    c.rect(x + w - 9, y + 78, 16, 64, fill=1, stroke=0)

    # Logic-level selector. The adapter's jumper selects both I/O level and VCC output.
    label(c, "LOGIC", x + 18, y + 166, 8, MUTED, "Helvetica-Bold")
    for i, txt in enumerate(["1.8", "3.3", "5"]):
        bx = x + 18 + i * 42
        c.setFillColor(NAVY if txt == "3.3" else LIGHT)
        c.setStrokeColor(NAVY)
        c.roundRect(bx, y + 137, 34, 22, 4, fill=1, stroke=1)
        centered(c, txt, bx + 17, y + 144, 8, white if txt == "3.3" else MUTED, "Helvetica-Bold")
    label(c, "SET 3.3 V", x + 148, y + 144, 10, NAVY, "Helvetica-Bold")

    labels = ["CTS", "RTS", "RXD", "TXD", "GND", "VCC"]
    pin_x = x + 36
    pin_y0 = y + 115
    pin_points = {}
    for i, name in enumerate(labels):
        py = pin_y0 - i * 18
        c.setFillColor(HexColor("#3B4652"))
        c.rect(pin_x, py - 4, 10, 10, fill=1, stroke=0)
        label(c, name, pin_x + 18, py - 2, 9, INK, "Helvetica-Bold")
        pin_points[name] = (pin_x, py + 1)

    label(c, "unused", x + 102, pin_points["CTS"][1] - 3, 8, MUTED)
    label(c, "unused", x + 102, pin_points["RTS"][1] - 3, 8, MUTED)
    label(c, "NO WIRE", x + 102, pin_points["VCC"][1] - 3, 8, RED, "Helvetica-Bold")
    c.setStrokeColor(RED)
    c.setLineWidth(2.5)
    vx, vy = pin_points["VCC"]
    c.line(vx - 3, vy - 6, vx + 13, vy + 6)
    c.line(vx - 3, vy + 6, vx + 13, vy - 6)

    label(c, "Use the labels printed on the adapter.", x + 18, y + 12, 8, MUTED, "Helvetica-Oblique")
    return pin_points


def connect(c: Canvas, key: str, start, end, route_y, bend_x):
    sx, sy = start
    ex, ey = end
    c.setStrokeColor(WIRE[key])
    c.setLineWidth(4)
    c.setLineCap(1)
    c.line(sx, sy, sx, route_y)
    c.line(sx, route_y, bend_x, route_y)
    c.line(bend_x, route_y, bend_x, ey)
    c.line(bend_x, ey, ex - 3, ey)
    wire_badge(c, key, bend_x, route_y, 8)


def bullet(c: Canvas, text: str, x: float, y: float, size=8.4, max_width=222):
    c.setFillColor(NAVY)
    c.circle(x + 2.5, y + 3, 2.2, fill=1, stroke=0)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if stringWidth(trial, "Helvetica", size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        label(c, line, x + 10, y - i * 11, size, INK)
    return y - max(15, len(lines) * 11 + 3)


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(OUTPUT), pagesize=landscape(letter))
    page_w, page_h = landscape(letter)
    c.setTitle("PCB-01 J7 to USB-UART Wiring Guide")
    c.setAuthor("Stillair")

    c.setFillColor(HexColor("#F3F6F8"))
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    label(c, "PCB-01 J7 -> USB-UART", 34, 575, 23, NAVY, "Helvetica-Bold")
    label(c, "Solder the five board leads with all power OFF. Board power stays separate.", 34, 555, 10, MUTED)

    board_x, diagram_y = 34, 301
    adapter_x = 504
    pads = draw_board(c, board_x, diagram_y)
    pins = draw_adapter(c, adapter_x, diagram_y)

    # Permanent data/ground lines.
    connect(c, "A", pads["2"], pins["RXD"], 510, 382)
    connect(c, "B", pads["3"], pins["TXD"], 326, 410)
    connect(c, "C", pads["6"], pins["GND"], 385, 438)

    # Service tails terminate in labeled, insulated loose ends rather than at adapter pins.
    for key, pad, tx, route_y, text in [
        ("D", pads["5"], 474, 309, "BOOT tail"),
        ("E", pads["4"], 474, 529, "EN tail"),
    ]:
        sx, sy = pad
        c.setStrokeColor(WIRE[key])
        c.setLineWidth(4)
        c.line(sx, sy, sx, route_y)
        c.line(sx, route_y, tx, route_y)
        c.setFillColor(white)
        c.setStrokeColor(WIRE[key])
        c.circle(tx, route_y, 5, fill=1, stroke=1)
        wire_badge(c, key, tx - 24, route_y, 8)
        centered(c, text, tx - 9, route_y + (13 if key == "E" else -19), 8, WIRE[key], "Helvetica-Bold")

    # Legend.
    rounded_box(c, 34, 76, 250, 204, "WIRE LEGEND  (write your colours)")
    legend = [
        ("A", "J7.2 TX  ->  adapter RXD"),
        ("B", "J7.3 RX  ->  adapter TXD"),
        ("C", "J7.6 AGND  ->  adapter GND"),
        ("D", "J7.5 BOOT  ->  loose service tail"),
        ("E", "J7.4 EN  ->  loose service tail"),
    ]
    yy = 238
    for key, text in legend:
        wire_badge(c, key, 52, yy + 2, 8)
        label(c, text, 68, yy - 1, 8.5, INK, "Helvetica-Bold")
        label(c, "colour:", 68, yy - 15, 8, MUTED)
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.6)
        c.line(105, yy - 16, 260, yy - 16)
        yy -= 34

    rounded_box(c, 296, 76, 228, 204, "BOARD END")
    y = 238
    for text in [
        "Power OFF and discharged before attaching or moving wires.",
        "Strip 0.5-1 mm. Flux and tin the pad and wire separately.",
        "Lay the wire flat on the pad. Hold still and touch the iron briefly.",
        "Magnify and inspect. Then check continuity and every adjacent pad.",
    ]:
        y = bullet(c, text, 311, y, max_width=195)

    rounded_box(c, 536, 76, 222, 204, "ADAPTER END + FLASH")
    y = 238
    for text in [
        "Push female Dupont sockets onto RXD, TXD and GND by printed label.",
        "Set logic to 3.3 V. Leave VCC, CTS and RTS empty.",
        "Cold ROM boot: power off, join D to C, power board, then release D.",
        "E is the reset tail. Attach or move Dupont wires only with power off.",
    ]:
        y = bullet(c, text, 551, y, max_width=188)

    # Bottom rule and quick no-connect reminders.
    c.setStrokeColor(HexColor("#C9D2DC"))
    c.line(34, 58, 758, 58)
    label(c, "NO CONNECTION:", 34, 39, 9, RED, "Helvetica-Bold")
    label(c, "J7.1 3V3", 119, 39, 9, INK, "Helvetica-Bold")
    label(c, "+", 179, 39, 9, MUTED)
    label(c, "adapter VCC", 195, 39, 9, INK, "Helvetica-Bold")
    label(c, "PCB-01 J7 / component side / 2026-08-28", 544, 39, 8, MUTED)

    c.showPage()
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    build()
