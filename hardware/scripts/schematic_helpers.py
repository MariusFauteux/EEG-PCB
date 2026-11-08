from pathlib import Path
import sexpdata as sx,uuid,copy,json,csv
P=Path(__file__).resolve().parents[1];  # overridden by build.py
S=sx.Symbol
U=lambda:str(uuid.uuid4())
# Step 14: sheet and symbol UUIDs are derived from names, so footprint paths (sheet/symbol UUIDs) stay the same on
# every rebuild and the PCB keeps matching the schematic. Wires, labels and text keep random UUIDs.
NS_SCH=uuid.UUID('3b8f0c1e-6a2d-4f5e-9c7b-1d2e3f405162')
UD=lambda key:str(uuid.uuid5(NS_SCH,key))
def E(k,*a):return [S(k),*a]
def key(a):return str(a[0]) if isinstance(a,list) and a else ''
def sub(a,k):return next(x for x in a if key(x)==k)
def mm(n):return round(n*1.27,3)
def effects(size=1,justify=None,hide=False):
 a=E('effects',E('font',E('size',size,size)))
 if justify:a.append(E('justify',*[S(z) for z in justify.split()]))
 if hide:a.append(S('hide'))
 return a
ROOT=U();PROJ='EEG_ADS1299_RevB';LIB={};BOM={};PINMAP={};SHEETS={}
def prop(name,value,x=0,y=0,hidden=False):return E('property',name,value,E('at',mm(x),mm(y),0),effects(hide=hidden))
def rect(x1,y1,x2,y2):return E('rectangle',E('start',mm(x1),mm(y1)),E('end',mm(x2),mm(y2)),E('stroke',E('width',.254),E('type',S('default'))),E('fill',E('type',S('none'))))
def line(x1,y1,x2,y2):return E('polyline',E('pts',E('xy',mm(x1),mm(y1)),E('xy',mm(x2),mm(y2))),E('stroke',E('width',.254),E('type',S('default'))),E('fill',E('type',S('none'))))
def pin(num,name,typ,x,y,ang):return E('pin',S(typ),S('line'),E('at',mm(x),mm(y),ang),E('length',mm(2)),E('name',name,effects(.9)),E('number',str(num),effects(.8)))
def mk(name,units,hide=False):
 lib=E('symbol','EEG:'+name,E('pin_names',E('offset',.7)),E('in_bom',S('yes')),E('on_board',S('yes')),prop('Reference','U'),prop('Value',name))
 if hide:lib[2].append(S('hide'));lib.insert(3,E('pin_numbers',S('hide')))
 for i,(body,pins) in enumerate(units,1):
  lib.append(E('symbol',f'{name}_{i}_1',*body,*[pin(*p) for p in pins]));PINMAP[(name,i)]={str(p[0]):p for p in pins}
 LIB[name]=lib
mk('R',[([rect(-2,.8,2,-.8)],[(1,'1','passive',-4,0,0),(2,'2','passive',4,0,180)])],True)
mk('C',[([line(-2,.6,2,.6),line(-2,-.6,2,-.6)],[(1,'1','passive',0,3,270),(2,'2','passive',0,-3,90)])],True)
mk('L',[([rect(-2,.8,2,-.8),line(-1,.8,-1,-.8),line(0,.8,0,-.8),line(1,.8,1,-.8)],[(1,'1','passive',-4,0,0),(2,'2','passive',4,0,180)])],True)
mk('F',[([rect(-2,1,2,-1),line(-2,0,2,0)],[(1,'1','passive',-4,0,0),(2,'2','passive',4,0,180)])],True)
mk('SW',[([line(-2,0,1,1),line(1,0,2,0)],[(1,'1','passive',-4,0,0),(2,'2','passive',4,0,180)])],True)
mk('D',[([line(-1.5,-1.5,-1.5,1.5),line(1.5,-1.5,1.5,1.5),line(1.5,1.5,-1.5,0),line(1.5,-1.5,-1.5,0)],[(1,'K','passive',-4,0,0),(2,'A','passive',4,0,180)])])
mk('FLAG',[([line(-1,0,1,0),line(1,0,0,1),line(0,1,-1,0)],[(1,'pwr','power_out',0,-2,90)])],True)
def connector(name,n):
 pins=[(i+1,str(i+1),'passive',-4,-i*2,0) for i in range(n)]
 mk(name,[([rect(-2,1,2,-(n-1)*2-1)],pins)])
