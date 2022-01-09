# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 18:59:20 2022

@author: egu
"""

import numpy as np
from algorithms.scheduling.milp import minimize_charging_cost_milp
from algorithms.allocation.charger_rule_based import minimize_idleness

def schedule_optimization_allocation_random(solver, cs, ev, ts, t_delta, deptime, depsoc, crttime, crtsoc, v2x_allow, available_chargers,arbitrage_coeff=0.0):
    """
    This function allocates the EV into a particular charging in a randomly selected cluster
        1- It identifies the suitable charger type among the available chargers (algorithm: select_charger_type)
        2- It optimizese the schedule for the given demand and static TOU price signal
        3- It chooses a random cluster
        4- It connects the EV to one of the charges of selected type in the randomly selected cluster
    """
    # Checking the TOU prices for current opt_horizon
    ev_soc          = ev.soc[ts]
    demand_crt      = (crtsoc-ev_soc)*ev.bCapacity
    time_until_crt  = crttime - ts
    time_until_dep  = deptime - ts
    
    ev_p_max_ac_ph1=ev.p_max_ac_ph1
    ev_p_max_ac_ph3=ev.p_max_ac_ph3
    ev_p_max_dc    =ev.p_max_dc
        
    #Identify a suitable charger type for the given demand
    type_,ch_rate,ds_rate= minimize_idleness(demand_crt, time_until_crt, ev_p_max_ac_ph1,ev_p_max_ac_ph3,ev_p_max_dc,available_chargers)
    if type_=='ac1':
        p_ch=min(ch_rate,ev.p_max_ac_ph1)
        p_ds=min(ds_rate,ev.p_max_ac_ph1)
    elif type_=='ac3':
        p_ch=min(ch_rate,ev.p_max_ac_ph3)
        p_ds=min(ds_rate,ev.p_max_ac_ph3)
    else:
        p_ch=min(ch_rate,ev.p_max_dc)
        p_ds=min(ds_rate,ev.p_max_dc)
        
    #Find realistic optimization parameters
    hyp_ene_dep  = p_ch * (time_until_dep.seconds)                      #Maximum energy that the selected charger could supply in the given time until departure (hypothetical)
    hyp_ene_crt  = p_ch * (time_until_crt.seconds)                      #Maximum energy that the selected charger could supply in the given time until critical (hypothetical)
    fea_dep_soc  = min(depsoc, ev_soc + hyp_ene_dep / ev.bCapacity)     #Feasible SOC that could be achieved at departure time 
    fea_crt_soc  = min(crtsoc, ev_soc + hyp_ene_crt / ev.bCapacity)     #Feasible SOC that could be achieved at departure time

    ev.estimated_leave = deptime
    ev.fea_target_soc  = fea_dep_soc
    ev.v2x_allowance   = v2x_allow*3600  
    
    #Schedule optimization
    tou_price     = cs.tou_price.loc[ts:deptime]
    p_ref, s_ref  = minimize_charging_cost_milp(solver,ts,deptime,t_delta,p_ch,p_ds,ev.bCapacity,ev_soc,fea_dep_soc,ev.minSoC, ev.maxSoC,fea_crt_soc,crttime,ev.v2x_allowance,tou_price,arbitrage_coeff)
        
    #Identify candidate chargers (one suitable charger from each cluster) 
    all_chargers_with_selected_type    = available_chargers[(available_chargers['CU type']==type_)&(available_chargers['max p_ch']==ch_rate)] 
    candidate_chargers             = {}      
    for cc_id in all_chargers_with_selected_type['Cluster'].unique():    
        cluster_chargers_with_selected_type = all_chargers_with_selected_type[all_chargers_with_selected_type['Cluster']==cc_id]
        selected_charger_in_cluster         = cluster_chargers_with_selected_type.index[0]        
        candidate_chargers[cc_id]=selected_charger_in_cluster
        
    #Select one of the chargers randomly    
    optimal_cluster_id = np.random.choice(candidate_chargers.keys(),1)[0]
    optimal_cluster    = cs.clusters[optimal_cluster_id]
    optimal_charger    = optimal_cluster.cu[candidate_chargers[optimal_cluster_id]]
    net_charging       = p_ref.sum()*t_delta/3600
    
    #Reserve the selected charger
    reservation_id=optimal_charger.reserve(ts,ts,deptime,ev,net_charging)
    ev.reservation_id  = reservation_id
    
    #Connect the EV to selected charger
    optimal_charger.connect(ts,ev)
    optimal_charger.set_schedule(ts,p_ref,s_ref)
    
    #Enter data of the EV to cluster dataset
    optimal_cluster.enter_data_for_incoming_vehicle(ts,ev,optimal_charger)
    
    return optimal_charger.id
    
      
    
