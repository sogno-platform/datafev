# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 08:25:34 2022

@author: egu
"""

import pandas as pd
import numpy as np

def reservation_protocol(ts, tdelta, system, fleet, traffic_forecast):
    """
    This protocol is executed to reserve a charger for the EVs approaching clusters.
    The simple reservations specify which charger the approaching EVs must connect to in the target cluster.

    :param ts:                Current time                                                      datetime
    :param tdelta:            Resolution of scheduling                                          timedelta
    :param system:            Multi-cluster system object                                       datahandling.multiclust
    :param fleet:             EV fleet object                                                   datahandling.fleet

    """

    reserving_vehicles = fleet.reserving_vehicles_at(ts)

    for ev in reserving_vehicles:

        # The EV communicates with the cluster operator
        target_cluster_id=ev.cluster_target
        target_cluster   =system.clusters[target_cluster_id]

        # Charger availability check
        available_cus =target_cluster.query_availability(ts,ev.t_dep_est,tdelta)

        if len(available_cus) > 0:

            # There is available charger
            selected_charger_id = np.random.choice(list(available_cus.index))
            selected_charger = target_cluster.chargers[selected_charger_id]
            ev.reserved = True

            # Reserve the charger until estimated departure time
            target_cluster.reserve(ts, ts, ev.t_dep_est, ev, selected_charger)

        else:

            # There is no available charger for the considered period
            ev.reseved = False
