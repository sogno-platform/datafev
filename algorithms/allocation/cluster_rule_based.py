# -*- coding: utf-8 -*-
"""
Created on Tue Jul  6 11:52:12 2021

@author: egu
"""

import pandas as pd

def minimize_intercluster_unabalance(actual_schedule,newcar_schedule,candidate_clusters,cluster_installed_cap):
    """
    This function optimizes allocation of an incoming EV for the given EV schedule:
        -It compares the aggregate schedule of a cluster with the installed capacity of the cluster--> scheduled cluster loading
        -It puts the incoming EV to a single cluster to see how the scheduled cluster loading would change by the new allocation
        -It tests all clusters and identifies the allocation that leads to minimum inter-cluster unbalance in terms of scheduled loading    
    """
    
    unbt={}
    
    for c in candidate_clusters:
        
        newsys_schedule=actual_schedule.copy()/cluster_installed_cap
        newsys_schedule[c]+=newcar_schedule/cluster_installed_cap[c]
                
        unb_=0
        for t in newsys_schedule.index:
            load_t=newsys_schedule.loc[t]
            unb_ar=load_t.values-load_t.values[:,None]
            #unb.append(sum(unb_ar[unb_ar>0]))
            unb_+=sum(unb_ar[unb_ar>0])
            
        #unbl[c]=unb
        unbt[c]=unb_
        
    tot_unb=pd.Series(unbt)

    return tot_unb.idxmin()

        
def minimize_cluster_capacity_violation(actual_schedule,newcar_schedule,candidate_clusters,cluster_cap):
    """
    This function optimizes allocation of an incoming EV for the given EV schedule in an under-sized cluster scenario:
        -It compares the aggregate schedule of a cluster with the power capacity of the cluster--> scheduled capacity utilization
        -It puts the incoming EV to a single cluster to see how often the scheduled capacity utilization would violate the cluster power capability by the new allocation
        -It tests all clusters and identifies the allocation that leads to minimum capacity violation in terms of scheduled loading    
    """
    
    # copy actual schedule with candidate cluster filtering 
    newsys_schedule = actual_schedule[candidate_clusters]
    
    # create a dictionary in lenght of possible scenarios (number of clusters)
    # keys: scenario(cluster) id, values: scenario schedule df
    contestant_schedule = {}
    for cc_id in newsys_schedule.columns:
        contestant_schedule[cc_id]=newsys_schedule.copy()
    
    pd.options.mode.chained_assignment = None  # default='warn'
    # add new car schedule to each scenario (each time to different a cluster)
    for scenario_id, sch_df in contestant_schedule.items():
        for cc_id in sch_df.columns:
            if cc_id == scenario_id:
                for ts_cc in sch_df.index:
                    for ts_ev, power in newcar_schedule.items():
                        if ts_cc == ts_ev:
                            sch_df.loc[ts_cc][cc_id] += newcar_schedule[ts_ev]

    # create a dictionary which saves excess values
    # if contestant schedule exceeds cluster capacity save the difference, else 0
    # for that first copy dataframes
    excess_schedule = {}
    for scenario_id, sch_df in contestant_schedule.items():
        for cc_id in sch_df.columns:
            excess_schedule[cc_id] = sch_df.copy()
    # set its all values to 0
    for scenario_id, exc_df in excess_schedule.items():
        for col in exc_df.columns:
            exc_df[col].values[:] = 0
    # fill excess dataframe
    for scenario_id, sch_df in contestant_schedule.items():
        for cc_id in sch_df.columns:
            for ts_cc in sch_df.index:
                if sch_df.loc[ts_cc][cc_id] > cluster_cap[cc_id]:
                    excess_schedule[scenario_id].loc[ts_cc][cc_id] = sch_df.loc[ts_cc][cc_id] - cluster_cap[cc_id]
                else:
                    excess_schedule[scenario_id].loc[ts_cc][cc_id] = 0

    # store total exess values in a dictionary
    excess_dict = {}
    for scenario_id, sch_df in excess_schedule.items():
        excess_dict[scenario_id] = sch_df.to_numpy().sum()
    
    # min value
    min_value_cc_id = min(excess_dict, key=excess_dict.get)
    min_value = excess_dict[min_value_cc_id]

    # if there are more than one minimum values in the excess dict,
    # choose the one with min affect on cluster's occupancy   
    min_value_counter = 0
    for value in excess_dict.values():
        if value == min_value:
            min_value_counter += 1
            
    if min_value_counter == 1:
        return min_value_cc_id
    else:
        # store total import max power of clusters in a dictionary
        cc_total_power_dict = {}
        for cc_id, value in excess_dict.items():
            if value == min_value:
                cc_total_power_dict[cc_id] = cluster_cap[cc_id]
        # convert to series
        cc_total_power_ser = pd.Series(cc_total_power_dict)
        
        # store total occupied power of clusters in a pandas series
        cc_energy_ser = newsys_schedule.sum(axis=0)
        #print(cc_occupied_power_ser)
        
        # adding new car schedule average power to total occupied power of clusters
        cc_energy_ser += newcar_schedule.sum()
        
        # calculate occupancy rate of a cluster
        occupancy_rate = cc_energy_ser / cc_total_power_ser
        
        return occupancy_rate.idxmin()



        
        
        
        
    
    
    