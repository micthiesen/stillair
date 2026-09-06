import manualEdits from "./manual-edits.json"
import { createElement } from "react"
import { boardSpec, footprints, netMembers, placements } from "./board-spec"
import { componentDefinitions } from "./design-manifest"

const kicadFootprint = (footprintName: string) => ({ footprintName })
const kicadSymbol = (ref: keyof typeof componentDefinitions) => ({
  symbolName: componentDefinitions[ref].symbol,
})
const sourceFootprint = (footprintName: string) =>
  `kicad:${footprintName.replace(":", "/")}`

const U1_PIN_LABELS = {
  pin1: "SDA",
  pin2: "SCL",
  pin3: "INT_N",
  pin4: "RESET_N",
  pin5: "A2",
  pin6: "A1",
  pin7: "A0",
  pin8: "CS2_GPIO2",
  pin9: "CS0_GPIO0",
  pin10: "MOSI",
  pin11: "SPICLK",
  pin12: "VDD",
  pin13: "VSS",
  pin14: "CITO_MISO",
  pin15: "VREFP",
  pin16: "CS1_GPIO1",
} as const

const U2_PIN_LABELS = {
  pin1: "IO0",
  pin2: "IO1",
  pin3: "IO2",
  pin4: "VSS",
  pin5: "IO3",
  pin6: "SCL",
  pin7: "SDA",
  pin8: "VDD",
} as const

const J1_PIN_LABELS = {
  pin1: "AGND",
  pin2: "V3V3",
  pin3: "TEMP_SDA",
  pin4: "TEMP_SCL",
} as const

const J2_PIN_LABELS = {
  pin1: "V3V3",
  pin2: "AGND",
  pin3: "EPD_DIN",
  pin4: "EPD_CLK",
  pin5: "EPD_CS_N",
  pin6: "EPD_DC",
  pin7: "EPD_RESET_N",
  pin8: "EPD_BUSY",
} as const

const mountingHole = (name: "H1" | "H2") => (
  <chip
    name={name}
    manufacturerPartNumber="M2 NPTH"
    footprint={sourceFootprint(footprints[name])}
    kicadFootprintMetadata={kicadFootprint(footprints[name])}
    noSchematicRepresentation
    pcbRotation={placements[name].rotation}
  />
)

const hostConnector = (
  <chip
    name="J1"
    manufacturerPartNumber="S4B-PH-K-S"
    datasheetUrl="https://www.jst-mfg.com/product/index.php?series=199"
    footprint={sourceFootprint(footprints.J1)}
    kicadFootprintMetadata={kicadFootprint(footprints.J1)}
    kicadSymbolMetadata={kicadSymbol("J1")}
    pinLabels={J1_PIN_LABELS}
    pinAttributes={{
      AGND: { requiresGround: true },
      V3V3: { requiresPower: true },
      TEMP_SDA: { mustBeConnected: true, capabilities: ["i2c_sda"] },
      TEMP_SCL: { mustBeConnected: true, capabilities: ["i2c_scl"] },
    }}
    connections={{
      AGND: "net.AGND",
      V3V3: "net.V3V3",
      TEMP_SDA: "net.TEMP_SDA",
      TEMP_SCL: "net.TEMP_SCL",
    }}
    schSheetName="Main"
    schX={-12}
    schY={0}
    pcbX={placements.J1.x}
    pcbY={placements.J1.y}
    pcbRotation={placements.J1.rotation}
  />
)

const displayConnector = (
  <chip
    name="J2"
    manufacturerPartNumber="S8B-PH-K-S"
    datasheetUrl="https://www.jst-mfg.com/product/index.php?series=199"
    footprint={sourceFootprint(footprints.J2)}
    kicadFootprintMetadata={kicadFootprint(footprints.J2)}
    kicadSymbolMetadata={kicadSymbol("J2")}
    pinLabels={J2_PIN_LABELS}
    pinAttributes={{
      V3V3: { requiresPower: true },
      AGND: { requiresGround: true },
      EPD_DIN: { mustBeConnected: true, capabilities: ["spi_mosi"] },
      EPD_CLK: { mustBeConnected: true, capabilities: ["spi_sck"] },
      EPD_CS_N: { mustBeConnected: true, capabilities: ["spi_cs"] },
      EPD_DC: { mustBeConnected: true },
      EPD_RESET_N: { mustBeConnected: true },
      EPD_BUSY: { mustBeConnected: true },
    }}
    connections={{
      V3V3: "net.V3V3",
      AGND: "net.AGND",
      EPD_DIN: "net.EPD_DIN",
      EPD_CLK: "net.EPD_CLK",
      EPD_CS_N: "net.EPD_CS_N",
      EPD_DC: "net.EPD_DC",
      EPD_RESET_N: "net.EPD_RESET_N",
      EPD_BUSY: "net.EPD_BUSY",
    }}
    schSheetName="Main"
    schX={12}
    schY={0}
    pcbX={placements.J2.x}
    pcbY={placements.J2.y}
    pcbRotation={placements.J2.rotation}
  />
)

