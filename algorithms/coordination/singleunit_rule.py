# -*- coding: utf-8 -*-
"""
Created on Sat Jan  8 15:52:56 2022

@author: egu
"""

def calc_p_max_ch(ev_soc,ev_tarsoc,pmax, ev_bcap, period):
    """
    This function calculates the maximum energy that can be transferred
    to the EV battery within the given interval and returns the average power
    that allows for this energy transfer
    """         
    e_demand=(ev_tarsoc- ev_soc)*ev_bcap  #Energy demand of the EV 
    e_max   =pmax*period                  #Maximum energy that the charger can transfer in the given period
    
    if e_max<=e_demand: 
        p_max_ch=pmax                     #Charge with full power if EV battery can accept it
    else:
        p_max_ch=pmax*e_demand/e_max      #Modulate the power
        
    return p_max_ch
    
def calc_p_max_ds(ev_soc,ev_minsoc,pmax, ev_bcap, period):
    """
    This function calculates the maximum energy that can be transferred
    from the EV battery within the given interval and returns the average power
    that allows for this energy transfer
    """   

    e_supply=(ev_soc-ev_minsoc)*ev_bcap  #Energy available for discharge
    e_max   =pmax*period                 #Maximum energy that the charger can transfer in the given period
    
    if e_max<=e_supply: 
        p_max_ds=pmax                    #Discharge with full power if EV battery can accept it
    else:
        p_max_ds=pmax*e_supply/e_max     #Modulate the power
        
    return p_max_ds