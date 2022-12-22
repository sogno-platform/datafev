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


import numpy as np
import pandas as pd
from datetime import timedelta
import datetime as dt
import decimal
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
import os
import matplotlib.dates as mdates


def excel_to_sceneration_input_simple_pdfs(file_path):
    """
    This method converts the excel inputs into inputs suitable for the
    generate_fleet_from_simple_pdfs function under sceneration.py.

    Excel file structure, especially Sheet and Column names should be
    as it's in the 'tutorials/scenario_generation/input_generator_simple_pdfs.xlsx'.

    Parameters
    ----------
    file_path : str
        File path of the Excel input file.

    Returns
    -------
    arr_times_dict : dict
        Arrival times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and arrival probabilities}.
    dep_times_dict : dict
        Departure times nested dictionary.
        keys: weekend or weekday,
        values: {keys: time identifier, values: time lower bound, time upper bounds and departure probabilities}.
    arr_soc_dict : dict
        SoC nested dictionaries for arrival.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    dep_soc_dict : dict
        SoC nested dictionaries for departure.
        keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities.
    ev_dict : dict
        EV nested dictionary.
        keys: EV models, values: their data and probability.

    """

    # Read excel file
    dep_times_df = pd.read_excel(file_path, "DepartureTime")
    arr_times_df = pd.read_excel(file_path, "ArrivalTime")
    arr_soc_df = pd.read_excel(file_path, "ArrivalSoC")
    dep_soc_df = pd.read_excel(file_path, "DepartureSoC")
    ev_df = pd.read_excel(file_path, "EVData")

    # Convert percent probabilities to probabilities between 0 and 1
    arr_times_df["WeekdayArrivalPercentage"] = arr_times_df[
        "WeekdayArrivalPercentage"
    ].div(100)
    arr_times_df["WeekendArrivalPercentage"] = arr_times_df[
        "WeekendArrivalPercentage"
    ].div(100)
    dep_times_df["WeekdayDeparturePercentage"] = dep_times_df[
        "WeekdayDeparturePercentage"
    ].div(100)
    dep_times_df["WeekendDeparturePercentage"] = dep_times_df[
        "WeekendDeparturePercentage"
    ].div(100)
    # Separate weekday and weekend arrival/departure times dataframes, rename WeekdayArrivalPercentage to probability
    weekday_arr_times_df = arr_times_df.filter(
        ["TimeID", "TimeLowerBound", "TimeUpperBound", "WeekdayArrivalPercentage"],
        axis=1,
    )
    weekday_arr_times_df.columns = weekday_arr_times_df.columns.str.replace(
        "WeekdayArrivalPercentage", "Probability"
    )
    weekend_arr_times_df = arr_times_df.filter(
        ["TimeID", "TimeLowerBound", "TimeUpperBound", "WeekendArrivalPercentage"],
        axis=1,
    )
    weekend_arr_times_df.columns = weekend_arr_times_df.columns.str.replace(
        "WeekendArrivalPercentage", "Probability"
    )
    weekday_dep_times_df = dep_times_df.filter(
        ["TimeID", "TimeLowerBound", "TimeUpperBound", "WeekdayDeparturePercentage"],
        axis=1,
    )
    weekday_dep_times_df.columns = weekday_dep_times_df.columns.str.replace(
        "WeekdayDeparturePercentage", "Probability"
    )
    weekend_dep_times_df = dep_times_df.filter(
        ["TimeID", "TimeLowerBound", "TimeUpperBound", "WeekendDeparturePercentage"],
        axis=1,
    )
    weekend_dep_times_df.columns = weekend_dep_times_df.columns.str.replace(
        "WeekendDeparturePercentage", "Probability"
    )
    # Arrival/departure times nested dictionaries
    # keys: weekend or weekday
    # values: {keys: Time Identifier, values: Time Lower Bound, Time Upper Bounds and arrival/departure probabilities}
    arr_times_dict = {}
    weekday_arr_times_df = weekday_arr_times_df.set_index("TimeID")
    arr_times_dict["Weekday"] = weekday_arr_times_df.to_dict(orient="index")
    weekend_arr_times_df = weekend_arr_times_df.set_index("TimeID")
    arr_times_dict["Weekend"] = weekend_arr_times_df.to_dict(orient="index")
    dep_times_dict = {}
    weekday_dep_times_df = weekday_dep_times_df.set_index("TimeID")
    dep_times_dict["Weekday"] = weekday_dep_times_df.to_dict(orient="index")
    weekend_dep_times_df = weekend_dep_times_df.set_index("TimeID")
    dep_times_dict["Weekend"] = weekend_dep_times_df.to_dict(orient="index")

    # Convert percent SoCs to values between 0 and 1
    arr_soc_df["SoCLowerBound(%)"] = arr_soc_df["SoCLowerBound(%)"].div(100)
    arr_soc_df["SoCUpperBound(%)"] = arr_soc_df["SoCUpperBound(%)"].div(100)
    dep_soc_df["SoCLowerBound(%)"] = dep_soc_df["SoCLowerBound(%)"].div(100)
    dep_soc_df["SoCUpperBound(%)"] = dep_soc_df["SoCUpperBound(%)"].div(100)

    # SoC nested dictionaries for both arrival and departure
    # keys: SoC Identifier, values: SoC Lower Bounds, SOC Upper Bounds and their probabilities
    arr_soc_df = arr_soc_df.set_index("SoCID")
    arr_soc_dict = arr_soc_df.to_dict(orient="index")
    dep_soc_df = dep_soc_df.set_index("SoCID")
    dep_soc_dict = dep_soc_df.to_dict(orient="index")

    # EV nested dictionary
    # keys: EV models, values: their data and probability
    ev_df = ev_df.set_index("Model")
    ev_dict = ev_df.to_dict(orient="index")

    return arr_times_dict, dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict


