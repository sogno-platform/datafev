# -*- coding: utf-8 -*-
"""
Created on Sun Oct 23 11:46:52 2022

@author: aytugy
"""

import datetime as dt
import protocols.scenariogeneration.sceneration as sc
import protocols.scenariogeneration.utils as ut

def main():
    """
    Example script for the usage of independent times scenario generator.

    """

    # dep_day_prob_distribution is a list, which should be given to generate_fleet_data_independent_times as an input, consist of two elements:
    # The first element of the list should be the possibility of departure on the same day as arrival.
    # The second element of the list should be the possibility of not departing on the same day as arrival.
    same_day_departure_prob = 0.7
    overnight_stay_prob = 0.3
    dep_day_prob_distribution = [same_day_departure_prob, overnight_stay_prob]
    

    arr_times_dict, dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict = \
        ut.excel_to_sceneration_input_independent_times(file_path=r'C:\Users\aytugy\Desktop\workspace\datafev\src\datafev\tutorials\scenariogeneration\input_generator.xlsx')
        
    ev_df = sc.generate_fleet_data_independent_times(arr_soc_dict=arr_soc_dict, dep_soc_dict=dep_soc_dict, ev_dict=ev_dict,
                                  number_of_evs_per_day=5, startdate=dt.date(2021, 6, 1), enddate=dt.date(2021, 6, 3),
                                  timedelta_in_min=15, diff_arr_dep_in_min=0, arr_times_dict=arr_times_dict,
                                  dep_times_dict=dep_times_dict, dep_day_prob_distribution=dep_day_prob_distribution)

    
    ut.visualize_statistical_time_generation(r'C:\Users\aytugy\Desktop\workspace\datafev\src\datafev\outputs', ev_df, timedelta_in_min=15)
    
    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df['ArrivalTime'] = ev_df['ArrivalTime'].dt.tz_localize(None)
    ev_df['DepartureTime'] = ev_df['DepartureTime'].dt.tz_localize(None)
    ev_df.to_excel(r'C:\Users\aytugy\Desktop\workspace\datafev\src\datafev\outputs\output_generator_independent_times.xlsx')
    
    ut.output_to_sim_input(ev_df, r'C:\Users\aytugy\Desktop\workspace\datafev\src\datafev\outputs\input_simulator_independent_times.xlsx')
    
if __name__ == "__main__":
    main()