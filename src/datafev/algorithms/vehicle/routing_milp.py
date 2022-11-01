# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 11:46:44 2021

@author: egu
"""

from pyomo.core import *
import pyomo.kernel as pmo

def smart_routing(solver,opt_horizon,opt_step,
                  ecap,v2gall,tarsoc,minsoc,maxsoc,crtsoc,crttime,
                  arrtime,deptime,arrsoc,p_ch,p_ds,g2v_dps,v2g_dps):
    """
    This function optimizes 
    1) the allocation of an incoming EV to a cluster
    2) the charging schedule in the given parking duration
    considering cluster differentiated dynamic price signals.
    
    Inputs
    ------------------------------------------------------------------------------------------------------------------
    opt_step    : size of one time step in the optimization (seconds)   float
    opt_horizon : time step identifiers in the optimization horizon     list of integers
    ecap        : energy capacity of battery (kWs)                      float
    v2gall      : V2G allowance discharge (kWs)                         float
    tarsoc      : target final soc   (0<inisoc<1)                       float
	minsoc      : minimum soc                                           float
    maxsoc      : maximum soc                                           float
    crtsoc      : target soc at crttime                                 float
    crttime     : critical time s.t. s(srttime)> crtsoc                 int
    arrtime     : cluster differentiating arrival times                 dict of int
    deptime     : cluster differentiating departure times               dict of int
    arrsoc      : cluster differentiating arrival soc \in [0,1)         dict of float
    p_ch        : nominal charging power     (kW)                       dict of float
    p_ds        : nominal charging power     (kW)                       dict of float
    g2v_dps     : G2V dynamic price signals (Eur/kWh)                   dict of dict of float
    v2g_dps     : V2G dynamic price signals (Eur/kWh) for V2G           dict of dict of float
    ------------------------------------------------------------------------------------------------------------------
    
    Outputs
    ------------------------------------------------------------------------------------------------------------------
    p_schedule  : timeseries of charge power                            dict
    s_schedule  : timeseries of SOC reference                           dict
    target_cc   : cluster to send the EV                                string
    ------------------------------------------------------------------------------------------------------------------
    """

    conf_period={}
    for t in opt_horizon:
        if t<crttime:
            conf_period[t]=0
        else:
            conf_period[t]=1

    candidate_clusters=arrtime.keys()

    ####################Constructing the optimization model####################
    model       = ConcreteModel()
    
    model.T     = Set(initialize=opt_horizon,ordered=True)        #Time index set
    model.C     = Set(initialize=candidate_clusters,ordered=True)       #Cluster index set
    model.dt    = opt_step                  #Step size
    model.E     = ecap                      #Battery capacity in kWs

    model.SoC_F  = tarsoc                   #SoC to be achieved at the end
    model.SoC_R  = crtsoc                   #Minimim SOC must be ensured in the confidence period
    model.conf   = conf_period              #Confidence period where SOC must be larger than crtsoc
    model.V2G_ALL= v2gall                   #Maximum energy that can be discharged V2G

    model.P_CH_Max= max(p_ch.values())      #Maximum available charging power in kW
    model.P_DS_Max= max(p_ds.values())      #Maximum available discharging power in kW
    model.P_CH  = p_ch                      #Cluster dependent max charging power in kW
    model.P_DS  = p_ds                      #Cluster dependent max discharging power in kW
    model.W_G2V = g2v_dps                   #Time-variant G2V cost coefficients of clusters
    model.W_V2G = v2g_dps                   #Time-variant V2G cost coefficients of clusters
    model.t_arr = arrtime                   #Cluster dependent arrival time estimation
    model.t_dep = deptime                   #Cluster dependent departure time estimation
    model.SoC_I = arrsoc                    #Cluster dependent arrival SOCs estimation

    model.xc    = Var(model.C,within=pmo.Binary)                                        #Binary variable having 1 if v is allocated to c
    model.xp    = Var(model.T,within=pmo.Binary)                                        #Binary variable having 1/0 if v is charged/discharged at t 
    model.p     = Var(model.T,within=Reals)                                             #Net charge power at t
    model.p_pos = Var(model.T,within=NonNegativeReals)                                  #Charge power at t
    model.p_neg = Var(model.T,within=NonNegativeReals)                                  #Discharge power at t
    model.pc_pos= Var(model.C,model.T,within=NonNegativeReals)                          #Charge power at t if it is in cluster c 
    model.pc_neg= Var(model.C,model.T,within=NonNegativeReals)                          #Discharge power at t if it is in cluster c 
    model.SoC   = Var(model.T,within=NonNegativeReals,bounds=(minsoc,maxsoc))           #SOC to be achieved  at time step t
    
    #CONSTRAINTS
    def initialsoc(model):
        return model.SoC[0]==sum(model.xc[c]*model.SoC_I[c] for c in model.C)
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

    def supplyrule_end(model):
        return model.p[max(model.T)]==0.0
    model.supconst=Constraint(rule=supplyrule_end)

       
    def combinatorics0(model):       #EV can assigned to only one cluster
        return sum(model.xc[c] for c in model.C)==1
    model.comb0const=Constraint(rule=combinatorics0)
    
    def combinatorics11(model,c,t):
        if model.t_arr[c]<=t<model.t_dep[c]:
            return model.pc_neg[c,t]<=model.P_DS[c]*model.xc[c]
        else:
            return model.pc_neg[c,t]==0
    model.comb11const=Constraint(model.C,model.T,rule=combinatorics11)
    
    def combinatorics12(model,c,t):
        if model.t_arr[c] <= t < model.t_dep[c]:
            return model.pc_pos[c,t]<=model.P_CH[c]*model.xc[c]
        else:
            return model.pc_neg[c, t] == 0
    model.comb12const=Constraint(model.C,model.T,rule=combinatorics12)
       
    def combinatorics2(model,t):
        return model.p[t]==sum(model.pc_pos[c,t]-model.pc_neg[c,t] for c in model.C)
    model.comb2const=Constraint(model.T,rule=combinatorics2)
    
    def netcharging(model,t):
        return model.p[t]==model.p_pos[t]-model.p_neg[t]
    model.netchr=Constraint(model.T,rule=netcharging)
    
    def combinatorics31_pos(model,t):
        return model.p_pos[t]<=model.xp[t]*model.P_CH_Max
    model.comb31pconst=Constraint(model.T,rule=combinatorics31_pos)
    
    def combinatorics32_pos(model,t):
        return model.p_pos[t]==sum(model.pc_pos[c,t] for c in model.C)
    model.comb32pconst=Constraint(model.T,rule=combinatorics32_pos)
    
    def combinatorics31_neg(model,t):
        return model.p_neg[t]<=(1-model.xp[t])*model.P_DS_Max
    model.comb31nconst=Constraint(model.T,rule=combinatorics31_neg)
    
    def combinatorics32_neg(model,t):
        return model.p_neg[t]==sum(model.pc_neg[c,t] for c in model.C)
    model.comb32nconst=Constraint(model.T,rule=combinatorics32_neg)
      
    def v2g_limit(model):
        return sum(model.p_neg[t]*model.dt for t in model.T)<=model.V2G_ALL
    model.v2gconst   =Constraint(rule=v2g_limit)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum(model.W_G2V[c][t]*model.pc_pos[c,t]-model.W_V2G[c][t]*model.pc_neg[c,t] for c in model.C for t in opt_horizon[:-1])*opt_step/3600
    model.obj=Objective(rule=obj_rule, sense = minimize)

    #model.pprint()
    result=solver.solve(model)#,tee=True)
    #print(result)
    
    p_schedule={}
    s_schedule={}
    for t in model.T:
        p_schedule[t]=model.p[t]()
        s_schedule[t]=model.SoC[t]()
    
    for c in model.C:
        if abs(model.xc[c]()-1)<=0.01:
            target_cc=c
            
    return p_schedule,s_schedule,target_cc

if __name__ == '__main__':

    import pandas as pd
    import numpy as np
    from pyomo.environ import SolverFactory

    solver     = SolverFactory("cplex")
    opt_step   = 300        #seconds
    opt_horizon= range(13)  # [0 1 2 3 4 .. 12]  == 1 hour for opt_step=300 seconds
    ecap       = 50*3600    #kWs
    v2gall     = 10*3600    #kWs
    tarsoc     = 1.0
    minsoc     = 0.4
    maxsoc     = 1.0
    crtsoc     = tarsoc
    crttime    = 12
    arrtime    = {'C1':0  , 'C2':5   ,'C3':5}
    deptime    = {'C1':13 , 'C2':13  ,'C3':13}
    arrsoc     = {'C1':0.5, 'C2':0.49,'C3':0.49}
    p_ch       = {'C1':50 , 'C2':50  ,'C3':50}
    p_ds       = {'C1':50 , 'C2':50  ,'C3':50}

    np.random.seed(0)
    g2v_dps    = {}
    v2g_dps    = {}
    for c in ['C1','C2','C3']:
        g2v_tariff=np.random.uniform(low=0.4,high=0.8,size=12)
        g2v_dps[c]=dict(enumerate(g2v_tariff))
        v2g_dps[c]=dict(enumerate(g2v_tariff*0.9))

    dps={}
    for c in ['C1','C2','C3']:
        dps[c]=pd.DataFrame(columns=['G2V','V2G'])
        dps[c]['G2V'] = pd.Series(g2v_dps[c])
        dps[c]['V2G'] = pd.Series(v2g_dps[c])

    print("Reservation request of an EV with")
    print("Battery capacity   :",ecap/3600,"kWh")
    print("Target SOC         :",tarsoc)
    print("V2G allowance      :",v2gall/3600,"kWh")
    print()
    print("Since the available clusters are at different distances, some parameters are cluster dependent")
    print("Estimated arrival SOCs        :",arrsoc)
    print("Estimated arrival time steps  :",arrtime)
    print("Estimated departure time steps:",deptime)
    print("Dynamic price signals of the clusters:")
    print(pd.concat(dps,axis=1))
    print()

    p,s,c=smart_routing(solver, opt_horizon, opt_step, ecap, v2gall, tarsoc, minsoc, maxsoc, crtsoc, crttime, arrtime, deptime, arrsoc, p_ch, p_ds, g2v_dps, v2g_dps)
    print("Under the given price signals, the optimal decision is to go to the cluster",c)
    print()
    print("And charge with the profile")
    results=pd.DataFrame(columns=['P','SOC'],index=sorted(s.keys()))
    results['P']=pd.Series(p)
    results['SOC']=pd.Series(s)
    print(results)
    print()

