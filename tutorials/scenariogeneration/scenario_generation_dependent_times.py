# -*- coding: utf-8 -*-
"""
Created on Sun Oct 23 11:50:42 2022

@author: aytugy
"""

import datetime as dt
import protocols.scenariogeneration.sceneration as sc
import protocols.scenariogeneration.utils as ut

def main():
    """
    Example script for the usage of dependent times scenario generator.

    """
    
    times_dict, arr_dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict = \
        ut.excel_to_sceneration_input_dependent_times(file_path=r'C:\Users\aytugy\Desktop\workspace\charger-clusters\tutorials\scenariogeneration\input_generator.xlsx')

    ev_df = sc.generate_fleet_data_dependent_times(arr_soc_dict=arr_soc_dict, dep_soc_dict=dep_soc_dict, ev_dict=ev_dict,
                                 number_of_evs=5, startdate=dt.date(2021, 6, 1), enddate=dt.date(2021, 6, 3),
                                 timedelta_in_min=15, diff_arr_dep_in_min=0, times_dict=times_dict,
                                 arr_dep_times_dict=arr_dep_times_dict)
    
    ut.visualize_statistical_time_generation('output_generator/dependent_times/', ev_df, timedelta_in_min=15)
    
    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df['ArrivalTime'] = ev_df['ArrivalTime'].dt.tz_localize(None)
    ev_df['DepartureTime'] = ev_df['DepartureTime'].dt.tz_localize(None)
    ev_df.to_excel("output_generator/dependent_times/output_generator_dependent_times.xlsx")          
    
    ut.output_to_sim_input(ev_df, 'output_generator/dependent_times/input_simulator_dependent_times.xlsx')
    
if __name__ == "__main__":
    main()