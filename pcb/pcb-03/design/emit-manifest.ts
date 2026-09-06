import { mkdir } from "node:fs/promises"
import { designManifest } from "./design-manifest"

const output = process.argv[2] ?? "dist/pcb-03/design/design-manifest.json"
await mkdir(output.slice(0, output.lastIndexOf("/")), { recursive: true })
await Bun.write(output, `${JSON.stringify(designManifest, null, 2)}\n`)
console.log(`Wrote ${output}`)
