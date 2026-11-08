"""Linear small-signal estimates, NOT ESD, patient safety or electrode validation.

Step 7: input filter, resistor noise and shared-REF coupling of the passive network.
Step 12: reference distribution options compared with the same nodal model:
  passive  - REF electrode wired to JP pin 3 of every channel (Rev C4-C8)
  buffer   - REF electrode -> 94k / TPD2E2U06 / 4.7k -> OPA376 follower -> JP pin 3 (Rev C9)
  srb1     - REF electrode -> one 94k / TPD2E2U06 / 4.7k network -> ADS1299 SRB1, MISC1.SRB1 = 1
  bipolar  - every negative input on its own electrode (JP 1-2); no shared node
Writes checks/input_analysis.json; exits non-zero if a Step 12 rule fails.
Sources: ADS1299 SBAS499C (20 pF input capacitance, 300 pA bias, MISC1.SRB1, SRB1 switch resistance not
specified); TPD2E2U06 SLLSEG9C (1.5 pF, 10 nA max at 2.5 V); OPA376 SBOS406G (AOL >= 120 dB, 5.5 MHz GBW,
IB 10 pA max at 25 C, 0.8 uVpp 0.1-10 Hz, 7.5 nV/rtHz at 1 kHz, 2 fA/rtHz, 250 pF unity-gain load).
"""
from pathlib import Path
import numpy as np,json,math,sys
P=Path(__file__).resolve().parent
KT=1.380649e-23*300
R1,R2=94000,4700                      # per-leg series resistance before and after the clamp
C_TVS,C_PIN=1.5e-12,20e-12
# OPA376 follower output impedance: Ro/(1+AOL(f)). AOL from datasheet minimum 120 dB and 5.5 MHz GBW.
# Open-loop output resistance Ro is not tabulated in SBOS406G: 1 kohm is an assumed, pessimistic value.
A0,GBW,RO=1e6,5.5e6,1000.0
def z_buffer(f,r_trace=0.1):
    aol=A0/(1+1j*f*A0/GBW)
    return RO/(1+aol)+r_trace          # 0.1 ohm assumed for the REF_BUF copper to 16 header pins
R_SW=100.0                              # ADS1299 SRB1 switch resistance: not specified; assumed 100 ohm

def response(f,cd=220e-12,zp=1e5,zn=1e5,n=1,cm=False,mode='passive',zo=None):
    """Differential ADC voltage of each channel. Channel 0's positive electrode carries 1 V (or every
    electrode, cm=True). Nodes: per channel clamp P/N and ADC P/N, then REF_RAW, SRB1 pin, SRB1 clamp."""
    N=4*n+3;a=np.zeros((N,N),complex);b=np.zeros(N,complex);s=2j*np.pi*f
    R,SP,SC=4*n,4*n+1,4*n+2
    def branch(i,j,y):
        a[i,i]+=y
        if j is not None:a[j,j]+=y;a[i,j]-=y;a[j,i]-=y
    def source(i,z,v):a[i,i]+=1/z;b[i]+=v/z
    vref=1 if cm else 0
    if mode=='passive':source(R,zn,vref)
    elif mode=='buffer':source(R,zo if zo is not None else z_buffer(f),vref)
    else:a[R,R]=1
    if mode=='srb1':
        source(SC,zn+R1,vref);branch(SC,None,s*C_TVS);branch(SC,SP,1/R2);branch(SP,None,s*C_PIN)
    else:a[SP,SP]=a[SC,SC]=1
    for k in range(n):
        p,q,x,y=range(4*k,4*k+4)
        source(p,zp+R1,1 if cm or k==0 else 0)
        if mode in('passive','buffer'):branch(q,R,1/R1)
        elif mode=='bipolar':source(q,zn+R1,1 if cm else 0)
        elif mode=='srb1':branch(y,SP,1/R_SW)   # JP open: N leg hangs on INxN through 4.7k only
        for i in (p,q):branch(i,None,s*C_TVS)
        branch(p,x,1/R2);branch(q,y,1/R2)
        for i in (x,y):branch(i,None,s*C_PIN)
        branch(x,y,s*cd)
    v=np.linalg.solve(a,b)
    return [v[4*k+2]-v[4*k+3] for k in range(n)]
def db(x):return float(20*np.log10(abs(x))) if abs(x)>0 else -400.0
def coupling(f,mode,zref,n=8,cd=220e-12):
    v=response(f,cd=cd,zn=zref,n=n,mode=mode);return db(v[1]/v[0])

results={'assumptions':'300 K; resistors ideal; TVS 1.5 pF; ADC 20 pF/pin approximation; electrodes resistive; no electrochemical, layout or nonlinear model','noise_uV_rms_0p1_100Hz':{str(r):math.sqrt(4*KT*r*99.9)*1e6 for r in [188000,197400]},'simple_rc':[],'shared_reference':[]}
for z in [0,10000,100000,1000000]:
    fc=1/(2*np.pi*(197400+2*z)*220e-12)
    results['simple_rc'].append({'each_electrode_ohm':z,'pole_Hz':fc,'gain_at_100Hz_dB':db(1/(1+1j*100/fc))})
for c in [220e-12,470e-12]:
    for f in [10,50,100]:
        v=response(f,cd=c,n=8)
        results['shared_reference'].append({'C_pF':c*1e12,'Hz':f,'driven_gain_dB':db(v[0]),'other_to_driven_dB':db(v[1]/v[0])})
