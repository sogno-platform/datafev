# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 14:50:05 2022

@author: egu
"""

from datahandling.EV import ElectricVehicle

class EVFleet(object):
    
    def __init__(self,fleet_id,behavior,sim_horizon):
        
        self.fleet_id=fleet_id
        self.objects     ={}
        self.reserving_at=dict([(t,[]) for t in sim_horizon])
        self.incoming_at =dict([(t,[]) for t in sim_horizon])
        self.outgoing_at =dict([(t,[]) for t in sim_horizon])
        
        self.define_behavior(behavior)
        
        
    def define_behavior(self,behavior):
    
        for _,i in behavior.iterrows(): 
    
            #Initialization of an EV object
            evID     =i['ev_id']
            bcap     =i['Battery Capacity (kWh)']
            p_max_ac1=i['p_max_ac1']
            p_max_ac3=i['p_max_ac3']
            p_max_dc =i['p_max_dc']
            ev       =ElectricVehicle(evID,bcap,p_max_ac1,p_max_ac3,p_max_dc)      
            
            #Assigning the scenario parameters
            ev.t_res               =i['Reservation Time']
            ev.t_arr_est           =i['Estimated Arrival Time']
            ev.t_dep_est           =i['Estimated Departure Time']        
            ev.soc_arr_est         =i['Estimated Arrival SOC']       
            ev.t_crt               =i['Critical Time']
            ev.soc_tar_at_t_crt    =i['Target SOC @ Critical Time']
            ev.soc_tar_at_t_dep_est=i['Target SOC @ Estimated Departure Time']
            ev.v2x_allow           =i['V2X Allowance (kWh)']*3600
            ev.t_arr_real          =i['Real Arrival Time']
            ev.soc_arr_real        =i['Real Arrival SOC']
            ev.t_dep_real          =i['Real Departure Time']
            ev.soc[ev.t_arr_real ] =ev.soc_arr_real 
                     
            self.objects[evID]=ev
            self.reserving_at[ev.t_res].append(ev)
            self.incoming_at[ev.t_arr_real].append(ev)
            self.outgoing_at[ev.t_dep_real].append(ev)
        
    def incoming_vehicles_at(self,ts): 
        return self.incoming_at[ts]
    
    def outgoing_vehicles_at(self,ts):
        return self.outgoing_at[ts]
    
        
        
        
        
    
        