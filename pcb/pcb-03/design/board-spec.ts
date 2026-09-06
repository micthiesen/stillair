export const boardSpec = {
  designator: "PCB-03",
  title: "Stillair PCB-03 display bridge",
  widthMm: 39.75,
  heightMm: 21,
  layerCount: 2,
  material: "fr4",
  thicknessMm: 1.6,
  copperWeightOz: 1,
  solderMaskColor: "green",
  silkscreenColor: "white",
  surfaceFinish: "lead-free HASL",
  assemblySides: ["top"],
  minimums: {
    clearanceMm: 0.15,
    traceWidthMm: 0.15,
    viaDrillMm: 0.3,
    viaPadMm: 0.6,
  },
  routing: {
    signalWidthMm: 0.25,
    powerTrunkWidthMm: 0.5,
    powerEscapeWidthMm: 0.25,
    viaDrillMm: 0.3,
    viaPadMm: 0.6,
  },
  groundPlane: {
    net: "AGND",
    layer: "bottom",
    clearanceMm: 0.25,
    minimumFillWidthMm: 0.25,
  },
  coordinateFrames: {
    tscircuit: "board center, +Y north",
    releasedKicadNorthwestMm: { x: 50, y: 54.5 },
    releasedKicadCenterMm: { x: 69.875, y: 65 },
  },
} as const

export const netAliases = {
  V3V3: "3V3",
} as const

export const placements = {
  C1: { x: -3.675, y: -2.25, rotation: 0 },
  C2: { x: 4.425, y: -2.25, rotation: 0 },
  C3: { x: 9.325, y: -7.5, rotation: 270 },
  H1: { x: -8.125, y: 7.25, rotation: 0 },
  H2: { x: 4.875, y: -7, rotation: 0 },
  J1: { x: -12.375, y: 3, rotation: 270 },
  J2: { x: 12.375, y: -7, rotation: 90 },
  R1: { x: 1.025, y: 0.525, rotation: 90 },
  R2: { x: 1.025, y: 4.025, rotation: 90 },
  R3: { x: -9.25, y: 2.775, rotation: 90 },
  U1: { x: -4.125, y: 1.625, rotation: 180 },
  U2: { x: 6.05, y: 1.875, rotation: 180 },
} as const

export type Ref = keyof typeof placements

export const footprints = {
  C1: "Capacitor_SMD:C_0603_1608Metric",
  C2: "Capacitor_SMD:C_0603_1608Metric",
  C3: "Capacitor_SMD:C_0603_1608Metric",
  H1: "MountingHole:MountingHole_2.2mm_M2",
  H2: "MountingHole:MountingHole_2.2mm_M2",
  J1: "Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal",
  J2: "Connector_JST:JST_PH_S8B-PH-K_1x08_P2.00mm_Horizontal",
  R1: "Resistor_SMD:R_0603_1608Metric",
  R2: "Resistor_SMD:R_0603_1608Metric",
  R3: "Resistor_SMD:R_0603_1608Metric",
  U1: "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
  U2: "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
} as const satisfies Record<Ref, string>

export const netMembers = {
  V3V3: ["C1.1", "C2.1", "C3.1", "J1.2", "J2.1", "R1.1", "R2.1", "U1.12", "U1.15", "U2.8"],
  AGND: ["C1.2", "C2.2", "C3.2", "J1.1", "J2.2", "R3.2", "U1.5", "U1.6", "U1.7", "U1.13", "U2.4"],
  BRIDGE_INT_N: ["R1.2", "U1.3"],
  BRIDGE_RESET_N: ["R2.2", "U1.4", "U2.5"],
  CITO_PD: ["R3.1", "U1.14"],
  EPD_BUSY: ["J2.8", "U2.3"],
  EPD_CLK: ["J2.4", "U1.11"],
  EPD_CS_N: ["J2.5", "U1.9"],
  EPD_DC: ["J2.6", "U2.1"],
  EPD_DIN: ["J2.3", "U1.10"],
  EPD_RESET_N: ["J2.7", "U2.2"],
  TEMP_SCL: ["J1.4", "U1.2", "U2.6"],
  TEMP_SDA: ["J1.3", "U1.1", "U2.7"],
} as const
