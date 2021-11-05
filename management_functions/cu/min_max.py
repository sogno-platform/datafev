# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 15:40:46 2021

@author: egu
"""

def calc_p_max_ch(cu,ts,tdelta):
    """
    This function calculates maximum power that can be charged to the connected EV battery at the given moment
    """      
    ev= cu.connected_car
    
    dod        =ev.maxSoC- ev.soc[ts]        #Depth of discharge
    e_demand   =dod*ev.bCapacity             #Energy required to fill the battery (dod--> kWs)
    e_delta_max=cu.P_max_ch*tdelta.seconds    #Upper limit of energy that can be provided with the given charger rating in in tdelta
    
    if e_delta_max<=e_demand: 
        p_max_ch=cu.P_max_ch                     #Charge with full power if EV battery can accept it
    else:
        p_max_ch=cu.P_max_ch*e_demand/e_delta_max #Modulate the power
        
    return p_max_ch
    
def calc_p_max_ds(cu,ts,tdelta):
    """
    This function calculates maximum power that can be discharged from the connected EV battery at the given moment
    """      
    ev= cu.connected_car
    
    res_doc    =ev.soc[ts]-ev.minSoC         #Additional depth of discharge
    e_supply   =res_doc*ev.bCapacity         #Dischare required to empty the battery (dod--> kWs)
    e_delta_max=-cu.P_max_ds*tdelta.seconds   #Upper limit of energy that can be discharged with the given charger rating in in tdelta
    
    if e_delta_max<=e_supply: 
        p_max_ds=cu.P_max_ds                      #Charge with full power if EV battery can accept it
    else:
        p_max_ds=cu.P_max_ds*e_supply/e_delta_max #Modulate the power
        
    return p_max_ds