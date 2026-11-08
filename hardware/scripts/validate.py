from pathlib import Path
import xml.etree.ElementTree as ET
import csv
import sexpdata as sx
"""Netlist assertions for the current revision. Run via hardware/rebuild.sh after the KiCad export."""
import os,re,glob
SCRIPTS=Path(__file__).resolve().parent
exec((SCRIPTS/'validate_controller.py').read_text())  # defines P, CHECKS, nodes, check(), net(), same()
# Existing check helpers and parsed nodes remain in scope.
for pad, target in [(1,'CARD_DAT2'),(2,'CARD_CS_N'),(3,'CARD_DI'),(5,'CARD_CLK'),(7,'CARD_DO'),(8,'CARD_DAT1')]:
    check(net('J420',pad).endswith('/'+target), f'microSD pad {pad} = {target}')
for pad,target in [(4,'+3V3'),(6,'GND'),(10,'GND'),('SH','GND')]:
    check(net('J420',pad)==target,f'microSD supply/shield pad {pad}')
for ref,mpad,cpad in [('R420',52,5),('R421',50,3),('R422',51,2),('R423',48,7)]:
    check(same(('U300',mpad),(ref,1)) and same((ref,2),('J420',cpad)),f'{ref}: correct host-to-card series path')
for ref,pad in [('R424',3),('R425',2),('R426',7),('R427',8),('R428',1)]:
    check(net(ref,1)=='+3V3' and same((ref,2),('J420',pad)),f'{ref}: required CMD/DAT pullup')
check(same(('J420',9),('R430',2),('R431',1)) and same(('R431',2),('U300',47),('C422',1)), 'Card detect contact reaches MCU through RC network')
check(net('R430',1)=='+3V3' and net('C422',2)=='GND','Card detect default absent high')
for ref,p1,p2 in [('D420',5,3),('D421',2,7),('D422',8,1)]:
    check(same((ref,1),('J420',p1)) and same((ref,2),('J420',p2)) and net(ref,3)=='GND',f'{ref}: ESD I/O and ground mapping')
check(same(('D423',1),('J420',9)) and net('D423',2)=='+3V3' and net('D423',3)=='GND','D423 card detect / VDD ESD mapping')
for ref in ['C420','C421']:
    check(net(ref,1)=='+3V3' and net(ref,2)=='GND',f'{ref}: local card bypass')
for i,n in enumerate(['+3V3','GND','BAT_WARN_OK','SYS_OK','PACK_OK','DIGITAL_OK']):
    check(net(f'TP{420+i}',1)==n,f'Test access: {n}')
removed={'R305','R384','R385','R386','R387'}
check(not any(ref in removed for ref,pin in nodes),'Superseded SD placeholder resistors removed')
check({ref for ref,pin in nodes if net(ref,pin)=='SD_POWER_EN'}=={'U300','R383'},'SD_POWER_EN reserved only, no switched card domain')
def footprint_dir():
    # KiCad stock footprints: env override, then macOS app bundle, then Linux package paths.
    for k,v in sorted(os.environ.items()):
        if re.fullmatch(r'KICAD\d*_FOOTPRINT_DIR',k) and Path(v).is_dir():return Path(v)
    for c in ['/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints','/usr/share/kicad/footprints','/usr/local/share/kicad/footprints']:
        if Path(c).is_dir():return Path(c)
    raise SystemExit('KiCad footprint library not found; set KICAD9_FOOTPRINT_DIR')
