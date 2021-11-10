# -*- coding: utf-8 -*-
"""
Created on Fri Nov  5 16:00:29 2021

@author: egu
"""

from management_algorithms.singlevehicle.menu_reactions import ip_tmp_o_tme

def choose_among_menu_type1(ev,ev_demand,parking_duration,menu):
    """
    This function chooses one of the offers in the given price menu (type 1)
    
    ev              : Car object
    ev_demand       : float (Energy demand of the EV)
    parking_duration: timedelta
    menu(type1)     : dataframe   
    
             CType          Power   Energy  Price
             (AC1/AC3/DC)   (kW)
      ---------------------------------------------------
      1      AC1            3.7     3.7     0.2  
      2      AC3            11.0    11.0    0.3  
      3      AC3            22.0    22.0    0.5  
      ---------------------------------------------------
    
    """
    
    ev_p_max_ac1=ev.p_max_ac_ph1
    ev_p_max_ac3=0 if ev.p_max_ac_ph3==None else ev.p_max_ac_ph3
    ev_p_max_dc =ev.p_max_dc
    
    menu.loc[:,'F_Power']=0.0
    menu.loc[:,'F_Energy']=0.0  
    
    selected_offer,reserved_demand=ip_tmp_o_tme(ev_p_max_ac1,ev_p_max_ac3,ev_p_max_dc,ev_demand,parking_duration,menu)
     
    return reserved_demand,menu.loc[selected_offer,'Price']