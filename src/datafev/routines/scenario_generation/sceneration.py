# The datafev framework

# Copyright (C) 2022,
# Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC),
# RWTH Aachen University

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import pandas as pd
import numpy as np
from datetime import timedelta
import datetime as dt
import datafev.routines.scenario_generation.utils as ut


def generate_fleet_from_simple_pdfs(
    arr_times_dict,
    dep_times_dict,
    arr_soc_dict,
    dep_soc_dict,
    ev_dict,
    number_of_evs_per_day,
    startdate,
    enddate,
    timedelta_in_min=15,
    diff_arr_dep_in_min=0,
):
    """
    This function is executed to generate a simulation scenario with given statistical EV fleet data,
    which has independent arrival and departure times and SoCs.
    The user must provide two different independent statistical distribution inputs
    for both arrival and departure times and SoCs.

    Parameters
    ----------
    arr_times_dict : dict
        Arrival times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and arrival probabilities}.
        The default is None.
    dep_times_dict : dict
        Departure times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and departure probabilities}.
        The default is None.
    arr_soc_dict : dict
        SoC nested dictionaries for arrival.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    dep_soc_dict : dict
        SoC nested dictionaries for departure.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    ev_dict : dict
        EV nested dictionary.
        keys: EV models, values: their data and probability.
    number_of_evs_per_day : int
        Number of desired EVs per day for the simulation.
    startdate : datetime.date, optional
        The start date of the simulation.
    enddate : datetime.date, optional
        The end date of the simulation.
    timedelta_in_min : int
        Resolution of the simulation in minutes. The default is 15.
    diff_arr_dep_in_min : int, optional
        Minimum time between arrival and departure for each EV in minutes. The default is 0.

    Returns
    -------
    gen_ev_df : pandas.core.frame.DataFrame
        Generated EV dataset for future use in any simulation.

    """

    # Create date list
    date_list = pd.date_range(startdate, enddate, freq="d")

    # Convert date to datetime format for future use
    temp_time = dt.datetime.min.time()
    endtime = dt.datetime.combine(enddate + timedelta(days=1), temp_time)

    ###################################################################################################################
    # Generating arrival and departure times
    ###################################################################################################################

    # Time lowerbound arrays to be used in random choice method
    arr_times_weekday_df = pd.DataFrame(arr_times_dict["Weekday"]).T
    arr_times_weekend_df = pd.DataFrame(arr_times_dict["Weekend"]).T
    arr_time_lowerb_array = arr_times_weekday_df["TimeLowerBound"].to_numpy()
    dep_times_weekday_df = pd.DataFrame(dep_times_dict["Weekday"]).T
    dep_times_weekend_df = pd.DataFrame(dep_times_dict["Weekend"]).T
    dep_time_lowerb_array = dep_times_weekday_df["TimeLowerBound"].to_numpy()

    # Arrival/departure probability lists
    weekday_arr_prob_list = arr_times_weekday_df["Probability"].to_list()
    weekend_arr_prob_list = arr_times_weekend_df["Probability"].to_list()
    weekday_dep_prob_list = dep_times_weekday_df["Probability"].to_list()
    weekend_dep_prob_list = dep_times_weekend_df["Probability"].to_list()

    # Arrival and departure time bounds dictionary for future use
    arr_time_bounds_dict = pd.Series(
        arr_times_weekday_df["TimeUpperBound"].values,
        index=arr_times_weekday_df["TimeLowerBound"],
    ).to_dict()
    dep_time_bounds_dict = pd.Series(
        dep_times_weekday_df["TimeUpperBound"].values,
        index=dep_times_weekday_df["TimeLowerBound"],
    ).to_dict()

    # Dictionary -- keys: dates, values: assigned arrival time intervals
    pre_arr_assignment = {}
    # Loop through dates and assign generated datetimes
    # Create given number of EVs per each simulation day
    for date in date_list:
        # If date is weekday
        if date.weekday() <= 4:
            pre_arr_assignment[date] = np.random.choice(
                arr_time_lowerb_array, number_of_evs_per_day, p=weekday_arr_prob_list
            )
        else:
            pre_arr_assignment[date] = np.random.choice(
                arr_time_lowerb_array, number_of_evs_per_day, p=weekend_arr_prob_list
            )

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
            arr_datetime_upperb = dt.datetime.combine(
                day, arr_time_bounds_dict[arr_time_lowerb]
            )
            if arr_datetime_upperb < arr_datetime_lowerb:
                arr_datetime_upperb += dt.timedelta(days=1)
            while True:
                time_lst = ut.generate_time_list(
                    arr_datetime_lowerb, arr_datetime_upperb, timedelta_in_min, day
                )
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
        # If date is weekday
        if arrival_dt.weekday() <= 4:
            while True:
                dep_time_lowerb = np.random.choice(
                    dep_time_lowerb_array, 1, p=weekday_dep_prob_list
                )[0]
                dep_datetime_lowerb = dt.datetime.combine(arrival_dt, dep_time_lowerb)
                dep_datetime_upperb = dt.datetime.combine(
                    arrival_dt, dep_time_bounds_dict[dep_time_lowerb]
                )
                if dep_datetime_upperb < dep_datetime_lowerb:
                    dep_datetime_upperb += dt.timedelta(days=1)
                time_lst = ut.generate_time_list(
                    dep_datetime_lowerb,
                    dep_datetime_upperb,
                    timedelta_in_min,
                    arrival_dt,
                )
                departure_possibility = np.random.choice(time_lst, 1)[0]
                if departure_possibility > arrival_dt + dt.timedelta(
                    minutes=diff_arr_dep_in_min
                ):
                    if departure_possibility > arrival_dt:
                        dep_assignment[ev_id] = departure_possibility
                        break
                    else:
                        departure_possibility = arrival_dt + dt.timedelta(days=1)
                        dep_assignment[ev_id] = departure_possibility
                        break
        else:
            while True:
                dep_time_lowerb = np.random.choice(
                    dep_time_lowerb_array, 1, p=weekend_dep_prob_list
                )[0]
                dep_datetime_lowerb = dt.datetime.combine(arrival_dt, dep_time_lowerb)
                dep_datetime_upperb = dt.datetime.combine(
                    arrival_dt, dep_time_bounds_dict[dep_time_lowerb]
                )
                if dep_datetime_upperb < dep_datetime_lowerb:
                    dep_datetime_upperb += dt.timedelta(days=1)
                time_lst = ut.generate_time_list(
                    dep_datetime_lowerb,
                    dep_datetime_upperb,
                    timedelta_in_min,
                    arrival_dt,
                )
                departure_possibility = np.random.choice(time_lst, 1)[0]
                if departure_possibility > arrival_dt + dt.timedelta(
                    minutes=diff_arr_dep_in_min
                ):
                    if departure_possibility > arrival_dt:
                        dep_assignment[ev_id] = departure_possibility
                        break
                    else:
                        departure_possibility = arrival_dt + dt.timedelta(days=1)
                        dep_assignment[ev_id] = departure_possibility
                        break

    # Merge arrival and departure assignments into a pandas dataframe
    ev_assigned_times_dict = {}
    for ev_id in arr_assignment.keys() | dep_assignment.keys():
        if ev_id in arr_assignment:
            ev_assigned_times_dict.setdefault(ev_id, []).append(arr_assignment[ev_id])
        if ev_id in dep_assignment:
            ev_assigned_times_dict.setdefault(ev_id, []).append(dep_assignment[ev_id])
    gen_ev_df = pd.DataFrame.from_dict(
        ev_assigned_times_dict, orient="index", columns=["ArrivalTime", "DepartureTime"]
    )

    # Localize time entries
    gen_ev_df["ArrivalTime"] = gen_ev_df["ArrivalTime"].dt.tz_localize(tz="GMT+0")
    gen_ev_df["DepartureTime"] = gen_ev_df["DepartureTime"].dt.tz_localize(tz="GMT+0")

    ###################################################################################################################
    # Generating arrival and departure SoCs
    ###################################################################################################################

    # Arrival SoC probabilities
    arr_soc_df = pd.DataFrame(arr_soc_dict).T
    arr_soc_lowerb_array = arr_soc_df["SoCLowerBound(%)"].to_numpy()
    arr_soc_prob_list = arr_soc_df["Probability"].tolist()

    # Departure SoC probabilities
    dep_soc_df = pd.DataFrame(dep_soc_dict).T
    dep_soc_lowerb_array = dep_soc_df["SoCLowerBound(%)"].to_numpy()
    dep_soc_prob_list = dep_soc_df["Probability"].tolist()

    # Arrival and departure SoC bounds dictionary for future use
    arr_soc_bounds_dict = pd.Series(
        arr_soc_df["SoCUpperBound(%)"].values, index=arr_soc_df["SoCLowerBound(%)"]
    ).to_dict()
    dep_soc_bounds_dict = pd.Series(
        dep_soc_df["SoCUpperBound(%)"].values, index=dep_soc_df["SoCLowerBound(%)"]
    ).to_dict()
    for ev_id, row in gen_ev_df.iterrows():
        # Arrival SoCs
        ev_arr_soc_lowerb = np.random.choice(
            arr_soc_lowerb_array, 1, p=arr_soc_prob_list
        )[0]
        ev_arr_soc_possibilities = list(
            ut.drange(
                ev_arr_soc_lowerb, arr_soc_bounds_dict[ev_arr_soc_lowerb], "0.001"
            )
        )
        ev_arr_soc = np.random.choice(ev_arr_soc_possibilities, 1)[0]
        gen_ev_df.at[ev_id, "ArrivalSoC"] = ev_arr_soc
        # Departure SoCs
        while True:
            # Be sure that departure SoC is higher than arrival
            ev_dep_soc_lowerb = np.random.choice(
                dep_soc_lowerb_array, 1, p=dep_soc_prob_list
            )[0]
            if ev_dep_soc_lowerb > ev_arr_soc:
                ev_dep_soc_possibilities = list(
                    ut.drange(
                        ev_dep_soc_lowerb,
                        dep_soc_bounds_dict[ev_dep_soc_lowerb],
                        "0.001",
                    )
                )
                gen_ev_df.at[ev_id, "DepartureSoC"] = np.random.choice(
                    ev_dep_soc_possibilities, 1
                )[0]
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
        gen_ev_df.at[ev_id, "Model"] = chosen_model
        gen_ev_df.at[ev_id, "BatteryCapacity(kWh)"] = ev_df.at[
            chosen_model, "BatteryCapacity(kWh)"
        ]
        gen_ev_df.at[ev_id, "MaxChargingPower(kW)"] = ev_df.at[
            chosen_model, "MaxChargingPower(kW)"
        ]
        gen_ev_df.at[ev_id, "MaxFastChargingPower(kW)"] = ev_df.at[
            chosen_model, "MaxFastChargingPower(kW)"
        ]

    ###################################################################################################################
    return gen_ev_df