foot=footprint_dir()/'Connector_Card.pretty/microSD_HC_Hirose_DM3AT-SF-PEJM5.kicad_mod'
def tag(x):return str(x[0]) if isinstance(x,list) and x else ''
f=sx.loads(foot.read_text());pads=[x for x in f if tag(x)=='pad']
WARNINGS=[]
padnames={x[1] for x in pads}
# Step 13: the symbol shell pin is now 'SH', matching the KiCad 10 footprint's four shell pads (was pin 11).
check(padnames=={str(i) for i in range(1,11)}|{'SH'} and sum(x[1]=='SH' for x in pads)==4,'microSD footprint: pads 1-10 plus four SH shell pads, all reached by symbol pin SH on GND')
parts={x.get('ref'):x for x in root.findall('.//components/comp')}
for ref,val in [(f'R{i}','10k 1%') for i in range(424,429)]+[(f'R{i}','33R') for i in range(420,424)]:
    check(parts[ref].findtext('value')==val,f'{ref} value {val}')

# Assert the new physical series paths and protection pinouts, not just labels.
for ch in range(1,9):
    for side,offset,jpad in [('P',0,1),('N',1,2)]:
        r1=f'R{ch}{1 if side=="P" else 3}';r2=f'R{ch}{2 if side=="P" else 4}';r3=f'R{501+2*(ch-1)+offset}';d=f'D{500+ch}'
        check(same((r1,2),(r2,1)),f'{ch}{side}: two 47k series resistors')
        check(same((r2,2),(d,jpad),(r3,1)),f'{ch}{side}: clamp between 94k and 4.7k')
        check(net(r3,2)==f'ADC_IN{ch}{side}',f'{ch}{side}: post-clamp resistor to ADC')
        for ref,value in [(r1,'47k 0.1%'),(r2,'47k 0.1%'),(r3,'4.7k 0.1%')]:
            check(parts[ref].findtext('value')==value,f'{ref} value')
    check(net(f'D{500+ch}',3)=='GND',f'CH{ch} TVS ground')
    check(parts[f'C{ch}'].findtext('value')=='220p C0G 5% 50V',f'CH{ch} capacitor value')
    check({net(f'C{ch}',1),net(f'C{ch}',2)}=={f'ADC_IN{ch}P',f'ADC_IN{ch}N'},f'CH{ch} differential capacitor')
    check(same((f'JP{ch}',1),(f'J{2*ch}',1)) and same((f'JP{ch}',2),(f'R{ch}3',1)) and net(f'JP{ch}',3)=='REF_BUF',f'CH{ch} reference selection (JP pin 3 on buffered REF_BUF)')
# Step 8: compensated BIAS feedback and midpoint clamp.
for ref,val in [('RFB1','1M'),('CFB1','10n C0G 5% 50V'),('RZB1','100k 0.1%'),('RB1','499k 0.1%'),('RB2','499k 0.1%')]:
    check(parts[ref].findtext('value')==val,f'{ref} value {val}')
