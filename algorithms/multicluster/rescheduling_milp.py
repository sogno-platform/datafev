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


def reschedule(solver,opt_step,opt_horizon,powerlimits,evdata,clusters,rho_y,rho_eps):
    """
    This function reschedules the charging operations of all clusters in a multicluster system by considering
    1) upper-lower limits of aggregate power consumption of the multi-cluster system
    2) upper-lower limits of aggregate power consumption of individual clusters
    3) inter-cluster unbalances between aggregate power consumption of clusters
    4) pre-defined reference schedules of the individual EVs in the system.
    This is run typically when some events require deviations from previously determined schedules.

    Inputs
    ------------------------------------------------------------------------------------------------------------------
    solver      : optimization solver                                                   pyomo SolverFactory object
    opt_step    : size of one time step in the optimization (seconds)                   float
    opt_horizon : time step identifiers in the optimization horizon                     list of integers
    powerlimits : power consumption limits                                              dict of dict
    evdata      : data of connected EVs                                                 dict of dict
    clusters    : clusters in the multi-cluster system                                  list
    rho_y       : penalty factors for deviation of reference schedules                  dict of float
    rho_eps     : penalty factors for violation of clusters' upper-lower soft limits    dict of float
    ------------------------------------------------------------------------------------------------------------------

    Outputs
    ------------------------------------------------------------------------------------------------------------------
    p_schedule  : timeseries of new charging schedule                           dict
    s_schedule  : timeseries of new reference SOC trajectory                    dict
    ------------------------------------------------------------------------------------------------------------------
    """


    P_CC_up_lim   =powerlimits['P_CC_up_lim'] if 'P_CC_up_lim' in powerlimits.keys() else None
    P_CC_low_lim  =powerlimits['P_CC_low_lim'] if 'P_CC_lim_lim' in powerlimits.keys() else None
    P_CC_vio_lim  =powerlimits['P_CC_vio_lim'] if 'P_CC_vio_lim' in powerlimits.keys() else None
    P_IC_unb_max  =powerlimits['P_IC_unb_max'] if 'P_IC_unb_max' in powerlimits.keys() else None
    P_CS_up_lim   =powerlimits['P_CS_up_lim']
    P_CS_low_lim  =powerlimits['P_CS_low_lim']

    P_EV_pos_max  =evdata['P_EV_pos_max']
    P_EV_neg_max  =evdata['P_EV_neg_max']
    eta_ch        =evdata['charge_eff']
    eta_ds        =evdata['discharge_eff']
    battery_cap   =evdata['battery_cap']
    tarsoc        =evdata['target_soc']
    departure_time=evdata['departure_time']
    inisoc        =evdata['initial_soc']
    minsoc        =evdata['minimum_soc']
    maxsoc        =evdata['maximum_soc']
    location      =evdata['location']
    ev_connected_here={}
    rho_y_={}
    for v in location.keys():
        for c in clusters:
            if c==location[v][0]:
                ev_connected_here[v,c]=1
                rho_y_[v]=rho_y[c]
            else:
                ev_connected_here[v,c]=0
    ###########################################################################    
     
    ###########################################################################
    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.C = Set(initialize=clusters)                              #Index set for the clusters
    model.V = Set(initialize=list(evdata['battery_cap'].keys()))    #Index set for the EVs

    #Time parameters
    model.deltaSec=opt_step                                         #Time discretization (Size of one time step in seconds)
    model.T       =Set(initialize=opt_horizon[:-1],ordered=True)    #Index set for the time steps in opzimization horizon
    model.Tp      =Set(initialize=opt_horizon,ordered=True)         #Index set for the time steps in opzimization horizon for SoC

    #Power capability parameters
    model.P_EV_pos=P_EV_pos_max      #Maximum charging power to EV battery
    model.P_EV_neg=P_EV_neg_max      #Maximum discharging power from EV battery 
    model.P_CC_up =P_CC_up_lim       #Upper limit of the power that can be consumed by a cluster
    model.P_CC_low=P_CC_low_lim      #Lower limit of the power that can be consumed by a cluster
    model.P_CC_vio=P_CC_vio_lim      #Cluster upper-lower limit violation tolerance
    model.P_IC_unb=P_IC_unb_max      #Maximum inter-cluster unbalance
    model.P_CS_up =P_CS_up_lim       #Upper limit of the power that can be consumed by the multicluster system
    model.P_CS_low=P_CS_low_lim      #Lower limit of the power that can be consumed by the multicluster system
    
    #Charging efficiency 
    model.eff_ch  =eta_ch            #Charging efficiency
    model.eff_ds  =eta_ds            #Discharging efficiency
    model.E = evdata['battery_cap']  # Battery capacities
        
    #Reference SOC parameters
    model.s_ini    =inisoc   #SoC when the optimization starts
    model.s_tar    =tarsoc   #Target SOC
    model.s_min    =minsoc   #Minimum SOC
    model.s_max    =maxsoc   #Maximum SOC
        
    #EV Variables
    model.p_ev    =Var(model.V,model.T,within=Reals)                #Net charging power of EV indexed by
    model.p_ev_pos=Var(model.V,model.T,within=NonNegativeReals)     #Charging power of EV
    model.p_ev_neg=Var(model.V,model.T,within=NonNegativeReals)     #Disharging power of EV
    model.x_ev    =Var(model.V,model.T,within=pmo.Binary)           #Whether EV is charging
    model.s       =Var(model.V,model.Tp,within=NonNegativeReals)    #EV SOC variable
    
    #System variables
    model.p_cc  =Var(model.C,model.T,within=Reals)                  #Power flows into the cluster c
    model.p_cs  =Var(model.T,within=Reals)             #Total system power

    #Penalty parameters
    model.rho_y    =rho_y_
    model.rho_eps  =rho_eps

    # Deviation
    model.eps   =Var(model.C,within=NonNegativeReals)               #Deviation from aggregate conspumtion limit
    model.y     =Var(model.V,within=NonNegativeReals)               #Deviation from individual schedules

    #model.eps.pprint()
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

    def cluster_limit_violation(model,c):
        return model.eps[c]<=model.P_CC_vio[c]
    model.viol_clust   =Constraint(model.C,rule=cluster_limit_violation)

    def cluster_upper_limit(model,c,t):           #Import constraint for CC
        return model.p_cc[c,t]<=model.eps[c]+model.P_CC_up[c][t]
    if model.P_CC_up != None:
        model.ccpowcap_pos =Constraint(model.C,model.T,rule=cluster_upper_limit)
    
    def cluster_lower_limit(model,c,t):           #Export constraint for CC
        return -model.eps[c]+model.P_CC_low[t]<=model.p_cc[t]
    if model.P_CC_low!=None:
        model.ccpowcap_neg =Constraint(model.C,model.T,rule=cluster_lower_limit )

    def cluster_unbalance_limit(model,c1,c2,t):
        return model.p_cc[c1,t]<=model.p_cc[c2,t]+model.P_IC_unb[c1,c2][t]
    if model.P_IC_unb!=None:  
        model.inter_clust  =Constraint(model.C,model.C,model.T,rule=cluster_unbalance_limit)
        
    def clusteredsystem_upper_limit(model,t):             #Import constraint for CS
        return model.p_cs[t]<=model.P_CS_up[t]
    model.cspowcap_pos=Constraint(model.T,rule=clusteredsystem_upper_limit)
    
    def clusteredsystem_lower_limit(model,t):             #Export constraint for CS
        return model.p_cs[t]>=model.P_CS_low[t]
    model.cspowcap_neg=Constraint(model.T,rule=clusteredsystem_lower_limit)

    def individual_pos_deviation(model,v):
        return model.s_tar[v]-model.s[v,max(opt_horizon)]<=model.y[v]
    model.indev_pos=Constraint(model.V,rule=individual_pos_deviation)

    def individual_neg_deviation(model,v):
        return -model.y[v]<=model.s_tar[v]-model.s[v,max(opt_horizon)]
    model.indev_neg=Constraint(model.V,rule=individual_neg_deviation)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):
        return (sum(model.rho_y[v]*model.y[v]*model.E[v]/3600 for v in model.V))+\
               (sum(model.rho_eps[c]*model.eps[c] for c in model.C))
    model.obj=Objective(rule=obj_rule, sense = minimize)
    
    ###########################################################################         

    ###########################################################################
    ######################Solving the optimization model ######################            
    result = solver.solve(model)
    #print(result)
    ###########################################################################

    ###########################################################################
    ################################Saving the results#########################
    p_schedule={}
    s_schedule={}
    for v in model.V:
        p_schedule[v]={}
        s_schedule[v]={}
        for t in opt_horizon:
            if t<max(opt_horizon):
                p_schedule[v][t]=model.p_ev[v,t]()
            s_schedule[v][t]=model.s[v,t]()
    ###########################################################################

    return p_schedule, s_schedule

