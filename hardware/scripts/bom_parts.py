"""Step 13 (Rev C10): exact part selection for every reference. Imported by build.py.

assign(ref, value, footprint) returns the final value, footprint, manufacturer, MPN, description and population
for one schematic reference. Families are kept small for procurement:
  resistors   Panasonic ERJ-3EKF (0603 1 %), ERJ-8ENF (1206 1 %), ERJ-3GEY0R00V (0603 jumper),
              ERA-3ARB / ERA-3AEB (0603 0.1 % thin film, 10 / 25 ppm/K), ERJ-PB6B (0805 0.1 % thick film, 150 V)
  capacitors  Murata GCM (0603/0805/0402 automotive grade, in production) and GRM 1206/1210 25 V X7R
Sources and the checks behind each family are in docs/reviews/step13_bom_footprint_review.md.
"""
import re

STOCK = 'stock'
R0603, R0805, R1206 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Resistor_SMD:R_1206_3216Metric'
C0402, C0603, C0805 = 'Capacitor_SMD:C_0402_1005Metric', 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric'
C1206, C1210 = 'Capacitor_SMD:C_1206_3216Metric', 'Capacitor_SMD:C_1210_3225Metric'
E24 = {10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91}

# Values changed in Step 13 (finding numbers refer to the Step 13 review). Connectivity is unchanged.
VALUE_CHANGES = {
    'R201': '49.9k 0.1% <=10ppm/K (RSET, + R207)',      # F04: 50.5k is E192 only (ERA-3ARB is E24/E96)
    'R207': '1.00k 0.1% <=10ppm/K (RSET trim)',         # F04: RSET = 50.9k, VOUT 5.090 V
    'R210': '31.6k 0.1% <=10ppm/K',                     # F04: 32.0k is E192 only
    'R211': '9.88k 0.1% <=10ppm/K',                     # F04: ratio 4.198 (was 4.200)
    'R219': '44.2k 0.1% <=10ppm/K',                     # F04: 43.9k is in no E series; PACK_OK 6.233 V nominal
    'C240': '10u 25V X7R 1206 (SYS)', 'C202': '10u 25V X7R 1206 (SYS)',   # F06: 0805 16 V at 8.4 V SYS
    'C300': '10u 25V X7R 1206',
    'C241': '22u 25V X7R 1210', 'C420': '22u 25V X7R 1210',              # F06: "effective value TBD" closed by DC-bias data
    'C610': '15p C0G 5% 50V 0402',
}
FOOTPRINT_CHANGES = {'C240': C1206, 'C202': C1206, 'C300': C1206, 'C241': C1210, 'C420': C1210, 'C610': C0402,
                     'CFB1': C0603, 'C422': C0603, 'L240': 'Inductor_SMD:L_Coilcraft_XxL4020',
                     'U201': 'Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm',
                     **{f'U{n}': 'Package_SON:WSON-6_1.5x1.5mm_P0.5mm' for n in range(210, 215)},
                     'U300': 'EEG:u-blox_NINA-B306', 'U320': 'EEG:Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm',
                     'U400': 'EEG:Texas_RQM0029A_VQFN-HR-29_4x4mm', 'Q400': 'EEG:Texas_DQK_SON-6_2x2mm_CSD17571Q2',
                     'Q201': 'EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm', 'Q202': 'EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm',
                     **{f'SW{n}': 'Button_Switch_SMD:SW_SPST_TL3342' for n in (300, 301, 302)},
                     'J301': 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal',
                     'J601': 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal',
                     'J600': 'Connector_Coaxial:BNC_Amphenol_031-6575_Horizontal',
                     'J300': 'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD'}   # F15: CNC Tech 3220-10-0300-00 is SMD
# Generic 100 nF 0805 parts move to 0603: the Murata 0805 50 V part is "to be discontinued" (F07).
SMALL_CAP_TO_0603 = True

