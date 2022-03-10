# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 13:43:13 2021

@author: egu
"""

import pandas as pd
import numpy as np
from datetime import datetime,timedelta
from datahandling.ChargingUnit import ChargingUnit

class ChargerCluster(object):
    
    def __init__(self,cluster_id,topology_data,capacity_data,sim_horizon):
        
        self.type    ='CC'
        self.id      =cluster_id
        
        self.power_installed =0            #Total installed power of the CUs in the cluster
              
        self.cc_dataset=pd.DataFrame(columns=['EV ID','EV Battery [kWh]','Arrival Time','Arrival SOC','Scheduled G2V [kWh]',
                                              'Scheduled V2G [kWh]','Connected CU','Leave Time','Leave SOC','Net G2V [kWh]','Total V2G [kWh]'])
    
        self.cu={}
    
    
        sim_step=sim_horizon[1]-sim_horizon[0]
        
        for _,i in topology_data.iterrows():
               
            cuID = i['cu_id']
            ctype= i['cu_type']
            pch  = i['cu_p_ch_max']
            pds  = i['cu_p_ds_max']
            eff  = i['cu_eff']
            cu   =ChargingUnit(cuID,ctype,pch,pds,eff)
            self.add_cu(cu)
            
        capacity_data['TimeStep']=capacity_data['TimeStep'].round('S')
        capacity_lb=pd.Series(capacity_data['LB'].values,index=capacity_data['TimeStep'].values)
        capacity_ub=pd.Series(capacity_data['UB'].values,index=capacity_data['TimeStep'].values)
        
        self.set_capacity_constraints(capacity_ub,capacity_lb,sim_step)
              

    def add_cu(self,charging_unit):
        """
        To add charging units to the cluster. This method is run before running the simulations.
        """
        self.power_installed+=charging_unit.P_max_ch
        self.cu[charging_unit.id]=charging_unit
        
        
    def enter_data_of_incoming_vehicle(self,ts,ev,cu,scheduled=False):
        """
        To add an entry in cc_dataset for the incoming EV. This method is run when a car is allocated to a charger.
        """      
        cc_dataset_id=len(self.cc_dataset)+1
        ev.cc_dataset_id=cc_dataset_id
        ev.connected_cc =self
        
        self.cc_dataset.loc[cc_dataset_id,'EV ID']              =ev.vehicle_id
        self.cc_dataset.loc[cc_dataset_id,'EV Battery [kWh]']   =ev.bCapacity/3600
        self.cc_dataset.loc[cc_dataset_id,'Arrival Time']       =ts
        self.cc_dataset.loc[cc_dataset_id,'Arrival SOC']        =ev.soc[ts]
        self.cc_dataset.loc[cc_dataset_id,'Connected CU']       =cu.id
        
        if scheduled:
            self.cc_dataset.loc[cc_dataset_id,'Scheduled G2V [kWh]']=ev.scheduled_g2v
            self.cc_dataset.loc[cc_dataset_id,'Scheduled V2G [kWh]']=ev.scheduled_v2x
                       
    def enter_data_of_outgoing_vehicle(self,ts,ev):
        
        self.cc_dataset.loc[ev.cc_dataset_id,'Leave Time']      =ts
        self.cc_dataset.loc[ev.cc_dataset_id,'Leave SOC']       =ev.soc[ts]
        self.cc_dataset.loc[ev.cc_dataset_id,'Net G2V [kWh]']   =(ev.soc[ts]-ev.soc_arr_real)*ev.bCapacity/3600
        
        ev_v2x_   =pd.Series(ev.v2x)
        resolution=(ev_v2x_.index[1]-ev_v2x_.index[0])
        ev_v2x    =ev_v2x_[ev.t_arr_real:ev.t_dep_real-resolution]
        self.cc_dataset.loc[ev.cc_dataset_id,'Total V2X [kWh]'] =ev_v2x.sum()*resolution.seconds/3600
    
        ev.cc_dataset_id=None
        ev.connected_cc =None
                      
        
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
    
    def aggregate_schedule_for_actual_connections(self,period_start,period_end,period_step):
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
                #if period_end>cu.connected_ev.estimated_leave:
                if period_end>cu.connected_ev.t_dep_est:
                    #steps_after_disconnection=time_index[time_index>cu.connected_ev.estimated_leave]
                    steps_after_disconnection=time_index[time_index>cu.connected_ev.t_dep_est]
                    cu_sch[steps_after_disconnection]=0
                cu_sch[cu_sch>0]=cu_sch[cu_sch>0]/cu.eff
                cu_sch[cu_sch<0]=cu_sch[cu_sch<0]*cu.eff
                                    
            cu_sch_df[cu.id]=cu_sch.copy()
        
        cc_sch=cu_sch_df.sum(axis=1)
            
        return cc_sch
    
    
    def get_available_chargers(self,period_start,period_end,period_step):
        """
        This function identifies the available chargers for reservations/connections for the specificed period
        """  
        available_chargers=pd.DataFrame(columns=['CU type','max p_ch','max p_ds','eff'], dtype=np.float16)

        for cu in self.cu.values():    
            cu_availability_series=cu.availability(period_start,period_end,period_step)
            is_cu_available        =cu_availability_series.all() 
            if is_cu_available==True:
                available_chargers.loc[cu.id]={'CU type':cu.ctype,'max p_ch':cu.P_max_ch,'max p_ds':cu.P_max_ds,'eff':cu.eff}
    
        return available_chargers
    
    def import_profile(self,period_start,period_end,period_step):     
        df=pd.DataFrame(index=pd.date_range(start=period_start,end=period_end,freq=period_step))
        for cu_id,cu in self.cu.items():
            df[cu_id]=(cu.consumed_power.reindex(df.index)).fillna(0)      
        return df
    
    def occupation_profile(self,period_start,period_end,period_step):
        df=pd.DataFrame(index=pd.date_range(start=period_start,end=period_end,freq=period_step))
        for cu_id,cu in self.cu.items():
            df[cu_id]=(cu.occupation_record(period_start,period_end,period_step).reindex(df.index)).fillna(0)      
        return df
              
    def set_capacity_constraints(self,upper,lower,resolution):
        """
        Method to enter import constraint as time series
        """
        start=min(upper.index)
        end  =max(upper.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        
        upper=upper.reindex(timerange)
        lower=lower.reindex(timerange)
        self.upper_limit=upper.fillna(upper.fillna(method='ffill')) 
        self.lower_limit=lower.fillna(lower.fillna(method='ffill'))
        
        

        


    
    

    
    
    
        
        