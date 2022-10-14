# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 08:25:34 2022

@author: egu
"""

import pandas as pd
import numpy as np

def reservation_protocol(ts, tdelta, system, fleet, traffic_forecast):
    """
    This protocol is executed to reserve chargers for the EVs approaching a multi-cluster system.

    The smart reservations specifies the cluster and charger the approaching EVs must connect to.

    :param ts:                Current time                                                      datetime
    :param tdelta:            Resolution of scheduling                                          timedelta
    :param system:            Multi-cluster system object                                       datahandling.multiclust
    :param fleet:             EV fleet object                                                   datahandling.fleet
    :param traffic_forecast:  Traffic forecast data                                             dict of dict

    """

    reserving_vehicles = fleet.reserving_vehicles_at(ts)

    for ev in reserving_vehicles:

        ############################################################################
        ############################################################################
        #Step 1: Identify available chargers
        available_chargers=system.query_availability(ev.t_arr_est,ev.t_dep_est,tdelta,traffic_forecast)
        ############################################################################
        ############################################################################

        if len(available_chargers)==0:
            ev.reserved=False
        else:
            ############################################################################
            ############################################################################

            #Step 2: Apply a specific reservation management strategy
            #In the simple resevation strategy, an available charger is selected randomly
            selected_charger_id = np.random.choice(list(available_chargers.index))
            selected_cluster_id = available_chargers.loc[selected_charger_id, 'Cluster']
            selected_cluster    = system.clusters[selected_cluster_id]
            selected_charger    = selected_cluster.chargers[selected_charger_id]
            #End: Reservation management strategy

            ############################################################################
            ############################################################################

            ############################################################################
            ############################################################################
            #Step 3: Reserve the selected charger for the EV and assign relevant reservation parameters
            res_at   =ts
            res_from =ev.t_arr_est+traffic_forecast['arr_del'][selected_cluster_id]
            res_until=ev.t_dep_est+traffic_forecast['dep_del'][selected_cluster_id]

            selected_cluster.reserve(res_at,res_from,res_until,ev,selected_charger)
            ev.reserved = True
            ############################################################################
            ############################################################################
