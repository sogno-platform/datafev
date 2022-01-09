# -*- coding: utf-8 -*-
"""
Created on Sun Jan  9 13:01:43 2022

@author: egu
"""

from algorithms.scheduling.milp import minimize_charging_cost_milp
from datetime import datetime,timedelta
import numpy as np
import pandas as pd
from pyomo.environ import SolverFactory
from pyomo.core import *
import matplotlib.pyplot as plt

solver  =SolverFactory("cplex")
arrts   =datetime(2020,1,6,8,00)
leavets =datetime(2020,1,6,10,00)
stepsize=timedelta(minutes=1)
opt_hori=pd.date_range(start=arrts,end=leavets,freq=stepsize)

p_ch    =22
p_ds    =22 

ecap    =55*3600
inisoc  =0.6
tarsoc  =0.8
minsoc  =0.2
maxsoc  =1.0
crtsoc  =0.8
crttime =datetime(2020,1,6,9,00)
arbrate =0.1

v2x_lim1=0
v2x_lim2=11*3600

np.random.seed(0)
for trial in range(1,6):
    
    print("Trial",trial)
    costcoeffs=pd.Series(np.random.uniform(low=-0.1, high=0.5,size=len(opt_hori)),index=opt_hori)
    
    p_ref_v1g,s_ref_v1g=minimize_charging_cost_milp(solver,arrts,leavets,stepsize,p_ch,p_ch,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,leavets,v2x_lim1,costcoeffs,arbrate)
    p_ref_v2g,s_ref_v2g=minimize_charging_cost_milp(solver,arrts,leavets,stepsize,p_ch,p_ds,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,leavets,v2x_lim2,costcoeffs,arbrate)

    fig,axs=plt.subplots(3,1,sharex=True)
    fig.suptitle('Trial'+str(trial))
    
    axs[0].set_title("Cost coefficient of the clusters")
    costcoeffs.plot(ax=axs[0],color='b')
    axs[0].set_ylabel('Eur/kWh')
    
    axs[1].set_title("Charge schedules")
    p_ref_v1g.plot(ax=axs[1],color='r',label='V2X not allowed')
    p_ref_v2g.plot(ax=axs[1],color='g',label='V2X allowed')
    axs[1].set_ylabel('kW')
    
    axs[2].set_title("State of Charge")
    (s_ref_v1g*100).plot(ax=axs[2],color='r',label='V2X not allowed',legend=True)
    (s_ref_v2g*100).plot(ax=axs[2],color='g',label='V2X allowed',legend=True)
    axs[2].set_ylabel('%')    
      
    cost_v1g=((p_ref_v1g*stepsize.seconds/3600)*costcoeffs).sum()
    cost_v2g=((p_ref_v2g*stepsize.seconds/3600)*costcoeffs).sum()
    print("Cost reduction due to V2G:",cost_v1g-cost_v2g)
