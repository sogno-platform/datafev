# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 07:56:46 2021

@author: egu
"""
import pandas as pd

class ChargingStation(object):
    
    def __init__(self,clusters):
        self.clusters=clusters
        
        self.cluster_consumption={} #Net power consumption of the clusters
        self.cluster_occupation ={} #Number of occupied charging units in each cluster
        for cc in sorted(self.clusters.keys()): #One dictionary for each cluster
            self.cluster_consumption[cc]={}
            self.cluster_occupation[cc] ={}
            
            
        self.host_dataset=pd.DataFrame(columns=['Car Object','Car Battery Capacity','Arrival Time','Arrival SOC',
                                        'Estimated Leave','Desired Leave SOC', 'Charging Cluster','Charging Unit',
                                        'Leave Time','Leave SOC','Charged Energy [kWh]'])