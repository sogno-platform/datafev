# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 07:56:46 2021

@author: egu
"""

from datetime import datetime,timedelta
from itertools import product
import pandas as pd
import numpy as np

class MultiClusterSystem(object):
    
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
                       
    def set_peak_limits(self, start,end,step, peaklimits):
        """
        Method to enter peak power constraint as time series
        """
        roundedts=peaklimits['TimeStep'].dt.round("S")

        capacity_lb=pd.Series(peaklimits['LB'].values,index=roundedts)
        capacity_ub=pd.Series(peaklimits['UB'].values,index=roundedts)

        n_of_steps = int((end - start) / step)
        timerange = [start + t * step for t in range(n_of_steps + 1)]

        upper = capacity_ub.reindex(timerange)
        lower = capacity_lb.reindex(timerange)
        self.upper_limit = upper.fillna(upper.fillna(method='ffill'))
        self.lower_limit = lower.fillna(lower.fillna(method='ffill'))
           
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
            for cu_id,cu in cc.chargers.items():
                if cu.connected_ev!=None:
                   nb_of_connected_cu+=1
        return nb_of_connected_cu
    
    def query_availability(self,start,end,step,deviations):
        """
        This function creates a dataframe containing the data of the available chargers within a specific period.

        Inputs
        ------------------------------------------------------------------------------------------------------------
        start    : start of queried period (typically estimated arrival time of EV)              datetime
        end      : end of queried period (typically estimated departure time of EV)              datetime
        step     : time resolution of query                                                      timedelta
        deviations      : deviations in est. arrival/departure times (obtained from traffic forecast)   dict
        ------------------------------------------------------------------------------------------------------------
        """

        available_chargers=pd.DataFrame(columns=['Cluster','max p_ch','max p_ds','eff'], dtype=np.float16)

        for cc_id, cc in self.clusters.items():

            estimated_arr  =start+deviations['arr_del'][cc_id]       #estimated arrival time if ev goes to cc
            estimated_dep  =end+deviations['dep_del'][cc_id]         #estimated departure time if ev goes to cc
            cc_available_chargers=cc.query_availability(estimated_arr,estimated_dep-step,step)

            for cu_id in cc_available_chargers.index:

                available_chargers.loc[cu_id,'Cluster']=cc_id
                available_chargers.loc[cu_id,['max p_ch','max p_ds','eff']]=cc_available_chargers.loc[cu_id]

        return available_chargers

    def uncontrolled_supply(self,ts,step):
        for cc_id, cc in self.clusters.items():
            cc.uncontrolled_supply(ts,step)

    def export_results(self, start, end, step, xlfile):

        with pd.ExcelWriter(xlfile) as writer:

            cluster_datasets=[]
            con_cu_dict = {}
            occ_cu_dict = {}
            overall=pd.DataFrame(columns=['Net Consumption','Net G2V','Total V2G','Unfulfilled G2V','Unscheduled V2G'])

            for cc_id, cc in sorted(self.clusters.items()):

                ds=cc.cc_dataset.copy()
                cluster_datasets.append(ds)

                con_cu_dict[cc_id] = cc.import_profile(start, end, step)
                occ_cu_dict[cc_id] = cc.occupation_profile(start, end, step)

                unfulfilled_g2v_ser = ds['Scheduled G2V [kWh]'] - ds['Net G2V [kWh]']
                unscheduled_v2g_ser = ds['Total V2G [kWh]'] - ds['Scheduled V2G [kWh]']
                overall.loc[cc_id,'Unfulfilled G2V'] = (unfulfilled_g2v_ser[unfulfilled_g2v_ser > 0]).sum()
                overall.loc[cc_id,'Unscheduled V2G'] = (unscheduled_v2g_ser[unscheduled_v2g_ser > 0]).sum()
                overall.loc[cc_id,'Net Consumption'] = (con_cu_dict[cc_id].sum(axis=1)).sum() * step.seconds / 3600
                overall.loc[cc_id,'Net G2V']         = ds['Net G2V [kWh]'].sum()
                overall.loc[cc_id,'Total V2G']       = ds['Total V2G [kWh]'].sum()

            datasets=pd.concat(cluster_datasets,ignore_index=True)
            datasets=datasets.sort_values(by=['Arrival Time'],ignore_index=True)
            datasets.to_excel(writer,sheet_name="Connection Dataset")

            consu_cu_df = pd.concat(con_cu_dict, axis=1)
            consu_cu_df.to_excel(writer, sheet_name='Consumption (Units)')
            (consu_cu_df.sum(level=0, axis=1)).to_excel(writer, sheet_name='Consumption (Aggregate)')

            occup_cu_df = pd.concat(occ_cu_dict, axis=1)
            occup_cu_df.to_excel(writer, sheet_name='Occupation (Units)')
            (occup_cu_df.sum(level=0,axis=1)).to_excel(writer, sheet_name='Occupation (Aggregate)')

            overall.loc['Total']=overall.sum()
            overall.to_excel(writer, sheet_name="Overall")


