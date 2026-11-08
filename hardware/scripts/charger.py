# Step 11: BQ25798 buck-boost charger, power path, ship FET (soft-off), pack connector and charge control.
# Executed by build.py with shared helpers in scope. Pinout from TI SLUSDV2C Table 5-1 (RQM, 29-pin VQFN-HR);
# CSD17571Q2 from TI SLPS393A (SON 2x2: 1,2,5,6 drain, 3 gate, 4 source). See docs/reviews/step11_charger_review.md.
chip('BQ25798',[([(2,'VBUS','passive'),(3,'VBUS','passive'),(9,'VAC1','passive'),(8,'VAC2','passive'),(11,'ACDRV1','passive'),(10,'ACDRV2','passive'),
  (6,'D+','passive'),(7,'D-','passive'),(29,'PMID','passive'),(4,'BTST1','passive'),(28,'SW1','passive'),(5,'REGN','passive'),(20,'PROG','passive'),(17,'ILIM_HIZ','passive'),(16,'TS','passive')],
 [(25,'SYS','passive'),(26,'SW2','passive'),(19,'BTST2','passive'),(22,'BAT','passive'),(23,'BAT','passive'),(18,'BATP','passive'),(24,'SDRV','passive'),
  (13,'~{CE}','input'),(12,'~{QON}','input'),(14,'SCL','input'),(15,'SDA','bidirectional'),(21,'~{INT}','open_collector'),(1,'~{STAT}','open_collector'),(27,'GND','power_in')])])
chip('NFET_DQK',[([(3,'G','passive'),(4,'S','passive')],[(1,'D','passive'),(2,'D','passive'),(5,'D','passive'),(6,'D','passive')])])
chip('NMOS_SOT23',[([(1,'G','input')],[(3,'D','passive'),(2,'S','passive')])])
chip('SCHOTTKY_SOT23',[([(1,'A','passive')],[(3,'K','passive'),(2,'NC','no_connect')])])
globalnets.update(['SYS','PACK_POS','USB_5V','POWER_SDA','POWER_SCL','CHARGER_INT_N','CHARGE_REQUEST','POWER_BUTTON_N'])
c08='Capacitor_SMD:C_0805_2012Metric';c12='Capacitor_SMD:C_1206_3216Metric';c1210='Capacitor_SMD:C_1210_3225Metric';c06='Capacitor_SMD:C_0603_1608Metric'
ch=Sheet('charger','BQ25798 charger, power path and pack connector')
ch.txt('C8 STEP 11 / BQ25798 2S CHARGER AND POWER PATH / CHARGE ONLY WITH ELECTRODES DISCONNECTED',10,12,1.4)
ch.symbol('BQ25798','U400','BQ25798RQMR (I2C 0x6B)',60,90,mpn='BQ25798RQMR')
ch.connect('U400',1,{2:'USB_5V',3:'USB_5V',9:'USB_5V',8:'USB_5V',11:'GND',10:'GND',6:None,7:None,29:'CHG_PMID',4:'CHG_BTST1',28:'CHG_SW1',5:'REGN',20:'CHG_PROG',17:'CHG_ILIM',16:'CHG_TS',
 25:'SYS',26:'CHG_SW2',19:'CHG_BTST2',22:'PACK_POS',23:'PACK_POS',18:'CHG_BATP',24:'CHG_SDRV',13:'CHG_CE_N',12:'CHG_QON_N',14:'POWER_SCL',15:'POWER_SDA',21:'CHARGER_INT_N',1:'CHG_STAT_N',27:'GND'})
