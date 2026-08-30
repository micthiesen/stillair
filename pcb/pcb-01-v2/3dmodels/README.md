# PCB-01 V2 local 3D models

- `ESP32-C6-WROOM-1.STEP` is Espressif's module model. Its corner-origin model is offset in the
  footprint by (-9, -12.75) mm so the 18 x 25.5 mm body aligns with the official land pattern.
- `J1_43045-0200_ENVELOPE.stp` and `J2_43650-0300_ENVELOPE.stp` are conservative body-envelope
  solids built from the exact KiCad F.Fab extents and Molex customer-drawing maximum height. They
  replace nonexistent KiCad package paths and validate board/enclosure access; they are not detailed
  cosmetic connector models.
- `RV1_3224W_ENVELOPE.stp` is the corresponding Bourns body-envelope solid from the exact F.Fab
  extents and maximum body height.

Footprints, courtyards, holes, and fabrication data remain authoritative. These local solids are
mechanical review aids and must stay aligned with their footprint origins.
