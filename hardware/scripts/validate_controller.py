"""Connectivity checks on a fresh KiCad XML export, not a circuit simulation."""
from pathlib import Path
import csv, json, xml.etree.ElementTree as ET
P = Path(__file__).resolve().parents[1]  # hardware/
CHECKS = P/'checks'
root = ET.parse(CHECKS/'netlist.xml')
nodes = {}
for net in root.findall('.//nets/net'):
    for node in net.findall('node'):
        key = (node.get('ref'), node.get('pin'))
        assert key not in nodes, key
        nodes[key] = net.get('name')
checks = []
def check(condition, message):
    assert condition, message
    checks.append(message)
def net(ref, pin): return nodes[(ref, str(pin))]
def same(*pins): return len({net(*pin) for pin in pins}) == 1
expected = json.loads((CHECKS/'expected_module_map.json').read_text())
for pin, target in expected.items():
    actual = net('U300', pin)
    check(actual == target if target else actual.startswith('unconnected-'), f'Module pad {pin}: {target or "NC"}')
rows = list(csv.DictReader(open(P/'controller_pinmap.csv')))
check(len(rows)==35 and len({r['module_pad'] for r in rows})==35 and len({r['nrf_pin'] for r in rows})==35, '35 distinct module GPIO allocations')
for i, (pad, adc) in enumerate([(1,40),(2,34),(4,39),(7,38),(16,35)]):
    ref=f'U{310+i}'; series=f'R{310+3*i}'; pull=f'R{311+3*i}'
    check(same(('U300',pad),(ref,2)), f'{ref} input from correct MCU pad')
    check(same((ref,4),(series,1)) and same((series,2),('U1',adc),(pull,1)), f'{ref} buffered series path to ADC pin {adc}')
    check(net(pull,2)=='GND' and net(ref,1)=='ADC_IO_READY', f'{ref} startup pulldown and enable')
check(same(('U1',43),('R330',1)) and same(('R330',2),('U300',3)), 'ADC DOUT return path')
check(same(('U1',47),('R331',1)) and same(('R331',2),('U300',5)), 'ADC DRDY return path')
check(net('R332',1)=='ADS_RESET_N' and same(('R332',2),('U1',36),('R333',1)), 'ADC reset uses hardware-gated reset through series resistor')
for ref, a, b, out in [('U330','USB_ABSENT','SWD_ABSENT',None),('U331',None,'INTERLOCK_CLOSED','SERVICE_OK'),('U332','ANALOG_OK','DIGITAL_OK','MCU_IO_OK'),('U333','MCU_IO_OK','ANA_ENABLE','ADC_IO_READY')]:
    check((a is None or net(ref,1)==a) and net(ref,2)==b and (out is None or net(ref,4)==out), f'{ref} hardware gate connections')
check(same(('U330',4),('U331',1)), 'Service gates cascaded')
for pad, signal in [('A6','USB_DP'),('B6','USB_DP'),('A7','USB_DM'),('B7','USB_DM'),('A5','CC1'),('B5','CC2')]:
    check(net('J310',pad)==signal, f'USB-C {pad}: {signal}')
check(net('U320',1)=='CC1' and net('U320',2)=='CC2' and net('U320',3)=='GND' and net('U320',5)=='GND', 'CC controller sink mode / I2C address strap')
check(same(('J310','A4'),('R360',1)) and same(('R360',2),('U320',4)), 'VBUS detector through 887k resistor')
for ref, a,b in [('D310','USB_DP','USB_DM'),('D311','CC1','CC2'),('D312','USB_5V','USB_5V')]:
    check([net(ref,i) for i in (1,2,3)]==[a,b,'GND'], f'{ref} DCK ESD pin mapping')
check(len({net('U300',31),net('U300',10),net('U400',25),net('U400',22),net('Q400',1),net('U400',27)})==6, 'VBUS / 3V3 / SYS / PACK_POS / PACK_IN / GND are distinct nets')
check(same(('U300',19),('U211',6),('SW300',1),('R353',2)), 'Supervisor, reset button and SWD reset converge on MCU reset')
check(same(('J300',9),('U330',2)) and net('R354',1)=='+3V3', 'SWD presence input and default pullup')
check(same(('J300',2),('R350',1)) and same(('R350',2),('U300',15)), 'SWDIO access')
check(same(('J300',4),('R351',1)) and same(('R351',2),('U300',11)), 'SWCLK access')
check(not any(ref in {'J100','U2','U5'} for ref,pin in nodes), 'Obsolete host header, regulator and reset stage removed')
check({str(i) for i in range(1,65)} == {pin for ref,pin in nodes if ref=='U1'}, 'All 64 ADC pads represented, including explicit NCs')
import re
_erc=(CHECKS/'erc.rpt').read_text()
_m=re.search(r'ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)',_erc)
# Missing global footprint-library table is a local KiCad setup issue, not a circuit fault.
_env=r"\[footprint_link_issues\]: The current configuration does not include the footprint library"
_other=[l for l in re.findall(r'^\[\w+\]:.*$',_erc,re.M) if not re.match(_env,l)]
check(_m is not None and _m[2]=='0' and not _other, 'KiCad ERC: zero errors; no warnings other than local footprint-library configuration')
report = '# Step 5 validation\n\n' + f'{len(checks)} connectivity assertions passed against the KiCad XML export.\n\n' + '\n'.join('- PASS: '+x for x in checks) + '\n\nThese checks do not verify timing, component models, PCB footprints, firmware, noise or participant safety.\n'
(CHECKS/'validation.md').write_text(report)
print(f'{len(checks)} connectivity assertions passed')
