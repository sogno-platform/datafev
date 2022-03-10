# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 08:24:50 2022

@author: egu
"""

import pandas as pd
from algorithms.coordination.singleunit_rule import *
from algorithms.coordination.cluster_llfm import *

                              
def modified_least_laxity_first(cc, ts, t_delta, scheduled=False):
    
    period=t_delta.seconds
        
    demand_dic={}
    demand_dic['lb'] ={}
    demand_dic['ub'] ={}
    demand_dic['f_p']={}
    demand_dic['f_n']={}
    demand_dic['R']  ={}
    demand_dic['m']  ={}
    
    for cu_id, cu in cc.cu.items():
        
        connected_ev = cu.connected_ev             
        
        if connected_ev != None:
            
            if cu.ctype=='ac1':
                p_ev_pos_max=min(connected_ev.p_max_ac_ph1,cu.P_max_ch)
                p_ev_neg_max=min(connected_ev.p_max_ac_ph1,cu.P_max_ds) 
            if cu.ctype=='ac3':
                p_ev_pos_max=min(connected_ev.p_max_ac_ph3,cu.P_max_ch)
                p_ev_neg_max=min(connected_ev.p_max_ac_ph3,cu.P_max_ds)
            if cu.ctype=='dc':
                p_ev_pos_max=min(connected_ev.p_max_dc,cu.P_max_ch)
                p_ev_neg_max=min(connected_ev.p_max_dc,cu.P_max_ds)
        
            ev_soc   =connected_ev.soc[ts]
            ev_minsoc=connected_ev.minSoC
            ev_maxsoc=connected_ev.maxSoC
            ev_bcap  =connected_ev.bCapacity

            demand_dic['lb'][cu_id]=-max(calc_p_max_ds(ev_soc,ev_minsoc,p_ev_neg_max, ev_bcap, period),0)
            demand_dic['ub'][cu_id]=max(calc_p_max_ch(ev_soc,ev_maxsoc,p_ev_pos_max, ev_bcap, period),0)
            demand_dic['f_p'][cu_id]=cu.eff
            demand_dic['f_n'][cu_id]=cu.eff
            
            if scheduled==False:
                demand_dic['R'][cu_id]=demand_dic['ub'][cu_id]
                T_M=(1.0-connected_ev.soc_tar_at_t_dep_est)*ev_bcap/p_ev_pos_max
                T_L=(connected_ev.t_dep_est-ts).seconds
                demand_dic['m'][cu_id]=(T_L-T_M)/T_L
                    
    if len(demand_dic['R'])>0:
        demand_df=pd.DataFrame(demand_dic)
        cc_power_lb=cc.lower_limit[ts]
        cc_power_ub=cc.upper_limit[ts]
        set_points=least_laxity_first(demand_df,cc_power_lb,cc_power_ub)
        
        for cu_id,cu in cc.cu.items():
            if cu.connected_ev != None:
                cu.supply(ts, t_delta, set_points[cu_id])
    
    