def excel_to_sceneration_input_conditional_pdfs(file_path):
    """
    This method converts the excel inputs into inputs suitable for the
    generate_fleet_from_conditional_pdfs function under sceneration.py.

    Excel file structure, especially Sheet and Column names should be
    as it's in the 'tutorials/scenario_generation/input_generator_conditional_pdfs.xlsx'.

    Parameters
    ----------
    file_path : str
        File path of the Excel input file.

    Returns
    -------
    times_dict : dict
        Arrival-departure time combinations nested dictionary.
        keys: Arrival-departure time combination identifier, values: time upper and lower bounds.
    times_prob_dict : dict
        Arrival-departure time combinations' probabilities nested dictionary.
        keys: Arrival-departure time combination identifier, values: their probabilities.
    soc_dict : dict
        Arrival-departure SoC combinations nested dictionary.
        keys: SoC Identifier, values: SoC upper and lower bounds.
    soc_prob_dict : dict
        Arrival-departure SoC combinations' probabilities nested dictionary.
        keys: Arrival-departure SoC combination identifier, values: their probabilities.
    ev_dict : dict
        EV nested dictionary.
        keys: EV models, values: their data and probability.

    """

    # Read excel file
    times_df = pd.read_excel(file_path, "TimeID")
    times_prob_df = pd.read_excel(file_path, "TimeProbabilityDistribution")
    soc_df = pd.read_excel(file_path, "SoCID")
    soc_prob_df = pd.read_excel(file_path, "SoCProbabilityDistribution")
    ev_df = pd.read_excel(file_path, "EVData")

    times_df = times_df.set_index("TimeID")
    times_df["TimeLowerBound"] = times_df["TimeLowerBound"].round("S")
    times_df["TimeUpperBound"] = times_df["TimeUpperBound"].round("S")
    times_dict = times_df.T.to_dict("list")
    end_time = list(times_dict.values())[-1][-1]
    times_prob_df = times_prob_df.set_index("TimeID")
    times_prob_dict = {}
    for arr_time_id, row in times_prob_df.iterrows():
        id_list = []
        for dep_time_id, probability in row.items():
            id_list.append(arr_time_id)
            id_list.append(dep_time_id)
            id_tuple = tuple(id_list)
            times_prob_dict[id_tuple] = probability
            id_list.clear()

    soc_df = soc_df.set_index("SoCID")
    # Convert percent SoCs to values between 0 and 1
    soc_df["SoCLowerBound(%)"] = soc_df["SoCLowerBound(%)"].div(100)
    soc_df["SoCUpperBound(%)"] = soc_df["SoCUpperBound(%)"].div(100)
    soc_dict = soc_df.T.to_dict("list")
    soc_prob_df = soc_prob_df.set_index("SoCID")
    soc_prob_dict = {}
    for arr_soc_id, row in soc_prob_df.iterrows():
        id_list = []
        for dep_soc_id, probability in row.items():
            id_list.append(arr_soc_id)
            id_list.append(dep_soc_id)
            id_tuple = tuple(id_list)
            soc_prob_dict[id_tuple] = probability
            id_list.clear()

    # EV nested dictionary
    # keys: EV models, values: their data and probability
    ev_df = ev_df.set_index("Model")
    ev_dict = ev_df.to_dict(orient="index")

    return end_time, times_dict, times_prob_dict, soc_dict, soc_prob_dict, ev_dict


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
    times_str_list = [
        (time_lowerb + timedelta(hours=timedelta_in_min * i / 60)).strftime("%H:%M:%S")
        for i in range(
            int((time_upperb - time_lowerb).total_seconds() / 60.0 / timedelta_in_min)
        )
    ]
    for time_str in times_str_list:
        temp_time = dt.datetime.strptime(time_str, "%H:%M:%S")
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


