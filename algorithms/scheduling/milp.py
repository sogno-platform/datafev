# -*- coding: utf-8 -*-
"""
Created on Sat Jan  8 15:33:40 2022

@author: egu
"""

#TODO:  Implement mixed integer program for charging cost minimization
#       with consideration of power conversion losses 

from datetime import datetime,timedelta
import numpy as np
import pandas as pd

from pyomo.environ import SolverFactory
from pyomo.core import *
import pyomo.kernel as pmo


def minimize_charging_cost_milp(solver,arrts,leavets,stepsize,p_ch,p_ds,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,crttime,v2x_max,costcoeffs,arbrate):
    """
    This function minimizes the charging cost for the given cost coefficients
    by solving a mixed integer linear optimization problem. The losses 
    in power transfer are considered.
    
    Inputs
    ---------------------------------------------------------------------------
    arrts    : arrival time                              datetime.datetime
    leavets  : estimated leave time                      datetime.datetime
    stepsize : size of one time step                     datetime.timedelta
    p_ch     : nominal charging power     (kW)           float
    p_ds     : nominal charging power     (kW)           float
    ecap     : energy capacity of battery (kWs)          float   
    inisoc   : initial soc (0<inisoc<1)                  float
    tarsoc   : target final soc   (0<inisoc<1)           float
    crtsoc   : target soc at crttime                     float
    crttime  : critical time s.t. s(srttime)> crtsoc     datetime.datetime
    v2x_max  : maximum allowed V2G discharge (kWs)       float
    costcoefs: price signals (Eur/MWh)                   pandas series
    arbrate  : arbitrage rate (0<arbrate<1)              float
    ---------------------------------------------------------------------------
    
    Outputs
    ---------------------------------------------------------------------------
    schedule : timeseries of charge power        pandas series
    soc      : timeseries of SOC reference       pandas series
    ---------------------------------------------------------------------------
    """  
        
    duration=pd.date_range(start=arrts,end=leavets,freq=stepsize)    #Date range for the whole stay duration in the charging park
    opt_horizon=range(len(duration))
    
    conf_period={}
    for t in opt_horizon:
        if duration[t]<crttime:
            conf_period[t]=0
        else:
            conf_period[t]=1
            
    coef         =costcoeffs.reindex(duration)
    coef         =coef.fillna(method='ffill')
    coefficients =coef.values
                    
    ####################Constructing the optimization model####################
    model       = ConcreteModel()
    
    model.T        = Set(initialize=opt_horizon,ordered=True)   #Time index set    
    model.dt       = stepsize.seconds                           #Step size
    model.E        = ecap                                       #Battery capacity in kWs
    model.P_CH     = p_ch                                       #Maximum charging power in kW
    model.P_DS     = p_ds                                       #Maximum discharging power in kW
    model.W        = coefficients                               #Time-variant cost coefficient
    model.SoC_F    = tarsoc                                     #SoC to be achieved at the end
    model.conf     = conf_period                                #Confidence period where SOC must be larger than crtsoc
    model.SoC_R    = crtsoc                                     #Minimim SOC must be ensured in the confidence period  
    model.E_v2x_max= v2x_max                                    #Maximum energy that can be discharged V2X
    model.a        = arbrate                                    #Arbitrage coefficient  
         
    model.xp       = Var(model.T,within=pmo.Binary)                                        #Binary variable having 1/0 if v is charged/discharged at t 
    model.p        = Var(model.T,within=Reals)                                             #Net charge power at t
    model.p_pos    = Var(model.T,within=NonNegativeReals)                                  #Charge power at t
    model.p_neg    = Var(model.T,within=NonNegativeReals)                                  #Discharge power at t
    model.SoC      = Var(model.T,within=NonNegativeReals,bounds=(minsoc,maxsoc))           #SOC to be achieved  at time step t
    
    #CONSTRAINTS
    def initialsoc(model):
        return model.SoC[0]==inisoc
    model.inisoc=Constraint(rule=initialsoc)
            
    def storageConservation(model,t):#SOC of EV batteries will change with respect to the charged power and battery energy capacity
        if t<max(model.T):
            return model.SoC[t+1]==(model.SoC[t] + model.p[t]*model.dt/model.E)
        else:
            return model.SoC[t] ==model.SoC_F
    model.socconst=Constraint(model.T,rule=storageConservation)
    
    def socconfidence(model,t):
        return model.SoC[t]>=model.SoC_R*model.conf[t]
    model.socconfi=Constraint(model.T,rule=socconfidence)

    def supplyrule(model):
        return model.p[max(model.T)]==0.0
    model.supconst=Constraint(rule=supplyrule)
                  
    def netcharging(model,t):
        return model.p[t]==model.p_pos[t]-model.p_neg[t]
    model.netchr=Constraint(model.T,rule=netcharging)
    
    def combinatorics31_pos(model,t):
        return model.p_pos[t]<=model.xp[t]*model.P_CH
    model.comb31pconst=Constraint(model.T,rule=combinatorics31_pos)
        
    def combinatorics31_neg(model,t):
        return model.p_neg[t]<=(1-model.xp[t])*model.P_DS
    model.comb31nconst=Constraint(model.T,rule=combinatorics31_neg)
      
    def v2g_limit(model):
        return sum(model.p_neg[t]*model.dt for t in model.T)<=model.E_v2x_max
    model.v2gconst   =Constraint(rule=v2g_limit)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum((1+model.a)*model.W[t]*model.p_pos[t]-(1-model.a)*model.W[t]*model.p_neg[t] for t in model.T)
    model.obj=Objective(rule=obj_rule, sense = minimize)

    #model.obj.display()
    #model.pprint()
    result=solver.solve(model)
    
    sch_dict={}
    soc_dict={}    
    for t in model.T:
        sch_dict[duration[t]]=model.p[t]()
        soc_dict[duration[t]]=model.SoC[t]()    
    schedule=pd.Series(sch_dict)
    soc     =pd.Series(soc_dict)
    
    return schedule,soc