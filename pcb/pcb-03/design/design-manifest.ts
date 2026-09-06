import { boardSpec, footprints, netAliases, netMembers, placements, type Ref } from "./board-spec"

export const componentDefinitions: Record<Ref, { value: string; mpn?: string; symbol: string; pads: string[]; datasheet?: string }> = {
  C1: { value: "100nF", mpn: "C0603C104K5RACTU", symbol: "Device:C", pads: ["1", "2"] },
  C2: { value: "100nF", mpn: "C0603C104K5RACTU", symbol: "Device:C", pads: ["1", "2"] },
  C3: { value: "4.7uF", mpn: "EMK107ABJ475KA-T", symbol: "Device:C", pads: ["1", "2"] },
  H1: { value: "M2 NPTH", symbol: "Mechanical:MountingHole", pads: [] },
  H2: { value: "M2 NPTH", symbol: "Mechanical:MountingHole", pads: [] },
  J1: { value: "S4B-PH-K-S", mpn: "S4B-PH-K-S", symbol: "Connector_Generic:Conn_01x04", pads: ["1", "2", "3", "4"], datasheet: "https://www.jst-mfg.com/product/index.php?series=199" },
  J2: { value: "S8B-PH-K-S", mpn: "S8B-PH-K-S", symbol: "Connector_Generic:Conn_01x08", pads: ["1", "2", "3", "4", "5", "6", "7", "8"], datasheet: "https://www.jst-mfg.com/product/index.php?series=199" },
  R1: { value: "10k", mpn: "PTN0603Y1002BST1", symbol: "Device:R", pads: ["1", "2"] },
  R2: { value: "10k", mpn: "PTN0603Y1002BST1", symbol: "Device:R", pads: ["1", "2"] },
  R3: { value: "10k", mpn: "PTN0603Y1002BST1", symbol: "Device:R", pads: ["1", "2"] },
  U1: { value: "SC18IS606PWJ", mpn: "SC18IS606PWJ", symbol: "Interface_Expansion:SC18IS606PW", pads: Array.from({ length: 16 }, (_, index) => String(index + 1)), datasheet: "https://www.nxp.com/products/interfaces/ic-spi-i3c-interface-devices/bridges/ic-bus-to-spi-bridge%3ASC18IS606" },
  U2: { value: "PCA9536DR", mpn: "PCA9536DR", symbol: "Interface_Expansion:PCA9536D", pads: Array.from({ length: 8 }, (_, index) => String(index + 1)), datasheet: "https://www.ti.com/product/PCA9536" },
}

const stableComponentId = (ref: string) => `pcb03.component.${ref.toLowerCase()}`
const stableNetId = (name: string) => `pcb03.net.${(netAliases as Record<string, string>)[name]?.toLowerCase() ?? name.toLowerCase()}`

export const designManifest = {
  schema_version: 1,
  board: {
    stable_id: "pcb03.board.main",
    width_mm: boardSpec.widthMm,
    height_mm: boardSpec.heightMm,
    layer_count: boardSpec.layerCount,
    coordinate_system: "center-x-right-y-up",
    specs: {
      material: boardSpec.material,
      thickness_mm: boardSpec.thicknessMm,
      copper_weight_oz: boardSpec.copperWeightOz,
      solder_mask_color: boardSpec.solderMaskColor,
      silkscreen_color: boardSpec.silkscreenColor,
      surface_finish: boardSpec.surfaceFinish,
      assembly_sides: boardSpec.assemblySides,
    },
    outline: {
      kind: "rectangle",
      center_mm: [0, 0],
      width_mm: boardSpec.widthMm,
      height_mm: boardSpec.heightMm,
    },
    holes: (["H1", "H2"] as const).map((ref) => ({
      stable_id: `pcb03.hole.${ref.toLowerCase()}`,
      ref,
      x_mm: placements[ref].x,
      y_mm: placements[ref].y,
      drill_mm: 2.2,
      plated: false,
    })),
  },
  versions: {
    tscircuit: "0.0.2465",
    circuit_json_to_kicad: "0.0.205",
    node: typeof process === "undefined" ? "unavailable" : process.version.replace(/^v/, ""),
    bun: typeof Bun === "undefined" ? "unavailable" : Bun.version,
  },
  components: (Object.keys(placements) as Ref[]).map((ref) => {
    const component = componentDefinitions[ref]
    return {
      stable_id: stableComponentId(ref),
      ref,
      value: component.value,
      fields: {
        ...(component.mpn ? { manufacturer_part_number: component.mpn } : {}),
        ...(component.datasheet ? { datasheet_url: component.datasheet } : {}),
      },
      symbol: component.symbol,
      footprint: {
        tscircuit: `kicad:${footprints[ref].replace(":", "/")}`,
        kicad: footprints[ref],
        pad_numbers: component.pads,
      },
      placement: {
        x_mm: placements[ref].x,
        y_mm: placements[ref].y,
        rotation_deg: placements[ref].rotation,
        side: "front",
      },
    }
  }),
  nets: Object.entries(netMembers).map(([sourceName, members]) => ({
    stable_id: stableNetId(sourceName),
    name: (netAliases as Record<string, string>)[sourceName] ?? sourceName,
    endpoints: members.map((member) => {
      const [ref, pad] = member.split(".")
      if (!ref || !pad) throw new Error(`Invalid net member ${member}`)
      return { component: stableComponentId(ref), pad }
    }),
  })),
  metadata: {
    board_designator: boardSpec.designator,
    title: boardSpec.title,
    source_net_aliases: netAliases,
  },
} as const
