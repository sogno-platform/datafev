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
                old_reservation = reserved_cluster.re_dataset.loc[old_reservation_id]

                # Look for another available charger with same characteristics (identical)
                available_cus = reserved_cluster.query_availability(
                    ts, ev.t_dep_est, tdelta
                )

                if len(available_cus) > 0:
                    # There are available chargers
                    identical_cus = available_cus[
                        (available_cus["max p_ch"] == reserved_charger.p_max_ch)
                        & (available_cus["max p_ds"] == reserved_charger.p_max_ds)
                        & (available_cus["eff"] == reserved_charger.eff)
                    ]

                    if len(identical_cus) > 0:
                        # There are available chargers with same characteristics as the previously reserved one
                        # An identicle charger to be reserved
                        new_reserved_charger_id = identical_cus.idxmin()

                    else:
                        # There is no available charger identical to the reserved one
                        # The charger with maximum power capability to be reserved
                        new_reserved_charger_id = available_cus["max p_ch"].idxmax()

                    new_reserved_charger = reserved_cluster.chargers[
                        new_reserved_charger_id
                    ]

                    # The conditions of old reservations will be aimed in the new reservation
                    old_reservation_time = old_reservation["Reserved At"]
                    old_reservation_scheduled_g2v = old_reservation["Scheduled G2V"]
                    old_reservation_scheduled_v2g = old_reservation["Scheduled V2G"]
                    old_reservation_price = old_reservation["Price"]
                    old_reservation_p_schedule = reserved_charger.schedule_pow[
                        old_reservation_time
                    ]
                    old_reservation_s_schedule = reserved_charger.schedule_soc[
                        old_reservation_time
                    ]

                    # Reserve the charger until estimated departure time
                    reserved_cluster.reserve(
                        ts, ts, ev.t_dep_est, ev, new_reserved_charger
                    )

                    # Add the smart reservation details
                    reserved_cluster.re_dataset.loc[
                        ev.reservation_id, "Scheduled G2V"
                    ] = old_reservation_scheduled_g2v
                    reserved_cluster.re_dataset.loc[
                        ev.reservation_id, "Scheduled V2G"
                    ] = old_reservation_scheduled_v2g
                    reserved_cluster.re_dataset.loc[
                        ev.reservation_id, "Price V2G"
                    ] = old_reservation_price

                    # Enter the data of the EV to the connection dataset of the cluster
                    new_reserved_charger.connect(ts, ev)
                    new_reserved_charger.set_schedule(
                        ts, old_reservation_p_schedule, old_reservation_s_schedule
                    )

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
