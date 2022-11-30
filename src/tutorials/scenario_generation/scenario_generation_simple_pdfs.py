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


import datetime as dt
from datafev.routines.scenario_generation import sceneration
from datafev.routines.scenario_generation import utils


def main():
    """
    Example script for the usage of simple pdfs scenario generator.

    In this tutorial, these operations are carried out in this order:
        1)The data from Excel input file 'tutorials/scenario_generation/input_generator_simple_pdfs.xlsx' is read.
        2)The data provided by Excel is converted to dictionary datatype with
        'utils.excel_to_sceneration_input_simple_pdfs' function.
        3) Electric Vehicle Dataframe, which is an electric vehicle fleet scenario, is generated via
        'sceneration.generate_fleet_from_simple_pdfs' function with in 2) converted dictionary inputs
        4) The statistical distribution of generated arrival and departure times and SoCs are visualized via
        'utils.visualize_statistical_generation' function under '/results'.
        5) Generated statistical output dataframe is converted into an input dataframe for simulators, which are
        explained under 'tutorials/simulations'.

    The statistical data for both arrival and departure times are based on a research Takahashi, Tamura, et al.,
    'Day-Ahead Planning for EV Aggregators Based on Statistical Analysis of Road Traffic Data in Japan'
    in 2020 International Conference on Smart Grids and Energy Systems (SGES), 2020, DOI 10.1109/SGES51519.2020.00028.
    The rest of the data is not based on any research, the purpose of this tutorial is just to provide the user an
    example use-case.

    """
    (
        arr_times_dict,
        dep_times_dict,
        arr_soc_dict,
        dep_soc_dict,
        ev_dict,
    ) = utils.excel_to_sceneration_input_simple_pdfs(
        file_path="input_generator_simple_pdfs.xlsx"
    )

    ev_df = sceneration.generate_fleet_from_simple_pdfs(
        arr_times_dict=arr_times_dict,
        dep_times_dict=dep_times_dict,
        arr_soc_dict=arr_soc_dict,
        dep_soc_dict=dep_soc_dict,
        ev_dict=ev_dict,
        number_of_evs_per_day=5,
        startdate=dt.date(2021, 6, 1),
        enddate=dt.date(2021, 6, 2),
        timedelta_in_min=15,
        diff_arr_dep_in_min=0,
    )

    utils.visualize_statistical_generation("results/", ev_df, timedelta_in_min=15)

    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df["ArrivalTime"] = ev_df["ArrivalTime"].dt.tz_localize(None)
    ev_df["DepartureTime"] = ev_df["DepartureTime"].dt.tz_localize(None)
    ev_df.to_excel("results/output_generator_simple_pdfs.xlsx")

    utils.output_to_sim_input(ev_df, "results/input_simulator_simple_pdfs.xlsx")


if __name__ == "__main__":
    main()
