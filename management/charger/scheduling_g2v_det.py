# -*- coding: utf-8 -*-
"""
Created on Fri Apr 23 14:06:45 2021

@author: egu
"""

from datetime import datetime,timedelta
import numpy as np
import pandas as pd
import time

from pyomo.environ import SolverFactory
from pyomo.core import *

def optimal_schedule_v2g(solver,arrts,leavets,stepsize,p_ch,ecap,inisoc,tarsoc,minsoc,maxsoc,costcoeff):
    """
    arrts   : arrival time                      datetime.datetime
    leavets : estimated leave time              datetime.datetime
    stepsize: size of one time step             datetime.timedelta
    p_ch    : nominal charging power     (kW)   float
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
    model.price = obj_coeffic               #Energy price series
    model.SoC_F = tarsoc                    #SoC to be achieved at the end
    
    model.p     = Var(model.T,within=NonNegativeReals,bounds=(0,model.P_CH))
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
     
if __name__ == "__main__":
        
    now=datetime(2020,5,15,8)
    dT =timedelta(minutes=15)
    P_c=11
    E  =55*3600
    ini_soc=0.2
    fin_soc=0.8
    min_soc=0.2
    max_soc=1.0
    leave  =datetime(2020,5,15,14)
    
    cost_coeff_1=pd.Series(np.array([1,1,1,0,0,0,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))
    cost_coeff_2=pd.Series(np.array([0,0,1,1,1,0,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))
    cost_coeff_3=pd.Series(np.array([0,0,0,1,1,1,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))
    
    optsolver=SolverFactory("gurobi")
    
    schedule1,soc1=optimal_schedule_v2g(optsolver,now,leave,dT,P_c,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_1)
    schedule2,soc2=optimal_schedule_v2g(optsolver,now,leave,dT,P_c,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_2)
    schedule3,soc3=optimal_schedule_v2g(optsolver,now,leave,dT,P_c,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_3)
    
    sched1=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)
    sched2=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)
    sched3=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)
    
    sched1['Pow'] =schedule1/P_c
    sched1['SoC'] =soc1
    sched1['Cost']=cost_coeff_1.reindex(schedule1.index).fillna(method='ffill')
    sched1.plot(title="Schedule1")
    
    sched2['Pow'] =schedule2/P_c
    sched2['SoC'] =soc2
    sched2['Cost']=cost_coeff_2.reindex(schedule1.index).fillna(method='ffill')
    sched2.plot(title="Schedule2")
    
    sched3['Pow'] =schedule3/P_c
    sched3['SoC'] =soc3
    sched3['Cost']=cost_coeff_3.reindex(schedule1.index).fillna(method='ffill')
    sched3.plot(title="Schedule3")
