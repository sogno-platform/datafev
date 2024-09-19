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
import datetime as dt
import itertools


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

    # Convert input types to numpy for future use
    temp_time = dt.datetime.min.time()
    endtime = np.datetime64(dt.datetime.combine(enddate + dt.timedelta(days=1), temp_time))
    timedelta = np.timedelta64(timedelta_in_min, 'm')
    diff_arr_dep = np.timedelta64(diff_arr_dep_in_min, 'm')

    ###################################################################################################################
    # Generating arrival and departure times
    ###################################################################################################################

    gen_ev_dfs = []
    weekday_filter = date_list.weekday <= 4
    for date_key in ("Weekday", "Weekend"):
        # create a filter for weekdays and weekends concerning the date_list
        if date_key == "Weekday":
            day_filter = weekday_filter
        else:
            day_filter = ~weekday_filter
        if not day_filter.any():
            continue

        arr_times_df = pd.DataFrame.from_dict(arr_times_dict[date_key], orient="index")
        dep_times_df = pd.DataFrame.from_dict(dep_times_dict[date_key], orient="index")

        # create an array with dates for each ev arrival and departure from the date_list
        day_array = np.repeat(date_list[day_filter].values, number_of_evs_per_day)[:, np.newaxis]

        # convert input datetime.Time to pd.Timedelta arrays
        arr_times_input = arr_times_df[["TimeLowerBound", "TimeUpperBound"]].map(
                lambda x: pd.Timedelta(hours=x.hour, minutes=x.minute, seconds=x.second, microseconds=x.microsecond)
            ).values
        dep_times_input = dep_times_df[["TimeLowerBound", "TimeUpperBound"]].map(
                lambda x: pd.Timedelta(hours=x.hour, minutes=x.minute, seconds=x.second, microseconds=x.microsecond)
            ).values

        # randomly choose an index for arrival paris
        ev_arr_time_idx = np.random.choice(
            np.arange(len(arr_times_df)), sum(day_filter)*number_of_evs_per_day,
            p=arr_times_df["Probability"].values
        )

        # add date information to selected arrival time pairs
        ev_arr_time_pairs = arr_times_input[ev_arr_time_idx, :]
        ev_arr_time_pairs = day_array + ev_arr_time_pairs
        ev_arr_time_pairs[:, 1][ev_arr_time_pairs[:, 1] < ev_arr_time_pairs[:, 0]] += np.timedelta64(1, 'D')

        # ensure time pair stops before endtime
        ev_arr_time_pairs[:, 1].clip(max=endtime - timedelta)

        # calculate possible time steps in arrival period with more than one timedelta gap before endtime
        arr_time_delta = ev_arr_time_pairs[:, 1] - ev_arr_time_pairs[:, 0]
        arrival_possibility_filter = np.logical_and(arr_time_delta % timedelta == 0,
                                                    ev_arr_time_pairs[:, 1] == endtime - timedelta)
        arr_time_delta = (arr_time_delta / timedelta).astype(int)
        arr_time_delta[arrival_possibility_filter] -= 1

        # choose the exact arrival times
        arr_time_steps = np.random.randint(0, arr_time_delta)
        arr_times = ev_arr_time_pairs[:, 0] + arr_time_steps * timedelta

        # Assign possible departures from statistic input data
        # Find a datetime which satisfies following conditions
        # 1. departure after arrival
        # 2. there must be at least two hours difference between arrival and departure
        # 3. ...
        dep_times = np.zeros_like(arr_times)

        # keep a list of entries that do not fulfill criteria
        remaining_pairs = np.ones((dep_times.shape[0]), dtype=bool)

        # re-roll entries that didn't fulfill criteria
        while remaining_pairs.any():
            # choose departure time pair
            ev_dep_time_idx = np.random.choice(
                np.arange(len(dep_times_df)), remaining_pairs.sum(),
                p=dep_times_df["Probability"].values
            )
            # add date information
            new_ev_time_paris = dep_times_input[ev_dep_time_idx, :]
            new_ev_time_paris = day_array[remaining_pairs, :] + new_ev_time_paris
            new_ev_time_paris[:, 1][new_ev_time_paris[:, 1] < new_ev_time_paris[:, 0]] += np.timedelta64(1, 'D')
            # select a departure timestep
            dep_time_steps = ((new_ev_time_paris[:, 1] - new_ev_time_paris[:, 0])/timedelta).astype(int)
            new_ev_dep_times = new_ev_time_paris[:, 0] + np.random.randint(0, dep_time_steps) * timedelta
            new_ev_dep_times[new_ev_dep_times < arr_times[remaining_pairs]] += np.timedelta64(1, 'D')
            # set new departure times
            dep_times[remaining_pairs] = new_ev_dep_times
            # check if criteria is fulfilled and update entries to redo
            arr_dep_filter = new_ev_dep_times > arr_times[remaining_pairs] + diff_arr_dep
            remaining_pairs[remaining_pairs] ^= arr_dep_filter

        gen_ev_dfs.append(pd.DataFrame({"ArrivalTime": arr_times, "DepartureTime": dep_times}))

    gen_ev_df = pd.concat(gen_ev_dfs)

    # Localize time entries
    gen_ev_df["ArrivalTime"] = gen_ev_df["ArrivalTime"].dt.tz_localize(tz="GMT+0")
    gen_ev_df["DepartureTime"] = gen_ev_df["DepartureTime"].dt.tz_localize(tz="GMT+0")

    ###################################################################################################################
    # Generating arrival and departure SoCs
    ###################################################################################################################

    # Arrival SoC probabilities
    arr_soc_df = pd.DataFrame(arr_soc_dict).T

    # Departure SoC probabilities
    dep_soc_df = pd.DataFrame(dep_soc_dict).T

    # Select a arrival soc pair
    ev_arr_socs_idx = np.random.choice(
            np.arange(len(arr_soc_df)), len(gen_ev_df), p=arr_soc_df["Probability"].values
    )

    # choose an exact arrival soc
    ev_arr_soc_pairs = arr_soc_df[["SoCLowerBound(%)", "SoCUpperBound(%)"]].values[ev_arr_socs_idx, :]
    ev_arr_soc_pairs = (ev_arr_soc_pairs * 1000).astype(int)

    ev_arr_socs = np.random.randint(ev_arr_soc_pairs[:, 0], ev_arr_soc_pairs[:, 1], len(ev_arr_socs_idx))

    # choose a departure soc pair
    dep_soc_df.sort_values(by="SoCLowerBound(%)", ascending=True, inplace=True)
    ev_dep_soc_pairs_pre = dep_soc_df[["SoCLowerBound(%)", "SoCUpperBound(%)"]]
    ev_dep_soc_pairs_pre = (ev_dep_soc_pairs_pre.values * 1000).astype(int)

    # search what departure soc index is required so the departure pair is larger than the chosen arrival soc
    ev_dep_first_allowed_soc_idx = np.searchsorted(ev_dep_soc_pairs_pre[:, 0], ev_arr_socs, side="right")

    # calculate departure pairs for each possible sublist
    unique_idx, unique_inverse_idx = np.unique(ev_dep_first_allowed_soc_idx, return_inverse=True)
    ev_dep_socs_idx = np.zeros_like(ev_dep_first_allowed_soc_idx)

    for i, idx in enumerate(unique_idx):
        idx_filter = unique_inverse_idx == i
        probability_slice = dep_soc_df["Probability"].values[idx:]
        probability_slice /= np.sum(probability_slice)
        # set chosen departure soc pair index regarding sublist
        ev_dep_socs_idx[idx_filter] = np.random.choice(
            np.arange(idx, len(ev_dep_soc_pairs_pre)), idx_filter.sum(),
            p=probability_slice
        )

    # select specific departure soc
    ev_dep_soc_paris_post = ev_dep_soc_pairs_pre[ev_dep_socs_idx]
    ev_dep_socs = np.random.randint(ev_dep_soc_paris_post[:, 0], ev_dep_soc_paris_post[:, 1], len(ev_arr_socs))

    gen_ev_df["ArrivalSoC"] = ev_arr_socs / 1000
    gen_ev_df["DepartureSoC"] = ev_dep_socs / 1000

    ###################################################################################################################
    # Generating EV Data
    ###################################################################################################################

    # EV dictionary to Dataframe
    ev_df = pd.DataFrame(ev_dict).T
    ev_prob_array = ev_df["Probability"].values
    ev_model_array = ev_df.index.to_numpy()

    gen_ev_df["Model"] = np.random.choice(ev_model_array, len(gen_ev_df), p=ev_prob_array)
    gen_ev_df["BatteryCapacity(kWh)"] = (ev_df["BatteryCapacity(kWh)"].loc[gen_ev_df["Model"]]).values
    gen_ev_df["MaxChargingPower(kW)"] = (ev_df["MaxChargingPower(kW)"].loc[gen_ev_df["Model"]]).values
    gen_ev_df["MaxFastChargingPower(kW)"] = (ev_df["MaxFastChargingPower(kW)"].loc[gen_ev_df["Model"]]).values

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

    # prepare numpy time objects
    timedelta = np.timedelta64(timedelta_in_min, 'm')
    diff_arr_dep = np.timedelta64(diff_arr_dep_in_min, 'm')
    endtime = np.datetime64(endtime)

    # prepare arrays for time ids, probabilities and pairs
    times_keys = np.fromiter(times_dict.keys(), count=len(times_dict), dtype=int)
    times_probs = np.empty(shape=(len(times_keys) ** 2,), dtype=float)
    for i, (k1, k2) in enumerate(itertools.product(times_keys, times_keys)):
        times_probs[i] = times_prob_dict[k1, k2]

    times_pairs = np.empty(shape=(len(times_keys), 2), dtype='datetime64[s]')
    for i, k in enumerate(times_keys):
        time_pair = times_dict[k]
        times_pairs[i, 0] = np.datetime64(time_pair[0])
        times_pairs[i, 1] = np.datetime64(time_pair[1])

    # Pre assignment arrays, consist of assigned time pair's indices
    times_pre_assignment = np.random.choice(np.arange(len(times_probs)), number_of_evs, p=times_probs)

    # select corresponding time pairs
    arr_time_pairs = times_pairs[times_pre_assignment // len(times_keys), :]
    dep_time_pairs = times_pairs[times_pre_assignment % len(times_keys), :]

    # select specific arrival time
    arr_time_pairs[:, 1] = arr_time_pairs[:, 1].clip(max=endtime - timedelta)
    arr_time_steps = np.random.randint(0, ((arr_time_pairs[:, 1] - arr_time_pairs[:, 0]) / timedelta).astype(int))
    arr_times = arr_time_pairs[:, 0] + timedelta * arr_time_steps

    # calculate possible departure steps
    possible_dep_steps = ((dep_time_pairs[:, 1] - dep_time_pairs[:, 0]) / timedelta).astype(int)

    # reduce steps according to diff_arr_dep
    dep_start = np.maximum(arr_times, dep_time_pairs[:, 0])
    reduced_steps = np.minimum(((dep_start - arr_times - diff_arr_dep) / timedelta).astype(int), 0)
    possible_dep_steps += reduced_steps

    # select specific departure steps
    dep_time_steps = np.random.randint(0, possible_dep_steps)
    dep_times = dep_time_pairs[:, 0] + timedelta * dep_time_steps
    dep_times[dep_times < arr_times] += np.timedelta64(24, 'h')

    # readjust from reduced steps
    dep_times[dep_times < arr_times + diff_arr_dep] += diff_arr_dep

    gen_ev_df = pd.DataFrame(data=arr_times, columns=["ArrivalTime"])
    gen_ev_df["DepartureTime"] = dep_times
    # Localize time entries
    gen_ev_df["ArrivalTime"] = gen_ev_df["ArrivalTime"].dt.tz_localize(tz="GMT+0")
    gen_ev_df["DepartureTime"] = gen_ev_df["DepartureTime"].dt.tz_localize(tz="GMT+0")

    ###################################################################################################################
    # Generating arrival and departure SoCs
    ###################################################################################################################

    # prepare arrays for soc ids, probabilities and pairs
    soc_keys = np.fromiter(soc_dict.keys(), count=len(soc_dict), dtype=int)
    soc_pair_probs = np.empty(shape=(len(soc_dict) ** 2,), dtype=float)
    for i, (k1, k2) in enumerate(itertools.product(soc_keys, soc_keys)):
        soc_pair_probs[i] = soc_prob_dict[(k1, k2)]

    soc_pairs = np.empty(shape=(len(soc_keys), 2), dtype=int)
    for i, k in enumerate(soc_keys):
        soc_pairs[i, 0] = soc_dict[k][0] * 1000
        soc_pairs[i, 1] = soc_dict[k][1] * 1000

    # Pre assignment list, consist of assigned time pair's ID
    soc_pre_assignment = np.random.choice(np.arange(len(soc_pair_probs)), number_of_evs, p=soc_pair_probs)

    pre_assignment_arr_socs = soc_pairs[soc_pre_assignment // len(soc_keys), :]
    # Assign possible arrival SoCs
    ev_arr_socs = np.random.randint(pre_assignment_arr_socs[:, 0], pre_assignment_arr_socs[:, 1])
    gen_ev_df["ArrivalSoC"] = ev_arr_socs / 1000

    # assign departure socs
    pre_assignment_dst_socs = soc_pairs[soc_pre_assignment % len(soc_keys), :]
    ev_dep_socs = np.random.randint(pre_assignment_dst_socs[:, 0], pre_assignment_dst_socs[:, 1])
    gen_ev_df["DepartureSoC"] = ev_dep_socs / 1000

    ###################################################################################################################
    # Generating EV Data
    ###################################################################################################################

    # EV dictionary to Dataframe
    ev_df = pd.DataFrame(ev_dict).T
    ev_prob_array = ev_df["Probability"].values
    ev_model_array = ev_df.index.to_numpy()

    gen_ev_df["Model"] = np.random.choice(ev_model_array, len(gen_ev_df), p=ev_prob_array)
    gen_ev_df["BatteryCapacity(kWh)"] = (ev_df["BatteryCapacity(kWh)"].loc[gen_ev_df["Model"]]).values
    gen_ev_df["MaxChargingPower(kW)"] = (ev_df["MaxChargingPower(kW)"].loc[gen_ev_df["Model"]]).values
    gen_ev_df["MaxFastChargingPower(kW)"] = (ev_df["MaxFastChargingPower(kW)"].loc[gen_ev_df["Model"]]).values

    ###################################################################################################################
    return gen_ev_df
