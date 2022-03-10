# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 17:44:32 2022

@author: egu
"""

from algorithms.coordination.singleunit_rule import *

def uncontrolled_charging_for_cu(cu,ts,time_delta):
    
    period=time_delta.seconds
    
    ev       =cu.connected_ev
    ev_soc   =ev.soc[ts]
    ev_tarsoc=ev.soc_tar_at_t_dep_est
    ev_bcap  =ev.bCapacity
    
    if cu.ctype=='ac1':
        pmax=min(cu.P_max_ch,ev.p_max_ac_ph1)
    elif cu.ctype=='ac3':
        pmax=min(cu.P_max_ch,ev.p_max_ac_ph3)
    else:
        pmax=min(cu.P_max_ch,ev.p_max_dc)

    p=calc_p_max_ch(ev_soc,ev_tarsoc,pmax, ev_bcap, period)
    cu.supply(ts,time_delta,p)
     
def uncontrolled_charging_for_cc(cc,ts,time_delta): 

    for cu_id, cu in cc.cu.items():
        connected_ev = cu.connected_ev             
        if connected_ev != None:
            uncontrolled_charging_for_cu(cu,ts,time_delta)

def uncontrolled_charging_for_cs(cs,ts,time_delta): 

    for cc_id, cc in cs.clusters.items():
        for cu_id, cu in cc.cu.items():
            connected_ev = cu.connected_ev             
            if connected_ev != None:
                uncontrolled_charging_for_cu(cu,ts,time_delta)
                                                     
def uncontrolled_charging(entity,ts,time_delta):
    
    if entity.type=='CU':
        uncontrolled_charging_for_cu(entity,ts,time_delta)
    if entity.type=='CC':
        uncontrolled_charging_for_cc(entity,ts,time_delta)
    if entity.type=='CS':
        uncontrolled_charging_for_cs(entity,ts,time_delta)
        