if __name__ == '__main__':

    import pandas as pd
    import numpy as np
    from pyomo.environ import SolverFactory

    solver = SolverFactory("cplex")

    clusters = ['CC1', 'CC2']       # System has two clusters
    opt_horizon = list(range(13))   # 1 hour
    opt_step    = 300               # 5 minutes

    powlimits = {}
    # CC1's consumption should not exceed 22 kW and CC2's consumption 33 kW
    powlimits['P_CC_up_lim'] = {'CC1': dict(enumerate(np.ones(12) * 22)),
                                'CC2': dict(enumerate(np.ones(12) * 33))}
    powlimits['P_CC_low_lim'] = {'CC1': dict(enumerate(np.zeros(12))),
                                 'CC2': dict(enumerate(np.zeros(12)))}
    # It is not allowed to violate cluster constraints
    powlimits['P_CC_vio_lim'] = {'CC1':0.0,'CC2':0.0}

    # The multi-cluster system's aggregate consumption is not allowed to exceed 44 kW
    powlimits['P_CS_up_lim'] = dict(enumerate(np.ones(12) * 44))
    powlimits['P_CS_low_lim'] = dict(enumerate(np.zeros(12)))

    np.random.seed(0)
    evdata = {}
    evdata['P_EV_pos_max'] = {}
    evdata['P_EV_neg_max'] = {}
    evdata['charge_eff'] = {}
    evdata['discharge_eff'] = {}
    evdata['battery_cap'] = {}
    evdata['target_soc'] = {}
    evdata['departure_time'] = {}
    evdata['initial_soc'] = {}
    evdata['minimum_soc'] = {}
    evdata['maximum_soc'] = {}
    evdata['location'] = {}
    for v in ['v11', 'v12', 'v21', 'v22']:
        evdata['P_EV_pos_max'][v] = 22
        evdata['P_EV_neg_max'][v] = 22
        evdata['charge_eff'][v] = 1
        evdata['discharge_eff'][v] = 1
        evdata['battery_cap'][v] = 55 * 3600
        evdata['initial_soc'][v] = np.random.uniform(low=0.4, high=0.8)
        evdata['target_soc'][v] = evdata['initial_soc'][v] + 0.2 if v in ['v11', 'v21'] else \
        evdata['initial_soc'][v] + 0.18
        evdata['minimum_soc'][v] = 0.2
        evdata['maximum_soc'][v] = 1.0
        evdata['departure_time'][v] = 6 if v in ['v11', 'v21'] else 15
    evdata['location']['v11'] = ('CC1', 1)
    evdata['location']['v12'] = ('CC1', 2)
    evdata['location']['v21'] = ('CC2', 1)
    evdata['location']['v22'] = ('CC2', 2)

    rho_y       ={'CC1':1,'CC2':1}
    rho_eps     ={'CC1':1,'CC2':1}


    print("A system with two clusters:",clusters)
    print()
    print("...has power limits of:")
    limit_data=pd.DataFrame()
    limit_data['CC1']    = pd.Series(powlimits['P_CC_up_lim']['CC1'])
    limit_data['CC2']    = pd.Series(powlimits['P_CC_up_lim']['CC2'])
    limit_data['CC1+CC2']= pd.Series(powlimits['P_CS_up_lim'])
    print(limit_data)
    print()

    print("...optimizing the charging profiles of the EVs with charging demands:")
    demand_data=pd.DataFrame(columns=['Battery Capacity','Initial SOC','Target SOC','Estimated Departure'])
    demand_data['Battery Capacity']= pd.Series(evdata['battery_cap'])/3600
    demand_data['Initial SOC']     = pd.Series(evdata['initial_soc'])
    demand_data['Target SOC']      = pd.Series(evdata['target_soc'])
    demand_data['Estimated Departure']=pd.Series(evdata['departure_time'])
    demand_data['Location']          =pd.Series(evdata['location'])
    print(demand_data)
    print()

    print("Optimized charging profiles of EVs:")
    p_ref, s_ref = reschedule(solver,opt_step,opt_horizon,powlimits,evdata,clusters,rho_y,rho_eps)

    results={}
    for v in demand_data.index:
        results[v]=pd.DataFrame(columns=['P','S'],index=sorted(s_ref[v].keys()))
        results[v]['P']=pd.Series(p_ref[v])
        results[v]['S']=pd.Series(s_ref[v])
    print(pd.concat(results,axis=1))
    print()

    print("Optimized power profiles of clusters:")
    clust_prof=pd.DataFrame()
    clust_prof['CC1'] = pd.Series(p_ref['v11']) + pd.Series(p_ref['v12'])
    clust_prof['CC2'] = pd.Series(p_ref['v21']) + pd.Series(p_ref['v22'])
    clust_prof['CC1+CC2']=clust_prof.sum(axis=1)
    print(clust_prof)


