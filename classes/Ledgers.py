# -*- coding: utf-8 -*-
"""
Created on Tue Nov  9 14:40:15 2021

@author: egu
"""

import pandas as pd

class ReservationLedger(object):
    
    def __init__(self,ledger_id="clustered_cs"):
        self.id         =ledger_id
        self.table=pd.DataFrame(columns=['res_id','at','start','end','vehicle_id','host_id','cancelled'])
        self.dict ={}
        
    def check_validity(self,reservation):
        
        vehicle_id   =reservation.vehicle_id
        host_id      =reservation.host_id
        new_res_start    =reservation.start
        new_res_end      =reservation.end
        old_res_between  =self.table.loc[self.between_entities(vehicle_id,host_id)]
    
        if len(old_res_between)==0:                                            #No reservation between vehicle and host
            self.enter_reservation(reservation)
        else:
            old_res_between_noncancelled=old_res_between.loc[self.table['cancelled']!=True]
            
            if len(old_res_between_noncancelled)==0:                           #All reservations between vehicle and host are cancelled        
                self.enter_reservation(reservation)
            else:                                                              #There exist reservations not cancelled
                r_earlier  =old_res_between_noncancelled['end']<new_res_start
                r_later    =old_res_between_noncancelled['start']>new_res_end
                r_overlap  =~(r_earlier|r_later)
                old_res_between_noncancelled_overlapped =old_res_between_noncancelled.loc[r_overlap]
                
                if len(old_res_between_noncancelled_overlapped)==0:
                    self.enter_reservation(reservation)
                else:
                    raise Exception("This reservation overlaps with an existing reservation between vehicle and host")
           
    def enter_reservation(self,reservation):
  
        entry_id=len(self.dict)+1
        
        self.dict[entry_id]=reservation
        self.table.loc[entry_id,'res_id']           =reservation.id
        self.table.loc[entry_id,'at']               =reservation.time
        self.table.loc[entry_id,'start']            =reservation.start
        self.table.loc[entry_id,'end']              =reservation.end
        self.table.loc[entry_id,'vehicle_id']       =reservation.vehicle_id
        self.table.loc[entry_id,'host_id']          =reservation.host_id
        self.table.loc[entry_id,'cancelled']        =reservation.cancelled
        self.table.loc[entry_id,'cancallation time']=reservation.cancellation_time
        
    def of_vehicle(self,vehicle_id):
        return self.table['vehicle_id']==vehicle_id
        
    def to_host(self,host_id):
        return self.table['host_id']==host_id
    
    def between_entities(self,vehicle_id,host_id):
        res_of_vehicle=self.of_vehicle(vehicle_id)
        res_to_host   =self.to_host(host_id)
        return res_of_vehicle&res_to_host
    
    def start_by(self,start):
        return self.table['start']==start
    
    def end_by(self,end):
        return self.table['end']==end
    
    def for_period(self,start,end):
        res_starting_by=self.start_by(start)
        res_ending_by  =self.end_by(end) 
        return res_starting_by&res_ending_by
    
    def retrieve_reservation(self,vehicle_id,host_id,start,end):
        res_between_entities=self.between_entities(vehicle_id,host_id)
        res_for_period      =self.for_period(start,end)   
        res_id   =(self.table.loc[res_between_entities&res_for_period]).index[0] #TODO:Add Exception
        return res_id
        
    def cancel_reservation(self,ts,res_id):
        self.table.loc[res_id,'cancelled']=True
        self.table.loc[res_id,'cancellation time']=ts
        self.dict[res_id].cancel(ts)
        
        
        
    
    
        
        
        