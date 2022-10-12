# -*- coding: utf-8 -*-
"""
Created on Wed Nov  08:25:34 2022

@author: egu
"""

import numpy as np
import pandas as pd

def arrival_protocol(ts,tdelta,fleet):

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
                reserved_cluster.enter_data_of_incoming_vehicle(ts, ev, reserved_charger)
                ev.admitted=True

            else:
                # The reserved charger is occupied by another EV

                old_reservation_id  =ev.reservation_id
                old_reservation     =reserved_cluster.re_dataset.loc[old_reservation_id]

                # Look for another available charger with same characteristics (identical)
                available_cus=reserved_cluster.query_availability(ts,ev.t_dep_est,tdelta)

                if len(available_cus)>0:
                    #There are available chargers
                    identical_cus=available_cus[(available_cus['max p_ch']==reserved_charger.p_max_ch)&
                                                (available_cus['max p_ds']==reserved_charger.p_max_ds)&
                                                (available_cus['eff']==reserved_charger.eff)]

                    if len(identical_cus)>0:
                        #There are identical available chargers
                        new_reserved_charger_id       = identical_cus.idxmin()

                    else:
                        # There is no available charger identical to the reserved one
                        new_reserved_charger_id = available_cus['max p_ch'].idxmin()

                    new_reserved_charger = reserved_cluster.chargers[new_reserved_charger_id]

                    old_reservation_time          = old_reservation['Reserved At']
                    old_reservation_scheduled_g2v = old_reservation['Scheduled G2V']
                    old_reservation_scheduled_v2g = old_reservation['Scheduled V2G']
                    old_reservation_price         = old_reservation['Price']
                    old_reservation_p_schedule    = reserved_charger.schedule_pow[old_reservation_time]
                    old_reservation_s_schedule    = reserved_charger.schedule_soc[old_reservation_time]

                    reserved_cluster.reserve(ts, ts, ev.t_dep_est, ev, new_reserved_charger)
                    reserved_cluster.re_dataset.loc[ev.reservation_id,'Scheduled G2V']= old_reservation_scheduled_g2v
                    reserved_cluster.re_dataset.loc[ev.reservation_id,'Scheduled V2G']= old_reservation_scheduled_v2g
                    reserved_cluster.re_dataset.loc[ev.reservation_id,'Price V2G']    = old_reservation_price

                    new_reserved_charger.set_schedule(ts, old_reservation_p_schedule, old_reservation_s_schedule)

                    reserved_charger.unreserve(ts,old_reservation_id)



                    ev.admitted=True

                else:
                    # There is no available charger
                    ev.admitted=False

