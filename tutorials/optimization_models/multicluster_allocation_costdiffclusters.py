# -*- coding: utf-8 -*-
"""
Created on Fri Nov 19 10:28:37 2021

@author: egu
"""

import pandas as pd
import numpy as np
import time

from pyomo.environ import SolverFactory
from pyomo.core import *
from datetime import datetime,timedelta
import matplotlib.pyplot as plt

from management_algorithms.multicluster.allocation_optimization import optimal_costdif_cluster

solver  =SolverFactory("cplex")
arrts   =datetime(2020,1,6,8,00)
leavets =datetime(2020,1,6,9,00)
stepsize=timedelta(minutes=5)
opt_hori=pd.date_range(start=arrts,end=leavets,freq=stepsize)

p_ch    =22
p_ds_v1g=0
p_ds_v2g=22 

ecap    =55*3600
inisoc  =0.6
tarsoc  =0.8
minsoc  =0.2
maxsoc  =1.0
crtsoc  =0.8
crttime =datetime(2020,1,6,8,50)

color_code={'CC1':'r','CC2':'b'}

np.random.seed(0)
for trial in range(1,6):
    
    print("Trial",trial)
    
    costcoeffs   ={}
    costcoeffs["CC1"]=pd.Series(np.random.uniform(low=-0.1, high=0.5,size=len(opt_hori)),index=opt_hori)
    costcoeffs["CC2"]=pd.Series(np.random.uniform(low=-0.1, high=0.5,size=len(opt_hori)),index=opt_hori)  
    
    costcoeff_df =pd.concat(costcoeffs,axis=1)
    
    st1=time.time()
    p_ref_v1g,s_ref_v1g,c_ref_v1g=optimal_costdif_cluster(solver,arrts,leavets,stepsize/5,p_ch,p_ds_v1g,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,leavets,costcoeffs)
    en1=time.time()
    print("Computation time V1G:",en1-st1)
    
    st2=time.time()
    p_ref_v2g,s_ref_v2g,c_ref_v2g=optimal_costdif_cluster(solver,arrts,leavets,stepsize/5,p_ch,p_ds_v2g,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,leavets,costcoeffs)
    en2=time.time()
    print("Computation time V2G:",en2-st2)
    
    fig,axs=plt.subplots(3,1,sharex=True)
    fig.suptitle('Trial'+str(trial))
    
    axs[0].set_title("Cost coefficient of clusters")
    costcoeff_df.reindex(p_ref_v1g.index,method='ffill').plot(ax=axs[0],color=['r','b'])
    axs[0].set_ylabel('Eur/kWh')
    
    axs[1].set_title("V1G Allocation to "+c_ref_v1g)
    p_ref_v1g.plot(ax=axs[1],color=color_code[c_ref_v1g])
    axs1_=axs[1].twinx()
    s_ref_v1g.plot(ax=axs1_,color=color_code[c_ref_v1g],linestyle='dashed')
    axs[1].set_ylabel('Charging Schedule')
    axs1_.set_ylabel('SOC Reference')
    
    axs[2].set_title("V2G Allocation to "+c_ref_v2g)
    p_ref_v2g.plot(ax=axs[2],color=color_code[c_ref_v2g])
    axs2_=axs[2].twinx()
    s_ref_v2g.plot(ax=axs2_,color=color_code[c_ref_v2g],linestyle='dashed')
    axs[2].set_ylabel('Charging Schedule')
    axs2_.set_ylabel('SOC Reference')
    
    axs[2].set_xlabel('Time')
    
    
    cost_v1g=((p_ref_v1g*stepsize.seconds/3600)*(costcoeff_df[c_ref_v1g].reindex(p_ref_v1g.index,method='ffill'))).sum()
    cost_v2g=((p_ref_v2g*stepsize.seconds/3600)*(costcoeff_df[c_ref_v2g].reindex(p_ref_v2g.index,method='ffill'))).sum()
    print("Cost reduction due to V2G:",cost_v1g-cost_v2g)
    
    print("Statistical analysis of the cost coefficients")
    stats=pd.DataFrame(columns=['CC1','CC2'])
    stats.loc['max']=costcoeff_df.max()
    stats.loc['min']=costcoeff_df.min()
    stats.loc['mean']=costcoeff_df.mean()
    stats.loc['std'] =costcoeff_df.std()
    print(stats)  
    print()