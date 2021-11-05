# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 15:44:17 2021

@author: egu
"""

from management_algorithms.singlevehicle.scheduling_v2g_det import optimal_schedule_v2g

#TODO1: Write a method that calls scheduling_g2v or scheduling_v2g
def generate_schedule(cu, optsolver,now, t_delta, target_soc, est_leave, cost_coeff,v2g=False):
    """
    This method calls optimal_schedule_g2v/v2g function from management and generates schedules
    """
    
    current_soc  =cu.connected_car.soc[now]
    hyp_en_input=cu.P_max_ch*((est_leave-now).seconds)                    #Maximum energy that could be supplied within the given time with the given charger rating if the battery capacity was unlimited
    target_soc   =min(1,current_soc+hyp_en_input/cu.connected_car.bCapacity)
         
    schedule_pow, schedule_soc = optimal_schedule_v2g(optsolver,now,est_leave,
                                                      t_delta,cu.P_max_ch,cu.P_max_ds,cu.connected_car.bCapacity,
                                                      current_soc,target_soc,cu.connected_car.minSoC,cu.connected_car.maxSoC,
                                                      cost_coeff,v2g)

    return schedule_pow,schedule_soc