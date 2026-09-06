import { readFile } from "node:fs/promises"
import { basename, resolve } from "node:path"
import { CircuitJsonToKicadSchConverter } from "circuit-json-to-kicad"

const [circuitJsonArgument, schematicFilename] = process.argv.slice(2)
const stage = process.env.STILLAIR_HANDOFF_STAGE

if (!stage || !circuitJsonArgument || !schematicFilename) {
  throw new Error(
    "usage: STILLAIR_HANDOFF_STAGE=... export_kicad_schematic.ts <circuit.json> <root.kicad_sch>",
  )
}
if (basename(schematicFilename) !== schematicFilename) {
  throw new Error("schematic filename must not contain a directory")
}

const circuitJson = JSON.parse(await readFile(resolve(circuitJsonArgument), "utf8"))
const labelBackedPowerNetIds = new Set<string>()
for (const element of circuitJson) {
  if (
    element.type === "source_net" &&
    (element.is_power || element.is_ground || element.is_positive_voltage_source)
  ) {
    labelBackedPowerNetIds.add(element.source_net_id)
    element.is_power = false
    element.is_ground = false
    element.is_positive_voltage_source = false
  }
}
for (const element of circuitJson) {
  if (
    element.type === "schematic_net_label" &&
    labelBackedPowerNetIds.has(element.source_net_id)
  ) {
    delete element.symbol_name
  }
}
const converter = new CircuitJsonToKicadSchConverter(circuitJson)
converter.runUntilFinished()
const files = converter.getOutputFiles({ schematicFilename })

for (const file of files) {
  if (basename(file.filename) !== file.filename) {
    throw new Error(`converter emitted unsafe schematic filename: ${file.filename}`)
  }
  await Bun.write(resolve(stage, file.filename), file.content)
}

console.log(`Exported ${files.length} KiCad schematic file(s)`)