# Fixed parts: ref or MPN -> (manufacturer, MPN, description). MPNs already on the schematic keep their value.
MFR = {'ADS1299IPAGR': 'Texas Instruments', 'LT3045IDD#PBF': 'Analog Devices', 'TPS389001DSET': 'Texas Instruments',
       'SN74AUP1G08DBVR': 'Texas Instruments', 'SN74LVC1G126DBVR': 'Texas Instruments', 'SN74LVC1G14DBVR': 'Texas Instruments',
       'SN74LVC1G74DCUR': 'Texas Instruments', 'TPS62162DSGR': 'Texas Instruments', 'NINA-B306-00B': 'u-blox',
       'TUSB320LAIRWBR': 'Texas Instruments', 'BQ25798RQMR': 'Texas Instruments', 'OPA376AIDBVR': 'Texas Instruments',
       'TLV9061IDBVR': 'Texas Instruments', 'TLV7011DCKR': 'Texas Instruments', 'MCP4725A0T-E/CH': 'Microchip',
       'TLP2761(TP,E)': 'Toshiba', 'SIT8008BIF11-33E-2.048000': 'SiTime', 'TPD2E2U06DCKR': 'Texas Instruments',
       'CSD17381F4': 'Texas Instruments', 'CSD17571Q2': 'Texas Instruments', 'BSS138': 'onsemi', 'BAT54,215': 'Nexperia',
       'LTST-C190GKT': 'Lite-On', 'TL3342F160QG': 'E-Switch', '16SVP100M': 'Panasonic', 'DM3AT-SF-PEJM5': 'Hirose',
       'USB4105-GF-A': 'GCT', 'S3B-PH-K-S': 'JST', 'GRM31CR71E106KA12L': 'Murata', 'GRM32ER71E226KE15L': 'Murata',
       'GRM21BR71C475KE51L': 'Murata', 'GRM31C5C1H104JA01L': 'Murata',
       'TPD1S514-1YZR': 'Texas Instruments', 'TPS7A2050PDBVR': 'Texas Instruments'}   # Step 14
DESCR = {'ADS1299IPAGR': 'IC ADC 24-bit 8-ch biopotential AFE TQFP-64', 'LT3045IDD#PBF': 'IC LDO 500 mA ultralow noise DFN-10 3x3',
         'TPS389001DSET': 'IC voltage supervisor adj., open drain, WSON-6 1.5x1.5', 'SN74AUP1G08DBVR': 'IC AND gate 1-ch Schmitt SOT-23-5',
         'SN74LVC1G126DBVR': 'IC buffer 3-state SOT-23-5', 'SN74LVC1G14DBVR': 'IC inverter Schmitt SOT-23-5',
         'SN74LVC1G74DCUR': 'IC D flip-flop VSSOP-8', 'TPS62162DSGR': 'IC buck 3.3 V 1 A WSON-8 2x2', 'NINA-B306-00B': 'Module BLE 5 nRF52840 internal antenna',
         'TUSB320LAIRWBR': 'IC USB-C CC controller X2QFN-12', 'BQ25798RQMR': 'IC buck-boost charger 1-4S VQFN-HR-29',
         'OPA376AIDBVR': 'IC op-amp low noise RRIO SOT-23-5', 'TLV9061IDBVR': 'IC op-amp 10 MHz RRIO SOT-23-5',
         'TLV7011DCKR': 'IC comparator push-pull SC-70-5', 'MCP4725A0T-E/CH': 'IC DAC 12-bit I2C SOT-23-6',
         'TLP2761(TP,E)': 'Optocoupler logic out 5 kVrms SO6L', 'SIT8008BIF11-33E-2.048000': 'Oscillator 2.048 MHz +/-20 ppm 3.3 V 2.5x2.0',
         'TPD2E2U06DCKR': 'ESD array 2-ch 5.5 V SC-70', 'CSD17381F4': 'MOSFET N 30 V 3.1 A FemtoFET 1.0x0.6',
         'CSD17571Q2': 'MOSFET N 30 V 22 A SON 2x2', 'BSS138': 'MOSFET N 50 V 0.2 A SOT-23', 'BAT54,215': 'Diode Schottky 30 V 0.2 A SOT-23',
         'LTST-C190GKT': 'LED green 0603', 'TL3342F160QG': 'Switch tactile SPST 6.2x5.2 mm SMD', '16SVP100M': 'Capacitor polymer OS-CON 100 uF 16 V 6.3x6.0? see review',
         'DM3AT-SF-PEJM5': 'Connector microSD push-pull right-angle', 'USB4105-GF-A': 'Connector USB-C receptacle 16-pin USB 2.0',
         'S3B-PH-K-S': 'Connector JST PH 3-pin right-angle',
         'TPD1S514-1YZR': 'IC USB VBUS overvoltage switch 30 V, OVP 5.95 V, 39 mOhm, WCSP-12',
         'TPS7A2050PDBVR': 'IC LDO 5.0 V 300 mA low noise SOT-23-5'}
