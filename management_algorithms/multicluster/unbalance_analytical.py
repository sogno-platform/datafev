# -*- coding: utf-8 -*-
"""
Created on Tue Jul  6 11:52:12 2021

@author: egu
"""

import pandas as pd

def minimize_cluster_unabalance(actual_schedule,newcar_schedule,candidate_clusters):

    unbt={}
    
    for c in candidate_clusters:
        
        newsys_schedule=actual_schedule.copy()
        newsys_schedule[c]+=newcar_schedule
                
        unb_=0
        for t in newsys_schedule.index:
            load_t=newsys_schedule.loc[t]
            unb_ar=load_t.values-load_t.values[:,None]
            #unb.append(sum(unb_ar[unb_ar>0]))
            unb_+=sum(unb_ar[unb_ar>0])
            
        #unbl[c]=unb
        unbt[c]=unb_
        
    tot_unb=pd.Series(unbt)

    #print(tot_unb.idxmin())
    return tot_unb.idxmin()


def minimize_cluster_capacity_violation(actual_schedule,newcar_schedule,candidate_clusters,cluster_cap):
    
    test_df=actual_schedule.copy()
    for c in candidate_clusters:
        test_df[c]+=newcar_schedule
        
        
    loading    =test_df/cluster_cap
    overloading=loading.applymap(lambda x:x-1 if x>1 else 0)
    
    #TODO: Add another check for assigning to the least (normalized) populated cluster
    
        
        
        
        
        
    
    
    