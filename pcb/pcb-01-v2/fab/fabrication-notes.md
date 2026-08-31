# PCB-01 V2 fabrication notes

These requirements are not conveyed reliably by Gerber and Excellon alone. Paste the three quoted
requirements into the JLCPCB order remarks and require production-file confirmation before approval.

> POFV REQUIRED: Epoxy-fill and copper-cap the twelve 0.30 mm plated holes inside U1 exposed pad
> 41. Treat only the coordinates in pofv-locations.csv and pofv-location-map.pdf as POFV, even
> though Excellon calls them T2 ComponentDrill. The attachments state both KiCad top-view and
> Excellon signed coordinates. Keep U1 pad 41's submitted top solder-mask aperture open for
> soldering; add no separate bottom apertures. Do not leave resin exposed.

> U3 PADS 4/5 ARE SOLDER-MASK-DEFINED: Preserve the submitted 0.08 mm mask overlap on all sides.
> Do not convert pads 4/5 to NSMD or expand their mask apertures during CAM.

> USB IMPEDANCE: Hold 97 ohm differential on both via-free F.Cu USB sections, `USB_DP`/`USB_DN`
> from J4 through U13 to R58/R59 and `USB_D_MCU_P`/`USB_D_MCU_N` from R58/R59 to U2. Both use
> 0.20 mm track width and 0.20 mm pair gap. The worst plug-orientation path skew is 1.80 mm;
> the MCU-side skew is 0.01 mm. The USB-C duplicate-contact breakout is artwork-defined and must
> not be reshaped in CAM. JLC's live coated,
> non-coplanar calculator gives 96.85 ohm for this geometry, inside the USB 2.0 90 ohm +/-15%
> range. See impedance-requirements.csv and confirm the 97 ohm target in CAM before release.

Order and production-file checks:

- 88 x 64 mm, four layers, 1.6 mm, 2 oz outer copper, 1 oz inner copper, ENIG.
- FR-4 Tg >= 150 C, green solder mask, white silkscreen.
- Impedance-controlled JLC041621-7628 stack: 0.070 mm F.Cu / 0.203 mm 7628 prepreg
  (Er 4.4) / 0.030 mm In1 / 1.030 mm FR-4 core / 0.030 mm In2 / 0.203 mm 7628
  prepreg / 0.070 mm B.Cu. This is JLC's live 4-layer, 1.6 mm, 2 oz outer, 1 oz inner result.
- Select epoxy-filled and capped vias, attach pofv-location-map.pdf and pofv-locations.csv, and
  repeat in the order remarks that the request applies to these twelve pad holes. The ordinary via
  finish selector alone does not control component pad holes.
- Standard PCBA, top side only. Use bom-jlcpcb.csv and cpl-jlcpcb.csv.
- Confirm every U1 POFV coordinate, both U3 SMD mask apertures, and the 97 ohm differential USB
  requirement in JLC's production files.
- Do not approve manufacturing until routing is complete, zones are refilled, DRC has zero
  unconnected items, and a fresh non-assembly-only package has been generated.