connector('J2',2);connector('J14',14)
def chip(name,groups):
 units=[]
 for left,right in groups:
  h=max(len(left),len(right))*2+2
  pins=[]
  for side,entries in [(-1,left),(1,right)]:
   for i,(num,nm,tp) in enumerate(entries):pins.append((num,nm,tp,side*17,h/2-3-i*4,0 if side<0 else 180))
  # half-height includes row pitch 4
  h=max(len(left),len(right))*4+2
  pins=[]
  for side,entries in [(-1,left),(1,right)]:
   for i,(num,nm,tp) in enumerate(entries):pins.append((num,nm,tp,side*17,h/2-3-i*4,0 if side<0 else 180))
  units.append(([rect(-15,h/2,15,-h/2)],pins))
 mk(name,units)
inputs=[]
for ch in range(1,9):inputs += [(18-2*ch,f'IN{ch}P','input'),(17-2*ch,f'IN{ch}N','input')]
chip('ADS1299',[(inputs,[(17,'SRB1','bidirectional'),(18,'SRB2','bidirectional'),(60,'BIASREF','input'),(62,'BIASIN','input'),(61,'BIASINV','bidirectional'),(63,'BIASOUT','output')]),
 ([(34,'DIN','input'),(40,'SCLK','input'),(39,'~{CS}','input'),(38,'START','input'),(36,'~{RESET}','input'),(35,'~{PWDN}','input'),(37,'CLK','bidirectional'),(52,'CLKSEL','input'),(41,'DAISY_IN','input')],[(43,'DOUT','output'),(47,'~{DRDY}','output'),(42,'GPIO1','bidirectional'),(44,'GPIO2','bidirectional'),(45,'GPIO3','bidirectional'),(46,'GPIO4','bidirectional'),(31,'RESV1','input')]),
 ([(19,'AVDD_19','power_in'),(21,'AVDD_21','power_in'),(22,'AVDD_22','power_in'),(56,'AVDD_56','power_in'),(59,'AVDD_59','power_in'),(54,'AVDD1','power_in'),(48,'DVDD_48','power_in'),(50,'DVDD_50','power_in'),(24,'VREFP','bidirectional'),(28,'VCAP1','output'),(30,'VCAP2','output'),(55,'VCAP3','output'),(26,'VCAP4','output')],[(20,'AVSS_20','power_in'),(23,'AVSS_23','power_in'),(32,'AVSS_32','power_in'),(57,'AVSS_57','power_in'),(58,'AVSS_58','power_in'),(53,'AVSS1','power_in'),(33,'DGND_33','power_in'),(49,'DGND_49','power_in'),(51,'DGND_51','power_in'),(25,'VREFN','input'),(27,'NC','no_connect'),(29,'NC','no_connect'),(64,'RESERVED','no_connect')])])
