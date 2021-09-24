# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 13:43:13 2021

@author: egu
"""

import pandas as pd
import numpy as np

class ChargerCluster(object):
    
    def __init__(self,cluster_id,import_max,export_max=0):
        
        self.id      =cluster_id
        self.power_import_max=import_max   #Maximum power that the cluster can withdraw from upstream
        self.power_export_max=export_max   #Maximum power that the cluster can inject to upstream
        
        self.power_installed =0            #Total installed power of the CUs in the cluster
              
        self.cc_dataset=pd.DataFrame(columns=['Car ID','Car Battery Capacity','Arrival Time','Arrival SOC','Estimated Leave','Desired Leave SOC', 'Feasible Target SOC',
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
        car.connected_cc =self
        
        self.cc_dataset.loc[cc_dataset_id,'Car ID']              =car.vehicle_id
        self.cc_dataset.loc[cc_dataset_id,'Car Battery Capacity']=car.bCapacity     
        self.cc_dataset.loc[cc_dataset_id,'Arrival Time']         =ts
        self.cc_dataset.loc[cc_dataset_id,'Arrival SOC']          =car.soc[ts]
        self.cc_dataset.loc[cc_dataset_id,'Estimated Leave']      =estimated_leave
        self.cc_dataset.loc[cc_dataset_id,'Desired Leave SOC']    =desired_soc
        self.cc_dataset.loc[cc_dataset_id,'Feasible Target SOC']  =car.fea_target_soc
        
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
        car.connected_cc =None
        
        
    def pick_free_cu_random(self,ts,t_delta):
        
        cu_occupancy_actual =self.get_unit_occupancies(ts,t_delta,t_delta).iloc[0] #Check the current occupancy profile
        free_units   =(cu_occupancy_actual[cu_occupancy_actual==0].index).to_list() #All free CUs at this moment
        cu_id=np.random.choice(free_units)  #Select a random CU to connect the EV
        
        return cu_id
        
    def get_unit_schedules(self,ts,t_delta,horizon):
        """
        To retrieve the actual schedules of the charging units for the specified period 
        """
        time_index=pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        cu_sch_df=pd.DataFrame(index=time_index)
		
        for cu in self.cu.values():  
            
            if cu.connected_car==None:
                cu_sch=pd.Series(0,index=time_index)
            else:
                sch_inst=cu.active_schedule_instance
                cu_sch  =cu.schedule_pow[sch_inst].reindex(time_index,fill_value=0)
            cu_sch_df[cu.id]=cu_sch.copy()
            
        return cu_sch_df
    
    def get_unit_soc_schedules(self,ts,t_delta,horizon):
        """
        To retrieve the actual schedules of the charging units for the specified period 
        """
        time_index=pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        cu_sch_df=pd.DataFrame(index=time_index)
		
        for cu in self.cu.values():  
            
            if cu.connected_car==None:
                cu_sch=pd.Series(0,index=time_index)
            else:
                sch_inst=cu.active_schedule_instance
                cu_sch  =cu.schedule_soc[sch_inst] #TODO: Interpolate
            cu_sch_df[cu.id]=cu_sch.copy()
            
        cu_sch_df=cu_sch_df.fillna(method="ffill")
            
        return cu_sch_df    
    
    
    def get_unit_occupancies(self,ts,t_delta,horizon):
        """
        To calculate the cluster occupancy for the specified period with the connection data
        """
        time_index=pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        cu_occupancy=pd.DataFrame()
        
        for cu in self.cu.values():    
            cu_occ   =pd.Series(index=time_index,dtype=float)
            
            if cu.connected_car==None:
                cu_occ[time_index]=0
                
            else:
                est_leave=self.cc_dataset.loc[cu.connected_car.cc_dataset_id,'Estimated Leave']
                for t in time_index:
                    if t<est_leave:
                        cu_occ[t]=1
                    else:
                        cu_occ[t]=0    
            cu_occupancy[cu.id]=cu_occ.copy()
            
        return cu_occupancy


if __name__ == "__main__":
    
    from datetime import datetime, timedelta
    from classes.Charger import ChargingUnit as CU
    from classes.Car import ElectricVehicle as EV
    from pyomo.environ import SolverFactory
    from pyomo.core import *
    
    #solver=SolverFactory('glpk',executable="C:/Users/AytugIrem/anaconda3/pkgs/glpk-4.65-h8ffe710_1004/Library/bin/glpsol")
    solver=SolverFactory("cplex")
    
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
    
    
    
        
        