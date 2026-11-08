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
for pad,target in [(4,'+3V3'),(6,'GND'),(10,'GND'),(11,'GND')]:
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
if padnames=={str(i) for i in range(1,12)}:
    check(True,'Socket symbol numbers cover footprint pads 1-11')
    check(sum(x[1]=='11' for x in pads)==4,'Socket footprint has four shell pads on GND')
else:
    # KiCad 10 stock library renamed the shell pads (e.g. 'SH'); symbol pin 11 would then not reach them.
    check({str(i) for i in range(1,11)}<=padnames,'Socket footprint has signal/detect pads 1-10')
    WARNINGS.append(f"microSD footprint in {foot.parent.parent} names shell pads {sorted(padnames-{str(i) for i in range(1,11)})}, not '11': symbol pin 11 (shell to GND) will not map. Resolve before layout.")
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
    check(same((f'JP{ch}',1),(f'J{2*ch}',1)) and same((f'JP{ch}',2),(f'R{ch}3',1)) and net(f'JP{ch}',3)=='REF_RAW',f'CH{ch} reference selection')
# Step 8: compensated BIAS feedback and midpoint clamp.
for ref,val in [('RFB1','1M'),('CFB1','10n C0G 5% 50V'),('RZB1','100k 0.1%'),('RB1','499k 0.1%'),('RB2','499k 0.1%')]:
    check(parts[ref].findtext('value')==val,f'{ref} value {val}')
check(same(('U1',63),('RFB1',1),('CFB1',1),('RB1',1)),'BIASOUT drives RFB1, CFB1 and RB1')
check(same(('U1',61),('RFB1',2),('RZB1',2)),'BIASINV joins RFB1 and RZB1')
check(same(('CFB1',2),('RZB1',1)) and len({p for p,n in nodes.items() if n==net('CFB1',2)})==2,'CFB1-RZB1 series node has no other connection')
check(same(('RB1',2),('RB2',1),('D509',1),('D509',2)) and net('D509',3)=='GND','D509 clamps the RB1/RB2 midpoint to GND')
check(same(('RB2',2),('JBIAS1',1)) and len({p for p,n in nodes.items() if n==net('JBIAS1',1)})==2,'BIAS electrode reached only through RB2')
check(net('U1',60)=='GND' and net('U1',62)=='GND','BIASREF and BIASIN tied to AVSS (firmware must set BIASREF_INT=1)')
# Step 9: external ADC clock.
check(same(('U1',52),('R340',1)) and net('R340',2)=='GND','CLKSEL pulled to DGND through R340: external clock selected')
check(same(('Y340',3),('R349',1)) and same(('R349',2),('U1',37),('R341',1)) and net('R341',2)=='GND','Y340 output reaches ADC CLK through R349; R341 default pulldown')
check(net('Y340',4)=='+3V3_ADC' and net('U1',48)=='+3V3_ADC' and net('Y340',2)=='GND','Y340 powered from ADC DVDD rail')
check(same(('Y340',1),('R348',2)) and net('R348',1)=='+3V3_ADC','Y340 OE pulled up (output enabled)')
for ref,val in [('R341','100k'),('R349','33R near Y340')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
# Step 9: isolated trigger. Isolated-side nets must contain only isolated-side pins.
iso={('J600','1'),('J600','2'),('R600','1'),('R600','2'),('D600','1'),('D600','2'),('U600','1'),('U600','3')}
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
for ref,val in [('R611','33k 0.1%'),('C610','15p C0G'),('R615','1M'),('R614','10k')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
for ref,pin in [('U610',5),('U611',5),('U612',3)]:check(net(ref,pin)=='+3V3',f'{ref} supply')
# Step 10: analogue rail trim, restart latch, Schmitt-input gates, faster pull-ups, qualified capacitors.
check(same(('R201',1),('U201',7),('C201',1)) and same(('R201',2),('R207',1)) and net('R207',2)=='GND','RSET = R201 + R207 in series from SET to GND')
check(len({p for p,n in nodes.items() if n==net('R207',1)})==2,'RSET midpoint has no other connection')
for ref,val in [('R201','50.5k 0.1% <=10ppm/K (RSET, + R207)'),('R207','383R 0.1% <=10ppm/K (RSET trim)')]:check(parts[ref].findtext('value')==val,f'{ref} value {val}')
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
for ref,mpn in [('C203','GRM32ER71E226KE15L'),('C204','GRM32ER71E226KE15L'),('C201','GRM21BR71C475KE51L'),('C211','GRM31C5C1H104JA01L'),('C213','GRM31C5C1H104JA01L'),('C215','GRM1885C1H103JA01D'),('C217','GRM1885C1H103JA01D'),('C219','GRM1885C1H103JA01D')]:
    check(parts[ref].findtext('fields/field[@name="MPN"]')==mpn,f'{ref} MPN {mpn}')
check(same(('C203',1),('C204',1),('U201',10),('U201',9)) and net('C203',1)=='+5VA','Output capacitors on +5VA at OUT/OUTS')
# Everything outside the Step 10 changes is unchanged from the Step 9 baseline (pin-membership comparison).
oldroot=ET.parse(P/'baseline'/'step9_netlist.xml');oldnodes={}
for nn in oldroot.findall('.//nets/net'):
    for x in nn.findall('node'):oldnodes[(x.get('ref'),x.get('pin'))]=nn.get('name')
changed={'R201','U221'}
added={'R207','U226','C226','U227','C227','U228','C228','TP230'}
check({r for r,_ in nodes}-{r for r,_ in oldnodes}==added,'Only the Step 10 RSET trim and restart-latch parts added since Step 9')
check({r for r,_ in oldnodes}<={r for r,_ in nodes},'No Step 9 component removed')
retained=set(oldnodes)-{p for p in oldnodes if p[0] in changed}
for pin in retained:
    a={p for p in retained if oldnodes[p]==oldnodes[pin]}
    b={p for p in retained if nodes[p]==nodes[pin]}
    assert a==b,pin
check(True,f'{len(retained)} retained pin connections unchanged since Step 9')
# Report the ERC result actually produced by this run rather than a fixed claim.
erc=(CHECKS/'erc.rpt').read_text() if (CHECKS/'erc.rpt').exists() else ''
m=re.search(r'ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)',erc)
kinds=sorted(set(re.findall(r'^\[(\w+)\]',erc,re.M)))
erc_line=f'KiCad ERC: {m[2]} errors, {m[3]} warnings' + (f" ({', '.join(kinds)})" if kinds else '') + '.' if m else 'KiCad ERC: no report found.'
(CHECKS/'validation.md').write_text('# Rev C validation (C7, Step 10)\n\n'+str(len(checks))+' netlist assertions passed. '+erc_line+' Linear calculations are estimates; no physical testing performed. Visual sheet inspection is a separate manual step.\n\n'+''.join('\n**WARNING:** '+w+'\n' for w in WARNINGS)+'\n'+'\n'.join('- PASS: '+x for x in checks)+'\n')
print(erc_line)
for w in WARNINGS:print('WARNING:',w)
print(len(checks),'assertions passed')
