# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 13:28:37 2022

@author: egu
"""

import pandas as pd

def minimize_idleness(demand, lead_time, ev_p_max_ac_ph1,ev_p_max_ac_ph3,ev_p_max_dc,available_chargers):
    """
    This function chooses the CU type that allows to fulfill the charging 
    demand in the given charging time
    
    Inputs
    ---------------------------------------------------------------------------
    demand            : Energy demand of the EV                       float
    chargetime        : Time for which the EV will be charged         float
    ev_p_max_ac_ph1   : Maximum 1-phs AC charging power               float
    ev_p_max_ac_ph1   : Maximum 1-phs AC charging power               float
    ev_p_max_ac_ph1   : Maximum 1-phs AC charging power               float
    available_chargers: Table with data of all available chargers     dataframe                                              
    ---------------------------------------------------------------------------
    """
    #For calculation of the minimum charger rating to achieve desired final SOC
    p_min_to_fulfill_demand = demand / lead_time.total_seconds()
             
    sufficient_chargers                =pd.DataFrame(columns=available_chargers.columns) 
    if ev_p_max_ac_ph1>=p_min_to_fulfill_demand:
        sufficient_ac1_chargers=available_chargers[(available_chargers['max p_ch']>=p_min_to_fulfill_demand)&(available_chargers['CU type']=='ac1')]
        sufficient_chargers=sufficient_chargers.append(sufficient_ac1_chargers)
    if ev_p_max_ac_ph3>=p_min_to_fulfill_demand:
        sufficient_ac3_chargers=available_chargers[(available_chargers['max p_ch']>=p_min_to_fulfill_demand)&(available_chargers['CU type']=='ac3')]
        sufficient_chargers=sufficient_chargers.append(sufficient_ac3_chargers)
    if ev_p_max_dc>=p_min_to_fulfill_demand:
        sufficient_dc_chargers=available_chargers[(available_chargers['max p_ch']>=p_min_to_fulfill_demand)&(available_chargers['CU type']=='dc')]
        sufficient_chargers=sufficient_chargers.append(sufficient_dc_chargers)
        
    if len(sufficient_chargers)==0:
        a_charger_of_selected_type=available_chargers['max p_ch'].idxmax()
    else:
        a_charger_of_selected_type=sufficient_chargers['max p_ch'].idxmin()
    type_of_selected_charger      =available_chargers.loc[a_charger_of_selected_type,'CU type']
    ch_rating_of_selected_charger =available_chargers.loc[a_charger_of_selected_type,'max p_ch']
    ds_rating_of_selected_charger =available_chargers.loc[a_charger_of_selected_type,'max p_ds']
      
    return type_of_selected_charger,ch_rating_of_selected_charger,ds_rating_of_selected_charger