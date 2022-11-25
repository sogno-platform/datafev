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


def arrival_routine(ts, tdelta, fleet, system):
    """
    This routine is executed for admission of the EVs that arrive in charger clusters without reservations.

    Parameters
    ----------
    ts : datetime
        Current time.
    tdelta : timedelta
        Resolution of scheduling.
    fleet : data_handling.fleet
        EV fleet object.
    system : data_handling.multi_cluster
        Multi-cluster system object.

    Returns
    -------
    None.

    """

    incoming_vehicles = fleet.incoming_vehicles_at(ts)

    for ev in incoming_vehicles:

        # The EV approaches the cluster
        target_cluster_id = ev.cluster_target
        target_cluster = system.clusters[target_cluster_id]

        # Charger availability check
        available_cus = target_cluster.query_availability(ts, ev.t_dep_est, tdelta)

        if len(available_cus) > 0:

            # There is available charger
            selected_charger_id = np.random.choice(list(available_cus.index))
            selected_charger = target_cluster.chargers[selected_charger_id]
            ev.reserved = True

            # Reserve the charger until estimated departure time
            target_cluster.reserve(ts, ts, ev.t_dep_est, ev, selected_charger)

            # Connect to the reserved charger
            selected_charger.connect(ts, ev)

            # Enter the data of the EV to the connection dataset of the cluster
            target_cluster.enter_data_of_incoming_vehicle(ts, ev, selected_charger)

            ev.admitted = True

        else:

            # There is no available charger
            # TODO: Future work: add a re-routing routine
            ev.admitted = False
