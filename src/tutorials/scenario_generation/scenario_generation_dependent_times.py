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
    Example script for the usage of dependent times scenario generator.

    """

    (
        end_time,
        times_dict,
        arr_dep_times_dict,
        arr_soc_dict,
        dep_soc_dict,
        ev_dict,
    ) = utils.excel_to_sceneration_input_dependent_times(
        file_path="input_generator_dependent_times.xlsx"
    )

    ev_df = sceneration.generate_fleet_data_dependent_times(
        arr_soc_dict=arr_soc_dict,
        dep_soc_dict=dep_soc_dict,
        ev_dict=ev_dict,
        number_of_evs=100,
        endtime=end_time,
        timedelta_in_min=15,
        diff_arr_dep_in_min=0,
        times_dict=times_dict,
        arr_dep_times_dict=arr_dep_times_dict,
    )

    utils.visualize_statistical_time_generation("results/", ev_df, timedelta_in_min=15)

    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df["ArrivalTime"] = ev_df["ArrivalTime"].dt.tz_localize(None)
    ev_df["DepartureTime"] = ev_df["DepartureTime"].dt.tz_localize(None)
    ev_df.to_excel("results/output_generator_dependent_times.xlsx")

    utils.output_to_sim_input(ev_df, "results/input_simulator_dependent_times.xlsx")


if __name__ == "__main__":
    main()
