# -*- coding: utf-8 -*-
"""
Created on Mon Oct 17 11:39:27 2022

@author: aytugy
"""

import datetime as dt
import protocols.scenariogeneration.read_input as ri
import protocols.scenariogeneration.sceneration as sc

def main(dependent_times=False):
    """
    Example script for the usage of scenario generator.

    Parameters
    ----------
    dependent_times : bool, optional
        Scenario generator has the ability to generate scenarios from two different types of inputs:
            1. Independent arrival and departure times:
                The statistical data of arrival and departure times are independent.
                The user must provide two different independent statistical distribution inputs for both arrival and departure times.
                If the boolean is False:
                    Excel inputs will be converted into appropriate inputs to the scenario function for independent arrival and departure times use.
            2. Dependent arrival and departure times:
                The user must provide a single statistical distribution input for arrival and departure times. 
                The relationship between arrival and departure times is assumed to be predefined in that provided input.
                If the boolean is True:
                    Excel inputs will be converted into appropriate inputs to the scenario function for dependent arrival and departure times use.
        The default is False.

    Returns
    -------
    None.

    """

    #TODO: explain the parameters below
    same_day_departure_prob = 0.7
    overnight_stay_prob = 0.3
    dep_day_prob_distribution = [same_day_departure_prob, overnight_stay_prob]
    
    #TODO: should we seperate the scenario generation tutorials for these two cases
    if dependent_times is False:
        # independent times
        arr_times_dict, dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict = \
            ri.excel_to_sceneration_input(file_path='input_generator.xlsx',
                                          dependent_times=False)

        ev_df = sc.generate_fleet_data(arr_soc_dict=arr_soc_dict, dep_soc_dict=dep_soc_dict, ev_dict=ev_dict,
                                      number_of_evs=5,
                                     startdate=dt.date(2021, 6, 1), enddate=dt.date(2021, 6, 3),
                                     timedelta_in_min=15, diff_arr_dep_in_min=0,
                                     dependent_times=False, arr_times_dict=arr_times_dict,
                                     dep_times_dict=dep_times_dict, times_dict=None, arr_dep_times_dict=None,
                                     dep_day_prob_distribution=dep_day_prob_distribution)
    else:
        # dependent times
        times_dict, arr_dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict = \
            ri.excel_to_sceneration_input(file_path='input_generator.xlsx',
                                          dependent_times=True)

        ev_df = sc.generate_fleet_data(arr_soc_dict=arr_soc_dict, dep_soc_dict=dep_soc_dict, ev_dict=ev_dict,
                                     number_of_evs=5,
                                     startdate=dt.date(2021, 6, 1), enddate=dt.date(2021, 6, 3),
                                     timedelta_in_min=15, diff_arr_dep_in_min=0,
                                     dependent_times=True, arr_times_dict=None,
                                     dep_times_dict=None, times_dict=times_dict,
                                     arr_dep_times_dict=arr_dep_times_dict,
                                     dep_day_prob_distribution=dep_day_prob_distribution)
    
    sc.visualize_statistical_time_generation('output_generator/', ev_df, timedelta_in_min=15)
    
    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df['ArrivalTime'] = ev_df['ArrivalTime'].dt.tz_localize(None)
    ev_df['DepartureTime'] = ev_df['DepartureTime'].dt.tz_localize(None)
    ev_df.to_excel("output_generator.xlsx")          
    
    sc.output_to_sim_input(ev_df, 'input_simulator.xlsx')
    
if __name__ == "__main__":
    main(dependent_times=False)