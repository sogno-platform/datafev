# -*- coding: utf-8 -*-
"""
Created on Fri Nov 19 15:24:35 2021

@author: egu
"""

from pyomo.environ import SolverFactory
from pyomo.core import *
import numpy as np
import pandas as pd
import pyomo.kernel as pmo
from itertools import product

def minimize_deviation_from_schedules(parkdata,powerlimits,connections,solver):

    ###########################################################################
    ################################Data formatting############################
    clusters =parkdata['clusters']
    horizon  =parkdata['opt_horizon']
    horizonC =parkdata['con_horizon']
    deltaT   =parkdata['opt_step']
    
    P_CC_pos_max  =powerlimits['P_CC_pos_max']
    P_CC_neg_max  =powerlimits['P_CC_neg_max']
    P_CS_pos_max  =powerlimits['P_CS_pos_max']
    P_CS_neg_max  =powerlimits['P_CS_neg_max']
    P_IC_unb_max  =powerlimits['P_IC_unb_max'] if 'P_IC_unb_max' in powerlimits.keys() else None
     
    P_EV_pos_max  =connections['P_EV_pos_max']
    P_EV_neg_max  =connections['P_EV_neg_max']
    eta_ch        =connections['charge_eff']
    eta_ds        =connections['discharge_eff']
    battery_cap   =connections['battery_cap']
    tarsoc        =connections['target_soc']
    departure_time=connections['departure_time']
    inisoc        =connections['initial_soc']
    minsoc        =connections['minimum_soc']
    maxsoc        =connections['maximum_soc']
    location      =connections['location']
    ev_connected_here={} 
    for v in location.keys():
        for c in clusters:
            if c==location[v][0]:
                ev_connected_here[v,c]=1
            else:
                ev_connected_here[v,c]=0
    ###########################################################################    
     
    ###########################################################################
    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.C =Set(initialize=clusters)               #Index set for the clusters 
    model.V =Set(initialize=list(location.keys()))  #Index set for the EVs

    #Time parameters
    model.deltaSec=deltaT.seconds #Time discretization (Size of one time step in seconds)   
    model.T       =Set(initialize=horizon[:-1],ordered=True) #Index set for the time steps in opzimization horizon
    model.Tp      =Set(initialize=horizon,ordered=True)      #Index set for the time steps in opzimization horizon for SoC

    #Power capability parameters
    model.P_EV_pos=P_EV_pos_max      #Maximum charging power to EV battery
    model.P_EV_neg=P_EV_neg_max      #Maximum discharging power from EV battery 
    model.P_CC_pos=P_CC_pos_max      #Maximum power that can be imported by a cluster
    model.P_CC_neg=P_CC_neg_max      #Maximum power that can be exported by a cluster
    model.P_CS_pos=P_CS_pos_max      #Maximum power that can be imported by the system
    model.P_CS_neg=P_CS_neg_max      #Maximum power that can be exported by the system
    model.P_IC_unb=P_IC_unb_max      #Maximum inter-cluster unbalance
    
    #Charging efficiency 
    model.eff_ch  =eta_ch            #Charging efficiency
    model.eff_ds  =eta_ds            #Discharging efficiency   
        
    #Reference SOC parameters
    model.s_ini    =inisoc   #SoC when the optimization starts
    model.s_ref    =tarsoc   #Target SOC
    model.s_min    =minsoc   #Minimum SOC
    model.s_max    =maxsoc   #Maximum SOC
        
    #EV Variables
    model.p_ev    =Var(model.V,model.T,within=Reals)              #Net charging power of EV indexed by
    model.p_ev_pos=Var(model.V,model.T,within=NonNegativeReals)   #Charging power of EV
    model.p_ev_neg=Var(model.V,model.T,within=NonNegativeReals)   #Disharging power of EV
    model.x_ev    =Var(model.V,model.T,within=pmo.Binary)         #Whether EV is charging
    model.s       =Var(model.V,model.Tp,within=NonNegativeReals)  #EV SOC variable
    
    #System variables
    model.p_cc  =Var(model.C,model.T,within=Reals)     #Power flows into the cluster c
    model.p_cs  =Var(model.T,within=Reals)             #Total system power  
                           
    #CONSTRAINTS
    def initialsoc(model,v):
        return model.s[v,0]==model.s_ini[v]
    model.inisoc=Constraint(model.V,rule=initialsoc)
    
    def minimumsoc(model,v,t):
        return model.s_min[v]<=model.s[v,t]
    model.minsoc_con=Constraint(model.V,model.T,rule=minimumsoc)

    def maximumsoc(model,v,t):
        return model.s_max[v]>=model.s[v,t]
    model.maxsoc_con=Constraint(model.V,model.T,rule=maximumsoc)    
    
    def storageConservation(model,v,t):    #SOC of EV batteries will change with respect to the charged power and battery energy capacity
        return model.s[v,t+1]==(model.s[v,t] + (model.p_ev_pos[v,t]-model.p_ev_neg[v,t])/battery_cap[v] *model.deltaSec)
    model.socconst=Constraint(model.V,model.T,rule=storageConservation)
    
    def chargepowerlimit(model,v,t):                    #Net power into EV decoupled into positive and negative parts            
        return model.p_ev[v,t]==model.p_ev_pos[v,t]-model.p_ev_neg[v,t]
    model.chrpowconst=Constraint(model.V,model.T,rule=chargepowerlimit)
        
    def combinatorics_ch(model,v,t):                    #EV indexed by v can charge only when x[v,t]==1 at t
        if t>=departure_time[v]:
            return model.p_ev_pos[v,t]==0
        else:
            return model.p_ev_pos[v,t]<=model.x_ev[v,t]*model.P_EV_pos[v]
    model.combconst1 =Constraint(model.V,model.T,rule=combinatorics_ch)
    
    def combinatorics_ds(model,v,t):                    #EV indexed by v can discharge only when x[v,t]==0 at t
        if t>=departure_time[v]:
            return model.p_ev_neg[v,t]==0
        else:        
            return model.p_ev_neg[v,t]<=(1-model.x_ev[v,t])*model.P_EV_neg[v]
    model.combconst2 =Constraint(model.V,model.T,rule=combinatorics_ds)    
            
    def ccpower(model,c,t):                             #Mapping EV powers to CC power
        return model.p_cc[c,t]==sum(ev_connected_here[v,c]*(model.p_ev_pos[v,t]/model.eff_ch[v]-model.p_ev_neg[v,t]*model.eff_ds[v]) for v in model.V)
    model.ccpowtotal=Constraint(model.C,model.T,rule=ccpower)
        
    def cspower(model,t):                               #Mapping CC powers to CS power
        return model.p_cs[t]==sum(model.p_cc[c,t] for c in model.C)
    model.stapowtotal=Constraint(model.T,rule=cspower)

    def cluster_pos_limit_dynamic(model,c,t):           #Import constraint for CC
        return model.p_cc[c,t]<=model.P_CC_pos[c][t]
    model.ccpowcap_pos =Constraint(model.C,model.T,rule=cluster_pos_limit_dynamic)
    
    def cluster_neg_limit_dynamic(model,c,t):           #Export constraint for CC
        return model.p_cc[c,t]>=-model.P_CC_neg[c][t]
    model.ccpowcap_neg =Constraint(model.C,model.T,rule=cluster_neg_limit_dynamic)
    
    def cluster_unbalance_limit(model,c1,c2,t):
        return model.p_cc[c1,t]<=model.p_cc[c2,t]+model.P_IC_unb[c1,c2][t]
    if model.P_IC_unb!=None:  
        model.inter_clust  =Constraint(model.C,model.C,model.T,rule=cluster_unbalance_limit)
        
    def station_pos_limit_dynamic(model,t):             #Import constraint for CS
        return model.p_cs[t]<=model.P_CS_pos[t]
    model.cspowcap_pos=Constraint(model.T,rule=station_pos_limit_dynamic)
    
    def station_neg_limit_dynamic(model,t):             #Export constraint for CS
        return model.p_cs[t]>=-model.P_CS_neg[t]
    model.cspowcap_neg=Constraint(model.T,rule=station_neg_limit_dynamic)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum((model.s_ref[v]-model.s[v,max(horizon)])*
                   (model.s_ref[v]-model.s[v,max(horizon)]) 
                   for v in model.V)
    model.obj=Objective(rule=obj_rule, sense = minimize)
    
    ###########################################################################         
     
    ###########################################################################
    ######################Solving the optimization model ######################            
    #start=time.time()
    #end=time.time()
    #print("Solution in",end-start)
    result=solver.solve(model)
    #print(result)
    ###########################################################################
    
    ###########################################################################
    ################################Saving the results#########################      
    p_ref={}
    p_ref_pos={}
    p_ref_neg={}
    s_ref={}
    for v in model.V:
        c,n=location[v]
        p_ref[c,n]={}
        p_ref_pos[c,n]={}
        p_ref_neg[c,n]={}
        s_ref[c,n]={}
        for t in horizonC:
            if t<max(horizon): 
                p_ref[c,n][t]=model.p_ev[v,t]()
                p_ref_neg[c,n][t]=model.p_ev_neg[v,t]()
                p_ref_pos[c,n][t]=model.p_ev_pos[v,t]()
            s_ref[c,n][t]=model.s[v,t]()
            
    return p_ref,s_ref


