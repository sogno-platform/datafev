import pandas as pd
import numpy as np


def arrival_protocol(ts, tdelta, fleet):
    """
    This protocol is executed upon arrival of EVs that have smart reservations.

    :param ts:      Current time                datetime
    :param tdelta:  Resolution of scheduling    timedelta
    :param fleet:   EV fleet object             datahandling.fleet

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
                    # TODO: Future work: add a re-routing protocol
                    ev.admitted = False

        else:
            # The EV has no reservation will be rejected
            ev.admitted = False