chip('TPS7A4901', [([(8,'IN','power_in'),(5,'EN','input'),(6,'NR_SS','passive')],[(1,'OUT','power_out'),(2,'FB','input'),(4,'GND','power_in'),(9,'EP','power_in'),(3,'NC','no_connect'),(7,'DNC','no_connect')])])
chip('TPS62162', [([(2,'VIN','power_in'),(3,'EN','input'),(4,'AGND','power_in'),(1,'PGND','power_in'),(9,'EP','power_in')],[(7,'SW','output'),(6,'VOS','input'),(5,'FB','input'),(8,'PG','open_collector')])])
chip('TPS3700DDC', [([(5,'VDD','power_in'),(3,'INA+','input'),(4,'INB-','input')],[(1,'OUTA','open_collector'),(6,'OUTB','open_collector'),(2,'GND','power_in')])])
rfp='Resistor_SMD:R_0603_1608Metric';cfp='Capacitor_SMD:C_0805_2012Metric'
globalnets={'GND','+5VA','+3V3','+3V3_ADC','PG_3V3','BAT_OK_N','ANALOG_PG'}|{f'ADC_IN{i}{leg}' for i in range(1,9) for leg in 'PN'}|{'ADC_BIASINV','ADC_BIASOUT'}
class Sheet:
 def __init__(self,name,title,uid=None):
  self.name=name;self.uid=uid or UD('sheet:'+name);self.title=title;self.items=[];self.used=set();self.inst={};SHEETS[name]=self
 def txt(self,t,x,y,size=1.15):self.items.append(E('text',t,E('at',mm(x),mm(y),0),effects(size,'left'),E('uuid',U())))
 def wire(self,x,y,a,b):self.items.append(E('wire',E('pts',E('xy',mm(x),mm(y)),E('xy',mm(a),mm(b))),E('stroke',E('width',0),E('type',S('default'))),E('uuid',U())))
 def lab(self,net,x,y):
  if net in globalnets:
   self.items.append(E('global_label',net,E('shape',S('bidirectional')),E('at',mm(x),mm(y),0),effects(.9,'left'),E('uuid',U()),prop('Intersheetrefs','${INTERSHEET_REFS}',x,y,True)))
  else:self.items.append(E('label',net,E('at',mm(x),mm(y),0),effects(.95,'left bottom'),E('uuid',U())))
 def nc(self,x,y):self.items.append(E('no_connect',E('at',mm(x),mm(y)),E('uuid',U())))
 def symbol(self,name,ref,val,x,y,unit=1,fp='',mpn='',dnp=False):
  self.used.add(name);sid=UD(f'symbol:{self.name}:{ref}:{unit}');base=LIB[name]
  pts=PINMAP[(name,unit)]; maxy=max(z[4] for z in pts.values())
  obj=E('symbol',E('lib_id','EEG:'+name),E('at',mm(x),mm(y),0),E('unit',unit),E('in_bom',S('yes')),E('on_board',S('yes')),E('dnp',S('yes' if dnp else 'no')),E('uuid',sid),prop('Reference',ref,x,y-maxy-4),prop('Value',val,x,y-maxy-2),prop('Footprint',fp,x,y,True),prop('MPN',mpn,x,y,True),E('instances',E('project',PROJ,E('path',f'/{ROOT}/{self.uid}',E('reference',ref),E('unit',unit)))))
  for num in pts:obj.append(E('pin',num,E('uuid',U())))
  self.items.append(obj);self.inst[(ref,unit)]=(x,y,name);BOM[ref]=(val,fp,mpn,'DNP' if dnp else 'FIT');return obj
 def connect(self,ref,unit,mapping):
  x,y,name=self.inst[(ref,unit)]
  for num,net in mapping.items():
   pn=PINMAP[(name,unit)][str(num)];px=x+pn[3];py=y-pn[4]
   if net is None:self.nc(px,py);continue
   # labels on short stubs, aligned outward
   dx=-7 if pn[5]==0 else 7 if pn[5]==180 else 0
   dy=-5 if pn[5]==270 else 5 if pn[5]==90 else 0
   self.wire(px,py,px+dx,py+dy);self.lab(net,px+dx,py+dy)
 def r(self,ref,val,x,y,a,b,fp=rfp,mpn=''):
  self.symbol('R',ref,val,x,y,fp=fp,mpn=mpn);self.connect(ref,1,{1:a,2:b})
 def cap(self,ref,val,x,y,a,b='GND',fp=cfp,mpn=''):
  ob=self.symbol('C',ref,val,x,y,fp=fp,mpn=mpn)
  # side labels leave capacitor unobstructed
  for z in ob:
   if key(z)=='property' and z[1] in ['Reference','Value']:
    at=sub(z,'at');at[1:3]=[mm(x+5),mm(y+(-1 if z[1]=='Reference' else 1))]
  self.connect(ref,1,{1:a,2:b})
 def flag(self,ref,x,y,net):
  self.symbol('FLAG',ref,'PWR_FLAG',x,y);self.connect(ref,1,{1:net})
 def save(self):
  doc=E('kicad_sch',E('version',20250114),E('generator',S('eeschema')),E('uuid',self.uid),E('paper','A3'),E('title_block',E('title',self.title),E('date','2026-11-08'),E('rev','B - BENCH REVIEW')),E('lib_symbols',*[copy.deepcopy(LIB[n]) for n in sorted(self.used)]),*self.items)
  (P/(self.name+'.kicad_sch')).write_text(sx.dumps(doc));return doc
