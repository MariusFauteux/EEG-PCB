# Generated input network and REF/BIAS sheet; helper functions and shared project state supplied by build.py.
mk('ELECTRODE',[([rect(-2,1,2,-1)],[(1,'E','passive',4,0,180)])],True)
connector('JP3',3)
globalnets.update(['REF_RAW','REF_BUF','ADC_BIASOUT','ADC_BIASINV'])
# Step 13: the 18 electrode symbols stay as off-board leads; J500 is the on-board harness connector they plug into.
globalnets.update([f'E{ch}{leg}' for ch in range(1,9) for leg in 'PN']+['BIAS_ELEC'])
connector('J20',20)
for ch in range(1,9):globalnets.update([f'ADC_IN{ch}P',f'ADC_IN{ch}N'])
for bank in range(2):
 sh=Sheet(f'inputs_{bank*4+1}_{bank*4+4}',f'Electrode inputs {bank*4+1}-{bank*4+4} - protected bench candidate')
 sh.txt('C4 INPUTS / 94k BEFORE CLAMP + 4.7k AFTER CLAMP / NO HUMAN CONNECTION',10,12,1.4)
 sh.txt('TPD leakage limit applies at 2.5V. Ground shunt is NOT isolation. Only one shunt per JP; change with power OFF.',10,20,1)
 for j in range(4):
  ch=bank*4+j+1;y=35+j*48
  sh.txt(f'CH{ch}',10,y-5,1.3)
  sh.symbol('ELECTRODE',f'J{2*ch-1}',f'CH{ch}+',20,y)
  sh.wire(24,y,56,y);sh.lab(f'E{ch}P',30,y)
  sh.symbol('ELECTRODE',f'J{2*ch}',f'CH{ch}-',20,y+20)
  sh.wire(24,y+20,36,y+20);sh.lab(f'E{ch}N',36,y+20)
  sh.symbol('JP3',f'JP{ch}','1-2 bipolar / 2-3 REF',55,y+34,fp='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
  sh.connect(f'JP{ch}',1,{1:f'E{ch}N',2:f'NSEL{ch}',3:'REF_BUF'})
  sh.wire(47,y+20,56,y+20);sh.lab(f'NSEL{ch}',47,y+20)
  for leg,dy,k in [('P',0,1),('N',20,3)]:
   yy=y+dy
   for r,x in [(ch*10+k,60),(ch*10+k+1,92)]:
    sh.symbol('R',f'R{r}','47k 0.1%',x,yy,fp='Resistor_SMD:R_0805_2012Metric')
   sh.wire(64,yy,88,yy)
   sh.wire(96,yy,154,yy);sh.lab(f'CLAMP{ch}{leg}',112,yy)
   sh.symbol('R',f'R{500+2*(ch-1)+(1 if leg=="P" else 2)}','4.7k 0.1%',158,yy,fp='Resistor_SMD:R_0805_2012Metric')
   sh.wire(162,yy,195,yy);sh.wire(195,yy,215,yy);sh.lab(f'ADC_IN{ch}{leg}',215,yy)
   sh.items.append(E('junction',E('at',mm(195),mm(yy)),E('diameter',0),E('color',0,0,0,0),E('uuid',U())))
  sh.symbol('C',f'C{ch}','220p C0G 5% 50V',195,y+10,fp='Capacitor_SMD:C_0603_1608Metric')
  sh.wire(195,y,195,y+7);sh.wire(195,y+13,195,y+20)
  ref=f'D{500+ch}';sh.symbol('ESD2',ref,'TPD2E2U06DCKR',275,y+8,fp='Package_TO_SOT_SMD:SOT-323_SC-70',mpn='TPD2E2U06DCKR')
  sh.connect(ref,1,{1:f'CLAMP{ch}P',2:f'CLAMP{ch}N',3:'GND'})
 sh.txt('JP pin 3 is REF_BUF (buffered REF, ref_bias sheet); it passes through the same N-leg network as a bipolar electrode.',10,224,1)
q=Sheet('ref_bias','Reference buffer and BIAS drive network')
q.txt('C9 REFERENCE BUFFER / BIAS / BENCH ONLY',10,12,1.4)
q.symbol('ELECTRODE','JREF1','REF electrode',30,45);q.connect('JREF1',1,{1:'REF_RAW'})
# Step 12: buffered REF. The electrode sees one leg network (2 x 47k, clamp, 4.7k) into an OPA376 follower whose
# output REF_BUF feeds pin 3 of JP1-JP8; every selected channel keeps its own 94k / clamp / 4.7k after the jumper.
# OPA376 SOT-23-5 pinout from TI SBOS406G: 1 OUT, 2 V-, 3 +IN, 4 -IN, 5 V+.
chip('OPA376',[([(3,'+IN','input'),(4,'-IN','input')],[(5,'V+','power_in'),(1,'OUT','output'),(2,'V-','power_in')])])
q.r('R517','47k 0.1%',60,45,'REF_RAW','REF_MID',fp='Resistor_SMD:R_0805_2012Metric')
q.r('R518','47k 0.1%',90,45,'REF_MID','REF_CLAMP',fp='Resistor_SMD:R_0805_2012Metric')
q.symbol('ESD2','D510','TPD2E2U06DCKR',120,70,fp='Package_TO_SOT_SMD:SOT-323_SC-70',mpn='TPD2E2U06DCKR');q.connect('D510',1,{1:'REF_CLAMP',2:'REF_CLAMP',3:'GND'})
q.r('R519','4.7k 0.1%',150,45,'REF_CLAMP','REF_BUF_IN',fp='Resistor_SMD:R_0805_2012Metric')
q.symbol('OPA376','U500','OPA376AIDBVR',220,55,fp='Package_TO_SOT_SMD:SOT-23-5',mpn='OPA376AIDBVR')
q.connect('U500',1,{3:'REF_BUF_IN',4:'REF_BUF',5:'+5VA',1:'REF_BUF',2:'GND'})
q.cap('C500','100n 16V X7R (at U500 V+)',270,45,'+5VA',fp='Capacitor_SMD:C_0603_1608Metric')
q.cap('C501','1u 10V X7R',300,45,'+5VA')
q.txt('REF_RAW drives only the U500 input network. REF_BUF feeds pin 3 of JP1-JP8; each selected branch keeps its own 94k / clamp / 4.7k path.',10,70)
q.txt('REF is an electrode, not ADC VREF and not GND. Unselected negative electrodes are disconnected by JP.',10,82)
q.txt('Buffered REF: no shared electrode impedance between channels, 10 nA max DC from the REF electrode (was 8 x).',10,94)
q.symbol('R','RB1','499k 0.1%',75,135,fp='Resistor_SMD:R_0805_2012Metric');q.symbol('R','RB2','499k 0.1%',125,135,fp='Resistor_SMD:R_0805_2012Metric')
q.wire(45,135,71,135);q.lab('ADC_BIASOUT',45,135);q.wire(79,135,121,135);q.lab('BIAS_MID',100,135);q.wire(129,135,180,135);q.lab('BIAS_ELEC',150,135)
# Step 8: clamp at the RB1/RB2 midpoint keeps 499k on each side (electrode side and BIASOUT side).
q.symbol('ESD2','D509','TPD2E2U06DCKR',100,165,fp='Package_TO_SOT_SMD:SOT-323_SC-70',mpn='TPD2E2U06DCKR');q.connect('D509',1,{1:'BIAS_MID',2:'BIAS_MID',3:'GND'})
q.symbol('ELECTRODE','JBIAS1','BIAS electrode',176,135)
q.r('RFB1','1M',250,125,'ADC_BIASOUT','ADC_BIASINV',fp='Resistor_SMD:R_0805_2012Metric')
# Step 8 lead-lag compensation: Zf = RFB1 || (RZB1 + CFB1). Values from analyze_bias.py sweep; provisional.
q.cap('CFB1','10n C0G 5% 50V',250,155,'ADC_BIASOUT','BIAS_COMP')
q.r('RZB1','100k 0.1%',300,155,'BIAS_COMP','ADC_BIASINV',fp='Resistor_SMD:R_0805_2012Metric')
q.txt('Zf = 1M || (100k + 10n). Replaces TI example 1M || 1.5n: model phase margin 14 deg nominal -> 84 deg; >=47 deg over sweep.',10,185)
q.txt('FIRMWARE: BIASREF pin is tied to AVSS. Set BIASREF_INT=1 in the same CONFIG3 write that sets PD_BIAS=1. Monitor BIAS_STAT.',10,192)
q.txt('Do not inject sustained overvoltage or connect a person. RB1/RB2 need pulse/voltage-rated parts. AVDD backfeed clamp Q201 on the analog sheet.',10,199)
# Step 13 (C10): electrode harness connector. Pins 1-16 CH1+..CH8- (odd = +, even = -), 17 REF, 18 BIAS, 19-20 unused.
q.symbol('J20','J500','ELECTRODE HARNESS 2x10 (keyed box header)',30,215,fp='Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical')
q.connect('J500',1,{**{2*ch-1:f'E{ch}P' for ch in range(1,9)},**{2*ch:f'E{ch}N' for ch in range(1,9)},17:'REF_RAW',18:'BIAS_ELEC',19:None,20:None})