check(same(('U1',63),('RFB1',1),('CFB1',1),('RB1',1)),'BIASOUT drives RFB1, CFB1 and RB1')
check(same(('U1',61),('RFB1',2),('RZB1',2)),'BIASINV joins RFB1 and RZB1')
check(same(('CFB1',2),('RZB1',1)) and len({p for p,n in nodes.items() if n==net('CFB1',2)})==2,'CFB1-RZB1 series node has no other connection')
check(same(('RB1',2),('RB2',1),('D509',1),('D509',2)) and net('D509',3)=='GND','D509 clamps the RB1/RB2 midpoint to GND')
check({p for p,n in nodes.items() if n==net('JBIAS1',1)}=={('RB2','2'),('JBIAS1','1'),('J500','18')},'BIAS electrode (J500 pin 18) reached only through RB2')
check(net('U1',60)=='GND' and net('U1',62)=='GND','BIASREF and BIASIN tied to AVSS (firmware must set BIASREF_INT=1)')
# Step 9: external ADC clock.
check(same(('U1',52),('R340',1)) and net('R340',2)=='GND','CLKSEL pulled to DGND through R340: external clock selected')
check(same(('Y340',3),('R349',1)) and same(('R349',2),('U1',37),('R341',1)) and net('R341',2)=='GND','Y340 output reaches ADC CLK through R349; R341 default pulldown')
check(net('Y340',4)=='+3V3_ADC' and net('U1',48)=='+3V3_ADC' and net('Y340',2)=='GND','Y340 powered from ADC DVDD rail')
check(same(('Y340',1),('R348',2)) and net('R348',1)=='+3V3_ADC','Y340 OE pulled up (output enabled)')
for ref,val in [('R341','100k'),('R349','33R near Y340')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
# Step 9: isolated trigger. Isolated-side nets must contain only isolated-side pins.
iso={('J600','1'),('J600','2'),('J600','3'),('J600','4'),('R600','1'),('R600','2'),('D600','1'),('D600','2'),('U600','1'),('U600','3')}
for pin in iso:
    members={q for q,n in nodes.items() if n==nodes[pin]}
    assert members<=iso,(pin,members)
check(True,'Trigger isolated side (J600, R600, D600, U600 pins 1/3) has no connection to any other net')
check(same(('J600',1),('R600',1)) and same(('R600',2),('U600',1),('D600',1)) and same(('U600',3),('J600',2),('D600',2)),'Trigger: R600 to LED anode; D600 reverse clamp across LED')
check(net('U600',6)=='+3V3' and net('U600',4)=='GND' and same(('U600',5),('R601',1)) and same(('R601',2),('U300',32)),'TLP2761 output to TRIGGER_ISO (pad 32) through R601')
check(parts['R600'].findtext('value').startswith('620R') and parts['U600'].findtext('value')=='TLP2761(TP,E)','Trigger part values')
# Step 9: photodiode front end.
check(same(('J601',1),('D601',1),('D601',2),('R610',1)) and net('J601',2)=='GND','Photodiode cathode clamped and fed through R610; anode GND')
check(same(('R610',2),('U610',4),('R611',1),('C610',1)) and same(('U610',1),('R611',2),('C610',2),('U300',25)),'TIA feedback 33k || 15p; output to PHOTO_MONITOR (pad 25, AIN2)')
check(same(('U610',3),('R612',2),('R613',1),('C611',1)) and net('R612',1)=='+3V3' and net('R613',2)=='GND','TIA reference divider')
check(same(('U611',3),('R614',2),('R615',2)) and same(('R614',1),('U610',1)) and same(('U611',1),('R615',1),('R616',1)) and same(('R616',2),('U300',33)),'Comparator with hysteresis drives PHOTO_EDGE (pad 33)')
check(same(('U612',1),('R617',1)) and same(('R617',2),('U611',4),('C614',1)),'DAC threshold filtered into comparator IN-')
check(same(('U612',4),('U300',42)) and same(('U612',5),('U300',44)) and net('U612',6)=='GND','DAC on POWER I2C bus, A0 low (address 0x60)')
for ref,val in [('R611','33k 0.1%'),('C610','15p C0G 5% 50V 0402'),('R615','1M'),('R614','10k')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
for ref,pin in [('U610',5),('U611',5),('U612',3)]:check(net(ref,pin)=='+3V3',f'{ref} supply')
# Step 10: analogue rail trim, restart latch, Schmitt-input gates, faster pull-ups, qualified capacitors.
check(same(('R201',1),('U201',7),('C201',1)) and same(('R201',2),('R207',1)) and net('R207',2)=='GND','RSET = R201 + R207 in series from SET to GND')
check(len({p for p,n in nodes.items() if n==net('R207',1)})==2,'RSET midpoint has no other connection')
for ref,val in [('R201','49.9k 0.1% <=10ppm/K (RSET, + R207)'),('R207','1.00k 0.1% <=10ppm/K (RSET trim)')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
check(same(('U227',6),('U226',4)) and net('U226',1)=='POWER_OK' and net('U226',2)=='SERVICE_OK','RUN_PERMIT = POWER_OK . SERVICE_OK drives latch CLR')
check(same(('U220',4),('U222',1),('U226',1)),'POWER_OK (SYS_OK . PACK_OK) shared by ANA_ENABLE gate and latch permit')
check(net('U227',1)=='RUN_REQUEST' and net('U227',2)=='+3V3' and net('U227',7)=='+3V3' and net('U227',8)=='+3V3' and net('U227',4)=='GND','U227 clocked by RUN_REQUEST, D and PRE high')
check(net('U227',3).startswith('unconnected-'),'U227 Q-bar unused')
check(same(('U227',5),('U228',2),('TP230',1)) and net('U228',1)=='RUN_REQUEST','RUN_ARMED and RUN_REQUEST gate RUN_LATCHED')
check(same(('U228',4),('U221',1)) and net('U221',2)=='SERVICE_OK' and same(('U221',4),('U222',2)) and net('U222',4)=='ANA_ENABLE','RUN_LATCHED replaces RUN_REQUEST in the ANA_ENABLE chain')
check(same(('R230',1),('U300',22),('U227',1)),'RUN_REQUEST default pulldown and MCU pad 22 retained')
gates=[f'U{n}' for n in list(range(220,229)) if n!=227]+['U330','U331','U332','U333']
for g in gates:check(parts[g].findtext('value')=='SN74AUP1G08DBVR' and net(g,5)=='+3V3' and net(g,3)=='GND',f'{g}: Schmitt-input SN74AUP1G08 on +3V3')
for ref,n in [('R212','ANALOG_OK'),('R215','DIGITAL_OK'),('R218','SYS_OK'),('R221','PACK_OK'),('R224','BAT_WARN_OK')]:
    check(parts[ref].findtext('value')=='4.7k' and net(ref,1)=='+3V3' and net(ref,2)==n,f'{ref}: 4.7k pull-up on {n}')
check(parts['R354'].findtext('value')=='4.7k' and parts['R358'].findtext('value')=='4.7k','SWD_ABSENT and INTERLOCK_CLOSED defaults 4.7k')
for ref,mpn in [('C203','GRM32ER71E226KE15L'),('C204','GRM32ER71E226KE15L'),('C201','GRM21BR71C475KE51L'),('C211','GRM31C5C1H104JA01L'),('C213','GRM31C5C1H104JA01L'),('C215','GCM1885C1H103JA16D'),('C217','GCM1885C1H103JA16D'),('C219','GCM1885C1H103JA16D')]:
    check(parts[ref].findtext('fields/field[@name="MPN"]')==mpn,f'{ref} MPN {mpn}')
check(same(('C203',1),('C204',1),('U201',10),('U201',9)) and net('C203',1)=='+5VA','Output capacitors on +5VA at OUT/OUTS')
# Step 11: BQ25798 charger, ship FET, pack connector, charge enable and power button.
for pin,n in [(2,'USB_5V'),(3,'USB_5V'),(9,'USB_5V'),(8,'USB_5V'),(11,'GND'),(10,'GND'),(25,'SYS'),(22,'PACK_POS'),(23,'PACK_POS'),(27,'GND'),(14,'POWER_SCL'),(15,'POWER_SDA'),(21,'CHARGER_INT_N')]:
    check(net('U400',pin)==n,f'U400 pin {pin} on {n}')
check(net('U400',6).startswith('unconnected-') and net('U400',7).startswith('unconnected-'),'BQ25798 D+/D- left unconnected (USB data stays with the MCU)')
check(same(('U400',28),('L400',1),('C407',2)) and same(('U400',26),('L400',2),('C408',2)) and same(('U400',4),('C407',1)) and same(('U400',19),('C408',1)),'Inductor between SW1 and SW2; bootstrap capacitors SW1-BTST1 and SW2-BTST2')
check(same(('U400',5),('C409',1),('R402',1),('R404',1),('R406',1),('R407',1)),'REGN decoupled and biases ILIM_HIZ, TS, CE pull-up and charge LED only')
check(same(('U400',20),('R401',1)) and net('R401',2)=='GND' and parts['R401'].findtext('value').startswith('6.04k'),'PROG 6.04k to GND: 2S, 1.5 MHz')
check(same(('U400',17),('R402',2),('R403',1)) and net('R403',2)=='GND','ILIM_HIZ divider from REGN')
check(same(('U400',16),('R404',2),('R405',1),('J401',3)) and net('R405',2)=='GND','TS divider with pack NTC on J401 pin 3')
check(same(('U400',24),('Q400',3)) and net('Q400',4)=='PACK_POS' and all(same(('Q400',k),('J401',1)) for k in (1,2,5,6)),'Ship FET: gate on SDRV, source on BAT (PACK_POS), drain on pack +')
check(same(('U400',18),('R400',2)) and same(('R400',1),('J401',1)) and net('J401',2)=='GND','BATP senses the pack side of the ship FET through 100R')
check(same(('U400',13),('R406',2),('Q401',3)) and net('Q401',1)=='CHARGE_REQUEST' and net('Q401',2)=='GND','CE pulled high from REGN; Q401 enables charging only on CHARGE_REQUEST')
check(same(('R380',1),('Q401',1)) and net('R380',2)=='GND','CHARGE_REQUEST default low keeps charging disabled')
check(same(('U400',1),('D401',1)) and same(('D401',2),('R407',2)),'STAT drives the charge LED cathode')
check(same(('U400',12),('SW400',1),('D402',3)) and net('SW400',2)=='GND','POWER button pulls QON low')
check(same(('D402',1),('R408',2),('U300',37)) and net('R408',1)=='+3V3','BAT54 anode on POWER_BUTTON_N (module pad 37) with 10k pull-up')
check(net('U400',29)!=net('U400',2) and len([c for c in ['C403','C404','C405','C406'] if net(c,1)==net('U400',29)])==4,'PMID has its own 3 x 10 uF + 100 nF')
check(sum(net(f'C{n}',1)=='SYS' for n in range(410,417))==7,'Seven SYS hold-up capacitors on SYS')
check(sorted(r for r,p in nodes if p=='1' and nodes[(r,p)]=='VBUS_CON' and r.startswith('C'))==['C324'],'Connector-side VBUS bulk is C324 alone (USB Type-C sink limit; Step 14 moved the charger bulk behind the OVP soft start)')
check(net('C417',1)=='PACK_POS' and net('C418',1)=='PACK_POS','BAT capacitors on the charger side of the ship FET')
for ref in ['R216','R219','R222']:check(net(ref,1) in ('SYS','PACK_POS'),f'{ref} monitor divider fed from {net(ref,1)}')
check(net('R219',1)=='PACK_POS' and net('R222',1)=='PACK_POS','Pack monitors behind the ship FET: no divider drain in ship mode')
for ref,mpn in [('U400','BQ25798RQMR'),('Q400','CSD17571Q2'),('Q401','BSS138'),('C416','16SVP100M'),('D402','BAT54,215')]:
    check(parts[ref].findtext('fields/field[@name="MPN"]')==mpn,f'{ref} MPN {mpn}')
# Step 12: buffered REF distribution and +5VA backfeed clamp.
def members(ref,pin):return {p for p,n in nodes.items() if n==net(ref,pin)}
check(members('JREF1',1)=={('JREF1','1'),('R517','1'),('J500','17')},'REF electrode (J500 pin 17) reaches only R517 (no direct path to any JP or ADC pin)')
check(same(('R517',2),('R518',1)) and len(members('R517',2))==2,'REF front end: two 47k in series')
check(same(('R518',2),('D510',1),('D510',2),('R519',1)) and net('D510',3)=='GND','D510 clamps the REF node between the 94k and the 4.7k')
check(same(('R519',2),('U500',3)) and len(members('U500',3))==2,'4.7k from the REF clamp node to OPA376 +IN only')
check(net('U500',1)=='REF_BUF' and same(('U500',1),('U500',4)),'U500 wired as a unity follower driving REF_BUF')
check(members('U500',1)=={('U500','1'),('U500','4')}|{(f'JP{ch}','3') for ch in range(1,9)},'REF_BUF reaches only the follower and pin 3 of JP1-JP8')
check(net('U500',5)=='+5VA' and net('U500',2)=='GND','U500 powered from +5VA and AVSS/GND, so it is off whenever the analogue rail is off')
check(net('C500',1)=='+5VA' and net('C500',2)=='GND' and net('C501',1)=='+5VA' and net('C501',2)=='GND','U500 supply decoupling')
for ref,val in [('R517','47k 0.1%'),('R518','47k 0.1%'),('R519','4.7k 0.1%')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
check(same(('R208',2),('Q201',3)) and len(members('Q201',3))==2 and net('R208',1)=='+5VA' and net('Q201',2)=='GND','Q201 drain sinks +5VA through R208 100R; source on GND')
check(same(('Q201',1),('R209',2),('Q202',3)) and len(members('Q201',1))==3 and net('R209',1)=='+5VA','Q201 gate pulled to +5VA by R209 and released only by Q202')
check(net('Q202',1)=='ANA_ENABLE' and net('Q202',2)=='GND','Q202 grounds the clamp gate while ANA_ENABLE is high')
for ref,val in [('R208','100R 1% 0.25W (clamp drain)'),('R209','1M (clamp gate from +5VA)')]:check(parts[ref].findtext('value')==val,f'{ref} value')
for ref,mpn in [('U500','OPA376AIDBVR'),('D510','TPD2E2U06DCKR'),('Q201','CSD17381F4'),('Q202','CSD17381F4')]:
    check(parts[ref].findtext('fields/field[@name="MPN"]')==mpn,f'{ref} MPN {mpn}')
# Step 14 (C11): VBUS overvoltage protection. Connectivity is compared with the Step 13 netlist: the parts and pin
# moves listed here are the only differences; every other pin keeps exactly the same net partners.
old=ET.parse(P/'baseline'/'step13_netlist.xml').getroot();oldnodes={};oldparts={x.get('ref'):x for x in old.findall('.//components/comp')}
for nn in old.findall('.//nets/net'):
    for x in nn.findall('node'):oldnodes[(x.get('ref'),x.get('pin'))]=nn.get('name')
field=lambda r,n:parts[r].findtext(f'fields/field[@name="{n}"]') or ''
added={'U323','U324','C324','C325','C326','C327','C401','D324'}
moved={('J310',k):'VBUS_CON' for k in ('A4','A9','B4','B9')}|{('R360','1'):'VBUS_CON',('R362','1'):'USB_VPWR',('U300','31'):'MCU_VBUS',('C303','1'):'MCU_VBUS'}
check({r for r,_ in nodes}-{r for r,_ in oldnodes}==added,'Added since Step 13: U323 TPD1S514-1, U324 TPS7A2050, D324 BAT54, C324-C327 and C401 only')
check({r for r,_ in oldnodes}<={r for r,_ in nodes},'No parts removed since Step 13')
check(set(oldnodes)=={p for p in nodes if p[0] not in added},'No pins added to or removed from existing parts')
for pin,n in moved.items():
    check(oldnodes[pin]=='USB_5V' and net(*pin)==n,f'Changed: {pin[0]} pin {pin[1]} moved from USB_5V to {n}')
kept=[p for p in oldnodes if p not in moved]
oldgrp={};newgrp={}
for q in kept:oldgrp.setdefault(oldnodes[q],set()).add(q);newgrp.setdefault(nodes[q],set()).add(q)
for q in kept:
    assert oldgrp[oldnodes[q]]==newgrp[nodes[q]],(q,oldgrp[oldnodes[q]]^newgrp[nodes[q]])
check(True,f'Retained: {len(kept)} pin connections keep the same net partners as in Step 13')
check(not [r for r in oldparts if r in parts and oldparts[r].findtext('value')!=parts[r].findtext('value')],'Retained: no value changed on an existing part')
# The overvoltage switch and the nets it creates.
for ball,n in [('B3','VBUS_CON'),('C2','VBUS_CON'),('C3','VBUS_CON'),('A2','USB_5V'),('A3','USB_5V'),('B2','USB_5V'),('B1','USB_VPWR'),('A1','GND'),('A4','GND'),('B4','GND'),('C1','GND'),('C4','GND')]:
    check(net('U323',ball)==n,f'U323 ball {ball} on {n}')
check(members('U323','B3')=={('J310',k) for k in ('A4','A9','B4','B9')}|{('U323',k) for k in ('B3','C2','C3')}|{('C324','1'),('R360','1')},'VBUS_CON reaches only the J310 VBUS contacts, U323, C324 and the TUSB320 detect resistor R360')
check(net('C324',2)=='GND' and parts['C324'].findtext('value').startswith('1u 50V'),'C324 1 uF 50 V on VBUS_CON (connector side may see 30 V)')
check(not any(net('J310',k)=='USB_5V' for k in ('A4','A9','B4','B9')),'No USB-C contact on USB_5V: every USB_5V load sits behind U323')
check(members('U323','B1')=={('U323','B1'),('C325','1'),('R362','1')} and net('C325',2)=='GND','USB_VPWR (U323 VBUS_POWER) carries only its 1 uF and the USB-sense divider')
check(same(('R362',2),('R363',1),('U321',2)) and net('R363',2)=='GND','USB-sense divider from USB_VPWR into U321, so USB_ABSENT also falls while U323 blocks')
check(net('U324',1)=='USB_5V' and net('U324',3)=='USB_5V' and net('U324',2)=='GND' and net('U324',4).startswith('unconnected-'),'U324 IN and EN on USB_5V, NC pin open')
check(members('U324',5)=={('U324','5'),('U300','31'),('C303','1'),('C327','1'),('D324','1')},'MCU_VBUS: U324 OUT to module pad 31 with C303, C327 and the D324 anode only')
check(net('D324',3)=='USB_5V' and net('D324',2).startswith('unconnected-') and field('D324','MPN')=='BAT54,215','D324 BAT54 cathode on USB_5V: LDO reverse-current bypass')
check(net('C326',1)=='USB_5V' and net('C326',2)=='GND' and net('C327',2)=='GND','U324 input and output capacitors to GND')
check(sorted(r for r,p in nodes if p=='1' and nodes[(r,p)]=='USB_5V' and r.startswith('C'))==['C321','C326','C400','C401','C402'],'USB_5V bulk behind the soft start: C400 + C401 (TI 2 x 10 uF), C321, C326, C402')
check(net('C401',2)=='GND' and same(('C401',1),('U400',2)),'C401 on the charger VBUS pin net')
for ref,mpn in [('U323','TPD1S514-1YZR'),('U324','TPS7A2050PDBVR'),('C324','GCM21BR71H105KA03L'),('C401','GRM31CR71E106KA12L')]:
    check(field(ref,'MPN')==mpn,f'{ref} MPN {mpn}')
check(parts['U323'].findtext('footprint')=='EEG:Texas_YZ0012_DSBGA-12_P0.4mm','U323 on project footprint Texas_YZ0012_DSBGA-12_P0.4mm (TI land pattern 4221703/A)')
# Retained from Step 13: BOM fields, footprints, off-board leads and part families.
check(same(('J600',2),('J600',3),('J600',4)),'J600 shell pins 2-4 all on the isolated return TRIG_ISO_RTN')
for ch in range(1,9):
    check(same(('J500',2*ch-1),(f'J{2*ch-1}',1),(f'R{ch}1',1)) and same(('J500',2*ch),(f'J{2*ch}',1),(f'JP{ch}',1)),f'J500 pins {2*ch-1}/{2*ch} carry CH{ch}+ and CH{ch}-')
check(net('J500',19).startswith('unconnected-') and net('J500',20).startswith('unconnected-'),'J500 pins 19-20 unused: no GND or supply on the electrode connector')
props=lambda c:{x.get('name') for x in c.findall('property')}
offboard={r for r,c in parts.items() if 'exclude_from_board' in props(c)}
check(offboard=={f'J{n}' for n in range(1,17)}|{'JREF1','JBIAS1'},'Only the 18 electrode leads are excluded from the board')
fitted={r for r,c in parts.items() if r not in offboard and 'exclude_from_bom' not in props(c)}
check({r for r,c in parts.items() if r not in offboard and r not in fitted}=={'TP230'}|{f'TP{n}' for n in range(420,426)},'Only the seven bare test pads are on the board but not in the BOM')
check(all(parts[r].findtext('footprint') for r in fitted|{'TP230'}),'Every on-board part has a footprint')
check(all(field(r,'MPN') and field(r,'Manufacturer') and field(r,'Description') for r in fitted),f'Every fitted part ({len(fitted)}) has manufacturer, MPN and description')
for ref,val in [('R210','31.6k 0.1% <=10ppm/K'),('R211','9.88k 0.1% <=10ppm/K'),('R219','44.2k 0.1% <=10ppm/K')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
for ref,mpn in [('R201','ERA-3ARB4992V'),('R207','ERA-3ARB102V'),('R210','ERA-3ARB3162V'),('R211','ERA-3ARB9881V'),('R219','ERA-3ARB4422V'),('L400','XFL4020-102MEC'),('L240','XFL4020-222MEC')]:
    check(field(ref,'MPN')==mpn,f'{ref} MPN {mpn}')
for ref in [f'R{ch}{k}' for ch in range(1,9) for k in range(1,5)]+[f'R{n}' for n in range(501,520)]+['RB1','RB2']:
    assert field(ref,'MPN').startswith('ERJ-PB6B'),ref
check(True,'All electrode, REF and BIAS series resistors are ERJ-PB6B (0.1 %, 150 V element voltage, thick film)')
check(all(field(r,'MPN') not in ('GRM21BR71H104KA01L','GRM188R71H104KA93D','GRM21BR71E105KA99L','GRM188R71H473KA61D','GRM1885C1H221JA01D','GRM1885C1H103JA01D') for r in fitted),'No Murata part marked NRND or to be discontinued')
for ref,fp in [('U300','EEG:u-blox_NINA-B306'),('U400','EEG:Texas_RQM0029A_VQFN-HR-29_4x4mm'),('U320','EEG:Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm'),('Q400','EEG:Texas_DQK_SON-6_2x2mm_CSD17571Q2'),('Q201','EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm'),('Q202','EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm')]:
    check(parts[ref].findtext('footprint')==fp,f'{ref} on project footprint {fp.split(":")[1]}')
# Report the ERC result actually produced by this run rather than a fixed claim.
erc=(CHECKS/'erc.rpt').read_text() if (CHECKS/'erc.rpt').exists() else ''
m=re.search(r'ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)',erc)
kinds=sorted(set(re.findall(r'^\[(\w+)\]',erc,re.M)))
erc_line=f'KiCad ERC: {m[2]} errors, {m[3]} warnings' + (f" ({', '.join(kinds)})" if kinds else '') + '.' if m else 'KiCad ERC: no report found.'
(CHECKS/'validation.md').write_text('# Rev C validation (C11, Step 14)\n\n'+str(len(checks))+' netlist assertions passed. '+erc_line+' Linear calculations are estimates; no physical testing performed. Visual sheet inspection is a separate manual step.\n\n'+''.join('\n**WARNING:** '+w+'\n' for w in WARNINGS)+'\n'+'\n'.join('- PASS: '+x for x in checks)+'\n')
print(erc_line)
for w in WARNINGS:print('WARNING:',w)
print(len(checks),'assertions passed')
