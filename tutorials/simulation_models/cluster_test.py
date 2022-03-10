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

from datahandling.Fleet import EVFleet
from datahandling.EV import ElectricVehicle
from datahandling.ChargingUnit import ChargingUnit
from datahandling.ChargerCluster import ChargerCluster
from datahandling.MultiCluster import MultiCluster

from protocols.chargingcontrol.uncontrolled import *
from protocols.chargingcontrol.cluster_modifiedllf import *
from protocols.arrival.cluster_random_cu import *
from protocols.departure.disconnect_and_unreserve import *


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
controlApproaches=['Uncontrolled','Controlled']
consumption=pd.DataFrame(columns=controlApproaches)
datasets   ={}

#Simulation
for controlApproach in controlApproaches:
        
    print(controlApproach,"charging")
    np.random.seed(0)   #Same random behavior in all runs    

    #######################################################################
    #Cluster and fleet generation
    cluster  = ChargerCluster("test_cluster")
    cluster.initiate_cluster(input_cluster,input_capacity,sim_horizon)
    ev_fleet = EVFleet("test_fleet",input_fleet,sim_horizon)
    #######################################################################
    
    for ts in sim_horizon:
              
        print("Simulating time step:",ts)
        #######################################################################
        #Vehicle departures
        list_of_outgoing_vehicles=ev_fleet.outgoing_vehicles_at(ts)
        #Specific departure protocol
        handle_departures(list_of_outgoing_vehicles)
        #######################################################################
        
        #######################################################################
        #Vehicle arrivals 
        list_of_incoming_vehicles =ev_fleet.incoming_vehicles_at(ts)
        #Specific arrival protocol
        random_cu_select(cluster,list_of_incoming_vehicles,sim_step)
        
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
    consumption[controlApproach] =(cluster.import_profile(sim_start,sim_end,sim_step)).sum(axis=1)
    datasets[controlApproach]    =cluster.cc_dataset
    #######################################################################

#Analysis
consumption['Capacity']=cluster.upper_limit
consumption.plot()
        





