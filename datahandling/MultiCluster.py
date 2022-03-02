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
                       
    def set_capacity_constraints(self,upper,lower,resolution):
        """
        Method to enter peak power constraint as time series
        """
        start=min(upper.index)
        end  =max(upper.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        
        upper=upper.reindex(timerange)
        lower=lower.reindex(timerange)
        self.upper_limit=upper.fillna(upper.fillna(method='ffill')) 
        self.lower_limit=lower.fillna(lower.fillna(method='ffill')) 
           
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
    
    def get_available_chargers(self,period_start,period_end,period_step):
        """
        This function creates a dataframe with available chargers from all clusters
        """   
        available_chargers=pd.DataFrame(columns=['Cluster','CU type','max p_ch','max p_ds','eff'], dtype=np.float16)
        for cc_id, cc in self.clusters.items():
            cc_available_chargers=cc.get_available_chargers(period_start,period_end-period_step,period_step)
            for cu_id in cc_available_chargers.index:               
                available_chargers.loc[cu_id,'Cluster']=cc_id
                available_chargers.loc[cu_id,['CU type','max p_ch','max p_ds','eff']]=cc_available_chargers.loc[cu_id]
        return available_chargers
    