const spiBridge = (
  <chip
    name="U1"
    manufacturerPartNumber="SC18IS606PWJ"
    datasheetUrl="https://www.nxp.com/products/interfaces/ic-spi-i3c-interface-devices/bridges/ic-bus-to-spi-bridge%3ASC18IS606"
    footprint={sourceFootprint(footprints.U1)}
    kicadFootprintMetadata={kicadFootprint(footprints.U1)}
    kicadSymbolMetadata={kicadSymbol("U1")}
    pinLabels={U1_PIN_LABELS}
    noConnect={["CS2_GPIO2", "CS1_GPIO1"]}
    pinAttributes={{
      SDA: { mustBeConnected: true, capabilities: ["i2c_sda"] },
      SCL: { mustBeConnected: true, capabilities: ["i2c_scl"] },
      INT_N: { mustBeConnected: true, canUseOpenDrain: true },
      RESET_N: { mustBeConnected: true },
      A2: { requiresGround: true },
      A1: { requiresGround: true },
      A0: { requiresGround: true },
      CS2_GPIO2: { doNotConnect: true },
      CS0_GPIO0: { mustBeConnected: true, capabilities: ["spi_cs"] },
      MOSI: { mustBeConnected: true, capabilities: ["spi_mosi"] },
      SPICLK: { mustBeConnected: true, capabilities: ["spi_sck"] },
      VDD: { requiresPower: true, shouldHaveDecouplingCapacitor: true, recommendedDecouplingCapacitorCapacitance: "100nF" },
      VSS: { requiresGround: true },
      CITO_MISO: { mustBeConnected: true, capabilities: ["spi_miso"], needsExternalPulldown: true },
      VREFP: { requiresPower: true },
      CS1_GPIO1: { doNotConnect: true },
    }}
    connections={{
      SDA: "net.TEMP_SDA",
      SCL: "net.TEMP_SCL",
      INT_N: "net.BRIDGE_INT_N",
      RESET_N: "net.BRIDGE_RESET_N",
      A2: "net.AGND",
      A1: "net.AGND",
      A0: "net.AGND",
      CS0_GPIO0: "net.EPD_CS_N",
      MOSI: "net.EPD_DIN",
      SPICLK: "net.EPD_CLK",
      VDD: "net.V3V3",
      VSS: "net.AGND",
      CITO_MISO: "net.CITO_PD",
      VREFP: "net.V3V3",
    }}
    schSheetName="Main"
    schX={-3}
    schY={0}
    pcbRotation={placements.U1.rotation}
  />
)

const gpioExpander = (
  <chip
    name="U2"
    manufacturerPartNumber="PCA9536DR"
    datasheetUrl="https://www.ti.com/product/PCA9536"
    footprint={sourceFootprint(footprints.U2)}
    kicadFootprintMetadata={kicadFootprint(footprints.U2)}
    kicadSymbolMetadata={kicadSymbol("U2")}
    pinLabels={U2_PIN_LABELS}
    pinAttributes={{
      IO0: { mustBeConnected: true, isGpio: true },
      IO1: { mustBeConnected: true, isGpio: true },
      IO2: { mustBeConnected: true, isGpio: true },
      VSS: { requiresGround: true },
      IO3: { mustBeConnected: true, isGpio: true },
      SCL: { mustBeConnected: true, capabilities: ["i2c_scl"] },
      SDA: { mustBeConnected: true, capabilities: ["i2c_sda"] },
      VDD: { requiresPower: true, shouldHaveDecouplingCapacitor: true, recommendedDecouplingCapacitorCapacitance: "100nF" },
    }}
    connections={{
      IO0: "net.EPD_DC",
      IO1: "net.EPD_RESET_N",
      IO2: "net.EPD_BUSY",
      VSS: "net.AGND",
      IO3: "net.BRIDGE_RESET_N",
      SCL: "net.TEMP_SCL",
      SDA: "net.TEMP_SDA",
      VDD: "net.V3V3",
    }}
    schSheetName="Main"
    schX={5}
    schY={0}
    pcbRotation={placements.U2.rotation}
  />
)

