# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 16:23:42 2022

@author: egu
"""

def handle_departures(list_of_outgoing_vehicles):
    
    #Managing the leaving EVs
    for ev in list_of_outgoing_vehicles:
        
        if ev.admitted==True:
            cu=ev.connected_cu
            cu.disconnect(ev.t_dep_real)
            cu.unreserve(ev.t_dep_real,ev.reservation_id)
            ev.reservation_id=None
            cc=ev.connected_cc
            cc.enter_data_of_outgoing_vehicle(ev.t_dep_real,ev)
                        
    return list_of_outgoing_vehicles