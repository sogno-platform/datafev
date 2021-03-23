# -*- coding: utf-8 -*-
"""
@author: egu
"""

import pandas as pd

class ChargingUnit(object):
    
    def __init__(self,cu_id,p_max,eff=1.0,bidirectional=True):
        
        self.id   =cu_id
        self.P_max=p_max
        self.P_min=-p_max if bidirectional==True else 0.0
        self.eff  =eff
        
        self.connected_car =None
        self.connection_dataset=pd.DataFrame(columns=['Car ID','Connection','Disconnection'])
        self.supplied_power={}
        self.consumed_power={}
                
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
    
    def supply(self,ts,tdelta,p):
        self.supplied_power[ts]=p
        self.consumed_power[ts]=p/self.eff if p>0 else p*self.eff
        self.connected_car.charge(ts,tdelta,p)
    
    def calc_p_max(self,ts,tdelta):
        """
        This function calculates maximum power that can be charged to EV battery at the given moment
        """      
        ev= self.connected_car
        
        dod        =ev.maxSoC- ev.soc[ts]        #Depth of discharge
        e_demand   =dod*ev.bCapacity             #Energy required to fill the battery (dod--> kWs)
        e_delta_max=self.P_max*tdelta.seconds    #Upper limit of energy that can be provided with the given charger rating in in tdelta
        
        if e_delta_max<=e_demand: 
            p_max=self.P_max                      #Charge with full power if EV battery can accept it
        else:
            p_max=self.P_max*e_demand/e_delta_max #Modulate the power
            
        return p_max
        
    def calc_p_min(self,ts,tdelta):
        """
        This function calculates maximum power that can be discharged from EV battery at the given moment
        """      
        ev= self.connected_car
        
        res_doc    =ev.soc[ts]-ev.minSoC         #Additional depth of discharge
        e_supply   =res_doc*ev.bCapacity         #Dischare required to empty the battery (dod--> kWs)
        e_delta_max=-self.P_min*tdelta.seconds   #Upper limit of energy that can be discharged with the given charger rating in in tdelta
        
        if e_delta_max<=e_supply: 
            p_min=self.P_min                      #Charge with full power if EV battery can accept it
        else:
            p_min=self.P_min*e_supply/e_delta_max #Modulate the power
            
        return p_min
    
    
if __name__ == "__main__":
    
    from classes.Car import ElectricVehicle as EV
    from datetime import datetime, timedelta
    import numpy as np
    import pandas as pd
    
    history=pd.DataFrame(columns=['SOC','P_min','P_max','P'])
    
    cu_id           ="A001"
    cu_power        =11
    cu_efficiency   =1.0
    cu_bidirectional=True
    cu=ChargingUnit(cu_id,cu_power,cu_efficiency,cu_bidirectional)
    
    time_connection =datetime(2021,3,17,16)
    time_delta      =timedelta(minutes=5)
    
    ev_id           ="ev001"
    ev_bCapacity    =80 #tesla
    ev              =EV(ev_id,ev_bCapacity)
    ev.soc[time_connection]=0.4
     
    cu.connect(time_connection,ev)
    
    for t in range(24):
        ts=time_connection+t*time_delta
                      
        history.loc[ts,'SOC']=ev.soc[ts]
              
        p_min=cu.calc_p_min(ts,time_delta)
        p_max=cu.calc_p_max(ts,time_delta)
        history.loc[ts,'P_min']=p_min
        history.loc[ts,'P_max']=p_max
        
        action=np.random.choice([-1,0,1],p=[0.1,0.2,0.7])
        if action==0:
            p=0
        if action==-1:
            p=p_min
        if action==1:
            p=p_max
            
        cu.supply(ts,time_delta,p)
        history.loc[ts,'P']=p
            
    ts= time_connection+(t+1)*time_delta 
    cu.disconnect(ts)
        
    print(history)
        
            
        
        
        
    
    
    
    
    
    
    
    