# Input, PMID, bootstrap, REGN.
# One 10 uF only: with C321 (1 uF at J310) this keeps VBUS bulk near the USB Type-C 10 uF sink limit; TI minimum is 2 uF effective.
ch.cap('C400','10u 25V X7R 1206 (VBUS)',150,40,'USB_5V',fp=c12,mpn='GRM31CR71E106KA12L')
ch.cap('C402','100n 50V X7R (VBUS, at pin)',190,40,'USB_5V',fp=c06)
for i,ref in enumerate(['C403','C404','C405']):ch.cap(ref,'10u 25V X7R 1206 (PMID)',150+i*20,70,'CHG_PMID',fp=c12,mpn='GRM31CR71E106KA12L')
ch.cap('C406','100n 50V X7R (PMID, at pin)',210,70,'CHG_PMID',fp=c06)
ch.cap('C407','47n 25V X7R (BTST1)',150,100,'CHG_BTST1','CHG_SW1',fp=c06)
ch.cap('C408','47n 25V X7R (BTST2)',170,100,'CHG_BTST2','CHG_SW2',fp=c06)
ch.cap('C409','4.7u 10V X7R (REGN)',190,100,'REGN',fp=c08)
ch.symbol('L','L400','1.0uH XFL4020-102ME (Isat >= 3 A)',230,100,fp='Inductor_SMD:L_Coilcraft_XxL4020',mpn='XFL4020-102MEB');ch.connect('L400',1,{1:'CHG_SW1',2:'CHG_SW2'})
# SYS: TI minimum plus Step 10 hold-up so SYS_OK resets the ADC before AVDD leaves regulation.
for i,ref in enumerate(['C410','C411','C412','C413','C414']):ch.cap(ref,'22u 25V X7R 1210 (SYS)',150+i*20,130,'SYS',fp=c1210,mpn='GRM32ER71E226KE15L')
ch.cap('C415','100n 50V X7R (SYS, at pin)',250,130,'SYS',fp=c06)
ch.cap('C416','100u 16V OS-CON polymer (SYS hold-up)',270,130,'SYS',fp='Capacitor_SMD:CP_Elec_10x7.9',mpn='16SVP100M')
for i,ref in enumerate(['C417','C418']):ch.cap(ref,'10u 25V X7R 1206 (BAT)',150+i*20,160,'PACK_POS',fp=c12,mpn='GRM31CR71E106KA12L')
# Configuration straps: 2S at 1.5 MHz; ILIM_HIZ hardware input-current ceiling below 500 mA; TS window for 103AT NTC.
ch.r('R401','6.04k 1% (PROG: 2S, 1.5 MHz)',40,170,'CHG_PROG','GND')
ch.r('R402','27.0k 1%',40,185,'REGN','CHG_ILIM');ch.r('R403','10.0k 1%',90,185,'CHG_ILIM','GND')
ch.r('R404','5.23k 1%',40,200,'REGN','CHG_TS');ch.r('R405','30.1k 1%',90,200,'CHG_TS','GND')
# Pack, ship FET and battery sense. Q400 source on the charger BAT side so its body diode blocks pack discharge in ship mode.
ch.symbol('J3','J401','PACK: + / - / NTC 103AT (JST PH, keyed)',300,60,fp='Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal',mpn='S3B-PH-K-S')
ch.connect('J401',1,{1:'PACK_IN',2:'GND',3:'CHG_TS'})
ch.symbol('NFET_DQK','Q400','CSD17571Q2 (ship FET)',300,100,fp='Package_SON:Texas_DQK',mpn='CSD17571Q2')
ch.connect('Q400',1,{3:'CHG_SDRV',4:'PACK_POS',1:'PACK_IN',2:'PACK_IN',5:'PACK_IN',6:'PACK_IN'})
ch.r('R400','100R 1% (BATP sense)',300,140,'PACK_IN','CHG_BATP')
# Charge enable: CE is low (enabled) only while the MCU drives CHARGE_REQUEST high; REGN pull-up keeps it disabled otherwise.
ch.r('R406','100k',40,215,'REGN','CHG_CE_N')
ch.symbol('NMOS_SOT23','Q401','BSS138 (CE pull-down)',120,230,fp='Package_TO_SOT_SMD:SOT-23',mpn='BSS138');ch.connect('Q401',1,{1:'CHARGE_REQUEST',3:'CHG_CE_N',2:'GND'})
# Status LED (lit from REGN, so only with USB present) and power button on QON with an MCU-readable copy.
ch.r('R407','2.2k',200,200,'REGN','CHG_LED_A')
ch.symbol('D','D401','CHARGE LED green (LTST-C190GKT)',240,200,fp='LED_SMD:LED_0603_1608Metric',mpn='LTST-C190GKT');ch.connect('D401',1,{1:'CHG_STAT_N',2:'CHG_LED_A'})
ch.symbol('SW','SW400','POWER (hold 1 s: on; 10 s: system reset)',200,230,fp='Button_Switch_SMD:SW_SPST_TL3342',mpn='TL3342F160QG');ch.connect('SW400',1,{1:'CHG_QON_N',2:'GND'})
ch.symbol('SCHOTTKY_SOT23','D402','BAT54 (button sense, blocks QON back-feed)',260,230,fp='Package_TO_SOT_SMD:SOT-23',mpn='BAT54,215')
ch.connect('D402',1,{1:'POWER_BUTTON_N',3:'CHG_QON_N',2:None})
ch.r('R408','10k',300,230,'+3V3','POWER_BUTTON_N')
