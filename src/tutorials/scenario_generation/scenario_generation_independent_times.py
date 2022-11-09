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
from datafev.protocols.scenario_generation import sceneration
from datafev.protocols.scenario_generation import utils


def main():
    """
    Example script for the usage of independent times scenario generator.

    """

    # dep_day_prob_distribution is a list,
    # which should be given to generate_fleet_data_independent_times as an input, consist of two elements:
    #   1) The first element of the list should be the possibility of departure on the same day as arrival.
    #   2) The second element of the list should be the possibility of not departing on the same day as arrival.
    same_day_departure_prob = 0.7
    overnight_stay_prob = 0.3
    dep_day_prob_distribution = [same_day_departure_prob, overnight_stay_prob]

    (
        arr_times_dict,
        dep_times_dict,
        arr_soc_dict,
        dep_soc_dict,
        ev_dict,
    ) = utils.excel_to_sceneration_input_independent_times(
        file_path="input_generator.xlsx"
    )

    ev_df = sceneration.generate_fleet_data_independent_times(
        arr_soc_dict=arr_soc_dict,
        dep_soc_dict=dep_soc_dict,
        ev_dict=ev_dict,
        number_of_evs_per_day=5,
        startdate=dt.date(2021, 6, 1),
        enddate=dt.date(2021, 6, 3),
        timedelta_in_min=15,
        diff_arr_dep_in_min=0,
        arr_times_dict=arr_times_dict,
        dep_times_dict=dep_times_dict,
        dep_day_prob_distribution=dep_day_prob_distribution,
    )

    utils.visualize_statistical_time_generation("", ev_df, timedelta_in_min=15)

    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df["ArrivalTime"] = ev_df["ArrivalTime"].dt.tz_localize(None)
    ev_df["DepartureTime"] = ev_df["DepartureTime"].dt.tz_localize(None)
    ev_df.to_excel("output_generator_independent_times.xlsx")

    utils.output_to_sim_input(ev_df, "input_simulator_independent_times.xlsx")


if __name__ == "__main__":
    main()
