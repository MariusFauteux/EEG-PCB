"""Generate the Rev C KiCad schematic, BOM and pin map. Run via hardware/rebuild.sh."""
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parent
exec((SCRIPTS/'schematic_helpers.py').read_text())
# P = KiCad project directory (hardware/); outputs land there, check data in hardware/checks/.
P=SCRIPTS.parent; CHECKS=P/'checks'; CHECKS.mkdir(exist_ok=True); PROJ='EEG_RevC'; REV='C12 - STEP14'; ROOT=UD('root'); SHEETS={};BOM={};import csv,re
# Import proven baseline sheets, update identities, preserve circuit topology. Files are written after the
# Step 10 patches below, which need the helper pin maps defined further down.
imported=[];DOCS={}
# Step 10 (C7): value/MPN/footprint changes on imported power parts. (value, footprint or None, MPN or None)
STEP10_PARTS={'C201':('4.7u 16V X7R 0805 (CSET)','Capacitor_SMD:C_0805_2012Metric','GRM21BR71C475KE51L'),
 'C203':('22u 25V X7R 1210','Capacitor_SMD:C_1210_3225Metric','GRM32ER71E226KE15L'),'C204':('22u 25V X7R 1210','Capacitor_SMD:C_1210_3225Metric','GRM32ER71E226KE15L'),
 'C211':('100n C0G 5% 50V delay','Capacitor_SMD:C_1206_3216Metric','GRM31C5C1H104JA01L'),'C213':('100n C0G 5% 50V delay','Capacitor_SMD:C_1206_3216Metric','GRM31C5C1H104JA01L'),
 **{f'C{n}':('10n C0G 5% 50V delay','Capacitor_SMD:C_0603_1608Metric','GRM1885C1H103JA01D') for n in (215,217,219)},
 **{f'R{n}':('4.7k',None,None) for n in (212,215,218,221,224)},
 **{f'U{n}':('SN74AUP1G08DBVR',None,'SN74AUP1G08DBVR') for n in range(220,226)}}
def setprop(ob,name,value):
 for z in ob:
  if key(z)=='property' and z[1]==name:z[2]=value;return
for fn in ['ads1299_core','analog','supervision','reset_logic']:
 doc=sx.load(open(P/'baseline'/f'{fn}.kicad_sch'));sid=sub(doc,'uuid')[1]
 sub(doc,'title_block').append(E('comment',1,'C4 INTEGRATION DRAFT - BENCH ONLY'))
 for lib in sub(doc,'lib_symbols')[1:]:LIB[lib[1].split(':')[-1]]=copy.deepcopy(lib)
 for ob in doc:
  if key(ob)=='symbol':
   ref=next(z[2] for z in ob if key(z)=='property' and z[1]=='Reference');un=sub(ob,'unit')[1]
   sub(ob,'instances')[:]=E('instances',E('project',PROJ,E('path',f'/{ROOT}/{sid}',E('reference',ref),E('unit',un))))
   if ref in STEP10_PARTS:
    v,f,mp=STEP10_PARTS[ref];setprop(ob,'Value',v)
    if f:setprop(ob,'Footprint',f)
    if mp:setprop(ob,'MPN',mp)
   if ref=='R201':setprop(ob,'Value','50.5k 0.1% <=10ppm/K (RSET, + R207)')
   props={z[1]:z[2] for z in ob if key(z)=='property'};BOM[ref]=(props.get('Value',''),props.get('Footprint',''),props.get('MPN',''),'FIT')
  if key(ob) in ['global_label','label']:
   globalnets.add(ob[1])
   if fn=='ads1299_core' and ob[1]=='ADS_RESET_N':ob[1]='ADC_RESET_AT_PIN';globalnets.add(ob[1])
  if key(ob)=='text' and str(ob[1]).startswith('5.050 V nominal'):ob[1]='5.090 V nominal (R201+R207). C203+C204 1210 25V X7R: confirm >=10u total effective at 5.25V/85C from DC-bias curve.'
 DOCS[fn]=doc;imported.append((fn,fn.replace('_',' '),sid))
