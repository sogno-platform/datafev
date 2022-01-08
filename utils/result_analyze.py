import pandas as pd

def print_results(cs, ev_fleet, period, energy_price, xlfile):
    
    t_start=min(period)
    t_end  =max(period)
    t_delta=period[1]-period[0]
    
    with pd.ExcelWriter(xlfile) as writer:
        pow_to_cu_dict = {}
        occup_cu_dict  = {}
        pow_to_cc_df= pd.DataFrame()
        occup_cc_df = pd.DataFrame()
        csu_cc_dict = {} 
        dsh_cc_dict = {}
        v2x_cc_dict = {}

        for cc_id in sorted(cs.clusters.keys()):

            pow_to_cu_dict[cc_id] = pd.DataFrame()
            occup_cu_dict[cc_id] = pd.DataFrame()
            cc = cs.clusters[cc_id]
            cc_ds=cc.cc_dataset
            cc_ds.to_excel(writer, sheet_name='Cluster_' + cc_id)
               
            for cu_id in sorted(cc.cu.keys()):
                cu = cc.cu[cu_id]
                pow_to_cu_dict[cc_id][cu_id] = cu.consumed_power[t_start:t_end]
                occup_cu_dict[cc_id][cu_id]  = cu.occupation_record(t_start,t_end,t_delta)
            pow_to_cc_df[cc_id] = pow_to_cu_dict[cc_id].sum(axis=1)
            occup_cc_df[cc_id] = occup_cu_dict[cc_id].sum(axis=1)
            csu_cc_dict[cc_id] = cc_ds['Charged Energy [kWh]'].sum() 
            dsh_cc_dict[cc_id] = ((cc_ds['Feasible Target SOC']-cc_ds['Leave SOC'])*cc_ds['Car Battery Capacity']/3600).sum()
            
            cc_v2g=0
            for entry_id in cc_ds.index:
                ev_id  =cc_ds.loc[entry_id,'Car ID']
                ev     =ev_fleet[ev_id]
                ev_v2x =(pd.Series(ev.v2x)* t_delta.seconds / 3600).sum()
                cc_v2g+=ev_v2x
            v2x_cc_dict[cc_id] = cc_v2g
                
        power_cu_df = pd.concat(pow_to_cu_dict, axis=1)
        occup_cu_df = pd.concat(occup_cu_dict, axis=1)
        #pow_to_cc_df['Total'] = pow_to_cc_df.sum(axis=1).copy()

        occup_cu_df.to_excel(writer, sheet_name='Occupation_CU')
        power_cu_df.to_excel(writer, sheet_name='Power_CU')
        occup_cc_df.to_excel(writer, sheet_name='Occupation_CC')
        pow_to_cc_df.to_excel(writer, sheet_name='Power_CC')
        

        energy_summary = pd.DataFrame(columns=['Import (kWh)','Cost of Import (EUR)', 'Cumulative Supply (kWh)','Unfulfilled Demand (kWh)', 'V2X Utilization (kWh)'])
        energy_summary['Import (kWh)']            = (pow_to_cc_df * t_delta.seconds / 3600).sum()
        energy_summary['Cost of Import (EUR)']    = (pow_to_cc_df.mul(energy_price/1000)).sum()
        energy_summary['Cumulative Supply (kWh)'] = pd.Series(csu_cc_dict)
        energy_summary['Unfulfilled Demand (kWh)']= pd.Series(dsh_cc_dict)
        energy_summary['V2X Utilization (kWh)']   = pd.Series(v2x_cc_dict )
        energy_summary.loc['Total',:]= energy_summary.sum()
        energy_summary.to_excel(writer, sheet_name='Cost')