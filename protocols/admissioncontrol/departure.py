# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 16:23:42 2022

@author: egu
"""

def departure_protocol(ts,fleet):

    outgoing_vehicles=fleet.outgoing_vehicles_at(ts)
    
    #Managing the leaving EVs
    for ev in outgoing_vehicles:
        
        if ev.admitted==True:

            if ev.reserved==True:

                cu=ev.connected_cu
                cu.disconnect(ts)

                cc=ev.connected_cc
                cc.unreserve(ts, ev.reservation_id)
                cc.enter_data_of_outgoing_vehicle(ts,ev)

                ev.reservation_id = None