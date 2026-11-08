# Step 14 (C11): VBUS overvoltage protection. Executed by build.py after charger.py, with shared helpers in scope.
#
# U323 TPD1S514-1 (TI SLVSCF6F, May 2019) sits between the USB-C VBUS contacts (VBUS_CON) and USB_5V:
#   OVP 5.90-5.99 V rising, nFET off within 100 ns, VBUS_CON tolerates 30 V DC and 100 V IEC 61000-4-5 surge,
#   RON 39 mOhm typ / 50 mOhm max (25 C, 1 A), 20 ms start-up delay then 3.5 ms soft start after every UVLO
#   (plug-in) or OVP event. EN tied low = always enabled (TI section 9.2.1, Case 1).
#   WCSP YZ0012 ball map (TI section 6): A1 EN, B1 VBUS_POWER, A2/A3/B2 VBUS_SYS, B3/C2/C3 VBUS_CON, A4/B4/C1/C4 GND.
# VBUS_POWER (USB_VPWR) is an always-on LDO output: 4.7-4.95 V at VBUS_CON = 5 V, <= 5.5 V with 30 V on VBUS_CON,
#   3 mA max, 1 uF required. It feeds the USB-sense divider, so USB_ABSENT is low whenever a cable carries VBUS,
#   even while U323 is blocking an overvoltage source.
# U324 TPS7A2050P (TI SBVS338H, July 2024) gives the module VBUS pad 31 its own 5.0 V +/-1.5 %: the nRF52840 VBUS pin
#   is rated 4.35-5.5 V operating and 5.8 V absolute maximum (Nordic nRF52840 PS, read 2026-11-08), below the
#   TPD1S514-1 OVP ceiling of 5.99 V. DBV pinout: 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT.
chip('TPD1S514',[([('B3','VBUS_CON','passive'),('C2','VBUS_CON','passive'),('C3','VBUS_CON','passive'),('A1','~{EN}','input'),('B1','VBUS_POWER','power_out')],
 [('A2','VBUS_SYS','passive'),('A3','VBUS_SYS','passive'),('B2','VBUS_SYS','passive'),('A4','GND','power_in'),('B4','GND','power_in'),('C1','GND','power_in'),('C4','GND','power_in')])])
chip('LDO_DBV5',[([(1,'IN','power_in'),(3,'EN','input')],[(5,'OUT','power_out'),(2,'GND','power_in'),(4,'NC','no_connect')])])
globalnets.update(['MCU_VBUS','USB_5V','VBUS_CON','USB_VPWR'])  # global names keep the checks independent of sheet paths
c08o='Capacitor_SMD:C_0805_2012Metric'
u.symbol('TPD1S514','U323','TPD1S514-1YZR (VBUS OVP 5.9-5.99 V)',120,230,fp='EEG:Texas_YZ0012_DSBGA-12_P0.4mm',mpn='TPD1S514-1YZR')
u.connect('U323',1,{'B3':'VBUS_CON','C2':'VBUS_CON','C3':'VBUS_CON','A1':'GND','B1':'USB_VPWR','A2':'USB_5V','A3':'USB_5V','B2':'USB_5V','A4':'GND','B4':'GND','C1':'GND','C4':'GND'})
u.cap('C324','1u 50V X7R 0805 (VBUS_CON, at U323)',45,230,'VBUS_CON',fp=c08o)
u.cap('C325','1u 25V X7R 0805 (VBUS_POWER LDO)',200,230,'USB_VPWR',fp=c08o)
u.symbol('LDO_DBV5','U324','TPS7A2050PDBVR (module VBUS 5.0 V)',270,230,fp='Package_TO_SOT_SMD:SOT-23-5',mpn='TPS7A2050PDBVR')
u.connect('U324',1,{1:'USB_5V',3:'USB_5V',5:'MCU_VBUS',2:'GND',4:None})
u.cap('C326','1u 25V X7R 0805 (LDO IN)',230,255,'USB_5V',fp=c08o)
u.cap('C327','1u 25V X7R 0805 (LDO OUT, module VBUS)',310,255,'MCU_VBUS',fp=c08o)
# TI SBVS338H 6.3.7: reverse current OUT -> IN must stay below 5 % of 300 mA. After unplug the charger can pull USB_5V
# down faster than MCU_VBUS decays, so D324 carries that discharge instead of the LDO's internal path.
u.symbol('SCHOTTKY_SOT23','D324','BAT54 (U324 reverse-current bypass)',330,230,fp='Package_TO_SOT_SMD:SOT-23',mpn='BAT54,215')
u.connect('D324',1,{1:'MCU_VBUS',3:'USB_5V',2:None})
u.txt('Step 14: U323 cuts USB_5V off above 5.99 V within 100 ns (VBUS_CON rated 30 V); 20 ms delay + 3.5 ms soft start limit inrush.',10,272,1.0)
u.txt('USB_VPWR (U323 VBUS_POWER, <= 5.5 V at 30 V in) feeds the USB-sense divider; U324 gives module pad 31 5.0 V (nRF52840 VBUS abs max 5.8 V).',10,279,1.0)
# Second 10 uF on VBUS (TI SLUSDV2C recommends 2 x 10 uF + 100 nF at VBUS). Allowed now because U323's soft start, not the
# connector, charges the bulk: the source sees only C324 (1 uF) at attach.
ch.cap('C401','10u 25V X7R 1206 (VBUS, behind OVP soft start)',170,40,'USB_5V',fp=c12,mpn='GRM31CR71E106KA12L')
