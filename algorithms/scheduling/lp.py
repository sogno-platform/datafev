# -*- coding: utf-8 -*-
"""
Created on Fri Apr 23 11:30:19 2021

@author: egu
"""

from datetime import datetime,timedelta
import numpy as np
import pandas as pd
import time

from pyomo.environ import SolverFactory
from pyomo.core import *


def minimize_charging_cost_lp(solver,arrts,leavets,stepsize,p_ch,p_ds,ecap,inisoc,tarsoc,minsoc,maxsoc,costcoeff):
    """
    This function minimizes the charging cost for the given cost coefficients
    by solving a linear optimization problem. The losses in power transfer 
    are neglected.
    
    arrts   : arrival time                      datetime.datetime
    leavets : estimated leave time              datetime.datetime
    stepsize: size of one time step             datetime.timedelta
    p_ch    : nominal charging power     (kW)   float
    p_ds    : nominal charging power     (kW)   float
    ecap    : energy capacity of battery (kWs)  float   
    inisoc  : initial soc (0<inisoc<1)          float
    tarsoc  : target final soc   (0<inisoc<1)   float
    costcoef: price signal (Eur/MWh)            pandas series
    """  
        
    duration=pd.date_range(start=arrts,end=leavets,freq=stepsize)    #Date range for the whole stay duration in the charging park
    priceseries=costcoeff.reindex(duration)
    priceseries=priceseries.fillna(method='ffill')
   
    opt_horizon=range(len(duration))
    obj_coeffic=pd.Series(priceseries.values,index=opt_horizon)
    
    ####################Constructing the optimization model####################
    model       = ConcreteModel()
    
    model.T     = Set(initialize=opt_horizon,ordered=True)  #Time index set
    
    model.dt    = stepsize.seconds          #Step size
    model.E     = ecap                      #Battery capacity in kWs
    model.P_CH  = p_ch                      #Maximum charging power in kW
    model.P_DS  = p_ds                      #Maximum discharging power in kW
    model.price = obj_coeffic               #Energy price series
    model.SoC_F = tarsoc                    #SoC to be achieved at the end
    
    model.p     = Var(model.T,bounds=(-model.P_DS,model.P_CH))
    model.SoC   = Var(model.T,within=NonNegativeReals,bounds=(minsoc,maxsoc))
    
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
    
    def supplyrule(model):
        return model.p[max(model.T)]==0.0
    model.supconst=Constraint(rule=supplyrule)
       
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum(model.p[t]*model.price[t] for t in model.T)
    model.obj=Objective(rule=obj_rule, sense = minimize)
    
    solver.solve(model)
    
    sch_dict={}
    soc_dict={}
    
    for t in model.T:
        sch_dict[duration[t]]=model.p[t]()
        soc_dict[duration[t]]=model.SoC[t]()
    
    schedule=pd.Series(sch_dict)
    soc     =pd.Series(soc_dict)

    return schedule,soc
     