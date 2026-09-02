# Board-extracted netlist (source of truth: pcb-03.kicad_pcb)
# Generated read-only from the board file. Pad numbers are footprint pad
# numbers; map them to pin FUNCTIONS via the part's datasheet.

## Components  (ref | value | footprint | fields)

C1 | 100nF | Capacitor_SMD:C_0603_1608Metric | MPN=C0603C104K5RACTU
C2 | 100nF | Capacitor_SMD:C_0603_1608Metric | MPN=C0603C104K5RACTU
C3 | 4.7uF | Capacitor_SMD:C_0603_1608Metric | MPN=EMK107ABJ475KA-T
H1 | M2 NPTH | MountingHole:MountingHole_2.2mm_M2 |
H2 | M2 NPTH | MountingHole:MountingHole_2.2mm_M2 |
J1 | S4B-PH-K-S HOST | Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal | MPN=S4B-PH-K-S
J2 | S8B-PH-K-S E-PAPER | Connector_JST:JST_PH_S8B-PH-K_1x08_P2.00mm_Horizontal | MPN=S8B-PH-K-S
R1 | 10k | Resistor_SMD:R_0603_1608Metric | MPN=PTN0603Y1002BST1
R2 | 10k | Resistor_SMD:R_0603_1608Metric | MPN=PTN0603Y1002BST1
R3 | 10k | Resistor_SMD:R_0603_1608Metric | MPN=PTN0603Y1002BST1
U1 | SC18IS606PWJ | Package_SO:TSSOP-16_4.4x5mm_P0.65mm | MPN=SC18IS606PWJ
U2 | PCA9536DR | Package_SO:SOIC-8_3.9x4.9mm_P1.27mm | MPN=PCA9536DR

## Nets  (net -> ref.pad list)

/3V3: C1.1, C2.1, C3.1, J1.2, J2.1, R1.1, R2.1, U1.12, U1.15, U2.8
/AGND: C1.2, C2.2, C3.2, J1.1, J2.2, R3.2, U1.5, U1.6, U1.7, U1.13, U2.4
/BRIDGE_INT_N: R1.2, U1.3
/BRIDGE_RESET_N: R2.2, U1.4, U2.5
/CITO_PD: R3.1, U1.14
/EPD_BUSY: J2.8, U2.3
/EPD_CLK: J2.4, U1.11
/EPD_CS_N: J2.5, U1.9
/EPD_DC: J2.6, U2.1
/EPD_DIN: J2.3, U1.10
/EPD_RESET_N: J2.7, U2.2
/TEMP_SCL: J1.4, U1.2, U2.6
/TEMP_SDA: J1.3, U1.1, U2.7
unconnected-(U1-~{SS1}{slash}GPIO1-Pad16): U1.16
unconnected-(U1-~{SS2}{slash}GPIO2-Pad8): U1.8
