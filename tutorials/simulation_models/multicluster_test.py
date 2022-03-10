# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 08:28:41 2022

@author: egu
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime,timedelta
import matplotlib.pyplot as plt 
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
from protocols.arrival.multicluster_random_cc_random_cu import *
from protocols.departure.disconnect_and_unreserve import *


#Simulation time parameters
sim_start       =datetime(2022,1,8,7)
sim_end         =datetime(2022,1,8,20)
sim_length      =sim_end-sim_start
sim_step        =timedelta(minutes=5)
sim_horizon     =[sim_start+t*sim_step for t in range(int(sim_length/sim_step))]

#Simulation inputs
inputs          = pd.ExcelFile('multicluster_test_scenario.xlsx')
input_fleet     = pd.read_excel(inputs, 'Fleet')#,index_col=0)
input_cluster1  = pd.read_excel(inputs, 'Cluster1')
input_capacity1 = pd.read_excel(inputs, 'Capacity1')
input_cluster2  = pd.read_excel(inputs, 'Cluster2')
input_capacity2 = pd.read_excel(inputs, 'Capacity2')

price           = pd.read_excel(inputs, 'Price')
price_t_steps   = price['TimeStep'].round('S')
tou_tariff      = pd.Series(price['Price'],index=price_t_steps)

#######################################################################
#System and fleet generation
cluster1  = ChargerCluster("cluster1",input_cluster1,input_capacity1,sim_horizon)
cluster2  = ChargerCluster("cluster2",input_cluster2,input_capacity2,sim_horizon)
system    = MultiCluster("multicluster")
system.add_cc(cluster1)
system.add_cc(cluster2)
system.set_tou_price(tou_tariff,sim_step)

ev_fleet = EVFleet("test_fleet",input_fleet,sim_horizon)
#######################################################################

#######################################################################
#Simulation     
np.random.seed(0)   #Same random behavior in all runs    
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
    random_cc_random_cu(system,list_of_incoming_vehicles,sim_step)
    
    #######################################################################
    #Real-time charging control
    for cc_id,cc in system.clusters.items():
        modified_least_laxity_first(cc, ts, sim_step)
    #######################################################################
#######################################################################

#%%
#######################################################################
#Analysis
cluster1_profile=pd.DataFrame(columns=['Constraint','Consumption'])
cluster2_profile=pd.DataFrame(columns=['Constraint','Consumption'])
cluster1_profile['Constraint']=cluster1.upper_limit
cluster2_profile['Constraint']=cluster2.upper_limit
cluster1_profile['Consumption']=(cluster1.import_profile(sim_start,sim_end,sim_step)).sum(axis=1)
cluster2_profile['Consumption']=(cluster2.import_profile(sim_start,sim_end,sim_step)).sum(axis=1)

fig,axs=plt.subplots(2,1,tight_layout=True,sharex=True,sharey=True)
cluster1_profile.plot(ax=axs[0],label=cluster1.id)
cluster2_profile.plot(ax=axs[1],label=cluster1.id)
#######################################################################
        





