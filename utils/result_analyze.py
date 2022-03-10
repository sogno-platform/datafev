# -*- coding: utf-8 -*-
"""
Created on Thu Mar 10 13:45:04 2022

@author: egu
"""

import pandas as pd

def print_results(system, fleet, simperiod, simres, xlfile):
    
    t_start=min(simperiod)
    t_end  =max(simperiod)
    t_delta=simres
    
    with pd.ExcelWriter(xlfile) as writer:
        pow_to_cu_dict = {}
        occ_of_cu_dict = {}
        pow_to_cc_df= pd.DataFrame()
        occup_cc_df = pd.DataFrame()
        
        g2v_cc_r = {}           #Simulation result grid-to-vehicle 
        g2v_cc__ = {}           #Difference between schedule vs simulation result grid-to-vehicle 
        v2x_cc_r = {}           #Simulation result vehicle-to-x
        v2x_cc__ = {}           #Difference between schedule vs simulation result vehicle-to-x     

        for cc_id,cc in sorted(system.clusters.items()):

            cc_ds=cc.cc_dataset
            cc_ds.to_excel(writer, sheet_name='Cluster_' + cc_id)
            
            pow_to_cu_dict[cc_id] = cc.import_profile(t_start,t_end,t_delta)
            pow_to_cc_df[cc_id]   = pow_to_cu_dict[cc_id].sum(axis=1)
            occ_of_cu_dict[cc_id] = cc.occupation_profile(t_start,t_end,t_delta) 
            occup_cc_df[cc_id]    = occ_of_cu_dict[cc_id].sum(axis=1)         
            
            g2v_cc_r[cc_id] = cc_ds['Net G2V [kWh]'].sum()
            unfulfilled_g2v = cc_ds['Scheduled G2V [kWh]']-cc_ds['Net G2V [kWh]']
            g2v_cc__[cc_id] = (unfulfilled_g2v[unfulfilled_g2v>0]).sum()
            
            v2x_cc_r[cc_id] = cc_ds['Total V2X [kWh]'].sum() 
            excessive_v2x   = cc_ds['Total V2X [kWh]']-cc_ds['Scheduled V2G [kWh]']
            v2x_cc__[cc_id] = (excessive_v2x[excessive_v2x>0]).sum()
                              
        power_cu_df = pd.concat(pow_to_cu_dict, axis=1)
        power_cu_df.to_excel(writer, sheet_name='Power_CU')
        
        occup_cu_df = pd.concat(occ_of_cu_dict, axis=1)
        occup_cu_df.to_excel(writer, sheet_name='Occupation_CU')
        
        occup_cc_df.to_excel(writer, sheet_name='Occupation_CC')
        pow_to_cc_df.to_excel(writer, sheet_name='Power_CC')
        
        energy_summary = pd.DataFrame(columns=['Import (kWh)','Cumulative Supply (kWh)','Cumulative V2X (kWh)','Unfulfilled Demand (kWh)', 'Excessive V2X (kWh)'])
        energy_summary['Import (kWh)']            = (pow_to_cc_df * t_delta.seconds / 3600).sum()
        energy_summary['Cumulative Supply (kWh)'] = pd.Series(g2v_cc_r)
        energy_summary['Cumulative V2X (kWh)']    = pd.Series(v2x_cc_r)
        energy_summary['Unfulfilled Demand (kWh)']= pd.Series(g2v_cc__)
        energy_summary['Excessive V2X (kWh)']     = pd.Series(v2x_cc__)
        energy_summary.loc['Total',:]= energy_summary.sum()
        energy_summary.to_excel(writer, sheet_name='Cost')