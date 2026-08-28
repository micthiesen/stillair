#!/usr/bin/env python3
"""Build the concise PCB-01 population and removable tuning-lead booklet."""

from __future__ import annotations

from pathlib import Path

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
        (0.965, 0.235),  # J8
        ((92.90 - 50.0) / 78.0, (108.0 - 73.05) / 58.0),  # TP20 FG
        ((92.90 - 50.0) / 78.0, (108.0 - 75.20) / 58.0),  # TP17 NFAULT
        ((89.60 - 50.0) / 78.0, (108.0 - 78.20) / 58.0),  # TP12 DRVOFF
        ((97.38 - 50.0) / 78.0, (108.0 - 56.45) / 58.0),  # TP26 AGND
        ((72.30 - 50.0) / 78.0, (108.0 - 74.00) / 58.0),  # TP2/TP3 pair
    ]
    for index, (px, py) in enumerate(points, start=1):
        numbered(c, index, dx + px * dw, dy + py * dh)

    c.setFillColor(PAPER)
    c.setStrokeColor(LINE)
    c.roundRect(50, 326, 512, 30, 7, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7.4)
    labels = [
        "1 J8 SOX/SPEED",
        "2 TP20 FG",
        "3 TP17 NFAULT",
        "4 TP12 DRVOFF",
        "5 TP26 AGND",
        "6 TP2/TP3 VM24",
    ]
    for index, label in enumerate(labels):
        c.drawString(60 + (index % 3) * 168, 344 - (index // 3) * 12, label)

    mini_card(
        c,
        "NORMAL TUNING: LOW-VOLTAGE PIGTAILS",
        "Use 30 AWG insulated wire, 50-100 mm. Fit J8.9 SOX (white), J8.6 SPEED (green), "
        "TP20 FG (yellow), TP17 NFAULT (orange), TP12 DRVOFF (blue), and TP26 AGND "
        "(black). Label both ends. Make insulated test loops at the free ends. For the OWON, "
        "CH1 is SOX and CH2 selects FG/SPEED/NFAULT/DRVOFF; both channel grounds use AGND.",
        35,
        190,
        350,
        125,
        GREEN,
        GREEN_BG,
    )
    mini_card(
        c,
        "VM24: DIRECT x10 PROBE",
        "Do not add a long VM24 pigtail. With power off, attach the x10 tip directly to TP2 "
        "and its spring ground to TP3. Strain-relieve the probe before mounting. In a bus "
        "session, every OWON ground must use PGND.",
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
        "end before power. Never wire TP4, motor phases, switch nodes, or USB data pads. Remove "
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
