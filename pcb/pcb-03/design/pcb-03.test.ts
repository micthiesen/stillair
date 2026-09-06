import { describe, expect, test } from "bun:test"
import packageJson from "../../package.json"
import manualEdits from "./manual-edits.json"
import augmentation from "./kicad-augment.json"
import { boardSpec, footprints, netMembers, placements } from "./board-spec"
import { componentDefinitions, designManifest } from "./design-manifest"

type CircuitElement = Record<string, any> & { type: string }

const circuitPath = new URL("../../dist/pcb-03/design/pcb-03/circuit.json", import.meta.url)
const circuit = JSON.parse(await Bun.file(circuitPath).text()) as CircuitElement[]
const byType = (type: string) => circuit.filter((element) => element.type === type)

describe("PCB-03 authoritative fixture", () => {
  test("pins the validated tscircuit toolchain", () => {
    expect(packageJson.dependencies.tscircuit).toBe("0.0.2465")
    expect(packageJson.dependencies["circuit-json-to-kicad"]).toBe("0.0.205")
    expect(String(designManifest.versions.tscircuit)).toBe(packageJson.dependencies.tscircuit)
    expect(String(designManifest.versions.circuit_json_to_kicad)).toBe(packageJson.dependencies["circuit-json-to-kicad"])
  })

  test("manual placement and stable manifest agree exactly", () => {
    expect(manualEdits.pcb_placements).toHaveLength(12)
    for (const edit of manualEdits.pcb_placements) {
      const expected = placements[edit.selector as keyof typeof placements]
      expect(edit.relative_to).toBe("group_center")
      expect(edit.center).toEqual({ x: expected.x, y: expected.y })
      const manifestComponent = designManifest.components.find(({ ref }) => ref === edit.selector)
      expect(manifestComponent?.placement).toEqual({
        x_mm: expected.x,
        y_mm: expected.y,
        rotation_deg: expected.rotation,
        side: "front",
      })
    }
  })

  test("Circuit JSON has the exact board and twelve placed references", () => {
    const board = byType("pcb_board")[0]
    expect(board).toMatchObject({
      center: { x: 0, y: 0 },
      width: boardSpec.widthMm,
      height: boardSpec.heightMm,
      thickness: boardSpec.thicknessMm,
      num_layers: boardSpec.layerCount,
      material: boardSpec.material,
      min_trace_width: boardSpec.minimums.traceWidthMm,
      min_trace_to_pad_edge_clearance: boardSpec.minimums.clearanceMm,
      min_pad_edge_to_pad_edge_clearance: boardSpec.minimums.clearanceMm,
      min_via_hole_diameter: boardSpec.minimums.viaDrillMm,
      min_via_pad_diameter: boardSpec.minimums.viaPadMm,
    })

    expect(designManifest.board.outline).toEqual({
      kind: "rectangle",
      center_mm: [board.center.x, board.center.y],
      width_mm: board.width,
      height_mm: board.height,
    })

    const sources = new Map(byType("source_component").map((item) => [item.source_component_id, item.name]))
    const pcbs = byType("pcb_component")
    expect(pcbs).toHaveLength(12)
    expect([...sources.values()].sort()).toEqual(Object.keys(placements).sort())
    for (const pcb of pcbs) {
      const ref = sources.get(pcb.source_component_id) as keyof typeof placements
      const expected = placements[ref]
      if (pcb.display_offset_x !== undefined || pcb.display_offset_y !== undefined) {
        expect({ x: pcb.display_offset_x, y: pcb.display_offset_y }).toEqual({ x: expected.x, y: expected.y })
        expect(pcb.position_mode).toBe("relative_to_group_anchor")
      } else {
        expect(pcb.center.x).toBeCloseTo(expected.x, 9)
        expect(pcb.center.y).toBeCloseTo(expected.y, 9)
      }
      expect(pcb.rotation).toBe(expected.rotation)
      expect(pcb.layer).toBe("top")
      expect(pcb.metadata.kicad_footprint.footprintName).toBe(footprints[ref])
    }
  })

  test("manifest component identities, values, symbols, pads, and holes match Circuit JSON", () => {
    const sources = new Map(byType("source_component").map((item) => [item.name, item]))
    const pcbs = new Map(byType("pcb_component").map((item) => [item.source_component_id, item]))
    const sourceById = new Map(byType("source_component").map((item) => [item.source_component_id, item]))
    const portsByComponent = Object.groupBy(byType("source_port"), ({ source_component_id }) => source_component_id)
    const schematicIds = new Set(byType("schematic_component").map(({ source_component_id }) => source_component_id))

    expect(designManifest.components).toHaveLength(12)
    for (const manifestComponent of designManifest.components) {
      const source = sources.get(manifestComponent.ref)
      expect(source).toBeDefined()
      if (!source) continue
      expect(source.manufacturer_part_number).toBe(manifestComponent.fields.manufacturer_part_number ?? manifestComponent.value)
      if (source.ftype === "simple_resistor") expect(source.resistance).toBe(Number.parseFloat(manifestComponent.value) * 1_000)
      else if (source.ftype === "simple_capacitor") {
        const farads = manifestComponent.value === "100nF" ? 100e-9 : 4.7e-6
        expect(source.capacitance).toBeCloseTo(farads, 15)
      } else expect(manifestComponent.value).toBe(source.manufacturer_part_number)

      const expectedPads = componentDefinitions[manifestComponent.ref].pads
      expect((portsByComponent[source.source_component_id] ?? []).map(({ pin_number }) => String(pin_number)).sort()).toEqual([...expectedPads].sort())
      expect(manifestComponent.symbol).toBe(componentDefinitions[manifestComponent.ref].symbol)
      expect(schematicIds.has(source.source_component_id)).toBe(!manifestComponent.ref.startsWith("H"))
      expect(pcbs.get(source.source_component_id)?.metadata.kicad_footprint.footprintName).toBe(manifestComponent.footprint.kicad)
    }

    const holes = byType("pcb_hole")
    expect(holes).toHaveLength(2)
    for (const expected of designManifest.board.holes) {
      const source = sources.get(expected.ref)
      const pcb = source ? pcbs.get(source.source_component_id) : undefined
      const hole = holes.find(({ pcb_component_id }) => pcb_component_id === pcb?.pcb_component_id)
      expect(hole).toMatchObject({
        hole_shape: "circle",
        hole_diameter: expected.drill_mm,
        x: expected.x_mm,
        y: expected.y_mm,
        is_covered_with_solder_mask: false,
      })
      expect(expected.plated).toBe(false)
      expect(sourceById.get(source?.source_component_id)?.name).toBe(expected.ref)
    }
  })

  test("Circuit JSON connectivity matches every specified pin and net", () => {
    const sourceComponents = new Map(byType("source_component").map((item) => [item.source_component_id, item.name]))
    const ports = new Map(byType("source_port").map((item) => [item.source_port_id, item]))
    const sourceNets = new Map(byType("source_net").map((item) => [item.source_net_id, item.name]))
    const actual = new Map<string, Set<string>>()
    for (const trace of byType("source_trace")) {
      for (const netId of trace.connected_source_net_ids ?? []) {
        const net = sourceNets.get(netId)
        const members = actual.get(net) ?? new Set<string>()
        for (const portId of trace.connected_source_port_ids ?? []) {
          const port = ports.get(portId)
          expect(port).toBeDefined()
          if (!port) continue
          members.add(`${sourceComponents.get(port.source_component_id)}.${port.pin_number}`)
        }
        actual.set(net, members)
      }
    }
    expect([...sourceNets.values()].sort()).toEqual(Object.keys(netMembers).sort())
    for (const [net, members] of Object.entries(netMembers)) {
      expect([...(actual.get(net) ?? new Set())].sort()).toEqual([...members].sort())
    }
  })

  test("build contains no error elements and handoff augmentation is explicit", () => {
    expect(circuit.filter(({ type }) => type.endsWith("error"))).toEqual([])
    const reviewedWarningClasses = new Set([
      "source_refdes_convention_warning",
      "source_pin_missing_trace_warning",
      "schematic_component_styling_warning",
    ])
    const warningClasses = new Set(circuit.filter(({ type }) => type.endsWith("warning")).map(({ type }) => type))
    expect([...warningClasses].filter((type) => !reviewedWarningClasses.has(type))).toEqual([])
    expect(augmentation.schema_version).toBe(1)
    expect(augmentation.board_id).toBe(designManifest.board.stable_id)
    expect(new Set(augmentation.operations.map(({ id }) => id)).size).toBe(augmentation.operations.length)
    expect(augmentation.operations.every(({ owner }) => owner === "kicad")).toBe(true)
    expect(augmentation.operations.find(({ kind }) => kind === "net_alias")).toMatchObject({
      target: { net_stable_id: "pcb03.net.3v3" },
      params: { source_name: "V3V3", kicad_name: "3V3" },
    })
    const footprintOverrides = augmentation.operations.filter(({ kind }) => kind === "footprint_override")
    expect(footprintOverrides).toHaveLength(12)
    for (const component of designManifest.components) {
      expect(footprintOverrides.find(({ target }) => target.component_stable_id === component.stable_id)).toMatchObject({
        params: { kicad_footprint: component.footprint.kicad },
      })
    }
  })
})
