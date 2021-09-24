# -*- coding: utf-8 -*-
"""
@author: egu
"""

import pandas as pd
from management.singlevehicle.scheduling_g2v_det import optimal_schedule_g2v
from management.singlevehicle.scheduling_v2g_det import optimal_schedule_v2g

class ChargingUnit(object):
    
    def __init__(self,cu_id,p_max,eff=1.0,bidirectional=True):
        
        self.id   =cu_id
        self.P_max_ch=p_max
        self.P_max_ds=p_max if bidirectional==True else 0.0
        self.eff  =eff
        
        self.connected_car =None
        self.connection_dataset=pd.DataFrame(columns=['Car ID','Connection','Disconnection'])
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
    
    def set_power_factor(self,pf):
        self.pf=pf
    
    def supply(self,ts,tdelta,p):
        self.supplied_power[ts]=p
        self.occupation[ts]=1
        #self.consumed_p[ts]=p/self.eff if p>0 else p*self.eff
        
        self.connected_car.charge(ts,tdelta,p)
    
    def idle(self,ts,tdelta):
        self.supplied_power[ts]=0.0
        self.occupation[ts]=0
    
    def calc_p_max_ch(self,ts,tdelta):
        """
        This function calculates maximum power that can be charged to EV battery at the given moment
        """      
        ev= self.connected_car
        
        dod        =ev.maxSoC- ev.soc[ts]        #Depth of discharge
        e_demand   =dod*ev.bCapacity             #Energy required to fill the battery (dod--> kWs)
        e_delta_max=self.P_max_ch*tdelta.seconds    #Upper limit of energy that can be provided with the given charger rating in in tdelta
        
        if e_delta_max<=e_demand: 
            p_max_ch=self.P_max_ch                     #Charge with full power if EV battery can accept it
        else:
            p_max_ch=self.P_max_ch*e_demand/e_delta_max #Modulate the power
            
        return p_max_ch
        
    def calc_p_max_ds(self,ts,tdelta):
        """
        This function calculates maximum power that can be discharged from EV battery at the given moment
        """      
        ev= self.connected_car
        
        res_doc    =ev.soc[ts]-ev.minSoC         #Additional depth of discharge
        e_supply   =res_doc*ev.bCapacity         #Dischare required to empty the battery (dod--> kWs)
        e_delta_max=-self.P_max_ds*tdelta.seconds   #Upper limit of energy that can be discharged with the given charger rating in in tdelta
        
        if e_delta_max<=e_supply: 
            p_max_ds=self.P_max_ds                      #Charge with full power if EV battery can accept it
        else:
            p_max_ds=self.P_max_ds*e_supply/e_delta_max #Modulate the power
            
        return p_max_ds
    
    
    def set_schedule(self,ts,schedule_pow,schedule_soc):
        self.schedule_pow[ts]=schedule_pow
        self.schedule_soc[ts]=schedule_soc
        self.set_active_schedule(ts)
        
        
    #TODO1: Write a method that calls scheduling_g2v or scheduling_v2g
    def generate_schedule(self, optsolver,now, t_delta, target_soc, est_leave, cost_coeff,v2g=False):
        """
        This method calls optimal_schedule_g2v/v2g function from management and generates schedules
        """
        
        current_soc  =self.connected_car.soc[now]
        hyp_en_input=self.P_max_ch*((est_leave-now).seconds)                    #Maximum energy that could be supplied within the given time with the given charger rating if the battery capacity was unlimited
        target_soc   =min(1,current_soc+hyp_en_input/self.connected_car.bCapacity)
                    
        if v2g:
            schedule_pow, schedule_soc = optimal_schedule_v2g(optsolver,now,est_leave,t_delta,
                                                  self.P_max_ch,self.P_max_ds,
                                                  self.connected_car.bCapacity,
                                                  current_soc,target_soc,self.connected_car.minSoC,self.connected_car.maxSoC,
                                                  cost_coeff)
        else:
            schedule_pow, schedule_soc = optimal_schedule_g2v(optsolver,now,est_leave,t_delta,
                                                              self.P_max_ch,
                                                              self.connected_car.bCapacity,
                                                              current_soc,target_soc,self.connected_car.minSoC,self.connected_car.maxSoC,
                                                              cost_coeff)
        self.schedule_pow[now]=schedule_pow
        self.schedule_soc[now]=schedule_soc
    
    def set_active_schedule(self,ts):
        self.active_schedule_instance=ts
    
if __name__ == "__main__":
    
    from classes.Car import ElectricVehicle as EV
    from datetime import datetime, timedelta
    import numpy as np
    import pandas as pd
    
    from pyomo.environ import SolverFactory
    from pyomo.core import *
    
    
    #solver=SolverFactory('glpk',executable="C:/Users/AytugIrem/anaconda3/pkgs/glpk-4.65-h8ffe710_1004/Library/bin/glpsol")
    solver=SolverFactory("gurobi")
    history=pd.DataFrame(columns=['SOC','P_min','P_max','P'])
    
    cu_id           ="A001"
    cu_power        =11
    cu_efficiency   =1.0
    cu_bidirectional=True
    cu=ChargingUnit(cu_id,cu_power,cu_efficiency,cu_bidirectional)
    
    time_connection =datetime(2021,3,17,16)
    time_delta      =timedelta(minutes=60)
    
    ev_id           ="ev001"
    ev_bCapacity    =55 #zoe
    ev              =EV(ev_id,ev_bCapacity)
    ev.soc[time_connection]=0.4
     
    cu.connect(time_connection,ev)
    
    # required inputs for optimized charging
    fin_soc = 0.8
    leave  = time_connection+time_delta*8        
    opt_times=pd.date_range(start=time_connection,end=leave,freq=time_delta)
    zero_time=int(len(opt_times)/2)
    one_time =len(opt_times)-zero_time
    cost    =np.append(np.ones(zero_time),np.zeros(one_time))
    cost_coeff = pd.Series(cost,index=opt_times)
    
    cu.generate_schedule(solver,time_connection, time_delta, fin_soc, leave, cost_coeff,True)
    cu.set_active_schedule(time_connection)
    
    nb_of_ts = int((leave-time_connection)/time_delta)
    for t in range(nb_of_ts):
        ts=time_connection+t*time_delta
                      
        history.loc[ts,'SOC']=ev.soc[ts]
        
        p_max_ds=cu.calc_p_max_ds(ts,time_delta)
        p_max_ch=cu.calc_p_max_ch(ts,time_delta)
        history.loc[ts,'P_min']=-p_max_ds
        history.loc[ts,'P_max']=p_max_ch
        
        p_real=cu.schedule_pow[cu.active_schedule_instance][t]
        cu.supply(ts,time_delta,p_real)
        history.loc[ts,'P']=p_real
            
    ts= time_connection+(t+1)*time_delta 
    cu.disconnect(ts)
        
    print(history)
        
            
        
        
        
    
    
    
    
    
    
    
    