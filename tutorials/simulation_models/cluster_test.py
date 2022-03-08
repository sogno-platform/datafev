# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 08:28:41 2022

@author: egu
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime,timedelta
from utils.result_analyze import print_results
from utils.scenario_analyze import analyze_occupation
import time

from interface.functions import *
from interface.realtime.uncontrolled import *
from interface.realtime.cluster_modifiedllf import *

from algorithms.allocation.charger_selection import minimize_idleness

#Simulation time parameters
sim_start       =datetime(2022,1,8,7)
sim_end         =datetime(2022,1,8,20)
sim_length      =sim_end-sim_start
sim_step        =timedelta(minutes=5)
sim_horizon     =[sim_start+t*sim_step for t in range(int(sim_length/sim_step))]

#Simulation inputs
inputs          = pd.ExcelFile('cluster_test_scenario.xlsx')
input_fleet     = pd.read_excel(inputs, 'Fleet')#,index_col=0)
input_cluster   = pd.read_excel(inputs, 'Cluster')
input_capacity  = pd.read_excel(inputs, 'Capacity')
analyze_occupation(input_fleet,sim_horizon)

#Simulation outputs
consumption={}
datasets   ={}

#%%
for controlApproach in ['Uncontrolled','Controlled']:
        
    print(controlApproach,"charging")
    np.random.seed(0)   #Same random behavior in all runs    
    #######################################################################
    #Cluster and fleet generation
    cluster= generate_cluster("test_cluster",input_cluster,input_capacity,sim_step)
    ev_fleet=generate_fleet(input_fleet)
    #######################################################################
    
    for ts in sim_horizon:
              
        print("Simulating time step:",ts)
        #######################################################################
        #Vehicle departures
        list_of_outgoing_vehicles =handle_departures(ts,input_fleet,ev_fleet)
        #######################################################################
        
        #######################################################################
        #Vehicle admissions 
        list_of_incoming_vehicles =handle_arrivals(ts,input_fleet,ev_fleet)    
        for ev in list_of_incoming_vehicles:
                        
            available_chargers=ev.request_available_charger_list(cluster,sim_step)
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
                selected_charger.connect(ts,ev)
                ev.reservation_id=selected_charger.reserve(ts,ts,ev.t_dep_est,ev)
                cluster.enter_data_of_incoming_vehicle(ts,ev,selected_charger)
                ######################################
        #######################################################################
        
        #######################################################################
        #Real-time charging control
        if controlApproach=='Uncontrolled': 
            #Specific control algorithm: Random in the simulated case
            uncontrolled_charging(cluster,ts,sim_step)
        if controlApproach=='Controlled': 
            #Specific control algorithm: Modified least laxity first
            modified_least_laxity_first(cluster, ts, sim_step)
        #######################################################################
    
        #######################################################################
        #Saving results
        consumption[controlApproach] =cluster.utilization_record(sim_start,sim_end,sim_step)
        datasets[controlApproach]    =cluster.cc_dataset
        #######################################################################

#%%
#Analysis
results=pd.DataFrame(columns=['Uncontrolled','Controlled','Capacity'])
results['Uncontrolled']=consumption['Uncontrolled']['Net consumption']
results['Controlled']  =consumption['Controlled']['Net consumption']
results['Capacity']    =consumption['Controlled']['UB']
results.plot()
        





