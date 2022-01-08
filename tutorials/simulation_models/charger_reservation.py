# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 16:48:21 2022

@author: egu
"""

from datahandling.EV import ElectricVehicle as EV
from datahandling.ChargingUnit import ChargingUnit
from algorithms.coordination.singleunit_rule import calc_p_max_ch 
from datetime import datetime, timedelta
import pandas as pd

#Charging units
cu_id           ="A001"
cu_type         ='ac3'
cu_power        =11
cu_efficiency   =1.0
cu=ChargingUnit(cu_id,cu_type,cu_power,cu_power,cu_efficiency)

#EVs
ev1_id           ="ev001"
ev1_bCapacity    =55 #zoe
ev1              =EV(ev1_id,ev1_bCapacity)

ev2_id           ="ev002"
ev2_bCapacity    =55 #zoe
ev2              =EV(ev1_id,ev1_bCapacity)
  
reservation1_at  =datetime(2021,3,17,15)
reservation1_fro =datetime(2021,3,17,16)
reservation1_to  =datetime(2021,3,17,18)
reservation1_dem =22

reservation2_at  =datetime(2021,3,17,16)
reservation2_fro =datetime(2021,3,17,19)
reservation2_to  =datetime(2021,3,17,21)
reservation2_dem =22

sim_start        =datetime(2021,3,17,12)
sim_end          =datetime(2021,3,17,22)
sim_ts           =timedelta(minutes=60)

for ts in pd.date_range(start=sim_start,end=sim_end,freq=sim_ts):
        
    if ts==reservation1_at:
        availability_for_next_4_hour=cu.availability(ts,ts+timedelta(hours=4),sim_ts)
        reservation1_id=cu.reserve(ts,reservation1_fro,reservation1_to,ev1,reservation1_dem)
        
    if ts==reservation1_fro:
        ev1.soc[ts]=0.4
        cu.connect(ts,ev1)
        
    if ts==reservation1_to:
        cu.unreserve(ts,reservation1_id)
        cu.disconnect(ts)
        
    if ts==reservation2_at:
        availability_for_next_4_hour=cu.availability(ts,ts+timedelta(hours=4),sim_ts)
        reservation2_id=cu.reserve(ts,reservation2_fro,reservation2_to,ev2,reservation2_dem)
        
    if ts==reservation2_fro:
        ev2.soc[ts]=0.4
        cu.connect(ts,ev2)
        
    if ts==reservation2_to:
        cu.unreserve(ts,reservation2_id)
        cu.disconnect(ts)
        
    #If the EV is connected to the CU, it will be charged with full power
    if cu.connected_ev in [ev1,ev2]:
        
        ev=cu.connected_ev
        ev_soc   =ev.soc[ts]
        ev_tarsoc=ev.maxSoC
        ev_bcap  =ev.bCapacity
        pmax     =cu.P_max_ch
        period   =sim_ts.seconds
        
        p_uncontrolled=calc_p_max_ch(ev_soc,ev_tarsoc,pmax, ev_bcap, period)
        cu.supply(ts,sim_ts,p_uncontrolled)