def visualize_statistical_generation(file_path, gen_ev_df, timedelta_in_min=15):
    """
    This method visualizes generated distribution of arrival and departure times and SoCs of the generated
    fleet behavior.

    Parameters
    ----------
    file_path : str
        The file path for image files to be saved.
    gen_ev_df : pandas.core.frame.DataFrame
        Output data frame from generate_fleet_data function.
    timedelta_in_min : int
        Resolution of the simulation in minutes. The default is 15.
        Note: The resolution must be equal to the resolution of the scenario generator!

    Returns
    -------
    None.

    """

    # Times
    # Create times dicts for arrival and departure Keys: All possible time assignments, Values: number of assigned EVs
    current = dt.datetime(2022, 1, 1)  # arbitrary day
    datetime_lst = [
        current + timedelta(minutes=m) for m in range(0, 24 * 60, timedelta_in_min)
    ]
    arr_times_dict = {}
    dep_times_dict = {}
    # Initialize with 0
    for item in datetime_lst:
        arr_times_dict[item.strftime("%H:%M")] = 0
        dep_times_dict[item.strftime("%H:%M")] = 0
    for ev_id, row in gen_ev_df.iterrows():
        for time, value in arr_times_dict.items():
            if time == gen_ev_df.at[ev_id, "ArrivalTime"].strftime("%H:%M"):
                arr_times_dict[time] += 1
        for time, value in dep_times_dict.items():
            if time == gen_ev_df.at[ev_id, "DepartureTime"].strftime("%H:%M"):
                dep_times_dict[time] += 1

    times_df = pd.DataFrame.from_dict([arr_times_dict, dep_times_dict]).transpose()
    times_df = times_df.rename(columns={0: "Arrival Times", 1: "Departure Times"})
    # Plotting
    times_df.plot(kind="bar", alpha=0.5, width=1)
    plt.xticks(np.arange(0, len(times_df), 6))
    plt.ylabel("Number of EVs", size=12)
    plot_name = "generated_time_distribution"
    plot_path = os.path.join(file_path, plot_name)
    plt.savefig(plot_path)
    # Clear memory
    plt.clf()

    # SoCs
    soc_df = gen_ev_df.filter(["ArrivalSoC", "DepartureSoC"])
    plot_name = "generated_soc_distribution"
    soc_df.plot(kind="hist", alpha=0.5)
    plt.ylabel("Number of EVs", size=12)
    plot_path = os.path.join(file_path, plot_name)
    plt.savefig(plot_path)
    # Clear memory
    plt.clf()


def output_to_sim_input(sce_output_df, xlfile, dc_power=False):
    """
    This function converts the fleet behavior (generated from statistical data) to the format that could be simulated
    in this simulation framework.

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

    """

    sim_input_df = pd.DataFrame(
        columns=[
            "Battery Capacity (kWh)",
            "p_max_ch (kW)",
            "p_max_ds (kW)",
            "Real Arrival Time",
            "Real Arrival SOC",
            "Estimated Departure Time",
            "Target SOC @ Estimated Departure Time",
        ]
    )

    sim_input_df["Battery Capacity (kWh)"] = sce_output_df[
        "BatteryCapacity(kWh)"
    ].values
    sim_input_df["Real Arrival Time"] = sce_output_df["ArrivalTime"].values
    sim_input_df["Real Arrival SOC"] = sce_output_df["ArrivalSoC"].values
    sim_input_df["Estimated Departure Time"] = sce_output_df["DepartureTime"].values
    sim_input_df["Target SOC @ Estimated Departure Time"] = sce_output_df[
        "DepartureSoC"
    ].values
    if dc_power is False:  # use AC-charging-powers
        sim_input_df["p_max_ch (kW)"] = sce_output_df["MaxChargingPower(kW)"].values
        sim_input_df["p_max_ds (kW)"] = sce_output_df["MaxChargingPower(kW)"].values
    else:  # use DC-fast-charging-powers
        sim_input_df["p_max_ch (kW)"] = sce_output_df["MaxFastChargingPower(kW)"].values
        sim_input_df["p_max_ds (kW)"] = sce_output_df["MaxFastChargingPower(kW)"].values
    # Simulation input dataframe to excel file
    sim_input_df.to_excel(xlfile)
