# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 11:46:44 2021

@author: egu
"""

from datetime import datetime,timedelta
import numpy as np
import pandas as pd
import time

from pyomo.environ import SolverFactory
from pyomo.core import *
import pyomo.kernel as pmo


def optimal_costdif_cluster(solver,arrts,leavets,stepsize,p_ch,p_ds,ecap,inisoc,tarsoc,minsoc,maxsoc,crtsoc,crttime,v2g_max,costcoeffs):
    """
    This function optimizes 
    1) the allocation of an incoming EV to a cluster
    2) the charging schedule in the given parking duration
    considering cluster differentiated pricing.
    
    Inputs
    ---------------------------------------------------------------------------
    arrts    : arrival time                             datetime.datetime
    leavets  : estimated leave time                     datetime.datetime
    stepsize : size of one time step                    datetime.timedelta
    p_ch     : nominal charging power     (kW)          float
    p_ds     : nominal charging power     (kW)          float
    ecap     : energy capacity of battery (kWs)         float   
    inisoc   : initial soc (0<inisoc<1)                 float
    tarsoc   : target final soc   (0<inisoc<1)          float
    crtsoc   : target soc at crttime                    float
    crttime  : critical time s.t. s(srttime)> crtsoc    datetime.datetime
    v2g_max  : maximum allowed V2G discharge (kWs)      float
    costcoefs: price signals (Eur/MWh)                  dictionary of pandas series
    ---------------------------------------------------------------------------
    
    Outputs
    ---------------------------------------------------------------------------
    schedule : timeseries of charge power        pandas series
    soc      : timeseries of SOC reference       pandas series
    target_cc: cluster to send the EV            string
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
            
    candidate_clusters=costcoeffs.keys()
    coefficients        ={}      
    for cc in candidate_clusters:
        cc_coef=costcoeffs[cc].reindex(duration)
        cc_coef=cc_coef.fillna(method='ffill')
        coefficients[cc]=cc_coef.values  
            
        
    ####################Constructing the optimization model####################
    model       = ConcreteModel()
    
    model.T     = Set(initialize=opt_horizon,ordered=True)              #Time index set
    model.C     = Set(initialize=candidate_clusters,ordered=True)       #Cluster index set    
    
    model.dt    = stepsize.seconds          #Step size
    model.E     = ecap                      #Battery capacity in kWs
    model.P_CH  = p_ch                      #Maximum charging power in kW
    model.P_DS  = p_ds                      #Maximum discharging power in kW
    model.W     = coefficients              #Time-variant cost coefficients of clusters
    model.SoC_F = tarsoc                    #SoC to be achieved at the end
    model.conf  = conf_period               #Confidence period where SOC must be larger than crtsoc
    model.SoC_R = crtsoc                    #Minimim SOC must be ensured in the confidence period  
    model.E_neg_max=v2g_max                 #Maximum energy that can be discharged V2G 
         
    model.xc    = Var(model.C,within=pmo.Binary)                                        #Binary variable having 1 if v is allocated to c
    model.xp    = Var(model.T,within=pmo.Binary)                                        #Binary variable having 1/0 if v is charged/discharged at t 
    model.p     = Var(model.T,within=Reals)                                             #Net charge power at t
    model.p_pos = Var(model.T,within=NonNegativeReals)                                  #Charge power at t
    model.p_neg = Var(model.T,within=NonNegativeReals)                                  #Discharge power at t
    model.pc    = Var(model.C,model.T,within=Reals,bounds=(-model.P_DS,model.P_CH))     #Net charge power at t if it is in cluster c 
    model.SoC   = Var(model.T,within=NonNegativeReals,bounds=(minsoc,maxsoc))           #SOC to be achieved  at time step t
    
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
       
    def combinatorics0(model):       #EV can assigned to only one cluster
        return sum(model.xc[c] for c in model.C)==1
    model.comb0const=Constraint(rule=combinatorics0)
    
    def combinatorics11(model,c,t):  
        return -model.P_DS*model.xc[c]<=model.pc[c,t]
    model.comb11const=Constraint(model.C,model.T,rule=combinatorics11)
    
    def combinatorics12(model,c,t):
        return model.pc[c,t]<=model.P_CH*model.xc[c]
    model.comb12const=Constraint(model.C,model.T,rule=combinatorics12)
       
    def combinatorics2(model,t):
        return model.p[t]==sum(model.pc[c,t] for c in model.C)
    model.comb2const=Constraint(model.T,rule=combinatorics2)
    
    def netcharging(model,t):
        return model.p[t]==model.p_pos[t]-model.p_neg[t]
    model.netchr=Constraint(model.T,rule=netcharging)
    
    def combinatorics3_pos(model,t):
        return model.p_pos[t]<=model.xp[t]*model.P_CH
    model.comb3pconst=Constraint(model.T,rule=combinatorics3_pos)
    
    def combinatorics3_neg(model,t):
        return model.p_neg[t]<=(1-model.xp[t])*model.P_DS
    model.comb3nconst=Constraint(model.T,rule=combinatorics3_neg)
    
    def v2g_limit(model):
        return sum(model.p_neg[t]*model.dt for t in model.T)<=model.E_neg_max
    model.v2gconst   =Constraint(rule=v2g_limit)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum(model.W[c][t]*model.pc[c,t] for c in model.C for t in model.T)
    model.obj=Objective(rule=obj_rule, sense = minimize)

    #model.obj.display()
    #model.pprint()
    solver.solve(model)
    
    sch_dict={}
    soc_dict={}    
    for t in model.T:
        sch_dict[duration[t]]=model.p[t]()
        soc_dict[duration[t]]=model.SoC[t]()    
    schedule=pd.Series(sch_dict)
    soc     =pd.Series(soc_dict)
    
    #model.x.pprint()
    for c in model.C:
        if model.xc[c]()==1:
            target_cc=c
            
    return schedule,soc,target_cc