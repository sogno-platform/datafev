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


def arrival_routine(ts, tdelta, fleet):
    """
    This routine is executed upon arrival of EVs that have smart reservations.
    
    Parameters
    ----------
    ts : datetime
        Current time.
    tdelta : timedelta
        Resolution of scheduling.
    fleet : data_handling.fleet
        EV fleet object.

    Returns
    -------
    None.

    """

    incoming_vehicles = fleet.incoming_vehicles_at(ts)

    for ev in incoming_vehicles:

        if ev.reserved == True:

            # The EV approaches the cluster where it has reservation
            reserved_cluster = ev.reserved_cluster
            reserved_charger = ev.reserved_charger

            if reserved_charger.connected_ev == None:

                # The reserved charger is available
                # Connect to the reserved charger and enter the data to the cluster dataset
                reserved_charger.connect(ts, ev)

                # Enter the data of the EV to the connection dataset of the cluster
                reserved_cluster.enter_data_of_incoming_vehicle(
                    ts, ev, reserved_charger
                )
                ev.admitted = True

            else:

                # The reserved charger is occupied by another EV
                old_reservation_id = ev.reservation_id

                # Look for another available charger with same characteristics (identical)
                available_cus = reserved_cluster.query_availability(
                    ts, ev.t_dep_est, tdelta
                )

                if len(available_cus) > 0:

                    # There are available chargers
                    new_reserved_charger_id = np.random.choice(
                        list(available_cus.index)
                    )
                    new_reserved_charger = reserved_cluster.chargers[
                        new_reserved_charger_id
                    ]

                    # Reserve the charger until estimated departure time
                    reserved_cluster.reserve(
                        ts, ts, ev.t_dep_est, ev, new_reserved_charger
                    )

                    # Enter the data of the EV to the connection dataset of the cluster
                    new_reserved_charger.connect(ts, ev)

                    # Enter the data of the EV to the connection dataset of the cluster
                    reserved_cluster.enter_data_of_incoming_vehicle(
                        ts, ev, new_reserved_charger
                    )

                    # Old reservation will be removed
                    reserved_charger.unreserve(ts, old_reservation_id)

                    ev.admitted = True

                else:

                    # There is no available charger
                    # TODO: Future work: add a re-routing routine
                    ev.admitted = False

        else:
            # The EV has no reservation will be rejected
            ev.admitted = False
