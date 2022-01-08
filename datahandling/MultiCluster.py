# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 07:56:46 2021

@author: egu
"""

from datetime import datetime,timedelta
from itertools import product
import pandas as pd
import numpy as np

class MultiCluster(object):
    
    def __init__(self,system_id):
        self.type='CS'
        self.id  =system_id
        self.clusters={}
        
    def add_cc(self,cluster):
        self.clusters[cluster.id]=cluster
        cluster.station=self
        
    def number_of_charging_units(self,cu_ids=None):
        
        number_dict={}
        self.cc_capacities={}
        self.cu_capacities={}
        for cc_id in self.clusters.keys():
            number_dict[cc_id]=len(self.clusters[cc_id].cu.keys())
            self.cc_capacities[cc_id]=self.clusters[cc_id].power_import_max
            self.cu_capacities[cc_id]={}
            for cu_id in sorted(self.clusters[cc_id].cu.keys()):
                self.cu_capacities[cc_id][cu_id]=self.clusters[cc_id].cu[cu_id].P_max_ch
            
        self.cu_numbers   =pd.Series(number_dict)
        self.cs_capacity  =sum(self.cc_capacities.values())
        
        self.cc_installed_capacities=pd.DataFrame(self.cu_capacities).sum()
        self.cs_installed_capacity  =self.cc_installed_capacities.sum()

        
    def set_tou_price(self,series,resolution):
        """
        Method to load electricity price data as time series
        """
        start=min(series.index)
        end  =max(series.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        temp_ser=series.reindex(timerange)
    
        self.tou_price=temp_ser.fillna(temp_ser.fillna(method='ffill'))
                
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
    
    def get_cluster_schedules(self,ts,t_delta,horizon):
        """
        To retrieve the actual schedules of the charging units for the specified period 
        """
        time_index =pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        clusterschedules=pd.DataFrame(index=time_index)
        
        for cc_id,cc in self.clusters.items():
            cc_sch=cc.get_unit_schedules(ts,t_delta,horizon)
            clusterschedules[cc_id]=(cc_sch.sum(axis=1)).copy()
            
        return clusterschedules
    
    def number_of_connected_chargers(self,ts):
        """
        This function identifies chargers with occupancy for the specified period 
        """     
        nb_of_connected_cu=0
        for cc_id,cc in self.clusters.items():
            for cu_id,cu in cc.cu.items():
                if cu.connected_ev!=None:
                   nb_of_connected_cu+=1
        return nb_of_connected_cu
    
    def available_chargers(self,period_start,period_end,period_step):
        """
        This function creates a dataframe with available chargers from all clusters
        """   
        available_chargers=pd.DataFrame(columns=['Cluster','CU type','max p_ch','max p_ds'], dtype=np.float16)
        for cc_id, cc in self.clusters.items():
            cc_available_chargers=cc.available_chargers(period_start,period_end-period_step,period_step)
            for cu_id in cc_available_chargers.index:               
                available_chargers.loc[cu_id,'Cluster']=cc_id
                available_chargers.loc[cu_id,['CU type','max p_ch','max p_ds']]=cc_available_chargers.loc[cu_id]
        return available_chargers
    