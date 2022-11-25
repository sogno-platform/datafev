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


def reservation_routine(ts, tdelta, system, fleet, traffic_forecast):
    """
    This routine is executed to reserve chargers for the EVs approaching a multi-cluster system.
    The smart reservations specifies the cluster and charger the approaching EVs must connect to.

    Parameters
    ----------
    ts : datetime
        Current time.
    tdelta : timedelta
        Resolution of scheduling.
    system : data_handling.multi_cluster
        Multi-cluster system object.
    fleet : data_handling.fleet
        EV fleet object.
    traffic_forecast : dict of dict
        Traffic forecast data.

    Returns
    -------
    None.

    """

    reserving_vehicles = fleet.reserving_vehicles_at(ts)

    for ev in reserving_vehicles:

        ############################################################################
        ############################################################################
        # Step 1: Identify available chargers
        available_chargers = system.query_availability(
            ev.t_arr_est, ev.t_dep_est, tdelta, traffic_forecast
        )
        ############################################################################
        ############################################################################

        if len(available_chargers) == 0:
            ev.reserved = False
        else:
            ############################################################################
            ############################################################################

            # Step 2: Apply a specific reservation management strategy
            # In the simple resevation strategy, an available charger is selected randomly
            selected_charger_id = np.random.choice(list(available_chargers.index))
            selected_cluster_id = available_chargers.loc[selected_charger_id, "cluster"]
            selected_cluster = system.clusters[selected_cluster_id]
            selected_charger = selected_cluster.chargers[selected_charger_id]
            # End: Reservation management strategy

            ############################################################################
            ############################################################################

            ############################################################################
            ############################################################################
            # Step 3: Reserve the selected charger for the EV and assign relevant reservation parameters
            res_at = ts
            res_from = ev.t_arr_est + traffic_forecast["arr_del"][selected_cluster_id]
            res_until = ev.t_dep_est + traffic_forecast["dep_del"][selected_cluster_id]

            selected_cluster.reserve(res_at, res_from, res_until, ev, selected_charger)
            ev.reserved = True
            ############################################################################
            ############################################################################
