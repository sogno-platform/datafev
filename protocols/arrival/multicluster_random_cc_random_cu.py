# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 17:35:44 2022

@author: egu
"""

import numpy as np
#from protocols.arrival.cluster_random_cu import random_cu_select

def random_cc_random_cu(system,incoming_vehicles,tdelta):
     
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
            #Allocation algorithm
            selected_charger_id = np.random.choice(available_chargers.index)
            selected_cluster_id = available_chargers.loc[selected_charger_id,'Cluster']
            selected_cluster    = system.clusters[selected_cluster_id]
            selected_charger    = selected_cluster.cu[selected_charger_id]
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
            selected_cluster.enter_data_of_incoming_vehicle(ev.t_arr_real,ev,selected_charger)
            ############################################################################