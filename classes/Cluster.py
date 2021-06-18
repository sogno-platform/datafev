# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 13:43:13 2021

@author: egu
"""

import pandas as pd

class ChargerCluster(object):
    
    def __init__(self,import_max,export_max=0):
        
        self.power_import_max=import_max   #Maximum power that the cluster can withdraw from upstream
        self.power_export_max=export_max   #Maximum power that the cluster can inject to upstream
        
        self.power_installed =0            #Total installed power of the CUs in the cluster
              
        self.cc_dataset=pd.DataFrame(columns=['Car ID','Car Battery Capacity','Arrival Time','Arrival SOC','Estimated Leave','Desired Leave SOC',
                                              'Charging Unit','Leave Time','Leave SOC','Charged Energy [kWh]'])
    
        self.cu={}
        
        self.net_p={}
        self.net_q={}
        
    
    def add_cu(self,charging_unit):
        """
        To add charging units to the cluster. This method is run before running the simulations.
        """
        self.power_installed+=charging_unit.P_max_ch
        self.cu[charging_unit.id]=charging_unit
        
    
    def enter_car(self,ts,car,estimated_leave,desired_soc):
        """
        To add an entry in cc_dataset for the arriving car. This method is run when a car is allocated to this cluster.
        """
       
        cc_dataset_id=len(self.cc_dataset)+1
        car.cc_dataset_id=cc_dataset_id
        
        self.cc_dataset.loc[cc_dataset_id,'Car ID']              =car.vehicle_id
        self.cc_dataset.loc[cc_dataset_id,'Car Battery Capacity']=car.bCapacity     
        self.cc_dataset.loc[cc_dataset_id,'Arrival Time']         =ts
        self.cc_dataset.loc[cc_dataset_id,'Arrival SOC']          =car.soc[ts]
        self.cc_dataset.loc[cc_dataset_id,'Estimated Leave']      =estimated_leave
        self.cc_dataset.loc[cc_dataset_id,'Desired Leave SOC']    =desired_soc
        
    def connect_car(self,ts,car,cu_id):
        """
        To connect the car to one of the chargers. This method is run when a car is allocated to cu_id
        """    
        cu=self.cu[cu_id]
        cu.connect(ts,car)
        self.cc_dataset.loc[car.cc_dataset_id,'Charging Unit']=cu_id
        
    def disconnect_car(self,ts,car):
        
        cu=car.connected_cu
        cu.disconnect(ts)
        
        self.cc_dataset.loc[car.cc_dataset_id,'Leave Time']=ts
        self.cc_dataset.loc[car.cc_dataset_id,'Leave SOC']=car.soc[ts]
        self.cc_dataset.loc[car.cc_dataset_id,'Charged Energy [kWh]']=(car.soc[ts]-self.cc_dataset.loc[car.cc_dataset_id,'Arrival SOC'])*car.bCapacity/3600
    
        car.cc_dataset_id=None


if __name__ == "__main__":
    
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    from classes.Charger import ChargingUnit as CU
    from classes.Car import ElectricVehicle as EV
    from pyomo.environ import SolverFactory
    from pyomo.core import *
    
    #solver=SolverFactory('glpk',executable="C:/Users/AytugIrem/anaconda3/pkgs/glpk-4.65-h8ffe710_1004/Library/bin/glpsol")
    solver=SolverFactory("gurobi")
    
    cu_power        =22
    cu_efficiency   =1.0
    cu_bidirectional=True
    cu_id1          ="A001"
    cu_id2          ="A002"
    cu_id3          ="A003"
    cu1=CU(cu_id1,cu_power,cu_efficiency,cu_bidirectional)
    cu2=CU(cu_id2,cu_power,cu_efficiency,cu_bidirectional)
    cu3=CU(cu_id3,cu_power,cu_efficiency,cu_bidirectional)
    
    cc              =ChargerCluster(110)
    cc.add_cu(cu1)
    cc.add_cu(cu2)
    cc.add_cu(cu3)
    
    sim_start       =datetime(2021,3,17,15,30)
    time_delta      =timedelta(minutes=5)
    ev_desired_soc  =1.0
    ev_estimat_dep  =datetime(2021,3,17,17,30)
    ev_bCapacity    =22 #tesla
    
    cost_coeff=pd.Series(np.random.randint(low=-1, high=2, size=25),index=pd.date_range(start=sim_start,end=datetime(2021,3,17,17,30),freq=timedelta(minutes=5)))
    #print(cost_coeff)
    
    dsc_time=datetime(2021,3,17,17,30)
    
    ev1_connection  =datetime(2021,3,17,16,0)
    ev1_disconnect  =dsc_time-timedelta(hours=1)
    ev1_soc         =0.5
    ev1_id          ="ev001"
    
    ev2_connection  =datetime(2021,3,17,16,5)
    ev2_disconnect  =dsc_time
    ev2_soc         =0.9
    ev2_id          ="ev002"    
    
    ev3_connection  =datetime(2021,3,17,16,10)
    ev3_disconnect  =dsc_time
    ev3_soc         =0.7
    ev3_id          ="ev003"
    
    ev4_connection  =datetime(2021,3,17,16,40)
    ev4_disconnect  =dsc_time
    ev4_soc         =0.7
    ev4_id          ="ev004"
    
    
    for t in range(25):
        ts=sim_start+t*time_delta
        print(ts)
        #Arrivals
        if ts==ev1_connection:
            
            car1=EV(ev1_id,ev_bCapacity)
            car1.soc[ts]=ev1_soc
            cc.enter_car(ts,car1,ev_estimat_dep,ev_desired_soc)
            cc.connect_car(ts,car1,cu_id1)
            cost_coeff1=cost_coeff[ev1_connection:ev_estimat_dep]
            car1.connected_cu.generate_schedule(solver,ev1_connection, time_delta, ev_desired_soc, ev1_disconnect, cost_coeff1,True)
            car1.connected_cu.set_active_schedule(ev1_connection)
        
        if ts==ev2_connection:
            car2=EV(ev2_id,ev_bCapacity)
            car2.soc[ts]=ev2_soc
            cc.enter_car(ts,car2,ev_estimat_dep,ev_desired_soc)
            cc.connect_car(ts,car2,cu_id2)
            cost_coeff2=cost_coeff[ev2_connection:ev_estimat_dep]
            car2.connected_cu.generate_schedule(solver,ev2_connection, time_delta, ev_desired_soc, ev_estimat_dep, cost_coeff2,True)
            car2.connected_cu.set_active_schedule(ev2_connection)
            
        if ts==ev3_connection:
            car3=EV(ev3_id,ev_bCapacity)
            car3.soc[ts]=ev3_soc
            cc.enter_car(ts,car3,ev_estimat_dep,ev_desired_soc)
            cc.connect_car(ts,car3,cu_id3)
            cost_coeff3=cost_coeff[ev3_connection:ev_estimat_dep]
            car3.connected_cu.generate_schedule(solver,ev3_connection, time_delta, ev_desired_soc, ev_estimat_dep, cost_coeff3,True)
            car3.connected_cu.set_active_schedule(ev3_connection)
                 
        if ts==ev4_connection:
            car4=EV(ev4_id,ev_bCapacity)
            car4.soc[ts]=ev4_soc
            cc.enter_car(ts,car4,ev_estimat_dep,ev_desired_soc)
            cc.connect_car(ts,car4,cu_id1) 
            cost_coeff4=cost_coeff[ev4_connection:ev_estimat_dep]
            car4.connected_cu.generate_schedule(solver,ev4_connection, time_delta, ev_desired_soc, ev_estimat_dep, cost_coeff4,True)
            car4.connected_cu.set_active_schedule(ev4_connection)
        
        #Departures
        if ts==ev1_disconnect:
            cc.disconnect_car(ts,car1)
        if ts==ev2_disconnect:
            cc.disconnect_car(ts,car2)    
        if ts==ev3_disconnect:
            cc.disconnect_car(ts,car3) 
        if ts==ev4_disconnect:
            cc.disconnect_car(ts,car4) 
            
        if ev1_connection<=ts<ev1_disconnect:
            p_real=car1.connected_cu.schedule_pow[car1.connected_cu.active_schedule_instance][ts]
            car1.connected_cu.supply(ts,time_delta,p_real)          
        if ev2_connection<=ts<ev2_disconnect:
            p_real=car2.connected_cu.schedule_pow[car2.connected_cu.active_schedule_instance][ts]
            car2.connected_cu.supply(ts,time_delta,p_real) 
        if ev3_connection<=ts<ev3_disconnect:
            p_real=car3.connected_cu.schedule_pow[car3.connected_cu.active_schedule_instance][ts]
            car3.connected_cu.supply(ts,time_delta,p_real)  
        if ev4_connection<=ts<ev4_disconnect:
            p_real=car4.connected_cu.schedule_pow[car4.connected_cu.active_schedule_instance][ts]
            car4.connected_cu.supply(ts,time_delta,p_real) 
            
    print("A001 history:")
    print(cc.cu['A001'].connection_dataset)
    print()
    print("Charger cluster history:")
    print(cc.cc_dataset)
    
    
    
        
        