# Local labels POWER_OK etc. were sheet-local in the baseline; Step 10 needs POWER_OK on the restart-latch sheet.
# New symbol definitions use manufacturer package pin numbers.
chip('TUSB320LAI',[([(12,'VDD','power_in'),(1,'CC1','bidirectional'),(2,'CC2','bidirectional'),(4,'VBUS_DET','input'),(3,'PORT','input'),(5,'ADDR','input')],[(7,'SDA','bidirectional'),(8,'SCL','input'),(6,'INT_N','open_collector'),(9,'ID','open_collector'),(11,'EN_N','input'),(10,'GND','power_in')])])
chip('ESD2',[([(1,'IO1','passive'),(2,'IO2','passive')],[(3,'GND','passive')])])
chip('INV',[([(2,'A','input'),(5,'VCC','power_in')],[(4,'Y','output'),(3,'GND','power_in'),(1,'NC','no_connect')])])
chip('BUF',[([(1,'OE','input'),(2,'A','input'),(5,'VCC','power_in')],[(4,'Y','tri_state'),(3,'GND','power_in')])])
# imported AND library needs helper pin coordinates too
chip('AND',[([(1,'A','input'),(2,'B','input'),(5,'VCC','power_in')],[(4,'Y','output'),(3,'GND','power_in')])])
connector('J10',10);connector('J3',3);connector('J1',1)
usb_pins=[('A1','GND'),('A4','VBUS'),('A5','CC1'),('A6','D+'),('A7','D-'),('A8','SBU1'),('A9','VBUS'),('A12','GND'),('B1','GND'),('B4','VBUS'),('B5','CC2'),('B6','D+'),('B7','D-'),('B8','SBU2'),('B9','VBUS'),('B12','GND'),('SH','SHIELD')]  # Step 13: KiCad 10 GCT footprint names the shell pads SH
chip('USBC',[([(a,b,'passive') for a,b in usb_pins[:9]],[(a,b,'passive') for a,b in usb_pins[9:]])])
rows=list(csv.DictReader(open(P/'baseline'/'pinmap_baseline.csv')))
rename={'ADS_SCLK':'MCU_SCLK','ADS_MOSI':'MCU_MOSI','ADS_MISO':'HOST_MISO','ADS_CS_N':'MCU_CS_N','ADS_DRDY_N':'HOST_DRDY_N','ADS_START':'MCU_START','ADS_RESET_REQUEST':'ADC_RESET_REQUEST','ADS_PWDN_N':'MCU_PWDN_N','ANALOG_PG':'ANALOG_OK','PG_3V3':'DIGITAL_OK','BAT_WARN':'BAT_WARN_OK','SERVICE_INTERLOCK':'INTERLOCK_CLOSED','POWER_HOLD':'POWER_BUTTON_N'}
for row in rows:row['net']=rename.get(row['net'],row['net'])
extra=[{'module_pad':'38','nrf_pin':'P1.10','net':'SYS_OK','purpose':'slow monitor input'},{'module_pad':'39','nrf_pin':'P1.11','net':'PACK_OK','purpose':'slow monitor input'}];rows+=extra
pin_names={str(i):f'PAD{i}' for i in range(1,56)};pin_names.update({r['module_pad']:r['nrf_pin'] for r in rows})
fixed={6:'GND',9:'+3V3',10:'+3V3',11:'SWCLK_MCU',12:'GND',13:None,14:'GND',15:'SWDIO_MCU',19:'DIGITAL_OK',26:'GND',28:None,29:None,30:'GND',31:'MCU_VBUS',53:'GND',54:'USB_DP',55:'USB_DM',8:'SWO_MCU',40:None,41:None,'EGP':'GND','EAGP':'GND'}
mapm={int(r['module_pad']):r['net'] for r in rows};mapm.update(fixed)
names={9:'VCC_IO',10:'VCC',11:'SWDCLK',15:'SWDIO',19:'RESET_N',31:'VBUS',54:'USB_DP',55:'USB_DM',13:'ANT_NC'}
groups=[]
for indices in [list(range(1,20)),list(range(20,40)),list(range(40,56))+['EGP','EAGP']]:
 pp=[]
 for k in indices:
  tp='power_in' if mapm[k] in ['GND','+3V3','USB_5V','MCU_VBUS'] else 'bidirectional'
  pp.append((k,names.get(k,pin_names.get(str(k),str(k))),tp))
 groups.append((pp[:(len(pp)+1)//2],pp[(len(pp)+1)//2:]))
chip('NINA_B306',groups)
newnets=list(mapm.values())+[x for _,x in usb_pins]+['USB_5V','CC1','CC2','SWD_ABSENT','USB_ABSENT','SERVICE_OK','INTERLOCK_CLOSED','ADC_IO_READY','MCU_IO_OK','GND','+3V3','SYS','PACK_POS','ADC_RESET_AT_PIN']
globalnets.update(n for n in newnets if n)
for n in ['HOST_SCLK','HOST_MOSI','HOST_CS_N','HOST_START','HOST_PWDN_N','HOST_MISO','HOST_DRDY_N']:globalnets.add(n)
m=Sheet('controller','NINA-B306 controller and reserved interfaces')
m.txt('C4 CONTROLLER / ALL GPIO NUMBERS VERIFIED AGAINST NINA-B3 R15 TABLE 7',10,12,1.5)
for un,x in enumerate([53,157,260],1):
 m.symbol('NINA_B306','U300','NINA-B306-00B',x,76,un,mpn='NINA-B306-00B')
 m.connect('U300',un,{k:mapm[k] for k in [list(range(1,20)),list(range(20,40)),list(range(40,56))+['EGP','EAGP']][un-1]})
m.cap('C300','10u 10V X7R',35,137,'+3V3');m.cap('C301','100n',90,137,'+3V3');m.cap('C302','100n',145,137,'+3V3');m.cap('C303','100n 10V',200,137,'MCU_VBUS')  # Step 14: module VBUS from U324 5.0 V LDO
m.r('R300','4.7k',60,167,'+3V3','POWER_SDA');m.r('R301','4.7k',155,167,'+3V3','POWER_SCL')
for i,(net,source) in enumerate([('TRIGGER_ISO','GND'),('PHOTO_EDGE','GND'),('CHARGER_INT_N','+3V3'),('SD_DETECT_N','+3V3'),('PHOTO_MONITOR','GND'),('PACK_MONITOR','GND')]):
 if i==3: continue
 m.r('R'+str(302+i),'100k provisional',45+(i%3)*95,178+(i//3)*17,net,source)
m.txt('SD on storage sheet; trigger and photodiode on event-inputs sheet (Step 9). Charger on the charger sheet.',10,24)
for row in rows:
 if row['net'] in ('TRIGGER_ISO','PHOTO_EDGE','HOST_DRDY_N'):row['purpose']='GPIOTE IN -> PPI -> TIMER3 capture (16 MHz, HFXO running)'
 if row['net']=='PHOTO_MONITOR':row['purpose']='TIA output; SAADC AIN2 for photodiode threshold calibration'
 if row['net']=='SD_POWER_EN':row['purpose']='Reserved only; SD always on with 3V3 in C4'
 if row['net']=='SD_SCLK':row['purpose']='SPIM3; 250 kHz init, <=8 MHz initial transfer target'
 if row['net']=='POWER_BUTTON_N':row['purpose']='input; 10k pull-up, low while POWER held (BAT54 from QON)'
 if row['net']=='CHARGE_REQUEST':row['purpose']='output; high enables charging (Q401 pulls BQ25798 CE low)'
 if row['net']=='CHARGER_INT_N':row['purpose']='input; BQ25798 INT 256 us active-low pulses'
m.txt('EGP/EAGP symbolic ground groups require matching custom footprint. Do not reuse NINA-B111 footprint.',10,32)
# ADC interface, replace old J100 and U5; buffers inhibit driven GPIOs until analog valid.
a=Sheet('adc_interface','ADC startup gating and SPI connections')
a.txt('C4 ADC INTERFACE - all MCU-driven controls forced LOW until ADC_IO_READY',10,12,1.4)
for i,(raw,host,adc) in enumerate([('MCU_SCLK','HOST_SCLK','ADS_SCLK'),('MCU_MOSI','HOST_MOSI','ADS_DIN'),('MCU_CS_N','HOST_CS_N','ADS_CS_N'),('MCU_START','HOST_START','ADS_START'),('MCU_PWDN_N','HOST_PWDN_N','ADS_PWDN_N')]):
 x=45+(i%3)*100;y=48+(i//3)*85
 a.symbol('BUF','U'+str(310+i),'SN74LVC1G126DBVR',x,y,fp='Package_TO_SOT_SMD:SOT-23-5',mpn='SN74LVC1G126DBVR');a.connect('U'+str(310+i),1,{1:'ADC_IO_READY',2:raw,5:'+3V3',4:host,3:'GND'})
 a.r('R'+str(310+i*3),'33R',x,y+24,host,adc);a.r('R'+str(311+i*3),'10k',x,y+38,adc,'GND');a.r('R'+str(312+i*3),'100k',x+37,y+38,raw,'GND');a.cap('C'+str(310+i),'100n',x+37,y+10,'+3V3')
a.r('R330','33R near ADC',245,147,'ADS_DOUT','HOST_MISO');a.r('R331','100R near ADC',245,162,'ADS_DRDY_N','HOST_DRDY_N');a.r('R332','33R',245,177,'ADS_RESET_N','ADC_RESET_AT_PIN');a.r('R333','100k',245,190,'ADC_RESET_AT_PIN','GND')
# Step 9: external 2.048 MHz +/-20 ppm clock. CLKSEL low selects CLK input (SBAS499C Table 6); R341 keeps CLK defined if Y340 is unfitted.
for i,(adc,n,v) in enumerate([('ADS_CLKSEL','GND','10k'),('ADS_CLK','GND','100k'),('ADS_DAISY','GND','10k'),('ADS_GPIO1','GND','10k'),('ADS_GPIO2','GND','10k'),('ADS_GPIO3','GND','10k'),('ADS_GPIO4','GND','10k')]):a.r('R'+str(340+i),v,35+(i%4)*55,190+(i//4)*18,adc,n)
chip('OSC4',[([(1,'OE','input'),(4,'VDD','power_in')],[(3,'OUT','output'),(2,'GND','power_in')])])
a.symbol('OSC4','Y340','SiT8008BIF11-33E-2.048000 (2.048 MHz +/-20 ppm)',300,60,fp='Oscillator:Oscillator_SMD_SiT_PQFN-4Pin_2.5x2.0mm',mpn='SIT8008BIF11-33E-2.048000')
a.connect('Y340',1,{1:'ADC_OSC_OE',4:'+3V3_ADC',3:'ADC_OSC_OUT',2:'GND'})
a.r('R348','10k',300,85,'+3V3_ADC','ADC_OSC_OE');a.r('R349','33R near Y340',300,100,'ADC_OSC_OUT','ADS_CLK');a.cap('C340','100n 10V X7R',330,85,'+3V3_ADC')
a.txt('Y340 shares +3V3_ADC (ADC DVDD) so the clock cannot drive an unpowered CLK pin. Route CLK short, away from inputs.',200,120,1.0)
# helper gate builder
fp='Package_TO_SOT_SMD:SOT-23-5'
def gate(sh,ref,x,y,aa,bb,out):
 # Step 10: Schmitt-input AUP gate (dt/dv <= 200 ns/V); several inputs are pulled-up open-drain or switch nodes.
 sh.symbol('AND',ref,'SN74AUP1G08DBVR',x,y,fp=fp,mpn='SN74AUP1G08DBVR');sh.connect(ref,1,{1:aa,2:bb,5:'+3V3',4:out,3:'GND'});sh.cap('C'+ref[1:],'100n',x,y+16,'+3V3')
s=Sheet('debug_service','SWD / buttons / hardware service inhibit')
s.txt('SWD PROGRAMMING AND USB SERVICE: DISCONNECT ALL ELECTRODES',10,12,1.5)
s.symbol('J10','J300','Cortex SWD 2x5 1.27mm',30,55,fp='Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical');s.connect('J300',1,{1:'+3V3',2:'SWDIO_HDR',3:'GND',4:'SWCLK_HDR',5:'GND',6:'SWO_HDR',7:None,8:None,9:'SWD_ABSENT',10:'RESET_HDR'})
for i,(aa,bb) in enumerate([('SWDIO_HDR','SWDIO_MCU'),('SWCLK_HDR','SWCLK_MCU'),('SWO_MCU','SWO_HDR'),('RESET_HDR','DIGITAL_OK')]):s.r('R'+str(350+i),'100R',105,34+i*16,aa,bb)
s.r('R354','4.7k',45,89,'+3V3','SWD_ABSENT')
for i,(net,label) in enumerate([('DIGITAL_OK','RESET'),('RECOVERY_BUTTON','RECOVERY'),('RECORD_BUTTON','RECORD')]):
 x=190+i*48;s.symbol('SW','SW'+str(300+i),label,x,45);s.connect('SW'+str(300+i),1,{1:net,2:'GND'})
 if i:s.r('R'+str(355+i),'10k',x,70,'+3V3',net)
s.symbol('J2','J301','INTERLOCK: closed only in recording position',46,127);s.connect('J301',1,{1:'+3V3',2:'INTERLOCK_CLOSED'});s.r('R358','4.7k',110,127,'INTERLOCK_CLOSED','GND')
s.txt('J300 pin 9 pulled low by compatible debug adapter. Verify cable; not universal probe-presence detection.',10,100)
gate(s,'U330',55,170,'USB_ABSENT','SWD_ABSENT','NO_SERVICE_CABLE');gate(s,'U331',155,170,'NO_SERVICE_CABLE','INTERLOCK_CLOSED','SERVICE_OK');gate(s,'U332',255,170,'ANALOG_OK','DIGITAL_OK','MCU_IO_OK');gate(s,'U333',255,115,'MCU_IO_OK','ANA_ENABLE','ADC_IO_READY')
s.txt('Mechanical interlock still required: an unpowered USB cable can connect grounds without VBUS detection.',10,24)
s.txt('SWD has NO target-power input. 3V3 is voltage reference only. No USB bootloader assumed preinstalled.',10,218)

# Step 10 (C7): persistent restart latch. A SYS, pack or service fault clears RUN_ARMED asynchronously; analogue power
# returns only after firmware drives a new rising edge on RUN_REQUEST while RUN_PERMIT is high.
def retarget(doc,ref,pin,newnet):
 """Move one pin of an imported symbol to newnet by relabelling the end of its stub wire."""
 sym=next(ob for ob in doc if key(ob)=='symbol' and any(key(z)=='property' and z[1]=='Reference' and z[2]==ref for z in ob))
 at=sub(sym,'at');name=sub(sym,'lib_id')[1].split(':')[-1];pn=PINMAP[(name,sub(sym,'unit')[1])][str(pin)]
 px,py=round(at[1]+mm(pn[3]),2),round(at[2]-mm(pn[4]),2)
 w=next(ob for ob in doc if key(ob)=='wire' and [round(v,2) for v in sub(ob,'pts')[1][1:3]]==[px,py])
 end=[round(v,2) for v in sub(w,'pts')[2][1:3]]
 i=next(i for i,ob in enumerate(doc) if key(ob) in ('label','global_label') and [round(v,2) for v in sub(ob,'at')[1:3]]==end)
 doc[i]=E('global_label',newnet,E('shape',S('bidirectional')),E('at',end[0],end[1],0),effects(.9,'left'),E('uuid',U()),prop('Intersheetrefs','${INTERSHEET_REFS}',0,0,True)) if newnet in globalnets else E('label',newnet,E('at',end[0],end[1],0),effects(.95,'left bottom'),E('uuid',U()))
globalnets.update(['POWER_OK','RUN_PERMIT','RUN_ARMED','RUN_LATCHED'])
rl=DOCS['reset_logic']
retarget(rl,'U220',4,'POWER_OK');retarget(rl,'U222',1,'POWER_OK');retarget(rl,'U221',1,'RUN_LATCHED')
an=DOCS['analog'];retarget(an,'R201',2,'RSET_LO')
pa=Sheet('_analog_patch','',uid=sub(an,'uuid')[1]);del SHEETS['_analog_patch']
pa.r('R207','383R 0.1% <=10ppm/K (RSET trim)',178,43,'RSET_LO','GND')
# Step 12 (C9): +5VA backfeed clamp. While ANA_ENABLE is low (rail commanded off, or board unpowered), Q201's gate
# follows +5VA through R209, so any rail voltage pushed up through the input clamp diodes turns Q201 on and R208
# sinks it. Q202 grounds the gate while ANA_ENABLE is high. CSD17381F4 pinout from TI SLPS411G: 1 G, 2 S, 3 D.
chip('NFET_YJC',[([(1,'G','input')],[(3,'D','passive'),(2,'S','passive')])])
pa.r('R208','100R 1% 0.25W (clamp drain)',250,150,'+5VA','AVDD_CLAMP_D',fp='Resistor_SMD:R_1206_3216Metric')
pa.symbol('NFET_YJC','Q201','CSD17381F4 (AVDD backfeed clamp)',290,165,mpn='CSD17381F4');pa.connect('Q201',1,{1:'AVDD_CLAMP_G',3:'AVDD_CLAMP_D',2:'GND'})
pa.r('R209','1M (clamp gate from +5VA)',250,185,'+5VA','AVDD_CLAMP_G')
pa.symbol('NFET_YJC','Q202','CSD17381F4 (clamp release)',290,205,mpn='CSD17381F4');pa.connect('Q202',1,{1:'ANA_ENABLE',3:'AVDD_CLAMP_G',2:'GND'})
an.extend(pa.items)
libs=sub(an,'lib_symbols');have={z[1] for z in libs[1:]}
for nm in sorted(pa.used):
 if 'EEG:'+nm not in have:libs.append(copy.deepcopy(LIB[nm]))
# Step 13 (C10): exact parts, footprints and BOM fields for every reference (scripts/bom_parts.py).
import sys;sys.path.insert(0,str(SCRIPTS));import bom_parts,footprints
def apply_parts(ob):
 props={z[1]:z for z in ob if key(z)=='property'};ref=props['Reference'][2]
 if ref.startswith('#'):return
 lib=sub(ob,'lib_id')[1].split(':')[-1]
 a=bom_parts.assign(ref,lib,props['Value'][2],props['Footprint'][2],props['MPN'][2] if 'MPN' in props else '')
 for name,val in [('Value',a['value']),('Footprint',a['fp']),('MPN',a['mpn']),('Manufacturer',a['mfr']),('Description',a['descr'])]:
  if name in props:props[name][2]=val
  else:
   at=sub(ob,'at');i=next(i for i,z in enumerate(ob) if key(z)=='instances');ob.insert(i,E('property',name,val,E('at',at[1],at[2],0),effects(hide=True)))
 for z in ob:
  if key(z)=='in_bom':z[1]=S('no' if a['pop']!='FIT' else 'yes')
  if key(z)=='on_board':z[1]=S('no' if a['pop']=='OFF-BOARD' else 'yes')
 BOM[ref]=(a['value'],a['fp'],a['mfr'],a['mpn'],a['descr'],'yes' if a['pop']!='FIT' else 'no',a['pop'])
for doc in DOCS.values():
 for ob in doc:
  if key(ob)=='symbol':apply_parts(ob)
for fn,doc in DOCS.items():(P/f'{fn}.kicad_sch').write_text(sx.dumps(doc))
chip('DFF',[([(1,'CLK','input'),(2,'D','input'),(7,'~{PRE}','input'),(6,'~{CLR}','input'),(8,'VCC','power_in')],[(5,'Q','output'),(3,'~{Q}','output'),(4,'GND','power_in')])])
L=Sheet('restart_latch','Persistent analogue restart latch (Step 10)')
L.txt('C7 STEP 10 / RESTART LATCH: FAULT CLEARS RUN_ARMED; RESTART NEEDS A NEW RUN_REQUEST RISING EDGE',10,12,1.4)
gate(L,'U226',55,60,'POWER_OK','SERVICE_OK','RUN_PERMIT')
L.symbol('DFF','U227','SN74LVC1G74DCUR',160,60,fp='Package_SO:VSSOP-8_2.3x2mm_P0.5mm',mpn='SN74LVC1G74DCUR')
L.connect('U227',1,{1:'RUN_REQUEST',2:'+3V3',7:'+3V3',6:'RUN_PERMIT',8:'+3V3',5:'RUN_ARMED',3:None,4:'GND'});L.cap('C227','100n',160,92,'+3V3')
gate(L,'U228',265,60,'RUN_REQUEST','RUN_ARMED','RUN_LATCHED')
mk('TP',[([line(-1,0,1,0)],[(1,'TP','passive',0,0,90)])],True)  # also defined on the storage sheet
L.symbol('TP','TP230','RUN_ARMED',200,110,fp='TestPoint:TestPoint_Pad_D1.0mm');L.connect('TP230',1,{1:'RUN_ARMED'})
L.txt('ANA_ENABLE = SYS_OK . PACK_OK . SERVICE_OK . RUN_REQUEST . RUN_ARMED (U220-U222 on reset logic sheet).',10,130)
L.txt('Power-up: supervisors hold POWER_OK low for their release delay, so U227 starts cleared. CLK edges need <=10 ns/V: drive RUN_REQUEST directly from GPIO, no RC.',10,140)
L.txt('Firmware: on any stop drive RUN_REQUEST low; to start, confirm SYS_OK/PACK_OK, then low >=1 us, then high. Battery rebound cannot restart analogue power.',10,150)
# USB connector with separate CC pins and joined USB2 duplicate contacts.
u=Sheet('usb_c','USB-C device connector / ESD / CC current detection')
u.txt('USB-C 5V SINK / NO PD / DATA TO MCU / VBUS TO BQ25798',10,12,1.5)
u.symbol('USBC','J310','USB4105-GF-A',40,66,fp='Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',mpn='USB4105-GF-A')
um={k:('GND' if sig in ['GND','SHIELD'] else 'VBUS_CON' if sig=='VBUS' else 'USB_DP' if sig=='D+' else 'USB_DM' if sig=='D-' else None if sig.startswith('SBU') else sig) for k,sig in usb_pins};u.connect('J310',1,um)
u.symbol('TUSB320LAI','U320','TUSB320LAIRWBR',160,65,mpn='TUSB320LAIRWBR');u.connect('U320',1,{12:'+3V3',1:'CC1',2:'CC2',4:'VBUS_DETECT_R',3:'GND',5:'GND',7:'POWER_SDA',8:'POWER_SCL',6:'USB_CC_INT_N',9:None,11:'GND',10:'GND'})
# Step 14: R360 from connector VBUS (TI SLLSEN9F: system VBUS <= 28 V); R362 from U323 VBUS_POWER, live even during OVP.
u.r('R360','887k 1%',250,36,'VBUS_CON','VBUS_DETECT_R');u.r('R361','10k',250,53,'+3V3','USB_CC_INT_N');u.cap('C320','100n',250,75,'+3V3');u.cap('C321','1u 10V X7R',300,75,'USB_5V')
for i,(aa,bb) in enumerate([('USB_DP','USB_DM'),('CC1','CC2'),('USB_5V','USB_5V')]):
 x=45+i*100;ref='D'+str(310+i);u.symbol('ESD2',ref,'TPD2E2U06DCKR',x,132,fp='Package_TO_SOT_SMD:SOT-323_SC-70',mpn='TPD2E2U06DCKR');u.connect(ref,1,{1:aa,2:bb,3:'GND'})
u.r('R362','10k 1%',55,175,'USB_VPWR','USB_SENSE_LOGIC');u.r('R363','100k 1%',55,190,'USB_SENSE_LOGIC','GND')
for i,(aa,out) in enumerate([('USB_SENSE_LOGIC','USB_ABSENT'),('USB_ABSENT','USB_PRESENT')]):
 x=160+i*95;ref='U'+str(321+i);u.symbol('INV',ref,'SN74LVC1G14DBVR',x,178,fp=fp,mpn='SN74LVC1G14DBVR');u.connect(ref,1,{2:aa,5:'+3V3',4:out,3:'GND',1:None});u.cap('C'+str(322+i),'100n',x,153,'+3V3')
u.txt('D312 is ESD suppression only. DC overvoltage cut-off: U323 TPD1S514-1 between VBUS_CON and USB_5V (Step 14).',10,102)
u.txt('No duplicate Rd. CC controller contains sink terminations. USB2 pair direct to module; route as short matched pair.',10,111)
# Digital rail from externally supplied SYS until charger integration.
b=Sheet('digital_power','Digital 3V3 rail')
b.txt('DIGITAL 3.3 V RAIL FROM SYS (BQ25798 POWER PATH ON THE CHARGER SHEET)',10,12,1.3)
b.symbol('TPS62162','U240','TPS62162DSGR',150,55,fp='Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm',mpn='TPS62162DSGR');b.connect('U240',1,{2:'SYS',3:'SYS',4:'GND',1:'GND',9:'GND',7:'SW_DIG',6:'+3V3',5:'GND',8:'BUCK_PG'})
b.symbol('L','L240','2.2uH XFL4020-222MEC',255,37,mpn='XFL4020-222MEC');b.connect('L240',1,{1:'SW_DIG',2:'+3V3'});b.cap('C240','10u 16V',90,105,'SYS');b.cap('C241','22u 10V effective value TBD',175,105,'+3V3');b.cap('C242','100n',250,105,'+3V3');b.r('R240','100k',255,75,'+3V3','BUCK_PG')

for i,(net,src) in enumerate([('CHARGE_REQUEST','GND'),('POWER_HOLD','GND'),('STATUS_LED','GND'),('SD_POWER_EN','GND'),('SD_MOSI','GND'),('SD_SCLK','GND'),('SD_MISO','+3V3'),('SD_CS_N','+3V3')]):
 if i>=4 or net=='POWER_HOLD': continue  # Step 11: POWER_HOLD pad repurposed as POWER_BUTTON_N (charger sheet)
 b.r('R'+str(380+i),'100k reserved default',35+(i%4)*75,180+(i//4)*15,net,src)

# Step 6: always-powered microSD avoids an independently unpowered I/O domain.
chip('MICROSD_DM3AT',[([(1,'DAT2','passive'),(2,'DAT3_CS_N','passive'),(3,'CMD_DI','passive'),(5,'CLK','passive'),(7,'DAT0_DO','passive'),(8,'DAT1','passive')],[(4,'VDD','power_in'),(6,'VSS','power_in'),(9,'CD_B','passive'),(10,'CD_A','passive'),('SH','SHELL_x4','passive')])])  # Step 13: KiCad 10 Hirose footprint names shell pads SH
mk('TP',[([line(-1,0,1,0)],[(1,'TP','passive',0,0,90)])],True)
globalnets.update(['SD_SCLK','SD_MOSI','SD_MISO','SD_CS_N','SD_DETECT_N'])
t=Sheet('storage','microSD SPI and shutdown test access')
t.txt('C4 STEP 7 / microSD 3V3 SPI / REMOVE CARD ONLY WITH BOARD POWER OFF',10,12,1.5)
t.symbol('MICROSD_DM3AT','J420','DM3AT-SF-PEJM5',245,65,fp='Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5',mpn='DM3AT-SF-PEJM5')
t.connect('J420',1,{1:'CARD_DAT2',2:'CARD_CS_N',3:'CARD_DI',4:'+3V3',5:'CARD_CLK',6:'GND',7:'CARD_DO',8:'CARD_DAT1',9:'CARD_DETECT_RAW_N',10:'GND','SH':'GND'})
for i,(host,card) in enumerate([('SD_SCLK','CARD_CLK'),('SD_MOSI','CARD_DI'),('SD_CS_N','CARD_CS_N'),('SD_MISO','CARD_DO')]):
 t.r('R'+str(420+i),'33R',55,40+18*i,host,card)
for i,card in enumerate(['CARD_DI','CARD_CS_N','CARD_DO','CARD_DAT1','CARD_DAT2']):
 t.r('R'+str(424+i),'10k 1%',145,38+16*i,'+3V3',card)
t.r('R429','100k',55,118,'SD_SCLK','GND')
t.r('R430','10k 1%',245,112,'+3V3','CARD_DETECT_RAW_N')
t.r('R431','100R',245,130,'CARD_DETECT_RAW_N','SD_DETECT_N')
t.cap('C420','22u 10V X7R - qualify DC bias',45,158,'+3V3',fp='Capacitor_SMD:C_1206_3216Metric')
t.cap('C421','100n 10V X7R',105,158,'+3V3')
t.cap('C422','10n',295,130,'SD_DETECT_N')
for i,(aa,bb) in enumerate([('CARD_CLK','CARD_DI'),('CARD_CS_N','CARD_DO'),('CARD_DAT1','CARD_DAT2'),('CARD_DETECT_RAW_N','+3V3')]):
 ref='D'+str(420+i);x=40+i*82
 t.symbol('ESD2',ref,'TPD2E2U06DCKR',x,192,fp='Package_TO_SOT_SMD:SOT-323_SC-70',mpn='TPD2E2U06DCKR');t.connect(ref,1,{1:aa,2:bb,3:'GND'})
for i,net in enumerate(['+3V3','GND','BAT_WARN_OK','SYS_OK','PACK_OK','DIGITAL_OK']):
 x=170+i*23;ref='TP'+str(420+i)
 t.symbol('TP',ref,net,x,158,fp='TestPoint:TestPoint_Pad_D1.0mm');t.connect(ref,1,{1:net})
t.txt('NO load switch or hold-up reservoir. SD_POWER_EN remains reserved; all SD pullups use the shared 3V3 rail.',10,215)
t.txt('BAT_WARN_OK low: stop capture, drain queue, wait card ready, sync best effort. No guaranteed flush interval.',10,223)

exec((SCRIPTS/'input_network.py').read_text())
exec((SCRIPTS/'event_inputs.py').read_text())
exec((SCRIPTS/'charger.py').read_text())
exec((SCRIPTS/'ovp.py').read_text())

u.flag('#FLG500',300,112,'USB_5V')
for sh in SHEETS.values():
 for ob in sh.items:
  if key(ob)=='symbol':apply_parts(ob)
footprints.build()
(P/'fp-lib-table').write_text('(fp_lib_table\n\t(version 7)\n\t(lib (name "EEG")(type "KiCad")(uri "${KIPRJMOD}/EEG.pretty")(options "")(descr "EEG Rev C project footprints (generated by scripts/footprints.py)"))\n)\n')
# Globalize all intersheet labels after all sheets defined, including generated intermediate nets harmlessly.
for sh in SHEETS.values():
 for ob in sh.items:
  if key(ob)=='label' and ob[1] in globalnets:
   at=sub(ob,'at');ob[:]=E('global_label',ob[1],E('shape',S('bidirectional')),E('at',at[1],at[2],0),effects(.9,'left'),E('uuid',U()),prop('Intersheetrefs','${INTERSHEET_REFS}',0,0,True))
 sh.save()
# Root manifest
root=E('kicad_sch',E('version',20250114),E('generator',S('eeschema')),E('uuid',ROOT),E('paper','A3'),E('lib_symbols'))
entries=imported+[(sh.name,sh.title,sh.uid) for sh in SHEETS.values()]
# Root sheet: one titled column per function. Page numbers keep the entries order.
import sys;sys.path.insert(0,str(SCRIPTS));import layout
ROOT_COLS=[('Acquisition chain','Electrodes to ADC samples, BIAS loop, ADC control and event timing.',['ads1299_core','inputs_1_4','inputs_5_8','ref_bias','adc_interface','event_inputs']),
 ('Power and supervision','Charger and pack, analogue and digital rails, supply monitors, hardware enable, reset and restart latch.',['charger','analog','supervision','reset_logic','restart_latch','digital_power']),
 ('Controller and interfaces','NINA-B306 module, programming and service inhibit, USB-C, microSD.',['controller','debug_service','usb_c','storage'])]
where={fn:(c,r) for c,(_,_,fns) in enumerate(ROOT_COLS) for r,fn in enumerate(fns)}
assert set(where)=={fn for fn,_,_ in entries},'every sheet needs a root column'
for c,(title,note,fns) in enumerate(ROOT_COLS):
 fx=15.24+c*129.54
 root.append(layout.frame_item(fx,27.94,fx+124.46,27.94+16.51+len(fns)*30.48))
 root.append(layout.text_item(title,fx+3.81,30.48,2.0,True));root.append(layout.text_item(note,fx+3.81,34.29,1.15))
for i,(fn,title,sid) in enumerate(entries):
 c,r=where[fn];x=19.05+c*129.54;y=48.26+r*30.48
 root.append(E('sheet',E('at',x,y),E('size',116.84,17.78),E('stroke',E('width',.254),E('type',S('default'))),E('fill',E('color',0,0,0,0)),E('uuid',sid),E('property','Sheetname',title,E('at',x,y-1.27,0),effects(1.2,'left bottom')),E('property','Sheetfile',fn+'.kicad_sch',E('at',x,y+19.05,0),effects(1,'left top')),E('instances',E('project',PROJ,E('path','/'+ROOT,E('page',str(i+2)))))))
root.append(E('sheet_instances',E('path','/',E('page','1'))));root.append(E('text','EEG RECORDER REV C12 (STEP 14 + IMPEDANCE TEST LINKS) - 8-CHANNEL ADS1299, NINA-B306, microSD, USB-C CHARGING - BENCH DRAFT, NO HUMAN CONNECTION',E('at',15.24,19.05,0),effects(1.4,'left'),E('uuid',U())))
(P/(PROJ+'.kicad_sch')).write_text(sx.dumps(root))
if not (P/(PROJ+'.kicad_pro')).exists():(P/(PROJ+'.kicad_pro')).write_text('{}')  # Step 14: pcb_place.py owns the board and net settings
for f in P.glob('*.kicad_sch'):f.write_text(f.read_text().replace('B - BENCH REVIEW',REV).replace('C1 - STEP4 MODULE',REV))
# Readability pass: titled, commented frames per functional group; labels point away from parts.
import layout_groups
for line in layout.run(P,layout_groups.GROUPS):print('layout',line)
libout=[]
for nm,lib in LIB.items():
 cp=copy.deepcopy(lib);cp[1]=nm;libout.append(cp)
(P/'EEG.kicad_sym').write_text(sx.dumps(E('kicad_symbol_lib',E('version',20241209),E('generator',S('kicad_symbol_editor')),*libout)))
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "EEG") (type "KiCad") (uri "${KIPRJMOD}/EEG.kicad_sym") (options "") (descr "EEG Rev C")))')
with (P/'bom.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Ref','Value','Footprint','Manufacturer','MPN','Description','DNP','Population']);w.writerows((k,*v) for k,v in sorted(BOM.items(),key=lambda kv:(re.sub(r'\d.*','',kv[0]),int(re.sub(r'\D','',kv[0]) or 0))) if not k.startswith('#'))
with (P/'controller_pinmap.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
(CHECKS/'expected_module_map.json').write_text(json.dumps({str(k):v for k,v in mapm.items()},indent=2));print('Built',len(entries)+1,'pages;',len(BOM),'references')
