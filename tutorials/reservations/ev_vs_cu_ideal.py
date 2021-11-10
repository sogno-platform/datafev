# -*- coding: utf-8 -*-
"""
Created on Wed Nov 10 12:11:31 2021

@author: egu
"""

import numpy as np
import pandas as pd
from datetime import datetime,timedelta

from classes.Car import ElectricVehicle
from classes.Charger import ChargingUnit
from classes.Reservation import Reservation
from classes.Ledgers import ReservationLedger

from management_functions.cu.min_max import calc_p_max_ch 


###############################################################################
###############################################################################
#Scenario set-up
###############################################################################
#Simulation time specifications
sim_start       =datetime(2020,3,1)
sim_end         =datetime(2020,4,1)
time_delta      =timedelta(hours=1)
sim_period      =pd.date_range(start=sim_start,end=sim_end,freq=time_delta)

#Data handling objects: Electric vehicle, charging unit and reservation ledger
ev    =ElectricVehicle('test_ev',55)           
cu    =ChargingUnit('test_cu',11)  
ledger=ReservationLedger('test_ledger')
constant_demand=33 #EV will always request 33 kWh when reserving CU

#Reservations: 
#The EV will reserve the CU for 08:00-16:00 every weekday throughout march
reservation_inputs=pd.DataFrame()
for d in range(1,32):
    if datetime(2020,3,d).weekday()<5:
        reservation_entry={'Reservation Time':sim_start,
                           'Start':datetime(2020,3,d,8),
                           'End':datetime(2020,3,d,16),
                           'Demand':33, #constant charging demand 33 kWh
                           'Tariff':0.3, #constant charging tariff 0.3 Eur/kWh
                           'Cancellation Time': np.nan}        
        reservation_inputs.loc[len(reservation_inputs)]=reservation_entry       
###############################################################################
###############################################################################

###############################################################################
###############################################################################
#Simulations
for ts in sim_period[:-1]:
    
    #Loop through the reservations placed at this time and add them to ledger
    for _,i in reservation_inputs[reservation_inputs['Reservation Time']].iterrows():    
        reserved_from  =i['Start']
        reserved_to    =i['End']
        reserved_energy=i['Demand']
        reserved_tariff=i['Tariff']
        reservation_obj=Reservation(ev.vehicle_id,cu.id,cu.type,ts,reserved_from,reserved_to,reserved_energy,reserved_tariff)
        ledger.check_validity(reservation_obj)

    #All disconnections take place at the time specified in the reservation
    if ts in reservation_inputs['End'].values:
        cu.disconnect(ts)

    #All connections take place at the time specified in the reservation
    if ts in reservation_inputs['Start'].values:
        ev.soc[ts]=0.4
        cu.connect(ts,ev)

    #If the EV is connected to the CU, it will be charged with full power
    if cu.connected_car==ev:
        p_uncontrolled=calc_p_max_ch(cu,ts,time_delta)
        cu.supply(ts,time_delta,p_uncontrolled)
###############################################################################
        


print("Monthly reservation list:")
print(ledger.table)
print()      
print("CU Connection Dataset")
print(cu.connection_dataset)
print()  
print("EV SOC")
print(pd.Series(ev.soc))    

    

