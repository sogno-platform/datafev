# -*- coding: utf-8 -*-
"""
@author: egu
"""

import pandas as pd

class ChargingUnit(object):
    
    def __init__(self,cu_id,ctype,p_max_ch,p_max_ds,efficiency):
        
        self.type ='CU'
        if ctype not in ['ac1','ac3','dc']:
            raise ValueError("Undefined charger type")        
        self.ctype=ctype
        self.id   =cu_id
        self.P_max_ch=p_max_ch
        self.P_max_ds=p_max_ds
        self.eff  =efficiency
        
        self.connected_ev       =None
        self.connection_dataset =pd.DataFrame(columns=['EV ID','Connection','Disconnection'])
        self.reservation_dataset=pd.DataFrame(columns=['Active','EV ID','At','From','Until','Demand','Cancelled At'])
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
        
    def reserve(self,ts,res_from,res_until,ev,demand):
        reservation_id=len(self.reservation_dataset)+1

        #TODO: Add check for overlap
        self.reservation_dataset.loc[reservation_id,'Active']=True   
        self.reservation_dataset.loc[reservation_id,'EV ID'] =ev.vehicle_id
        self.reservation_dataset.loc[reservation_id,'At']    =ts
        self.reservation_dataset.loc[reservation_id,'From']  =res_from
        self.reservation_dataset.loc[reservation_id,'Until'] =res_until
        self.reservation_dataset.loc[reservation_id,'Demand']=demand     
        return reservation_id
        
    def unreserve(self,ts,reservation_id):
        self.reservation_dataset.loc[reservation_id,'Cancelled At']=ts
        self.reservation_dataset.loc[reservation_id,'Active']      =False
        
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
    
    def availability(self,start,end,step):
        """
        This function checks the availability of the CU for the given period
        """
        active_reservations=self.reservation_dataset[self.reservation_dataset['Active']==True]
        period=pd.date_range(start=start,end=end,freq=step)
        
        if len(active_reservations)==0:
            availability=pd.Series(True,index=period)
        else:
            
            start_of_first_reservation=active_reservations['Until'].min()
            end_of_last_reservation   =active_reservations['Until'].max()
            
            index_set=pd.date_range(start=min(start,start_of_first_reservation),
                                    end  =max(end  ,end_of_last_reservation),
                                    freq =step)
            
            test_per_reservation=pd.DataFrame(index=index_set)
            test_per_reservation.loc[:,:]=True
            
            for res in active_reservations.index:
                res_start =self.reservation_dataset.loc[res,'From']
                res_until =self.reservation_dataset.loc[res,'Until']
                test_per_reservation.loc[res_start:res_until-step,step]=False
                
            availability=(test_per_reservation.all(axis='columns')).loc[period]
            
        return availability
    
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
        
        

            
        
        
            
        
            
        
        
        
    
    
    
    
    
    
    
    