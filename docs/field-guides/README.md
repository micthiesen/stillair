# Integration field guides

`build_field_guides.py` generates the printable Stillair integration binder from the
canonical requirements in `docs/`, `testing/test-matrix.csv`, and the KiCad board files.

```bash
UV_CACHE_DIR=/tmp/stillair-uv-cache uv run --with reportlab \
  python3 docs/field-guides/build_field_guides.py
```

The generated PDF is written to
`output/pdf/stillair-integration-field-guides.pdf`.

For a concise PCB-01 rebuild handout with only the manually installed parts and the removable
installed-tuning leads, run:

```bash
UV_CACHE_DIR=/tmp/stillair-uv-cache uv run --with reportlab \
  python3 docs/field-guides/build_pcb01_rebuild_booklet.py
```

This writes `output/pdf/pcb01-rebuild-and-tuning-leads.pdf`. Print it two-sided on the long edge.

For the one-page switched wiring map from PCB-01 J7 to the DSD TECH SH-U09C2 adapter, run:

```bash
UV_CACHE_DIR=/tmp/stillair-uv-cache uv run --with reportlab \
  python3 docs/field-guides/build_j7_usb_uart_guide.py
```

This writes `output/pdf/pcb-01-j7-usb-uart.pdf`. It includes normally-open BOOT/RESET switches,
the removable RTS automated-boot branch, manual fallback, and monochrome line patterns. Print it
one-sided in landscape orientation.

The sheets are intentionally concise. They complement, rather than replace, the detailed
requirements and vendor procedures. A `HOLD` badge means the guide records the boundary but
does not authorize work beyond it.

The PCB population pages use top/component-side target renders exported from KiCad and kept
in `docs/field-guides/assets/`. They are placement aids, not photographs of an already-built
board. Refresh them whenever either PCB layout changes, and re-check every callout against the
position export before printing.

For the fine-pitch techniques used on sheets 1A and 1B, see the curated
[SMD soldering video references](soldering-videos.md).
