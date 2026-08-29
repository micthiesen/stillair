#!/usr/bin/env python3
"""Build the concise PCB-01 population and removable tuning-lead booklet."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from build_field_guides import (
    ASSETS,
    BLUE,
    BLUE_BG,
    GREEN,
    GREEN_BG,
    INK,
    LINE,
    MARGIN,
    PAPER,
    PURPLE,
    PURPLE_BG,
    RED,
    RED_BG,
    Sheet,
    fit_image,
    mini_card,
    numbered,
    page_1a_visual,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "pcb01-rebuild-and-tuning-leads.pdf"


def page_tuning_leads(c: Canvas, page_no: int) -> None:
    s = Sheet(c, "1B", "Removable Tuning Leads", page_no)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, 708, "INSTALL ON THE BENCH BEFORE THE BOARD GOES OVERHEAD")

    dx, dy, dw, dh = fit_image(c, ASSETS / "pcb01-top.png", 50, 362, 512, 330)

    # Exact test-point locations from pcb/pcb-01/probe-map.json. J8 marks the
    # connector body because its individual 1.27 mm pads are too small to label.
    points = [
        (0.965, 0.235, colors.black),  # J8.9 SOX, black lead
        ((92.90 - 50.0) / 78.0, (108.0 - 73.05) / 58.0, colors.HexColor("#d6a900")),
        ((97.38 - 50.0) / 78.0, (108.0 - 56.45) / 58.0, BLUE),
    ]
    for index, (px, py, color) in enumerate(points, start=1):
        numbered(c, index, dx + px * dw, dy + py * dh, color)

    c.setFillColor(PAPER)
    c.setStrokeColor(LINE)
    c.roundRect(50, 326, 512, 30, 7, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7.4)
    labels = ["1 J8.9 SOX - BLACK", "2 TP20 FG - YELLOW", "3 TP26 AGND - BLUE"]
    for index, label in enumerate(labels):
        c.drawString(60 + index * 168, 338, label)

    mini_card(
        c,
        "FIXED TUNING SETUP - DO NOT MOVE THE SCOPE",
        "Physical leads: J8.9 SOX black, TP20 FG yellow, TP26 AGND blue. OWON CH1 uses black, "
        "CH2 uses yellow, and both common channel grounds use blue. Keep this hookup unchanged "
        "through unloaded and loaded tuning. Firmware already records SPEED, NFAULT, and DRVOFF.",
        35,
        190,
        350,
        125,
        GREEN,
        GREEN_BG,
    )
    mini_card(
        c,
        "VM24: ONE-TIME BEFORE TUNING",
        "If the required bus capture is still open, complete it before fixing the OWON to these "
        "leads: x10 tip directly on TP2, spring ground on TP3. Do not substitute VM24 into CH2 "
        "during tuning.",
        397,
        190,
        180,
        125,
        PURPLE,
        PURPLE_BG,
    )
    mini_card(
        c,
        "FIT, INSPECT, REMOVE AFTER FINAL TUNING",
        "All sources removed and bulk capacitors discharged. Solder once, route insulated wire "
        "flat, add Kapton strain relief away from each joint, inspect under magnification, then "
        "continuity-check every lead to its named net and for adjacent-pad shorts. Cap every free "
        "end before power. TP4 is also usable AGND; never wire motor phases, switch nodes, or USB "
        "data pads. Remove "
        "the pigtails after the complete exposed and housed tuning campaign, then clean and inspect.",
        35,
        96,
        542,
        80,
        BLUE,
        BLUE_BG,
    )
    s.warning(
        "OWON CHANNEL GROUNDS ARE COMMON. Never put one ground on AGND and the other on PGND in the same setup.",
        35,
        88,
        542,
        RED,
        RED_BG,
    )
    s.footer("docs/probing.md; docs/observability.md; pcb/pcb-01/probe-map.json")


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(OUTPUT), pagesize=letter, pageCompression=1)
    canvas.setTitle("PCB-01 Rebuild and Tuning Leads")
    canvas.setAuthor("Stillair project")
    canvas.setSubject("PCB-01 manual population and removable installed tuning leads")
    page_1a_visual(canvas, 1)
    canvas.showPage()
    page_tuning_leads(canvas, 2)
    canvas.showPage()
    canvas.save()
    return OUTPUT


if __name__ == "__main__":
    print(build())