def generate_fleet_from_conditional_pdfs(
    times_dict,
    times_prob_dict,
    soc_dict,
    soc_prob_dict,
    ev_dict,
    number_of_evs,
    endtime,
    timedelta_in_min=15,
    diff_arr_dep_in_min=0,
):
    """
    This function is executed to generate a simulation scenario with given statistical EV fleet data,
    which has dependent arrival and departure times and SoCs.
    The relationships between arrival and departure times and SoCs are assumed to be predefined in that provided input.

    Parameters
    ----------

    times_dict : dict, optional
        Arrival-departure time combinations nested dictionary.
        keys: Arrival-departure time combination identifier, values: time upper and lower bounds.
        The default is None.
    times_prob_dict : dict, optional
        Arrival-departure time combinations' probabilities nested dictionary.
        keys: Arrival-departure time combination identifier, values: their probabilities.
        The default is None.
    soc_dict : dict
        Arrival-departure SoC combinations nested dictionary.
        keys: SoC Identifier, values: SoC upper and lower bounds.
    soc_prob_dict : dict
        Arrival-departure SoC combinations' probabilities nested dictionary.
        keys: Arrival-departure SoC combination identifier, values: their probabilities.
    ev_dict : dict
        EV nested dictionary.
        keys: EV models, values: their data and probability.
    number_of_evs : int
        This parameter has different description for the two situations:
            - If user is using independent arrival and departure times: Number of desired EVs per day for the simulation.
            - If the user is using dependent arrival and departure times: Number of desired EVs for the simulation.
    endtime : datetime.datetime
        The last timestamp of the simulation.
    timedelta_in_min : int
        Resolution of the simulation in minutes. The default is 15.
    diff_arr_dep_in_min : int, optional
        Minimum time between arrival and departure for each EV in minutes. The default is 0.

    Returns
    -------
    gen_ev_df : pandas.core.frame.DataFrame
        Generated EV dataset for future use in any simulation.

    """

    ###################################################################################################################
    # Generating arrival and departure times
    ###################################################################################################################

    times_prob_list = list(times_prob_dict.values())

    # Time pairs dictionary, keys: keys to be used in choice function, values: arr/dep timeID pairs
    time_pairs_dict = {}
    for index, value in enumerate(list(times_prob_dict.keys())):
        time_pairs_dict[index] = value

    # Pre assignment list, consist of assigned time pair's ID
    times_pre_assignment = list(
        np.random.choice(list(time_pairs_dict.keys()), number_of_evs, p=times_prob_list)
    )

    # Assign possible arrival datetimes
    # Find a datetime which satisfies following conditions
    # 1. arrival at least one timedelta earlier than end time
    # 2. ...
    arr_assignment = {}
    dep_assignment = {}
    ev_id = 0

    # Dictionary, keys: EV ids, values: assigned arrival lower bounds
    ev_arr_time_lowerbs = {}
    for time_pair_id in times_pre_assignment:
        time_pair = time_pairs_dict[time_pair_id]
        # Arrival time
        arr_datetime_lowerb = times_dict[time_pair[0]][0]
        arr_datetime_upperb = times_dict[time_pair[0]][1]
        # Departure time
        dep_datetime_lowerb = times_dict[time_pair[1]][0]
        dep_datetime_upperb = times_dict[time_pair[1]][1]

        # Arrival time
        arr_time_lst = ut.generate_datetime_list(
            arr_datetime_lowerb, arr_datetime_upperb, timedelta_in_min
        )

        # Assign generated departure time if:
        # 1. time difference between arrival and departure is satisfied
        # 2. ...
        while True:
            arrival_possibility = np.random.choice(arr_time_lst, 1)[0]
            if arrival_possibility < endtime - timedelta(minutes=timedelta_in_min):
                arr_assignment[ev_id] = arrival_possibility
                ev_arr_time_lowerbs[ev_id] = arr_datetime_upperb
                # Departure time
                dep_time_lst = ut.generate_datetime_list(
                    dep_datetime_lowerb, dep_datetime_upperb, timedelta_in_min
                )
            while True:
                departure_possibility = np.random.choice(dep_time_lst, 1)[0]
                # Departure must be after arrival
                if departure_possibility < arr_assignment[ev_id]:
                    departure_possibility += dt.timedelta(days=1)
                if departure_possibility > arrival_possibility + dt.timedelta(
                    minutes=diff_arr_dep_in_min
                ):
                    dep_assignment[ev_id] = departure_possibility
                    break
            ev_id += 1
            break

    # Merge arrival and departure assignments into EV pandas dataframe
    ev_assigned_times_dict = {}
    for ev_id in arr_assignment.keys() | dep_assignment.keys():
        if ev_id in arr_assignment:
            ev_assigned_times_dict.setdefault(ev_id, []).append(arr_assignment[ev_id])
        if ev_id in dep_assignment:
            ev_assigned_times_dict.setdefault(ev_id, []).append(dep_assignment[ev_id])
    gen_ev_df = pd.DataFrame.from_dict(
        ev_assigned_times_dict, orient="index", columns=["ArrivalTime", "DepartureTime"]
    )
    # Localize time entries
    gen_ev_df["ArrivalTime"] = gen_ev_df["ArrivalTime"].dt.tz_localize(tz="GMT+0")
    gen_ev_df["DepartureTime"] = gen_ev_df["DepartureTime"].dt.tz_localize(tz="GMT+0")

    ###################################################################################################################
    # Generating arrival and departure SoCs
    ###################################################################################################################

    soc_prob_list = list(soc_prob_dict.values())
    # SoC pairs dictionary, keys: keys to be used in choice function, values: arr/dep SoCID pairs
    soc_pairs_dict = {}
    for index, value in enumerate(list(soc_prob_dict.keys())):
        soc_pairs_dict[index] = value
    # Pre assignment list, consist of assigned time pair's ID
    soc_pre_assignment = list(
        np.random.choice(list(soc_pairs_dict.keys()), number_of_evs, p=soc_prob_list)
    )

    # Assign possible arrival SoCs
    arr_soc_assignment = {}
    dep_soc_assignment = {}
    ev_id = 0
    for soc_pair_id in soc_pre_assignment:
        soc_pair = soc_pairs_dict[soc_pair_id]
        # Arrival SoC
        arr_soc_lowerb = soc_dict[soc_pair[0]][0]
        arr_soc_upperb = soc_dict[soc_pair[0]][1]
        ev_arr_soc_possibilities = list(
            ut.drange(arr_soc_lowerb, arr_soc_upperb, "0.001")
        )
        ev_arr_soc = np.random.choice(ev_arr_soc_possibilities, 1)[0]
        arr_soc_assignment[ev_id] = ev_arr_soc
        # Departure SoC
        dep_soc_lowerb = soc_dict[soc_pair[1]][0]
        dep_soc_upperb = soc_dict[soc_pair[1]][1]
        ev_dep_soc_possibilities = list(
            ut.drange(dep_soc_lowerb, dep_soc_upperb, "0.001")
        )
        ev_dep_soc = np.random.choice(ev_dep_soc_possibilities, 1)[0]
        dep_soc_assignment[ev_id] = ev_dep_soc
        ev_id += 1

    # Merge arrival and departure assignments into EV pandas dataframe
    for id, arr_soc in arr_soc_assignment.items():
        for ev_id, row in gen_ev_df.iterrows():
            if ev_id == id:
                gen_ev_df.at[ev_id, "ArrivalSoC"] = arr_soc
    for id, dep_soc in dep_soc_assignment.items():
        for ev_id, row in gen_ev_df.iterrows():
            if ev_id == id:
                gen_ev_df.at[ev_id, "DepartureSoC"] = dep_soc

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
        gen_ev_df.at[ev_id, "Model"] = chosen_model
        gen_ev_df.at[ev_id, "BatteryCapacity(kWh)"] = ev_df.at[
            chosen_model, "BatteryCapacity(kWh)"
        ]
        gen_ev_df.at[ev_id, "MaxChargingPower(kW)"] = ev_df.at[
            chosen_model, "MaxChargingPower(kW)"
        ]
        gen_ev_df.at[ev_id, "MaxFastChargingPower(kW)"] = ev_df.at[
            chosen_model, "MaxFastChargingPower(kW)"
        ]

    ###################################################################################################################
    return gen_ev_df
