# -*- coding: utf-8 -*-
"""
Created on Mon Oct 17 11:37:57 2022

@author: aytugy
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import datetime as dt
import decimal
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import os


def generate_fleet_data(arr_soc_dict, dep_soc_dict, ev_dict, number_of_evs,
                        startdate=dt.date(2020, 5, 17), enddate=dt.date(2020, 5, 19), timedelta_in_min=15,
                        diff_arr_dep_in_min=0, dependent_times=False, arr_times_dict=None, dep_times_dict=None,
                        times_dict=None, arr_dep_times_dict=None, dep_day_prob_distribution=None
                        ):
    """
    This function is executed to generate a simulation scenario with given statistical EV fleet data.
    
    It has the ability to generate scenarios from two different types of inputs:
        1. Independent arrival and departure times:
            The statistical data of arrival and departure times are independent.
            The user must provide two different independent statistical distribution inputs for both arrival and departure times.
        2. Dependent arrival and departure times:
            The user must provide a single statistical distribution input for arrival and departure times. 
            The relationship between arrival and departure times is assumed to be predefined in that provided input.

    Parameters
    ----------
    arr_soc_dict : dict
        SoC nested dictionaries for arrival.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    dep_soc_dict : dict
        SoC nested dictionaries for departure.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    ev_dict : dict
        EV nested dictionary.
        keys: EV models, values: their data and probability.
    number_of_evs : int
        This parameter has different description for the two situations:
            1. If user is using independent arrival and departure times:
                Number of desired EVs per day for the simulation
            2. If the user is using dependent arrival and departure times:
                Number of desired EVs for the simulation 
    startdate : datetime.date, optional
        The start date of the simulation. The default is dt.date(2020, 5, 17).
    enddate : TYPE, datetime.date
        The end date of the simulation. The default is dt.date(2020, 5, 19).
    timedelta_in_min : int, optional
        Resolution of the simulation in minutes. The default is 15.
    diff_arr_dep_in_min : int, optional
        Minimum time between arrival and departure for each EV in minutes. The default is 0.
    dependent_times : bool, optional
        1. If true: Dependent arrival and departure times is to be used.
        2. If false: Independent arrival and departure times to be used.
        The default is False.
    arr_times_dict : dict, optional
        Only to be given, if using independent arrival and departure times!
        Arrival times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and arrival probabilities}.
        The default is None.
    dep_times_dict : dict, optional
        Only to be given, if using independent arrival and departure times!
        Departure times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and departure probabilities}.
        The default is None..
    times_dict : dict, optional
        Only to be given, if using dependent arrival and departure times!
        Arrival-departure time combinations nested dictionary.
        keys: Arrival-departure time combination identifier, values: time upper and lower bounds.
        The default is None.
    arr_dep_times_dict : dict, optional
        Only to be given, if using dependent arrival and departure times!
        Arrival-departure time combinations' probabilities nested dictionary.
        keys: Arrival-departure time combination identifier, values: their probabilities.
        The default is None.
    dep_day_prob_distribution : list
        Only to be given, if using independent arrival and departure times!
        List consist of two elements:
            The first element of the list should be the possibility of departure on the same day as arrival.
            The second element of the list should be the possibility of not departing on the same day as arrival.
    Returns
    -------
    gen_ev_df : pandas.core.frame.DataFrame
        Generated EV dataset for future use in any simulation.

    """
    
    # Create date list
    date_list = pd.date_range(startdate, enddate - timedelta(days=1), freq='d')

    # Convert date to datetime format for future use
    temp_time = dt.datetime.min.time()
    endtime = dt.datetime.combine(enddate, temp_time)

    ###################################################################################################################
    # Generating arrival and departure times
    ###################################################################################################################

    if dependent_times is False:
        # Time lowerbound arrays to be used in random choice method
        arr_times_weekday_df = pd.DataFrame(arr_times_dict['Weekday']).T
        arr_times_weekend_df = pd.DataFrame(arr_times_dict['Weekend']).T
        arr_time_lowerb_array = arr_times_weekday_df['TimeLowerBound'].to_numpy()
        dep_times_weekday_df = pd.DataFrame(dep_times_dict['Weekday']).T
        dep_times_weekend_df = pd.DataFrame(dep_times_dict['Weekend']).T
        dep_time_lowerb_array = dep_times_weekday_df['TimeLowerBound'].to_numpy()

        # Arrival/departure probability lists
        weekday_arr_prob_list = arr_times_weekday_df['Probability'].to_list()
        weekend_arr_prob_list = arr_times_weekend_df['Probability'].to_list()
        weekday_dep_prob_list = dep_times_weekday_df['Probability'].to_list()
        weekend_dep_prob_list = dep_times_weekend_df['Probability'].to_list()
        # Arrival and departure time bounds dictionary for future use
        arr_time_bounds_dict = pd.Series(arr_times_weekday_df["TimeUpperBound"].values,
                                         index=arr_times_weekday_df["TimeLowerBound"]).to_dict()
        dep_time_bounds_dict = pd.Series(dep_times_weekday_df["TimeUpperBound"].values,
                                         index=dep_times_weekday_df["TimeLowerBound"]).to_dict()
        # Dictionary -- keys: dates, values: assigned arrival time intervals
        pre_arr_assignment = {}
        # Loop through dates and assign generated datetimes
        # Create given number of EVs per each simulation day
        number_of_evs_per_day = number_of_evs
        for date in date_list:
            # If date is weekday
            if date.weekday() <= 4:
                pre_arr_assignment[date] = np.random.choice(arr_time_lowerb_array, number_of_evs_per_day,
                                                             p=weekday_arr_prob_list)
            else:
                pre_arr_assignment[date] = np.random.choice(arr_time_lowerb_array, number_of_evs_per_day,
                                                             p=weekend_arr_prob_list)
        # Dictionary -- keys: dates, values: assigned arrival time stamp
        # Assign possible arrival datetimes
        # Find a datetime which satisfies following conditions
        # 1. arrival at least one timedelta earlier than end time
        # 2. ...
        arr_assignment = {}
        ev_id = 0
        # Dictionary, keys: EV ids, values: assigned arrival lower bounds
        # This dictionary will be used when calculating the arrival-dependent departure times
        ev_arr_time_lowerbs = {}
        for day, pre_assingment in pre_arr_assignment.items():
            for arr_time_lowerb in pre_assingment:
                # datetime.time objects to datetime.datetime
                arr_datetime_lowerb = dt.datetime.combine(day, arr_time_lowerb)
                arr_datetime_upperb = dt.datetime.combine(day, arr_time_bounds_dict[arr_time_lowerb])
                if arr_datetime_upperb < arr_datetime_lowerb:
                    arr_datetime_upperb += dt.timedelta(days=1)
                while True:
                    time_lst = generate_time_list(arr_datetime_lowerb, arr_datetime_upperb, timedelta_in_min, day)
                    arrival_possibility = np.random.choice(time_lst, 1)[0]
                    if arrival_possibility < endtime - timedelta(minutes=timedelta_in_min):
                        arr_assignment[ev_id] = arrival_possibility
                        ev_arr_time_lowerbs[ev_id] = arr_datetime_upperb
                        ev_id += 1
                        break
        # Assign possible departures from statistic input data
        # Find a datetime which satisfies following conditions
        # 1. departure after arrival
        # 2. there must be at least two hours difference between arrival and departure
        # 3. ...
        dep_assignment = {}
        for ev_id, arrival_dt in arr_assignment.items():
            # Randomly select EV to stay overnight or leave on the same day as arrival
            # according to the probability distribution
            assigned_date = np.random.choice([arrival_dt, arrival_dt + dt.timedelta(days=1)], 1,
                                             dep_day_prob_distribution)[0]
            # If date is weekday
            if arrival_dt.weekday() <= 4:
                while True:
                    dep_time_lowerb = np.random.choice(dep_time_lowerb_array, 1, p=weekday_dep_prob_list)[0]
                    dep_datetime_lowerb = dt.datetime.combine(assigned_date, dep_time_lowerb)
                    dep_datetime_upperb = dt.datetime.combine(assigned_date, dep_time_bounds_dict[dep_time_lowerb])
                    if dep_datetime_upperb < dep_datetime_lowerb:
                        dep_datetime_upperb += dt.timedelta(days=1)
                    time_lst = generate_time_list(dep_datetime_lowerb, dep_datetime_upperb, timedelta_in_min, assigned_date)
                    departure_possibility = np.random.choice(time_lst, 1)[0]
                    if departure_possibility > assigned_date + dt.timedelta(minutes=diff_arr_dep_in_min):
                        if departure_possibility <= endtime:
                            dep_assignment[ev_id] = departure_possibility
                        else:
                            dep_assignment[ev_id] = endtime
                        break
            else:
                while True:
                    dep_time_lowerb = np.random.choice(dep_time_lowerb_array, 1, p=weekend_dep_prob_list)[0]
                    dep_datetime_lowerb = dt.datetime.combine(assigned_date, dep_time_lowerb)
                    dep_datetime_upperb = dt.datetime.combine(assigned_date, dep_time_bounds_dict[dep_time_lowerb])
                    if dep_datetime_upperb < dep_datetime_lowerb:
                        dep_datetime_upperb += dt.timedelta(days=1)
                    time_lst = generate_time_list(dep_datetime_lowerb, dep_datetime_upperb, timedelta_in_min, assigned_date)
                    departure_possibility = np.random.choice(time_lst, 1)[0]
                    if departure_possibility > assigned_date + dt.timedelta(minutes=diff_arr_dep_in_min):
                        dep_assignment[ev_id] = departure_possibility
                        break
    else:  # if using dependent times
        prob_list = list(arr_dep_times_dict.values())
        # Time pairs dictionary, keys: keys to be used in choice function, values: arr/dep timeID pairs
        time_pairs_dict = {}
        for index, value in enumerate(list(arr_dep_times_dict.keys())):
            time_pairs_dict[index] = value
        # Pre assignment list, consist of assigned time pair's ID
        pre_assignment = list(np.random.choice(list(time_pairs_dict.keys()), number_of_evs, p=prob_list))
        # Dictionary -- keys: dates, values: assigned time stamps
        # Assign possible arrival datetimes
        # Find a datetime which satisfies following conditions
        # 1. arrival at least one timedelta earlier than end time
        # 2. ...
        arr_assignment = {}
        dep_assignment = {}
        ev_id = 0
        # Dictionary, keys: EV ids, values: assigned arrival lower bounds
        # This dictionary will be used when calculating the arrival-dependent departure times
        ev_arr_time_lowerbs = {}
        for time_pair_id in pre_assignment:
            time_pair = time_pairs_dict[time_pair_id]
            # Arrival time
            arr_datetime_lowerb = times_dict[time_pair[0]][0]
            arr_datetime_upperb = times_dict[time_pair[0]][1]
            # Departure time
            dep_datetime_lowerb = times_dict[time_pair[1]][0]
            dep_datetime_upperb = times_dict[time_pair[1]][1]

            # Arrival time        
            arr_time_lst = generate_datetime_list(arr_datetime_lowerb, arr_datetime_upperb, timedelta_in_min)
            # Assign generated departure time if:
            # 1. time difference between arrival and departure is satisfied
            # 2. ...
            while True:
                arrival_possibility = np.random.choice(arr_time_lst, 1)[0]
                if arrival_possibility < endtime - timedelta(minutes=timedelta_in_min):
                    arr_assignment[ev_id] = arrival_possibility
                    ev_arr_time_lowerbs[ev_id] = arr_datetime_upperb
                    # Departure time
                    dep_time_lst = generate_datetime_list(dep_datetime_lowerb, dep_datetime_upperb, timedelta_in_min)
                while True:
                    departure_possibility = np.random.choice(dep_time_lst, 1)[0]
                    # Departure must be after arrival
                    if departure_possibility < arr_assignment[ev_id]:
                        departure_possibility += dt.timedelta(days=1)
                    if departure_possibility > arrival_possibility + dt.timedelta(minutes=diff_arr_dep_in_min):
                        if departure_possibility <= endtime:
                            dep_assignment[ev_id] = departure_possibility
                        # if a car can not be assigned before the simulation end time,
                        # assign end time as departure time
                        else:
                            dep_assignment[ev_id] = endtime
                        break
                ev_id += 1
                break

    # Merge arrival and departure assignments into a pandas dataframe
    ev_assigned_times_dict = {}
    for ev_id in (arr_assignment.keys() | dep_assignment.keys()):
        if ev_id in arr_assignment: ev_assigned_times_dict.setdefault(ev_id, []).append(arr_assignment[ev_id])
        if ev_id in dep_assignment: ev_assigned_times_dict.setdefault(ev_id, []).append(dep_assignment[ev_id])
    gen_ev_df = pd.DataFrame.from_dict(ev_assigned_times_dict, orient='index',
                                         columns=['ArrivalTime', 'DepartureTime'])
    # Localize time entries
    gen_ev_df['ArrivalTime'] = gen_ev_df['ArrivalTime'].dt.tz_localize(tz='GMT+0')
    gen_ev_df['DepartureTime'] = gen_ev_df['DepartureTime'].dt.tz_localize(tz='GMT+0')

    ###################################################################################################################
    # Generating arrival and departure SoCs
    ###################################################################################################################
    # Arrival SoC probabilities
    arr_soc_df = pd.DataFrame(arr_soc_dict).T
    arr_soc_lowerb_array = arr_soc_df['SoCLowerBound'].to_numpy()
    arr_soc_prob_list = arr_soc_df['Probability'].tolist()
    # Departure SoC probabilities
    dep_soc_df = pd.DataFrame(dep_soc_dict).T
    dep_soc_lowerb_array = dep_soc_df['SoCLowerBound'].to_numpy()
    dep_soc_prob_list = dep_soc_df['Probability'].tolist()
    # Arrival and departure SoC bounds dictionary for future use
    arr_soc_bounds_dict = pd.Series(arr_soc_df["SoCUpperBound"].values,
                                     index=arr_soc_df["SoCLowerBound"]).to_dict()
    dep_soc_bounds_dict = pd.Series(dep_soc_df["SoCUpperBound"].values,
                                    index=dep_soc_df["SoCLowerBound"]).to_dict()
    for ev_id, row in gen_ev_df.iterrows():
        # Arrival SoCs
        ev_arr_soc_lowerb = np.random.choice(arr_soc_lowerb_array, 1, p=arr_soc_prob_list)[0]
        ev_arr_soc_possibilities = list(drange(ev_arr_soc_lowerb, arr_soc_bounds_dict[ev_arr_soc_lowerb], '0.001'))
        ev_arr_soc = np.random.choice(ev_arr_soc_possibilities, 1)[0]
        gen_ev_df.at[ev_id, 'ArrivalSoC'] = ev_arr_soc
        # Departure SoCs
        while True:
            # Be sure that departure SoC is higher than arrival
            ev_dep_soc_lowerb = np.random.choice(dep_soc_lowerb_array, 1, p=dep_soc_prob_list)[0]
            if ev_dep_soc_lowerb > ev_arr_soc:
                ev_dep_soc_possibilities = list(
                    drange(ev_dep_soc_lowerb, dep_soc_bounds_dict[ev_dep_soc_lowerb], '0.001'))
                gen_ev_df.at[ev_id, 'DepartureSoC'] = np.random.choice(ev_dep_soc_possibilities, 1)[0]
                break

    ###################################################################################################################
    # Generating EV Data
    ###################################################################################################################
    # EV dictionary to Dataframe
    ev_df = pd.DataFrame(ev_dict).T
    ev_prob_array = ev_df["Probability"].to_numpy()
    ev_model_array = ev_df.index.to_numpy()
    ev_prob_list = ev_prob_array.tolist()

    for ev_id, row in gen_ev_df.iterrows():
        chosen_model = np.random.choice(ev_model_array, 1, p=ev_prob_list)[0]
        gen_ev_df.at[ev_id, 'Model'] = chosen_model
        gen_ev_df.at[ev_id, 'BatteryCapacity'] = ev_df.at[chosen_model, 'BatteryCapacity']
        gen_ev_df.at[ev_id, 'MaxChargingPower'] = ev_df.at[chosen_model, 'MaxChargingPower']
        gen_ev_df.at[ev_id, 'MaxFastChargingPower'] = ev_df.at[chosen_model, 'MaxFastChargingPower']

    ###################################################################################################################
    return gen_ev_df


def generate_time_list(time_lowerb, time_upperb, timedelta_in_min, date):
    """
    Generates a datetime list with the given resolution and given date.

    Parameters
    ----------
    time_lowerb : datetime.datetime
        Start datetime.
    time_upperb : datetime.datetime
        End datetime.
    timedelta_in_min : int
        Resolution in minutes.
    date : datetime.datetime
        Date of the datetimes to be returned.

    Returns
    -------
    times : list
        Datetime list.

    """
    times = []
    times_str_list = [(time_lowerb + timedelta(hours=timedelta_in_min * i / 60)).strftime("%H:%M:%S")
                  for i in range(int((time_upperb - time_lowerb).total_seconds() / 60.0 / timedelta_in_min))]
    for time_str in times_str_list:
        temp_time = dt.datetime.strptime(time_str, '%H:%M:%S')
        time = dt.datetime.combine(date, temp_time.time())
        times.append(time)
    return times


def generate_datetime_list(sdate, edate, timedelta_in_min):
    """
    Generates a datetime list with the given resolution.

    Parameters
    ----------
    sdate : TYPE
        Start datetime.
    edate : TYPE
        End datetime.
    timedelta_in_min : int
        Resolution in minutes.

    Returns
    -------
    datetime_lst : TYPE
        Datetime list.

    """
    diff_delta = edate - sdate  # as timedelta
    number_of_ts = int(diff_delta / dt.timedelta(minutes=timedelta_in_min))
    datetime_lst = []
    new_datetime = sdate
    for n in range(0, number_of_ts):
        datetime_lst.append(new_datetime)
        new_datetime = new_datetime + dt.timedelta(minutes=timedelta_in_min)
    return datetime_lst


def drange(x, y, jump):
    """
    Generate a range from x to y with jump spaces.
    
    Parameters
    ----------
    x : numpy.float64
        Start point.
    y : float
        End point.
    jump : str
        Space between generated jumps.

    Yields
    ------
    decimal.Decimal
        Parts in the equal range of the jump between x and y.

    """

    while x < y:
        yield float(x)
        x = decimal.Decimal(x) + decimal.Decimal(jump)


def visualize_statistical_time_generation(file_path, gen_ev_df, timedelta_in_min=15):
    """
    This method visualizes generated EV arrival and departure data.

    Parameters
    ----------
    file_path : str
        The file path for image files to be saved.
    gen_ev_df : pandas.core.frame.DataFrame
        Output data frame from generate_fleet_data function.
    timedelta_in_min : int, optional
        Resolution of the simulation in minutes. The default is 15.

    Returns
    -------
    None.

    """

    # Create times dicts for arrival and departure Keys: All possible time assignments, Values: number of assigned EVs
    current = dt.datetime(2022, 1, 1)  # arbitrary day
    datetime_lst = [current + timedelta(minutes=m) for m in range(0, 24 * 60, timedelta_in_min)]
    arr_times_dict = {}
    dep_times_dict = {}
    # Initialize with 0
    for item in datetime_lst:
        arr_times_dict[item.strftime("%H:%M")] = 0
        dep_times_dict[item.strftime("%H:%M")] = 0
    for ev_id, row in gen_ev_df.iterrows():
        for time, value in arr_times_dict.items():
            if time == gen_ev_df.at[ev_id, 'ArrivalTime'].strftime("%H:%M"):
                arr_times_dict[time] += 1
        for time, value in dep_times_dict.items():
            if time == gen_ev_df.at[ev_id, 'DepartureTime'].strftime("%H:%M"):
                dep_times_dict[time] += 1
    # Plotting
    # Arrival times of EVs
    arr_times = list(arr_times_dict.keys())
    arr_values = list(arr_times_dict.values())
    plt.title("Arrival Times of EVs", size=16)
    plt.xlabel("Time", size=12)
    plt.ylabel("Number of EVs", size=12)
    plt.bar(arr_times, arr_values, color='g', width=0.4)
    plt.gca().yaxis.set_major_locator(tck.MultipleLocator(1))
    plt.gca().xaxis.set_major_locator(tck.MultipleLocator(10))
    plot_name = 'arrival_times_of_EVs'
    plot_path = os.path.join(file_path, plot_name)
    plt.savefig(plot_path)
    # Clear memory
    plt.clf()
    # Departure times of EVs
    dep_times = list(dep_times_dict.keys())
    dep_values = list(dep_times_dict.values())
    plt.title("Departure Times of EVs", size=16)
    plt.xlabel("Time", size=12)
    plt.ylabel("Number of EVs", size=12)
    plt.bar(dep_times, dep_values, color='r', width=0.4)
    plt.gca().yaxis.set_major_locator(tck.MultipleLocator(1))
    plt.gca().xaxis.set_major_locator(tck.MultipleLocator(10))
    plot_name = 'departure_times_of_EVs'
    plot_path = os.path.join(file_path, plot_name)
    plt.savefig(plot_path)

def output_to_sim_input(sce_output_df, xlfile, dc_power=False):
    '''
    This function makes the electric vehicle information generated from statistical data available to the different simulation tools in the project

    Parameters
    ----------
    sce_output_df : pandas.core.frame.DataFrame
        Output data frame from generate_fleet_data function.
    xlfile : str
        Desired name of the output excel file.
    dc_power : bool, optional
        This parameter indicates whether dc or ac will be used as charging power in the simulation. 
        The default is False.

    Returns
    -------
    None.

    '''

    sim_input_df=pd.DataFrame(columns=['Battery Capacity (kWh)','p_max_ch',
                                       'p_max_ds','Real Arrival Time','Real Arrival SOC', 
                                       'Estimated Departure Time', 'Target SOC @ Estimated Departure Time'])
    
    sim_input_df['Battery Capacity (kWh)'] = sce_output_df['BatteryCapacity'].values
    sim_input_df['Real Arrival Time'] = sce_output_df['ArrivalTime'].values
    sim_input_df['Real Arrival SOC'] = sce_output_df['ArrivalSoC'].values
    sim_input_df['Estimated Departure Time'] = sce_output_df['DepartureTime'].values   
    sim_input_df['Target SOC @ Estimated Departure Time'] = sce_output_df['DepartureSoC'].values  
    if dc_power is False: # use AC-charging-powers
        sim_input_df['p_max_ch'] = sce_output_df['MaxChargingPower'].values
        sim_input_df['p_max_ds'] = sce_output_df['MaxChargingPower'].values
    else: # use DC-fast-charging-powers
        sim_input_df['p_max_ch'] = sce_output_df['MaxFastChargingPower'].values
        sim_input_df['p_max_ds'] = sce_output_df['MaxFastChargingPower'].values
    # Simulation input dataframe to excel file
    sim_input_df.to_excel(xlfile)