DESCR['16SVP100M'] = 'Capacitor aluminium polymer OS-CON 100 uF 16 V'
EXTRA = {  # (manufacturer, MPN, description) for references that had none
    'U201': None, 'L400': ('Coilcraft', 'XFL4020-102MEC', 'Inductor 1.0 uH 20 % Isat 4.5 A 4x4x2.1 mm'),
    'L240': ('Coilcraft', 'XFL4020-222MEC', 'Inductor 2.2 uH 20 % Isat 3.1 A 4x4x2.1 mm'),
    'C116': ('KEMET', 'T491D107K010AT', 'Capacitor tantalum 100 uF 10 V 10 % case D 7343-31'),
    'D600': ('Diodes Inc.', '1N4148WS-7-F', 'Diode switching 75 V 150 mA SOD-323'),
    'J500': ('Wurth Elektronik', '61202021621', 'Connector box header 2x10 2.54 mm vertical THT (electrode harness)'),
    'J300': ('CNC Tech', '3220-10-0300-00', 'Connector header 2x5 1.27 mm shrouded SWD'),
    'J301': ('JST', 'S2B-PH-K-S', 'Connector JST PH 2-pin right-angle'), 'J601': ('JST', 'S2B-PH-K-S', 'Connector JST PH 2-pin right-angle'),
    'J600': ('Amphenol RF', '031-6575', 'Connector BNC jack right-angle PCB (isolated trigger)'),
    **{f'JP{n}': ('Wurth Elektronik', '61300311121', 'Connector header 1x3 2.54 mm vertical THT') for n in range(1, 9)},
    **{f'SW{n}': ('E-Switch', 'TL3342F160QG', 'Switch tactile SPST 6.2x5.2 mm SMD') for n in (300, 301, 302)},
}


def ohms(v):
    m = re.match(r'\s*([0-9.]+)\s*([RkM]?)', v)
    n, s = float(m[1]), m[2]
    return n * {'R': 1, '': 1, 'k': 1e3, 'M': 1e6}[s]


def code4(r):
    """Panasonic 4-character resistance code: 3 significant figures + number of zeros; 'R' marks the decimal below 100."""
    if r < 100:
        return f'{r:.2f}'.rstrip('0').replace('.', 'R').ljust(4, '0') if r < 10 else f'{r:.1f}'.replace('.', 'R')
    e = 0
    while r >= 1000:
        r /= 10; e += 1
    return f'{int(round(r)):03d}{e}'


def code3(r):
    """Panasonic E24 3-character code: 2 significant figures + number of zeros."""
    e = 0
    while r >= 100:
        r /= 10; e += 1
    return f'{int(round(r)):02d}{e}'


def is_e24(r):
    while r >= 100: r /= 10
    while r < 10: r *= 10
    return abs(r - round(r)) < 1e-6 and int(round(r)) in E24


def resistor(ref, value, fp):
    r = ohms(value)
    if r == 0:
        return 'Panasonic', 'ERJ-3GEY0R00V', 'Resistor 0 ohm jumper 0603'
    if fp == R0805:   # electrode, REF, BIAS and BIAS-feedback networks: 0.1 % thick film, 150 V element voltage
        return 'Panasonic', f'ERJ-PB6B{code4(r)}V', f'Resistor {value.split()[0]} 0.1 % 50 ppm/K 0.25 W 150 V 0805 thick film'
    if fp == R1206:
        return 'Panasonic', f'ERJ-8ENF{code4(r)}V', f'Resistor {value.split()[0]} 1 % 100 ppm/K 0.25 W 1206'
    if '0.1%' in value:
        tc, rng = ('R', (1e3, 100e3)) if 1e3 <= r <= 100e3 else ('E', (47, 330e3))
        code = code3(r) if is_e24(r) else code4(r)
        ppm = 10 if tc == 'R' else 25
        return 'Panasonic', f'ERA-3A{tc}B{code}V', f'Resistor {value.split()[0]} 0.1 % {ppm} ppm/K 0.1 W 0603 thin film'
    return 'Panasonic', f'ERJ-3EKF{code4(r)}V', f'Resistor {value.split()[0]} 1 % 100 ppm/K 0.1 W 0603'


