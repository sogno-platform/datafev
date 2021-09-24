# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 07:56:46 2021

@author: egu
"""

from datetime import datetime,timedelta
from itertools import product
import pandas as pd
import numpy as np

class ChargingStation(object):
    
    def __init__(self):
        self.clusters={}
        
        self.cluster_consumption={} #Net power consumption of the clusters
        self.cluster_occupation ={} #Number of occupied charging units in each cluster
        for cc in sorted(self.clusters.keys()): #One dictionary for each cluster
            self.cluster_consumption[cc]={}
            self.cluster_occupation[cc] ={}
            
            
        self.host_dataset=pd.DataFrame(columns=['Car ID','Car Battery Capacity','Arrival Time','Arrival SOC',
                                        'Estimated Leave','Desired Leave SOC', 'Connected Cluster','Charging Unit',
                                        'Leave Time','Leave SOC','Charged Energy [kWh]'])
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
        #self.cu_indices   =cu_ids
        
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
           
    def set_standard_power_level_for_scheduling(self,power_rat):
        """
        This method sets a standard power rating for scheduling before allocation
        """
        self.P_RAT=power_rat
        
    def set_peak_power_limit_for_station(self,P_CS_Max):
        self.P_CS_Max=P_CS_Max

    def calculate_cost_coef_for_scheduling(self,ts,t_delta,horizon):
        """
        Method to calculate dynamic cost coefficient that will be used in individual scheduling
        """
        cc_schedules  =self.get_cluster_schedules(ts,t_delta,horizon)        
        cs_schedule   =cc_schedules.sum(axis=1)
        
        overloadedsteps_int=cs_schedule[cs_schedule>self.P_CS_Max].index #Time steps at which the aggregate station load exceeds the power capacity of the station
        
        if self.peaklim:
            overloadedsteps_ext=cs_schedule[cs_schedule>self.gridcon[cs_schedule.index]].index
            overloadedsteps=overloadedsteps_int.union(overloadedsteps_ext)
        else:
            overloadedsteps=overloadedsteps_int.copy()
            
        dyn_cost_=self.tou_price.copy()
        dyn_cost_[overloadedsteps]=dyn_cost_[overloadedsteps]*2
        
        rel_peri=pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        dyn_cost=dyn_cost_[rel_peri]
    
        return dyn_cost,cc_schedules

    def set_dyn_load_constraint(self,series,resolution):
        """
        Method to enter dynamic grid constraint as time series
        """
        start=min(series.index)
        end  =max(series.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        temp_ser=series.reindex(timerange)
    
        self.gridcon=temp_ser.fillna(temp_ser.fillna(method='ffill')) #TODO: change the forward fill such that faster completion is prioritized
        self.peaklim=True
        
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
    
    def get_cluster_occupations(self,ts,t_delta,horizon):
        """
        To retrieve the cluster occupancy for the specified period 
        """
        
        time_index =pd.date_range(start=ts,end=ts+horizon-t_delta,freq=t_delta)
        clusteroccupancy=pd.DataFrame(index=time_index)
        
        for cc_id,cc in self.clusters.items():
            cc_occ=cc.get_unit_occupancies(ts,t_delta,horizon)
            clusteroccupancy[cc_id]=(cc_occ.sum(axis=1)).copy()
            
        return clusteroccupancy
    
    