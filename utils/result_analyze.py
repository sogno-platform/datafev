import pandas as pd

def print_results(cs, xlfile, t_delta):
    with pd.ExcelWriter(xlfile) as writer:
        power_cu_dict = {}
        occup_cu_dict = {}
        power_cc_df = pd.DataFrame()
        occup_cc_df = pd.DataFrame()

        for cc_id in sorted(cs.clusters.keys()):

            power_cu_dict[cc_id] = pd.DataFrame()
            occup_cu_dict[cc_id] = pd.DataFrame()
            cc = cs.clusters[cc_id]
            cc.cc_dataset.to_excel(writer, sheet_name='Cluster_' + cc_id)

            for cu_id in sorted(cc.cu.keys()):
                cu = cc.cu[cu_id]
                power_cu_dict[cc_id][cu_id] = pd.Series(cu.supplied_power)
                occup_cu_dict[cc_id][cu_id] = pd.Series(cu.occupation)
            power_cc_df[cc_id] = power_cu_dict[cc_id].sum(axis=1)
            occup_cc_df[cc_id] = occup_cu_dict[cc_id].sum(axis=1)

        power_cu_df = pd.concat(power_cu_dict, axis=1)
        occup_cu_df = pd.concat(occup_cu_dict, axis=1)
        power_cc_df['Total'] = power_cc_df.sum(axis=1).copy()

        occup_cu_df.to_excel(writer, sheet_name='Occupation_CU')
        power_cu_df.to_excel(writer, sheet_name='Power_CU')
        occup_cc_df.to_excel(writer, sheet_name='Occupation_CC')
        power_cc_df.to_excel(writer, sheet_name='Power_CC')

        energy_summary = {}
        energy_summary['Import'] = (power_cc_df['Total'] * t_delta.seconds / 3600).sum()
        energy_summary['Bill'] = (power_cc_df['Total'] * cs.tou_price[power_cc_df.index] / 1000).sum()
        energy_summary_df = pd.Series(energy_summary)

        energy_summary_df.to_excel(writer, sheet_name='Cost')