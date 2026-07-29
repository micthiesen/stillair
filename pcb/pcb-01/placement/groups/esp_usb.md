# Group: esp_usb

Region (absolute board mm, Y down): x 96..111, y 52..79

## Intent

Support for U2 ESP32-C6 module (pinned; its west pad column is at x=114.1, y57-69 - your region's east boundary faces it) and J6 USB-C (pinned at top edge (104,53)) and J7 TC2030 (pinned obstacle at (107.5,78.5)). C17 (22uF) + C18 (100nF) 3V3 decoupling at the region's east edge near the module's 3V3 pad (pad 5 'IO13'... the 3V3 pin is pad 3 at (116.6,68.9)-ish - closest approach is your SE corner). USB chain northward: J6 -> R20/R21 (22R series) -> U12 TPD2EUSB30 ESD -> module: keep R20/R21/U12 between J6 and the module, short. R55/R56 (5.1k CC pulldowns) + R57/R58 (VBUS divider) + TP25 (VBUS_SENSE) tight to J6. SW1 (EN/reset) + R11/C19 EN network together; SW2 (BOOT) + R12; R13 (GPIO8 pullup); buttons pressable, not under the module. R16/R17 (I2C 0R links), R14/R15 (100R SPEED/DIR series) at the region's SW corner heading toward the MCF. R18 (MCU_CLEAR_N pullup), R19+C20 (NTC divider). TP13=WD_HEARTBEAT, TP14=WDO, TP26=AGND probe.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| C17 | 4.60 x 3.20 | 0 | 1:3V3@(-1.5,+0.0); 2:AGND@(+1.5,+0.0) |
| C18 | 2.02 x 1.12 | 0 | 1:3V3@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| C19 | 2.02 x 1.12 | 0 | 1:ESP_EN@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| C20 | 2.02 x 1.12 | 0 | 1:TEMP_SENSE@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R11 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:ESP_EN@(+0.5,+0.0) |
| R12 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:ESP_BOOT@(+0.5,+0.0) |
| R13 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:/SCH-04 ESP32-C6 Supervisor/ESP_GPIO8@(+0.5,+0.0) |
| R14 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_SPEED@(-0.5,+0.0); 2:SPEED@(+0.5,+0.0) |
| R15 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_DIR@(-0.5,+0.0); 2:DIR@(+0.5,+0.0) |
| R16 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_SDA@(-0.5,+0.0); 2:SDA@(+0.5,+0.0) |
| R17 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_SCL@(-0.5,+0.0); 2:SCL@(+0.5,+0.0) |
| R18 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:MCU_CLEAR_N@(+0.5,+0.0) |
| R19 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:TEMP_SENSE@(+0.5,+0.0) |
| R20 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_USB_DM@(-0.5,+0.0); 2:USB_DM@(+0.5,+0.0) |
| R21 | 2.06 x 1.14 | 0 | 1:/SCH-04 ESP32-C6 Supervisor/ESP_USB_DP@(-0.5,+0.0); 2:USB_DP@(+0.5,+0.0) |
| R55 | 2.06 x 1.14 | 0 | 1:/SCH-07 Connectors/CC1@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R56 | 2.06 x 1.14 | 0 | 1:/SCH-07 Connectors/CC2@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R57 | 2.06 x 1.14 | 0 | 1:/SCH-07 Connectors/VBUS@(-0.5,+0.0); 2:/SCH-07 Connectors/VBUS_SENSE@(+0.5,+0.0) |
| R58 | 2.06 x 1.14 | 0 | 1:/SCH-07 Connectors/VBUS_SENSE@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| U12 | 2.50 x 2.00 | 0 | 1:USB_DP@(-0.7,-0.5); 2:USB_DM@(-0.7,+0.0); 3:AGND@(-0.7,+0.5); 4:-@(+0.7,+0.5); 5:-@(+0.7,+0.0); 6:-@(+0.7,-0.5) |
| SW1 | 10.20 x 6.90 | 0 | 1:ESP_EN@(-4.0,-2.2); 1:ESP_EN@(+4.0,-2.2); 2:AGND@(-4.0,+2.2); 2:AGND@(+4.0,+2.2) |
| SW2 | 10.20 x 6.90 | 0 | 1:ESP_BOOT@(-4.0,-2.2); 1:ESP_BOOT@(+4.0,-2.2); 2:AGND@(-4.0,+2.2); 2:AGND@(+4.0,+2.2) |
| TP13 | 2.00 x 2.00 | 0 | 1:WD_HEARTBEAT@(+0.0,+0.0) |
| TP14 | 2.00 x 2.00 | 0 | 1:WDO@(+0.0,+0.0) |
| TP25 | 2.00 x 2.00 | 0 | 1:/SCH-07 Connectors/VBUS_SENSE@(+0.0,+0.0) |
| TP26 | 2.00 x 2.00 | 0 | 1:AGND@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J5 | (94.0,49.9)-(102.0,55.1) |
| J6 | (98.9,50.8)-(109.1,57.5) |
| J7 | (104.5,76.5)-(111.5,80.5) |
| U2 | (111.1,61.1)-(128.3,74.9) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
