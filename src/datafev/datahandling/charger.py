# -*- coding: utf-8 -*-
"""
@author: egu
"""

import pandas as pd

class ChargingUnit(object):
    
    def __init__(self,cu_id,p_max_ch,p_max_ds,efficiency):
        
        self.type ='CU'
        self.id   =cu_id
        self.p_max_ch=p_max_ch
        self.p_max_ds=p_max_ds
        self.eff  =efficiency
        
        self.connected_ev       =None
        self.connection_dataset =pd.DataFrame(columns=['EV ID','Connection','Disconnection'])
        self.supplied_power     =pd.Series(dtype=float)
        self.consumed_power     =pd.Series(dtype=float)
        
        self.schedule_pow={}
        self.schedule_soc={}
                
    def connect(self,ts,ev):      
        self.connected_ev=ev
        ev.connected_cu  =self
        
        dataset_ind=len(self.connection_dataset)+1
        self.connection_dataset.loc[dataset_ind,'EV ID']    =ev.vehicle_id
        self.connection_dataset.loc[dataset_ind,'Connection']=ts
    
    def disconnect(self,ts):
        self.connected_ev.connected_cu  =None
        self.connected_ev               =None
        dataset_ind=max(self.connection_dataset.index)
        self.connection_dataset.loc[dataset_ind,'Disconnection']=ts

    def supply(self,ts,tdelta,p):
        self.connected_ev.charge(ts,tdelta,p)
        self.supplied_power[ts]=p
        self.consumed_power[ts]=p/self.eff if p>0 else p*self.eff
        
    def set_schedule(self,ts,schedule_pow,schedule_soc):
        self.schedule_pow[ts]=schedule_pow
        self.schedule_soc[ts]=schedule_soc
        self.set_active_schedule(ts)
    
    def set_active_schedule(self,ts):
        self.active_schedule_instance=ts

    def occupation_record(self,start,end,step):
        period     =pd.date_range(start=start,end=end,freq=step)
        connections=pd.DataFrame(index=period)
        connections.loc[:,:]=0
        for _id,con in self.connection_dataset.iterrows():
            con_start=con['Connection']
            con_end  =con['Disconnection']
            connections.loc[con_start:con_end,_id]=1
        record     =connections.sum(axis=1)
        return record

    def uncontrolled_supply(self,ts, step):

        ev_soc =self.connected_ev.soc[ts]

        if ev_soc<1:

            ev_bcap=self.connected_ev.bCapacity
            lim_ev_batcap = (1-ev_soc)*ev_bcap                  #Limit due to the battery capacity of EV
            lim_ch_pow    = self.p_max_ch*step.seconds          #Limit due to the charger power capability

            if self.connected_ev.pow_soc_table!=None:
                # The EV battery has a specific charger power-SOC dependency limiting the power transfer
                table=self.connected_ev.pow_soc_table
                soc_range = (table[(table['SOC_LB'] <= ev_soc) & (ev_soc < table['SOC_UB'])]).index[0]
                p_max     = table.loc[soc_range, 'P_UB']
                lim_ev_socdep = p_max*step.seconds                  #Limit due to the SOC dependency of charge power
                e_max = min(lim_ev_batcap,lim_ch_pow,lim_ev_socdep)

            else:
                # The power transfer is only limited by the charger's power and battery capacity
                e_max = min(lim_ev_batcap,lim_ch_pow)

            p_avr =e_max/step.seconds                           #Average charge power during the simulation step

        else:
            p_avr=0

        self.supply(ts, step, p_avr)

        
        

            
        
        
            
        
            
        
        
        
    
    
    
    
    
    
    
    