export default () => (
  <board
    title={boardSpec.title}
    width={`${boardSpec.widthMm}mm`}
    height={`${boardSpec.heightMm}mm`}
    layers={boardSpec.layerCount}
    material={boardSpec.material}
    thickness={`${boardSpec.thicknessMm}mm`}
    solderMaskColor={boardSpec.solderMaskColor}
    silkscreenColor={boardSpec.silkscreenColor}
    routingDisabled
    manualEdits={manualEdits}
    defaultTraceWidth={`${boardSpec.routing.signalWidthMm}mm`}
    nominalTraceWidth={`${boardSpec.routing.signalWidthMm}mm`}
    minTraceWidth={`${boardSpec.minimums.traceWidthMm}mm`}
    minTraceToPadEdgeClearance={`${boardSpec.minimums.clearanceMm}mm`}
    minPadEdgeToPadEdgeClearance={`${boardSpec.minimums.clearanceMm}mm`}
    minBoardEdgeClearance="0.25mm"
    minViaHoleDiameter={`${boardSpec.minimums.viaDrillMm}mm`}
    minViaPadDiameter={`${boardSpec.minimums.viaPadMm}mm`}
  >
    <schematicsheet name="Main" displayName="PCB-03 display bridge" sheetIndex={0} />
    <net name="V3V3" isPowerNet />
    <net name="AGND" isGroundNet />
    <net name="BRIDGE_INT_N" />
    <net name="BRIDGE_RESET_N" />
    <net name="CITO_PD" />
    <net name="EPD_BUSY" />
    <net name="EPD_CLK" />
    <net name="EPD_CS_N" />
    <net name="EPD_DC" />
    <net name="EPD_DIN" />
    <net name="EPD_RESET_N" />
    <net name="TEMP_SCL" />
    <net name="TEMP_SDA" />

    {hostConnector}
    {displayConnector}
    {spiBridge}
    {gpioExpander}

    <resistor name="R1" resistance="10k" manufacturerPartNumber="PTN0603Y1002BST1" footprint={sourceFootprint(footprints.R1)} kicadFootprintMetadata={kicadFootprint(footprints.R1)} kicadSymbolMetadata={kicadSymbol("R1")} connections={{ pin1: "net.V3V3", pin2: "net.BRIDGE_INT_N" }} schSheetName="Main" schX={-3} schY={-7} pcbRotation={placements.R1.rotation} />
    <resistor name="R2" resistance="10k" manufacturerPartNumber="PTN0603Y1002BST1" footprint={sourceFootprint(footprints.R2)} kicadFootprintMetadata={kicadFootprint(footprints.R2)} kicadSymbolMetadata={kicadSymbol("R2")} connections={{ pin1: "net.V3V3", pin2: "net.BRIDGE_RESET_N" }} schSheetName="Main" schX={1} schY={-7} pcbRotation={placements.R2.rotation} />
    <resistor name="R3" resistance="10k" manufacturerPartNumber="PTN0603Y1002BST1" footprint={sourceFootprint(footprints.R3)} kicadFootprintMetadata={kicadFootprint(footprints.R3)} kicadSymbolMetadata={kicadSymbol("R3")} connections={{ pin1: "net.CITO_PD", pin2: "net.AGND" }} schSheetName="Main" schX={-7} schY={-7} pcbRotation={placements.R3.rotation} />
    <capacitor name="C1" capacitance="100nF" manufacturerPartNumber="C0603C104K5RACTU" footprint={sourceFootprint(footprints.C1)} kicadFootprintMetadata={kicadFootprint(footprints.C1)} kicadSymbolMetadata={kicadSymbol("C1")} connections={{ pin1: "net.V3V3", pin2: "net.AGND" }} schSheetName="Main" schX={-3} schY={7} schOrientation="vertical" pcbRotation={placements.C1.rotation} />
    <capacitor name="C2" capacitance="100nF" manufacturerPartNumber="C0603C104K5RACTU" footprint={sourceFootprint(footprints.C2)} kicadFootprintMetadata={kicadFootprint(footprints.C2)} kicadSymbolMetadata={kicadSymbol("C2")} connections={{ pin1: "net.V3V3", pin2: "net.AGND" }} schSheetName="Main" schX={5} schY={7} schOrientation="vertical" pcbRotation={placements.C2.rotation} />
    <capacitor name="C3" capacitance="4.7uF" manufacturerPartNumber="EMK107ABJ475KA-T" footprint={sourceFootprint(footprints.C3)} kicadFootprintMetadata={kicadFootprint(footprints.C3)} kicadSymbolMetadata={kicadSymbol("C3")} connections={{ pin1: "net.V3V3", pin2: "net.AGND" }} schSheetName="Main" schX={10} schY={7} schOrientation="vertical" pcbRotation={placements.C3.rotation} />

    {mountingHole("H1")}
    {mountingHole("H2")}

    {Object.entries(netMembers).flatMap(([net, members]) =>
      members.map((member) =>
        createElement("netlabel", { key: `${net}-${member}`, net, connection: member } as any),
      ),
    )}

    <silkscreentext text="HOST" pcbX={-15} pcbY={8.6} fontSize="1mm" layer="top" />
    <silkscreentext text="E-PAPER" pcbX={14.2} pcbY={8.6} fontSize="1mm" layer="top" />
    <silkscreentext text="J1: 1 AGND  2 3V3  3 SDA  4 SCL" pcbX={0} pcbY={8.6} fontSize="0.8mm" layer="bottom" />
    <silkscreentext text="J2: 1 3V3 2 AGND 3 DIN 4 CLK 5 CS 6 DC 7 RST 8 BUSY" pcbX={0} pcbY={-8.6} fontSize="0.7mm" layer="bottom" />
  </board>
)
