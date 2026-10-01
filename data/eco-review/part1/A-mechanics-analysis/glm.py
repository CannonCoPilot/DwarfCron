import numpy as np
from scipy import stats
def fit(X, y, fam="binom", m=None, off=None, it=100):
    X=np.asarray(X,float); y=np.asarray(y,float); n,p=X.shape
    off=np.zeros(n) if off is None else np.asarray(off,float)
    b=np.zeros(p)
    if fam=="binom": m=np.asarray(m,float); b[0]=np.log((y.sum()+.5)/(m.sum()-y.sum()+.5))
    else: b[0]=np.log(y.mean()+1e-9)-off.mean()
    for _ in range(it):
        eta=X@b+off
        if fam=="binom":
            mu=1/(1+np.exp(-eta)); W=m*mu*(1-mu)+1e-12; z=eta-off+(y-m*mu)/W
        else:
            mu=np.exp(eta); W=mu+1e-12; z=eta-off+(y-mu)/W
        XtW=X.T*W
        try: bn=np.linalg.solve(XtW@X+1e-9*np.eye(p),XtW@z)
        except np.linalg.LinAlgError: break
        if np.max(abs(bn-b))<1e-9: b=bn; break
        b=bn
    eta=X@b+off
    if fam=="binom":
        mu=1/(1+np.exp(-eta)); W=m*mu*(1-mu)
        with np.errstate(divide='ignore',invalid='ignore'):
            dev=2*np.sum(np.where(y>0,y*np.log(y/(m*mu)),0)+np.where(m-y>0,(m-y)*np.log((m-y)/(m-m*mu)),0))
        pear=np.sum((y-m*mu)**2/(m*mu*(1-mu)+1e-12))
    else:
        mu=np.exp(eta); W=mu
        with np.errstate(divide='ignore',invalid='ignore'):
            dev=2*np.sum(np.where(y>0,y*np.log(y/mu),0)-(y-mu))
        pear=np.sum((y-mu)**2/(mu+1e-12))
    cov=np.linalg.pinv((X.T*W)@X); se=np.sqrt(np.diag(cov))
    return dict(b=b,se=se,dev=dev,df=n-p,pear=pear,disp=pear/max(n-p,1),aic=dev+2*p,n=n,p=p)
def report(name,r,names,scale=1.0,quasi=False):
    s=r["se"]*(np.sqrt(max(r["disp"],1)) if quasi else 1)
    out=[f"{name}: n={r['n']} dev={r['dev']:.2f} df={r['df']} AIC*={r['aic']:.1f} dispersion={r['disp']:.2f}"]
    for nm,b,se in zip(names,r["b"],s):
        if nm=="const": continue
        z=b/se; p=2*stats.norm.sf(abs(z))
        out.append(f"   {nm:14s} b={b:+.3f} SE={se:.3f}  95%CI [{b-1.96*se:+.3f},{b+1.96*se:+.3f}]  exp(b)={np.exp(b):.2f} [{np.exp(b-1.96*se):.2f},{np.exp(b+1.96*se):.2f}] p={p:.3f}")
    return "\n".join(out)
def lrt(r0,r1): d=r0["dev"]-r1["dev"]; k=r0["df"]-r1["df"]; return d,k,stats.chi2.sf(d,k)
