# PCB-01 V2 fabrication notes

These requirements are not conveyed reliably by Gerber and Excellon alone. Paste the two quoted
lines into the JLCPCB order remarks and require production-file confirmation before approval.

> POFV REQUIRED: Fill and copper-cap the twelve 0.30 mm plated holes inside U1 exposed pad 41.
> Treat only the coordinates in pofv-locations.csv as POFV, even if Excellon calls them component
> drills. They are tented on both outer masks. Do not leave resin exposed and do not open the mask.

> U3 PADS 4/5 ARE SOLDER-MASK-DEFINED: Preserve the submitted 0.08 mm mask overlap on all sides.
> Do not convert pads 4/5 to NSMD or expand their mask apertures during CAM.

Order and production-file checks:

- 88 x 64 mm, four layers, 1.6 mm, 2 oz outer copper, 1 oz inner copper, ENIG.
- FR-4 Tg >= 150 C, green solder mask, white silkscreen.
- Select filled and capped vias / POFV. The KiCad stackup records filling and capping as enabled.
- Standard PCBA, top side only. Use bom-jlcpcb.csv and cpl-jlcpcb.csv.
- Confirm every U1 POFV coordinate and both U3 SMD mask apertures in JLC's production files.
- Do not approve manufacturing until routing is complete, zones are refilled, DRC has zero
  unconnected items, and a fresh non-assembly-only package has been generated.
