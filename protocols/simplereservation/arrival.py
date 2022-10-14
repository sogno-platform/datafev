# -*- coding: utf-8 -*-
"""
Created on Wed Nov  08:25:34 2022

@author: egu
"""

import numpy as np
import pandas as pd

def arrival_protocol(ts,tdelta,fleet):
    """
    This protocol is executed upon arrival of EVs that have simple reservations.

    :param ts:      Current time                datetime
    :param tdelta:  Resolution of scheduling    timedelta
    :param fleet:   EV fleet object             datahandling.fleet

    """

    incoming_vehicles = fleet.incoming_vehicles_at(ts)

    for ev in incoming_vehicles:

        if ev.reserved==True:

            #The EV approaches the cluster where it has reservation
            reserved_cluster   =ev.reserved_cluster
            reserved_charger   =ev.reserved_charger

            if reserved_charger.connected_ev==None:

                # The reserved charger is available
                # Connect to the reserved charger and enter the data to the cluster dataset
                reserved_charger.connect(ts, ev)

                # Enter the data of the EV to the connection dataset of the cluster
                reserved_cluster.enter_data_of_incoming_vehicle(ts, ev, reserved_charger)
                ev.admitted=True

            else:

                # The reserved charger is occupied by another EV
                old_reservation_id  =ev.reservation_id
                old_reservation     =reserved_cluster.re_dataset.loc[old_reservation_id]

                # Look for another available charger with same characteristics (identical)
                available_cus=reserved_cluster.query_availability(ts,ev.t_dep_est,tdelta)

                if len(available_cus)>0:

                    # There is available charger
                    new_reserved_charger_id = np.random.choice(list(available_cus.index))
                    new_reserved_charger = reserved_cluster.chargers[new_reserved_charger_id]

                    # Connect the EV to the selected charger
                    new_reserved_charger.connect(ts, ev)

                    # Enter the data of the EV to the connection dataset of the cluster
                    reserved_cluster.enter_data_of_incoming_vehicle(ts, ev, new_reserved_charger)

                    # Old reservation will be removed
                    reserved_charger.unreserve(ts,old_reservation_id)

                    ev.admitted=True

                else:
                    # There is no available charger
                    # TODO: Future work: add a re-routing protocol
                    ev.admitted=False

        else:
            # The EV without reservations will be rejected
            ev.admitted=False

