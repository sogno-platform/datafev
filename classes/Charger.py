# -*- coding: utf-8 -*-
"""
@author: egu
"""

import pandas as pd

class ChargingUnit(object):
    
    def __init__(self,cu_id,p_max,ctype='ac1',eff=1.0,bidirectional=True):
        
        self.type ='CU'
        self.ctype=ctype
        self.id   =cu_id
        self.P_max_ch=p_max
        self.P_max_ds=p_max if bidirectional==True else 0.0
        self.eff  =eff
        
        self.connected_car =None
        self.reserved_car  =None
        self.connection_dataset =pd.DataFrame(columns=['Car ID','Connection','Disconnection'])
        self.booking_dataset    =pd.DataFrame(columns=['Car ID','Booked At','From','To','Demand','Unbooked At'])
        self.occupation={}
        self.supplied_power={}
        self.consumed_p={}
        self.consumed_q={}
        
        self.schedule_pow={}
        self.schedule_soc={}
                
    def connect(self,ts,car):      
        self.connected_car=car
        car.connected_cu  =self
        
        dataset_ind=len(self.connection_dataset)+1
        self.connection_dataset.loc[dataset_ind,'Car ID']    =car.vehicle_id
        self.connection_dataset.loc[dataset_ind,'Connection']=ts
    
    def disconnect(self,ts):
        self.connected_car.connected_cu  =None
        self.connected_car=None
        dataset_ind=(self.connection_dataset.index)
        self.connection_dataset.loc[dataset_ind,'Disconnection']=ts
        
    def book(self,ts,res_from,res_to,car,car_demand):
        booking_id=len(self.booking_dataset)+1
        
        self.booking_dataset.loc[booking_id,'Car ID']   =car.vehicle_id
        self.booking_dataset.loc[booking_id,'Booked At']=ts
        self.booking_dataset.loc[booking_id,'From']     =res_from
        self.booking_dataset.loc[booking_id,'To']       =res_to
        self.booking_dataset.loc[booking_id,'Demand']   =car_demand
        
        return booking_id
        
    def unbook(self,ts,booking_id):
        self.booking_dataset.loc[booking_id,'Unbooked At']=ts
    
    def set_power_factor(self,pf):
        self.pf=pf
    
    def supply(self,ts,tdelta,p):
        self.supplied_power[ts]=p/self.eff if p>0 else p*self.eff
        self.occupation[ts]=1
        #self.consumed_p[ts]=p/self.eff if p>0 else p*self.eff
        
        self.connected_car.charge(ts,tdelta,p)
    
    def idle(self,ts,tdelta):
        self.supplied_power[ts]=0.0
        self.occupation[ts]=0
         
    def set_schedule(self,ts,schedule_pow,schedule_soc):
        self.schedule_pow[ts]=schedule_pow
        self.schedule_soc[ts]=schedule_soc
        self.set_active_schedule(ts)
    
    def set_active_schedule(self,ts):
        self.active_schedule_instance=ts
    
if __name__ == "__main__":
    
    from classes.Car import ElectricVehicle as EV
    from management_functions.single_cu.min_max import calc_p_max_ch
    from datetime import datetime, timedelta
    import numpy as np
    
    #solver=SolverFactory("gurobi")
    
    cu_id           ="A001"
    cu_power        =11
    cu_efficiency   =1.0
    cu_bidirectional=True
    cu=ChargingUnit(cu_id,cu_power,cu_efficiency,cu_bidirectional)
    
    ev_id           ="ev001"
    ev_bCapacity    =55 #zoe
    ev              =EV(ev_id,ev_bCapacity)
      
    booking1_at  =datetime(2021,3,17,15)
    booking1_fro =datetime(2021,3,17,16)
    booking1_to  =datetime(2021,3,17,18)
    booking1_dem =22
    
    booking2_at  =booking1_at+timedelta(minutes=30)
    booking2_fro =booking1_fro+timedelta(minutes=30)
    booking2_to  =booking1_to+timedelta(minutes=30)
    booking2_dem =booking1_dem
    
    
    connection_at   =datetime(2021,3,17,17)
    disconnection_at=datetime(2021,3,17,19)
    
    sim_start  =booking1_at
    sim_ts     =timedelta(minutes=5)

    nb_of_ts = int((disconnection_at-booking1_at)/sim_ts)
    for t in range(nb_of_ts+1):
        ts=sim_start+t*sim_ts
        
        if ts==booking1_at:
            booking1_id=cu.book(ts,booking1_fro,booking1_to,ev,booking1_dem)
            
        if ts==booking2_at:
            cu.unbook(ts,booking1_id)
            booking2_id=cu.book(ts,booking2_fro,booking2_to,ev,booking2_dem)
    
        if ts==connection_at:
            ev.soc[ts]=0.4
            cu.connect(ts,ev)
            
        if ts==disconnection_at:
            ev.connected_cu.disconnect(ts)
            cu.unbook(ts,booking2_id)
            
        if cu.connected_car!=None:
            p=calc_p_max_ch(cu,ts,sim_ts)
            cu.supply(ts,sim_ts,p)
            
            
        
            
        
        
        
    
    
    
    
    
    
    
    