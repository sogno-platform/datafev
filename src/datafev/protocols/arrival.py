import numpy as np
import pandas as pd


def arrival_protocol(ts, tdelta, fleet, system):
    """
    This protocol is executed for admission of the EVs that arrive in charger clusters without reservations.

    :param ts:      Current time                    datetime
    :param tdelta:  Resolution of scheduling        timedelta
    :param fleet:   EV fleet object                 datahandling.fleet
    :param system:  Multi-cluster system object     datahandling.multicluster

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
            # TODO: Future work: add a re-routing protocol
            ev.admitted = False