results['sinc3_dB']={str(f):db((np.sin(np.pi*f/1000)/(1024*np.sin(np.pi*f/1024000)))**3) for f in [50,100,500,900,1024100]}
results['asymmetric_common_mode']=[{'Hz':f,'cm_to_diff_dB':db(response(f,zp=10000,zn=100000,cm=True)[0])} for f in [50,100]]

# ---- Step 12: reference distribution options ----
opts=[]
for mode in ['passive','buffer','srb1','bipolar']:
    for zref in [10e3,100e3,1e6]:
        for n in [2,8]:
            for f in [10,50,100]:
                opts.append({'mode':mode,'Zref_ohm':zref,'channels_on_ref':n,'Hz':f,'other_to_driven_dB':coupling(f,mode,zref,n)})
results['reference_options']=opts
results['passive_no_Cdiff']=[{'Zref_ohm':z,'Hz':100,'other_to_driven_dB':coupling(100,'passive',z,8,cd=1e-18)} for z in [100e3,1e6]]
results['buffer_output_impedance_ohm']={str(f):abs(z_buffer(f)) for f in [10,50,100,1000]}
# Noise over 0.1-100 Hz. Common = identical in every referential channel; per-channel N-leg noise unchanged.
B=99.9
def vt(r):return math.sqrt(4*KT*r*B)*1e6
# OPA376 voltage noise: 7.5 nV/rtHz white with 1/f corner fitted to 0.8 uVpp (taken as 6.6 x rms) in 0.1-10 Hz.
ew=7.5e-9;rms_01_10=0.8e-6/6.6;fc=(rms_01_10**2-ew**2*9.9)/(ew**2*math.log(100))
e_op=math.sqrt(ew**2*(B+fc*math.log(1000)))*1e6
noise={'opamp_1f_corner_Hz':fc,'opamp_uV':e_op}
for zref in [10e3,100e3,1e6]:
    noise[str(int(zref))]={'passive_common_uV':vt(zref),
        'buffer_common_uV':math.sqrt(vt(zref+R1+R2)**2+e_op**2+(2e-15*(zref+R1+R2)*math.sqrt(B)*1e6)**2),
        'per_channel_N_leg_uV':vt(R1+R2)}
results['reference_noise_uV_rms_0p1_100Hz']=noise
# DC current drawn from the REF electrode (TVS 10 nA max at 2.5 V; ADC 300 pA; OPA376 10 pA at 25 C).
dc={'passive_8ch_A':8*(10e-9+300e-12),'buffer_A':10e-9+10e-12}
dc['passive_shift_100k_mV']=dc['passive_8ch_A']*1e5*1e3
dc['buffer_shift_100k_mV']=dc['buffer_A']*(1e5+R1+R2)*1e3
results['reference_dc']=dc
# Common-mode to differential with the buffer: N legs see ~0 ohm source, P legs see their electrode.
results['buffered_common_mode']=[{'Zp_ohm':zp,'Hz':f,'buffer_8ch_dB':db(response(f,zp=zp,zn=zp,n=8,cm=True,mode='buffer')[0]),
    'passive_8ch_equal_electrodes_dB':db(response(f,zp=zp,zn=zp,n=8,cm=True)[0])} for zp in [10e3,100e3,1e6] for f in [50]]
results['srb1_switch_resistance_sensitivity']=[{'R_sw_ohm':r,'dB_100k_100Hz':None} for r in [10,100,1000]]
for row in results['srb1_switch_resistance_sensitivity']:
    R_SW=row['R_sw_ohm'];row['dB_100k_100Hz']=coupling(100,'srb1',1e5)
R_SW=100.0

def get(mode,z,n,f):return next(o['other_to_driven_dB'] for o in opts if o['mode']==mode and o['Zref_ohm']==z and o['channels_on_ref']==n and o['Hz']==f)
rules=[
 ('Passive model reproduces the Step 7 figure (-37.3 dB, 8 ch, 100k, 100 Hz)',abs(get('passive',1e5,8,100)+37.3)<0.1),
 ('Buffered REF coupling <= -100 dB at 100 Hz, 8 ch, REF electrode up to 1 Mohm',max(get('buffer',z,8,100) for z in [1e4,1e5,1e6])<=-100),
 ('SRB1 route is no better than passive at 100 Hz (8 ch, 100k), so it is not adopted',get('srb1',1e5,8,100)>=get('passive',1e5,8,100)),
 ('Buffered REF adds <= 0.5 uV rms common noise (0.1-100 Hz) to a 100k REF electrode',
    math.sqrt(noise['100000']['buffer_common_uV']**2-noise['100000']['passive_common_uV']**2)<=0.5),
 ('Buffered REF converts 50 Hz common mode less than passive (8 ch, equal electrodes 10k-1M)',
    all(r['buffer_8ch_dB']<r['passive_8ch_equal_electrodes_dB'] for r in results['buffered_common_mode'])),
 ('Buffered REF draws <= 1/8 of the passive DC current from the REF electrode',dc['buffer_A']<=dc['passive_8ch_A']/8),
]
results['rules']=[{'rule':r,'pass':bool(ok)} for r,ok in rules]
(P.parent/'checks'/'input_analysis.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
for r,ok in rules:print(('PASS ' if ok else 'FAIL ')+r)
sys.exit(0 if all(ok for _,ok in rules) else 1)
