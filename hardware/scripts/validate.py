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
oldroot=ET.parse(P/'baseline'/'step6_netlist.xml');oldnodes={}
for nn in oldroot.findall('.//nets/net'):
    for x in nn.findall('node'):oldnodes[(x.get('ref'),x.get('pin'))]=nn.get('name')
changed={f'R{ch}{i}' for ch in range(1,9) for i in range(1,5)}|{f'C{i}' for i in range(1,9)}|{f'JP{i}' for i in range(1,9)}|{f'J{i}' for i in range(1,17)}|{'JREF1','JBIAS1','RB1','RB2','RFB1','CFB1'}
# Compare net connectivity by pin membership, robust to anonymous net renaming.
retained=set(oldnodes)-{p for p in oldnodes if p[0] in changed}
for pin in retained:
    a={p for p in retained if oldnodes[p]==oldnodes[pin]}
    b={p for p in retained if nodes[p]==nodes[pin]}
    assert a==b,pin
check(True,f'{len(retained)} retained non-input pin connections preserved')
for ref in ['RB1','RB2','RFB1','CFB1','JBIAS1']:
    for pin in [p for p in oldnodes if p[0]==ref]:
        a={p for p,n in oldnodes.items() if n==oldnodes[pin]}
        b={p for p,n in nodes.items() if n==nodes[pin]}
        assert a==b,pin
check(True,'BIAS network topology preserved')
# Report the ERC result actually produced by this run rather than a fixed claim.
erc=(CHECKS/'erc.rpt').read_text() if (CHECKS/'erc.rpt').exists() else ''
m=re.search(r'ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)',erc)
kinds=sorted(set(re.findall(r'^\[(\w+)\]',erc,re.M)))
erc_line=f'KiCad ERC: {m[2]} errors, {m[3]} warnings' + (f" ({', '.join(kinds)})" if kinds else '') + '.' if m else 'KiCad ERC: no report found.'
(CHECKS/'validation.md').write_text('# Rev C validation\n\n'+str(len(checks))+' netlist assertions passed. '+erc_line+' Linear calculations are estimates; no physical testing performed. Visual sheet inspection is a separate manual step.\n\n'+''.join('\n**WARNING:** '+w+'\n' for w in WARNINGS)+'\n'+'\n'.join('- PASS: '+x for x in checks)+'\n')
print(erc_line)
for w in WARNINGS:print('WARNING:',w)
print(len(checks),'assertions passed')
