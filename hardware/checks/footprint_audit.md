# Footprint audit (Rev C12, Step 14)

377 on-board parts, 42 footprints. No failures.


## Project footprints (hardware/EEG.pretty)

| Footprint | Pads | Courtyard (mm) | Min gap (mm) |
|---|---:|---|---:|
| Texas_DQK_SON-6_2x2mm_CSD17571Q2 | 8 | 2.8 x 2.5 | 0.145 |
| Texas_RQM0029A_VQFN-HR-29_4x4mm | 33 | 4.9 x 4.9 | 0.2 |
| Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm | 12 | 2.5 x 2.5 | 0.2 |
| Texas_YJC0003A_FemtoFET-3_1.0x0.6mm | 6 | 1.5 x 1.1 | 0.1 |
| Texas_YZ0012_DSBGA-12_P0.4mm | 24 | 2.5 x 1.8 | 0.175 |
| u-blox_NINA-B306 | 71 | 10.5 x 15.5 | 0.3 |

## Area

Sum of courtyards: 4855 mm² = 52 % of one side of 110 x 85 mm.

| Ref | Footprint | Courtyard (mm) | mm² |
|---|---|---|---:|
| J600 | Connector_Coaxial:BNC_Amphenol_031-6575_Horizontal | 15.4 x 37.2 | 573 |
| J500 | Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical | 9.9 x 34.06 | 337 |
| J420 | Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5 | 15.7 x 17.7 | 278 |
| U1 | Package_QFP:TQFP-64_10x10mm_P0.5mm | 13.3 x 13.3 | 177 |
| U300 | EEG:u-blox_NINA-B306 | 10.5 x 15.5 | 163 |
| C416 | Capacitor_SMD:CP_Elec_10x7.9 | 13.6 x 10.8 | 147 |
| J310 | Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal | 10.64 x 8.94 | 95 |
| J401 | Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal | 8.9 x 8.6 | 77 |
| J300 | Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD | 8.58 x 7.36 | 63 |
| J301 | Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal | 6.9 x 8.6 | 59 |
| J601 | Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal | 6.9 x 8.6 | 59 |
| SW300 | Button_Switch_SMD:SW_SPST_TL3342 | 8.5 x 6.0 | 51 |

## Tall parts (≥ 5 mm)

| Ref | Height (mm) | Source |
|---|---:|---|
| J600 | 12.5 | Amphenol 031-6575 right-angle BNC body, est. - confirm from drawing |
| JP1 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP2 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP3 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP4 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP5 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP6 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP7 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP8 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP9 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| JP10 | 11.0 | 2.54 mm header 8.5 mm pins + shunt, est. |
| J500 | 8.9 | Wurth WR-BHD 2.54 mm box header, est. - confirm from drawing |
| C416 | 8.0 | OS-CON on CP_Elec_10x7.9 footprint (7.9 mm can), footprint name |
| J301 | 6.0 | JST PH right-angle (S2B-PH-K-S), est. |
| J601 | 6.0 | JST PH right-angle (S2B-PH-K-S), est. |
| J401 | 6.0 | JST PH right-angle (S3B-PH-K-S), est. |
| J300 | 5.0 | 1.27 mm shrouded header, est. |

## Needs a physical or 3D check

- `EEG:u-blox_NINA-B306`: Drawn from Table 28 positions; compare with a module sample or the u-blox EVK Gerbers before release; antenna cut-out per SIM Figure 14.
- `EEG:Texas_RQM0029A_VQFN-HR-29_4x4mm`: L-shaped corner lands drawn as two overlapping rectangles; check paste and 0.2 mm lands with the assembler.
- `EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm`: Solder-mask-defined lands; confirm the fabricator can hold 0.05 mm mask overlap.
- `EEG:Texas_DQK_SON-6_2x2mm_CSD17571Q2`: Exposed drain and source pads renumbered to 1 and 4; verify against a part.
- `EEG:Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm`: 0.2 mm lands at 0.4 mm pitch; confirm assembler capability.
- `Connector_Coaxial:BNC_Amphenol_031-6575_Horizontal`: Isolated trigger: body and mounting pegs carry TRIG_ISO_RTN; keep 8 mm to all other copper; confirm part drawing.
- `Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical`: Stock box-header footprint; confirm Wurth 61202021621 pin 1 and key orientation.
- `Capacitor_SMD:CP_Elec_10x7.9`: Footprint chosen in Step 11 for 16SVP100M; confirm can diameter against the Panasonic drawing.
- `Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm`: LT3045 DD package: Analog Devices data sheet could not be re-downloaded; pin map from the Step 4 reading.
