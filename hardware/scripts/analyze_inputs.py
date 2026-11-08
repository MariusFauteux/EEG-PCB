"""Linear small-signal estimates, NOT ESD, patient safety or electrode validation."""
from pathlib import Path
import numpy as np,json,math
P=Path(__file__).resolve().parent
def response(f,cd=220e-12,zp=1e5,zn=1e5,n=1,cm=False):
    # Four nodes per channel (clamp P/N, ADC P/N) + shared reference node.
    a=np.zeros((4*n+1,4*n+1),complex);b=np.zeros(4*n+1,complex);s=2j*np.pi*f
    def branch(i,j,y):
        a[i,i]+=y
        if j is not None:a[j,j]+=y;a[i,j]-=y;a[j,i]-=y
    def source(i,r,v):a[i,i]+=1/r;b[i]+=v/r
    source(4*n,zn,1 if cm else 0)
    for k in range(n):
        p,q,x,y=range(4*k,4*k+4)
        source(p,zp+94000,1 if cm or k==0 else 0)
        branch(q,4*n,1/94000)
        for i in (p,q):branch(i,None,s*1.5e-12)
        branch(p,x,1/4700);branch(q,y,1/4700)
        for i in (x,y):branch(i,None,s*20e-12)
        branch(x,y,s*cd)
    v=np.linalg.solve(a,b)
    return [v[4*k+2]-v[4*k+3] for k in range(n)]
def db(x):return float(20*np.log10(abs(x)))
results={'assumptions':'300 K; resistors ideal; TVS 1.5 pF; ADC 20 pF/pin approximation; electrodes resistive; no electrochemical, layout or nonlinear model','noise_uV_rms_0p1_100Hz':{str(r):math.sqrt(4*1.380649e-23*300*r*99.9)*1e6 for r in [188000,197400]},'simple_rc':[],'shared_reference':[]}
for z in [0,10000,100000,1000000]:
    fc=1/(2*np.pi*(197400+2*z)*220e-12)
    results['simple_rc'].append({'each_electrode_ohm':z,'pole_Hz':fc,'gain_at_100Hz_dB':db(1/(1+1j*100/fc))})
for c in [220e-12,470e-12]:
    for f in [10,50,100]:
        v=response(f,cd=c,n=8)
        results['shared_reference'].append({'C_pF':c*1e12,'Hz':f,'driven_gain_dB':db(v[0]),'other_to_driven_dB':db(v[1]/v[0])})
results['sinc3_dB']={str(f):db((np.sin(np.pi*f/1000)/(1024*np.sin(np.pi*f/1024000)))**3) for f in [50,100,500,900,1024100]}
results['asymmetric_common_mode']=[{'Hz':f,'cm_to_diff_dB':db(response(f,zp=10000,zn=100000,cm=True)[0])} for f in [50,100]]
(P.parent/'checks'/'input_analysis.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
