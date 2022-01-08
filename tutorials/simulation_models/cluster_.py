# -*- coding: utf-8 -*-
"""
Created on Wed Jan  5 14:01:52 2022

@author: egu
"""

from datetime import datetime, timedelta
from classes.Charger import ChargingUnit as CU
from classes.Car import ElectricVehicle as EV
from pyomo.environ import SolverFactory
from pyomo.core import *

solver=SolverFactory('glpk',executable="C:/Users/aytugy/anaconda3/pkgs/glpk-4.65-h8ffe710_1004/Library/bin/glpsol")
#solver=SolverFactory("cplex")

cu_power        =22
cu_efficiency   =1.0
cu_bidirectional=True
cu_id1          ="A001"
cu_id2          ="A002"
cu_id3          ="A003"
cu1=CU(cu_id1,cu_power,cu_efficiency,cu_bidirectional)
cu2=CU(cu_id2,cu_power,cu_efficiency,cu_bidirectional)
cu3=CU(cu_id3,cu_power,cu_efficiency,cu_bidirectional)

cc              =ChargerCluster('cc_01',50)
cc.add_cu(cu1)
cc.add_cu(cu2)
cc.add_cu(cu3)

sim_start       =datetime(2021,3,17,16,00)
time_delta      =timedelta(minutes=5)
sim_period      =pd.date_range(start=sim_start,end=sim_start+timedelta(hours=2),freq=time_delta)
cost_coeff=pd.Series(np.random.randint(low=-1, high=2, size=len(sim_period)),index=sim_period)


inputs   = pd.ExcelFile('cluster_test.xlsx')
events   = pd.read_excel(inputs, 'Events')

ev_dict  ={}

for ts in sim_period:
    
    #######################################################################
    #Managing the leaving EVs
    leaving_now=events[events['Estimated Leave']==ts]                          #EVs leaving at this moment  
    for _,i in leaving_now.iterrows():
        evID=i['ev_id']
        ev  =ev_dict[evID]
        cc.disconnect_car(ts,ev)
    #######################################################################
           
    #######################################################################
    #Managing the incoming EVs
    incoming_now=events[events['Arrival Time']==ts]                             #EVs entering at this moment 
    cu_occupancy_actual =cc.get_unit_occupancies(ts,time_delta,time_delta).iloc[0] #Check the current occupancy profile
    free_units   =(cu_occupancy_actual[cu_occupancy_actual==0].index).to_list() #All free CUs at this moment

    for _,i in incoming_now.iterrows():  
        bcap=i['Battery Capacity (kWh)']
        estL=i['Estimated Leave']
        socA=i['Arrival SOC']
        socT=i['Target SOC']
        evID=i['ev_id'] 
        
        ev  =EV(evID,bcap)                  #Initialize an EV 
        ev.soc[ts]=socA                     #Assign its initial SOC
        
        cc.enter_car(ts,ev,estL,socT)       #Open an entry in the dataset for this EV
        ev_dict[evID]=ev                    #All EVs in this simulation are stored in this dictionary such that they can be called to disconnect easily
        
        cu_id=np.random.choice(free_units)  #Select a random CU to connect the EV
        cc.connect_car(ts,ev,cu_id)         #Connect the EV to the selected CU
        free_units.remove(cu_id)            #Remve the CU from free_units sit
        
        ev.connected_cu.generate_schedule(solver,ts, time_delta, socT, estL, cost_coeff[ts:estL],True) #Scheduling
        ev.connected_cu.set_active_schedule(ts)                                                        #Saving the schedule
        #print("Schedule of",evID)
        #print(cc.cu[cu_id].schedule_pow[cc.cu[cu_id].active_schedule_instance])
    #######################################################################    
        
    #######################################################################
    #Managing the chargin process
    cu_occupancy_actual =cc.get_unit_occupancies(ts,time_delta,time_delta).iloc[0] #Check the current occupancy profile
    occupied_units      =(cu_occupancy_actual[cu_occupancy_actual==1].index).to_list() #All CUs with connected EVs at this moment
    
    for cu_id in occupied_units:
        
        cu=cc.cu[cu_id]
        p_real=cu.schedule_pow[cu.active_schedule_instance][ts]             #Check the active schedule
        cu.supply(ts,time_delta,p_real)                                     #Supply as much as specified by the schedule
        
    
    
print("Charger cluster history:")
ds=cc.cc_dataset
print(ds)