# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 13:43:13 2021

@author: egu
"""

import pandas as pd
import numpy as np
from datetime import datetime,timedelta

class ChargerCluster(object):
    
    def __init__(self,cluster_id,import_max,export_max=0):
        
        self.type    ='CC'
        self.id      =cluster_id
        self.power_import_max=import_max   #Maximum power that the cluster can withdraw from upstream
        self.power_export_max=export_max   #Maximum power that the cluster can inject to upstream
        
        self.power_installed =0            #Total installed power of the CUs in the cluster
              
        self.cc_dataset=pd.DataFrame(columns=['Car ID','Car Battery Capacity','Arrival Time','Arrival SOC','Estimated Leave','Feasible Target SOC',
                                              'V2X_Allowance','Charging Unit','Leave Time','Leave SOC','Charged Energy [kWh]'])
    
        self.cu={}
        
        self.net_p={}
        self.net_q={}
        
    
    def add_cu(self,charging_unit):
        """
        To add charging units to the cluster. This method is run before running the simulations.
        """
        self.power_installed+=charging_unit.P_max_ch
        self.cu[charging_unit.id]=charging_unit
        
    
    def enter_data_for_incoming_vehicle(self,ts,ev,cu):
        """
        To add an entry in cc_dataset for the arriving car. This method is run when a car is allocated to this cluster.
        """
       
        cc_dataset_id=len(self.cc_dataset)+1
        ev.cc_dataset_id=cc_dataset_id
        ev.connected_cc =self
        
        self.cc_dataset.loc[cc_dataset_id,'Car ID']               =ev.vehicle_id
        self.cc_dataset.loc[cc_dataset_id,'Car Battery Capacity'] =ev.bCapacity
        self.cc_dataset.loc[cc_dataset_id,'Arrival Time']         =ts
        self.cc_dataset.loc[cc_dataset_id,'Arrival SOC']          =ev.soc[ts]
        self.cc_dataset.loc[cc_dataset_id,'Estimated Leave']      =ev.estimated_leave
        self.cc_dataset.loc[cc_dataset_id,'Feasible Target SOC']  =ev.fea_target_soc
        self.cc_dataset.loc[cc_dataset_id,'V2X_Allowance']        =ev.v2x_allowance
        self.cc_dataset.loc[cc_dataset_id,'Charging Unit']        =cu.id
               
    def enter_data_for_leaving_vehicle(self,ts,ev):
        
        self.cc_dataset.loc[ev.cc_dataset_id,'Leave Time']=ts
        self.cc_dataset.loc[ev.cc_dataset_id,'Leave SOC']           =ev.soc[ts]
        self.cc_dataset.loc[ev.cc_dataset_id,'Charged Energy [kWh]']=(ev.soc[ts]-self.cc_dataset.loc[ev.cc_dataset_id,'Arrival SOC'])*ev.bCapacity/3600
    
        ev.cc_dataset_id=None
        ev.connected_cc =None
        
              
    def pick_free_cu_random(self,ts,t_delta):
        
        cu_occupancy_actual =self.get_unit_occupancies(ts,t_delta,t_delta).iloc[0] #Check the current occupancy profile
        free_units   =(cu_occupancy_actual[cu_occupancy_actual==0].index).to_list() #All free CUs at this moment
        cu_id=np.random.choice(free_units)  #Select a random CU to connect the EV
        
        return cu_id
        
    def schedules_for_actual_connections(self,period_start,period_end,period_step):
        """
        To retrieve the actual schedules of the charging units for the specified period 
        """
        time_index=pd.date_range(start=period_start,end=period_end,freq=period_step)
        cu_sch_df=pd.DataFrame(index=time_index)
		
        for cu in self.cu.values():  
            
            if cu.connected_ev==None:
                cu_sch=pd.Series(0,index=time_index)
            else:
                sch_inst=cu.active_schedule_instance
                cu_sch  =(cu.schedule_pow[sch_inst].reindex(time_index)).fillna(method='ffill')
                if period_end>cu.connected_ev.estimated_leave:
                    steps_after_disconnection=time_index[time_index>cu.connected_ev.estimated_leave]
                    cu_sch[steps_after_disconnection]=0
                    
            cu_sch_df[cu.id]=cu_sch.copy()
            
        return cu_sch_df
    
    def available_chargers(self,period_start,period_end,period_step):
        """
        This function identifies the available chargers for reservations/connections for the specificed period
        """  
        available_chargers=pd.DataFrame(columns=['CU type','max p_ch','max p_ds'], dtype=np.float16)

        for cu in self.cu.values():    
            cu_availability_series=cu.availability(period_start,period_end,period_step)
            is_cu_available        =cu_availability_series.all() 
            if is_cu_available==True:
                available_chargers.loc[cu.id]={'CU type':cu.ctype,'max p_ch':cu.P_max_ch,'max p_ds':cu.P_max_ds}
    
        return available_chargers
    
    def set_import_constraint(self,series,resolution):
        """
        Method to enter import constraint as time series
        """
        start=min(series.index)
        end  =max(series.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        temp_ser=series.reindex(timerange)
        self.import_max=temp_ser.fillna(temp_ser.fillna(method='ffill')) 
        self.import_lim=True
        
    def set_export_constraint(self,series,resolution):
        """
        Method to enter export constraint as time series
        """
        start=min(series.index)
        end  =max(series.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        temp_ser=series.reindex(timerange)
        self.export_max=temp_ser.fillna(temp_ser.fillna(method='ffill')) 
        self.export_lim=True
    
    

    
    
    
        
        