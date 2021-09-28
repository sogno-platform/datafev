# -*- coding: utf-8 -*-
"""
Created on Mon Jul 19 06:44:18 2021

@author: egu
"""

import numpy as np
import pandas as pd
from datetime import datetime,timedelta
from pyomo.environ import SolverFactory
from utils.result_analyze import print_results
import time

from classes.Car import ElectricVehicle
from classes.Charger import ChargingUnit
from classes.Cluster import ChargerCluster
from classes.Station import ChargingStation

from management_functions.cluster_based_cs_station.chargingratecontrol import optimal_intervention_v1g,simple_intervention_v1g
from management_functions.cluster_based_cs_station.positioncontrol import optimal_allocation_min_unbalance
from management_functions.cluster_based_cs_station.schedulecontrol import pre_allocation_scheduling_selective

#######################################################################
#Solver specifications
solver=SolverFactory("cplex")
sim_start       =datetime(2020,1,6,9,00)
sim_end         =datetime(2020,1,6,10,00)
time_delta      =timedelta(minutes=5)
sim_period      =pd.date_range(start=sim_start,end=sim_end,freq=time_delta)

alloc_opt_step   =time_delta
sched_opt_step   =time_delta
alloc_opt_horizon=timedelta(hours=1)
sched_opt_horizon=timedelta(hours=1)
#######################################################################

n_of_cc=6

#######################################################################
#Topology parameters
n_of_cu=300
N_cu_per_cluster=int(n_of_cu/n_of_cc)
undersizing=0.70
low_power_rating=11
cu_undirectional=False
cu_efficiency   =1.0
cc_capacity     =low_power_rating*N_cu_per_cluster*(1-undersizing)

cs=ChargingStation()
for c in range(1,n_of_cc+1):
    clust_id='CC'+'{:02d}'.format(int(c))
    clust=ChargerCluster(clust_id,cc_capacity)
    cs.add_cc(clust)
    for u in range(1,N_cu_per_cluster+1):
        cunit_id=u
        cunit=ChargingUnit(cunit_id,low_power_rating,cu_efficiency,cu_undirectional)
        clust.add_cu(cunit)

cs.set_standard_power_level_for_scheduling(low_power_rating)
cs.set_peak_power_limit_for_station(low_power_rating*n_of_cu*(1-undersizing))
cs.number_of_charging_units(list(range(1,N_cu_per_cluster+1)))
#######################################################################

#######################################################################
#Events
inputs = pd.ExcelFile('scenario.xlsx')
events = pd.read_excel(inputs, 'Events')
prices = pd.read_excel(inputs, 'Prices',index_col=0)
cs.set_tou_price(prices['Price'],time_delta)
cs.set_dyn_load_constraint(prices['Grid_Const'],time_delta)
#######################################################################

start=time.time()
ev_dict  ={}
for ts in sim_period:
    print(ts)
    #######################################################################
    #Managing the leaving EVs
    leaving_now=events[events['Estimated Leave']==ts]                          #EVs leaving at this moment
    for _,i in leaving_now.iterrows():
        evID=i['ev_id']
        ev  =ev_dict[evID]
        if ev.admitted==True:
            cc=ev.connected_cc
            cc.disconnect_car(ts,ev)
    #######################################################################

    #######################################################################
    #Managing the incoming EVs
    incoming_now=events[events['Arrival Time']==ts]                             #EVs entering at this moment
    for _,i in incoming_now.iterrows():
        #######################################################################
        #Initialize an EV object
        bcap=i['Battery Capacity (kWh)']
        estL=i['Estimated Leave']
        socA=i['Arrival SOC']
        socT=i['Target SOC']
        evID=i['ev_id']
        ev  =ElectricVehicle(evID,bcap)     #Initialize an EV
        ev.soc[ts]=socA                     #Assign its initial SOC
        ev_dict[evID]=ev                    #All EVs in this simulation are stored in this dictionary such that they can be called to disconnect easily
        #######################################################################

        #######################################################################
        #Calculate an individual optimum schedule for the EV
        opt_horizon=estL-ts
        ev_temp_p_sch, ev_temp_s_sch=pre_allocation_scheduling_selective(cs, solver, ts, time_delta, ev, estL, socT, minsoc=0.2,maxsoc=1.0, v2g=False, min_tol_for_optimization=0)
        cc_schedules = cs.get_cluster_schedules(ts, time_delta, opt_horizon)
        #######################################################################

        #######################################################################
        #Find the optimal allocation that causes the min unbalance between the clusters
        opt_cc_id=optimal_allocation_min_unbalance(cs,ts,time_delta,alloc_opt_horizon,ev_temp_p_sch,cc_schedules) #Optimal
        if opt_cc_id!=None:
            opt_cc=cs.clusters[opt_cc_id]
            #######################################################################
            #Connect the EV to a CU in the selected CC
            opt_cc.enter_car(ts,ev,estL,socT)                               #Open an entry in the dataset for this EV
            cu_id=opt_cc.pick_free_cu_random(ts,time_delta)                 #Select a CU to connect the EV
            opt_cc.connect_car(ts,ev,cu_id)                                 #Connect the EV to the selected CU
            opt_cc.cu[cu_id].set_schedule(ts,ev_temp_p_sch,ev_temp_s_sch)   #Save the schedule
            ev.admitted=True
            #######################################################################
        else:
            ev.admitted=False
        #######################################################################
    #######################################################################

    #######################################################################
    optimal_intervention_v1g(cs,ts,time_delta,sched_opt_horizon,solver) #optimal
    #simple_intervention_v1g(cs, ts, time_delta) #benchmark
    #######################################################################

print_results(cs,"test_result.xlsx",time_delta)
end=time.time()

print("Nb clusters",n_of_cc,":",end-start)