def capacitor(ref, value, fp):
    v = value.lower()
    if fp == C0402:
        return 'Murata', 'GCM1555C1H150JA16D', 'Capacitor 15 pF 5 % 50 V C0G 0402'
    if '220p' in v:
        return 'Murata', 'GCM1885C1H221JA16D', 'Capacitor 220 pF 5 % 50 V C0G 0603'
    if v.startswith('10n'):
        return 'Murata', 'GCM1885C1H103JA16D', 'Capacitor 10 nF 5 % 50 V C0G 0603'
    if v.startswith('47n'):
        return 'Murata', 'GCM188R71H473KA55D', 'Capacitor 47 nF 10 % 50 V X7R 0603'
    if v.startswith('100n') and 'c0g' in v:
        return 'Murata', 'GRM31C5C1H104JA01L', 'Capacitor 100 nF 5 % 50 V C0G 1206'
    if v.startswith('100n'):
        return 'Murata', 'GCM188R71H104KA57D', 'Capacitor 100 nF 10 % 50 V X7R 0603'
    if v.startswith('1u') and '50v' in v:   # Step 14: C324 on VBUS_CON, which may see 30 V DC
        return 'Murata', 'GCM21BR71H105KA03L', 'Capacitor 1 uF 10 % 50 V X7R 0805'
    if v.startswith('1u'):
        return 'Murata', 'GCM21BR71E105KA56L', 'Capacitor 1 uF 10 % 25 V X7R 0805'
    if v.startswith('4.7u'):
        return 'Murata', 'GRM21BR71C475KE51L', 'Capacitor 4.7 uF 10 % 16 V X7R 0805'
    if v.startswith('10u'):
        return 'Murata', 'GRM31CR71E106KA12L', 'Capacitor 10 uF 10 % 25 V X7R 1206'
    if v.startswith('22u'):
        return 'Murata', 'GRM32ER71E226KE15L', 'Capacitor 22 uF 10 % 25 V X7R 1210'
    raise KeyError(f'{ref}: no capacitor rule for {value!r}')


def assign(ref, lib, value, fp, mpn):
    """Return dict(value, fp, mfr, mpn, descr, pop) for one reference. pop: FIT, PAD (bare test pad) or OFF-BOARD."""
    value = VALUE_CHANGES.get(ref, value)
    fp = FOOTPRINT_CHANGES.get(ref, fp)
    if lib == 'ELECTRODE':
        return dict(value=value, fp='', mfr='', mpn='', descr='Electrode lead (off board; reaches the PCB through J500)', pop='OFF-BOARD')
    if lib == 'TP':
        return dict(value=value, fp=fp, mfr='', mpn='', descr='Test pad (copper only, no part)', pop='PAD')
    if lib == 'R':
        mfr, mpn, d = resistor(ref, value, fp)
    elif lib == 'C' and ref not in EXTRA:
        if SMALL_CAP_TO_0603 and fp == C0805 and value.lower().startswith('100n'):
            fp = C0603
        try:
            mfr, mpn, d = capacitor(ref, value, fp)
        except KeyError:
            if mpn not in MFR:
                raise
            mfr, d = MFR[mpn], DESCR.get(mpn, '')
    elif EXTRA.get(ref):
        mfr, mpn, d = EXTRA[ref]
    else:
        mpn = mpn or value
        if mpn not in MFR:
            raise KeyError(f'{ref}: no manufacturer for {mpn!r}')
        mfr, d = MFR[mpn], DESCR.get(mpn, '')
    return dict(value=value, fp=fp, mfr=mfr, mpn=mpn, descr=d, pop='FIT')
