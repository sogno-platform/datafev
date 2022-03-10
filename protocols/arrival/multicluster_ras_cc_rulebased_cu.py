# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 08:25:34 2022

@author: egu
"""

import numpy as np
import pandas as pd
from algorithms.pricing.cluster_constrained import penalize_violation
from algorithms.scheduling.milp import minimize_cost_in_dp
from algorithms.allocation.location_aware_scheduling import minimize_cost_in_dlp
from algorithms.allocation.charger_selection import minimize_idleness

def simple_scheduling_minimize_idleness(ts, tdelta, system, incoming_vehicles, solver, arbitrage_coeff=0.0):
        
    for ev in incoming_vehicles:
                          
        ############################################################################
        #Identify available chargers
        available_chargers=system.get_available_chargers(ev.t_arr_real,ev.t_dep_est,tdelta)
        ############################################################################
              
        if len(available_chargers)==0:
            ev.admitted=False
        else:
            ev.admitted=True

            ############################################################################
            ############################################################################
            #Start: Allocation algorithm
            
            ############################################################################
            #EV parameters
            ev_bcap         = ev.bCapacity
            ev_soc          = ev.soc_arr_real
            ev_minsoc       = ev.minSoC
            ev_maxsoc       = ev.maxSoC
            crtsoc          = ev.soc_tar_at_t_crt
            depsoc          = ev.soc_tar_at_t_dep_est
            demand_crt      = (ev.soc_tar_at_t_crt-ev_soc)*ev_bcap
            crttime         = ev.t_crt
            deptime         = ev.t_dep_est
            time_until_crt  = crttime - ts
            time_until_dep  = deptime - ts
            ev_p_max_ac_ph1 = ev.p_max_ac_ph1
            ev_p_max_ac_ph3 = ev.p_max_ac_ph3
            ev_p_max_dc     = ev.p_max_dc
            v2x_allow       = ev.v2x_allow  
            ############################################################################
                                
            ############################################################################
            #Step 1: Identify candidate chargers (one suitable charger from each cluster) 
            type_,ch_rate,ds_rate,eff= minimize_idleness(demand_crt, time_until_crt, ev_p_max_ac_ph1,ev_p_max_ac_ph3,ev_p_max_dc,available_chargers)
            all_chargers_with_selected_type    = available_chargers[(available_chargers['CU type']==type_)&(available_chargers['max p_ch']==ch_rate)] 
            candidate_chargers=all_chargers_with_selected_type.drop_duplicates()
            #########################################################################
                
            ############################################################################
            #Step 2: Find realistic optimization parameters for the selected charger type
            if type_=='ac1':
                p_ch=min(ch_rate,ev.p_max_ac_ph1)
                p_ds=min(ds_rate,ev.p_max_ac_ph1)
            elif type_=='ac3':
                p_ch=min(ch_rate,ev.p_max_ac_ph3)
                p_ds=min(ds_rate,ev.p_max_ac_ph3)
            else:
                p_ch=min(ch_rate,ev.p_max_dc)
                p_ds=min(ds_rate,ev.p_max_dc)
            hyp_ene_dep  = p_ch * (time_until_dep.seconds)                      #Maximum energy that the selected charger could supply in the given time until departure (hypothetical)
            hyp_ene_crt  = p_ch * (time_until_crt.seconds)                      #Maximum energy that the selected charger could supply in the given time until critical (hypothetical)
            fea_dep_soc  = min(depsoc, ev_soc + hyp_ene_dep / ev_bcap)          #Feasible SOC that could be achieved at departure time 
            fea_crt_soc  = min(crtsoc, ev_soc + hyp_ene_crt / ev_bcap)          #Feasible SOC that could be achieved at critical time  
            ############################################################################
                                 
            ############################################################################
            #Step 3: Random selection among the candidate chargers
            selected_charger_id = np.random.choice(candidate_chargers.index)
            selected_cluster_id = candidate_chargers.loc[selected_charger_id,'Cluster']
            selected_cluster    = system.clusters[selected_cluster_id]
            selected_charger    = selected_cluster.cu[selected_charger_id]
            ############################################################################
            
            ############################################################################
            #Step 4: Call DLP for the selected cluster
            cc_upper_lim  = selected_cluster.upper_limit[ts:deptime]
            cc_lower_lim  = selected_cluster.lower_limit[ts:deptime]
            cc_schedule   = selected_cluster.aggregate_schedule_for_actual_connections(ts,deptime,tdelta)
            tou_price     = system.tou_price.loc[ts:deptime]
            dyn_price     = penalize_violation(cc_schedule,cc_upper_lim,cc_lower_lim,tou_price,p_ch/eff,p_ds*eff)
            ############################################################################
            
            ############################################################################
            #Step 5: Simple scheduling (schedule optimization for the selected cluster)
            p_ref, s_ref       = minimize_cost_in_dp(solver,ts,deptime,tdelta,p_ch,p_ds,ev_bcap,ev_soc,fea_dep_soc,ev_minsoc, ev_maxsoc,fea_crt_soc,crttime,v2x_allow,dyn_price,arbitrage_coeff)      
            ############################################################################
            
            ############################################################################
            #Step 5: Assign the schedule parameters to the EV
            ev.scheduled_g2v   = p_ref.sum()*tdelta.seconds/3600
            ev.scheduled_v2x   = -(p_ref[p_ref<0].sum())*tdelta.seconds/3600
            selected_charger.set_schedule(ts,p_ref,s_ref)
            ############################################################################
            
            #End: Allocation algorithm
            ############################################################################
            ############################################################################            
                          
            ############################################################################   
            #Connection to the selected charger
            selected_charger.connect(ev.t_arr_real,ev)
            ############################################################################
            
            ############################################################################   
            #Reserving the selected charger for the EV during the specified period            
            ev.reservation_id=selected_charger.reserve(ev.t_arr_real,ev.t_arr_real,ev.t_dep_est,ev)
            ############################################################################
            
            ############################################################################
            #Enter the data to the cluster dataset
            selected_cluster.enter_data_of_incoming_vehicle(ev.t_arr_real,ev,selected_charger,True)
            ############################################################################