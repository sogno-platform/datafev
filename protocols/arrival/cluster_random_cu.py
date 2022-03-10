# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 16:11:13 2022

@author: egu
"""

import numpy as np

def random_cu_select(cluster,incoming_vehicles,tdelta):
    
    for ev in incoming_vehicles:
                          
        ######################################
        #Identify available chargers
        period_start=ev.t_arr_real
        period_end  =ev.t_dep_est
        period_step =tdelta
        available_chargers=cluster.get_available_chargers(period_start,period_end,period_step)
        ######################################
        
        if len(available_chargers)==0:
            ev.admitted=False
        else:
            ev.admitted=True
            
            ######################################
            #Specific allocation algorithm: Random in the simulated case 
            selected_charger_id = np.random.choice(available_chargers.index)
            ######################################
            
            ######################################
            #Connection to the selected charger
            selected_charger    = cluster.cu[selected_charger_id]
            selected_charger.connect(ev.t_arr_real,ev)
            ev.reservation_id=selected_charger.reserve(ev.t_arr_real,ev.t_arr_real,ev.t_dep_est,ev)
            cluster.enter_data_of_incoming_vehicle(ev.t_arr_real,ev,selected_charger)
            ######################################