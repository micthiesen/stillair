# Integration field guides

`build_field_guides.py` generates the printable Stillair integration binder from the
canonical requirements in `docs/` and `testing/test-matrix.csv`.

```bash
UV_CACHE_DIR=/tmp/stillair-uv-cache uv run --with reportlab \
  python3 docs/field-guides/build_field_guides.py
```

The generated PDF is written to
`output/pdf/stillair-integration-field-guides.pdf`.

The sheets are intentionally concise. They complement, rather than replace, the detailed
requirements and vendor procedures. A `HOLD` badge means the guide records the boundary but
does not authorize work beyond it.
