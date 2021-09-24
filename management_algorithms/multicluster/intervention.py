# -*- coding: utf-8 -*-
"""
Created on Mon Jul 19 07:34:46 2021

@author: egu
"""

from pyomo.environ import SolverFactory
from pyomo.core import *
import numpy as np
import pandas as pd
from itertools import product


def short_term_rescheduling(parkdata,connections,solver):

    ###########################################################################
    ################################Data formatting############################
    clusters =parkdata['clusters']
    horizon  =parkdata['opt_horizon']
    deltaT   =parkdata['opt_step']        
    cun_cap  =parkdata['chrunit_cap']
    cls_cap  =parkdata['cluster_cap']
    sta_cap  =parkdata['station_cap']
            
    battery_cap   =connections['battery_cap']
    refsoc        =connections['reference_soc']
    departure_time=connections['departure_time']
    inisoc        =connections['initial_soc']
    dessoc        =connections['desired_soc']
    location      =connections['location']
    ev_connected_here={} 
    for a in location.keys():
        for c in clusters:
            if c==location[a][0]:
                ev_connected_here[a,c]=1
            else:
                ev_connected_here[a,c]=0
    ###########################################################################    
     
    ###########################################################################
    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.C =Set(initialize=clusters)  #Index set for the clusters 
    model.A =Set(initialize=list(location.keys()))          #Index set for the EVs

    #Time parameters
    model.deltaSec=deltaT.seconds #Time discretization (Size of one time step in seconds)   
    model.T       =Set(initialize=horizon[:-1],ordered=True) #Index set for the time steps in opzimization horizon
    model.Tp      =Set(initialize=horizon,ordered=True)      #Index set for the time steps in opzimization horizon for SoC

    #Power capability parameters
    model.P_CU  =cun_cap        #Maximum charging power to EV battery
    model.P_CC  =cls_cap        #Maximum cluster power
    model.P_CS  =sta_cap        #Maximum station power
        
    #Reference parameters
    model.iniSoC   =inisoc   #SoC when the optimization starts
    model.desSoC   =dessoc   #Desired SOC of EVs
    model.refSoC   =refsoc   #Refernce SOC trajectory
        
    #Variables
    model.p_ev  =Var(model.A,model.T,within=NonNegativeReals)                   #Charging power to the car a
    model.p_cc  =Var(model.C,model.T,within=NonNegativeReals)                   #Power flows into the cluster c
    model.p_cs  =Var(model.T,within=NonNegativeReals)                           #Total system power  
    model.SoC   =Var(model.A,model.Tp,bounds=(0,1)) 
    model.dev   =Var(model.A,model.Tp,within=Reals)
                           
    #CONSTRAINTS
    def storageConservation(model,a,t):    #SOC of EV batteries will change with respect to the charged power and battery energy capacity
        if t==min(horizon):
            return model.SoC[a,t]==model.iniSoC[a]
        else:
            return model.SoC[a,t]==(model.SoC[a,t - deltaT] + model.p_ev[a,t - deltaT]/battery_cap[a] *model.deltaSec)
    model.socconst=Constraint(model.A,model.Tp,rule=storageConservation)
    
    def chargepowerlimit(model,a,t):   #Cars can only be charged until the departure
        if t<departure_time[a]:
            return model.p_ev[a,t]<=model.P_CU[location[a][0]][location[a][1]]
        else:
            return model.p_ev[a,t]==0
    model.carpowconst=Constraint(model.A,model.T,rule=chargepowerlimit)
            
    def ccpower(model,c,t):          #Constraint for arm power: Summation of the powers charging cells of an arm
        return model.p_cc[c,t]==sum(ev_connected_here[a,c]*model.p_ev[a,t] for a in model.A)
    model.ccpowtotal=Constraint(model.C,model.T,rule=ccpower)
    
    def cluster_undersizing(model,c,t):  #Constraint for arm power: Summation of the powers charging cells of a cluster
        return model.p_cc[c,t]<=model.P_CC[c]
    model.ccpowcap =Constraint(model.C,model.T,rule=cluster_undersizing)
    
    def cspower(model,t):              #Constraint for total power to CS
        return model.p_cs[t]==sum(model.p_cc[c,t] for c in model.C)
    model.stapowtotal=Constraint(model.T,rule=cspower)
    
    def station_undersizing(model,t):
        return model.p_cs[t]<=model.P_CS
    model.cspowcap=Constraint(model.T,rule=station_undersizing)
    
    def reftrack(model,a,t):
        if t<departure_time[a]: 
            return model.dev[a,t]==model.refSoC[a][t]-model.SoC[a,t]
        else:
            return model.dev[a,t]==model.desSoC[a]-model.SoC[a,t]
    model.refcon =Constraint(model.A,model.Tp,rule=reftrack)
      
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        #return sum(model.dev[a,t]*model.dev[a,t] for a,t in product(model.A,model.T))
        return sum(model.dev[a,max(horizon)]*model.dev[a,max(horizon)] for a in model.A)
    model.obj=Objective(rule=obj_rule, sense = minimize)
    
    ###########################################################################         
     
    ###########################################################################
    ######################Solving the optimization model ######################            
    #start=time.time()
    solver.solve(model)
    #end=time.time()
    #print("Solution in",end-start)
    ###########################################################################
    
    ###########################################################################
    ################################Saving the results#########################      
    opt_ref={}
    for a in model.A:
        c,n=location[a]
        opt_ref[c,n]=model.p_ev[a,min(horizon)]()
            
    return opt_ref