import { afterAll, expect, test } from "bun:test"
import { mkdtemp, readFile, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

const stage = await mkdtemp(join(tmpdir(), "stillair-kicad-export-test-"))

afterAll(async () => {
  await rm(stage, { recursive: true, force: true })
})

test("exports every hierarchical schematic file", async () => {
  const process = Bun.spawn(
    [
      "bun",
      "run",
      "tools/export_kicad_schematic.ts",
      "dist/pcb-03/design/pcb-03/circuit.json",
      "pcb-03.circuit.kicad_sch",
    ],
    {
      cwd: import.meta.dir + "/..",
      env: { ...Bun.env, STILLAIR_HANDOFF_STAGE: stage },
      stdout: "pipe",
      stderr: "pipe",
    },
  )
  expect(await process.exited).toBe(0)
  const root = await readFile(join(stage, "pcb-03.circuit.kicad_sch"), "utf8")
  expect(root).toContain('(property "Sheetfile" "main.kicad_sch"')
  expect((await readFile(join(stage, "main.kicad_sch"), "utf8")).length).toBeGreaterThan(1000)
})
