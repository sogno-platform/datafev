# -*- coding: utf-8 -*-
"""
Created on Mon Nov  8 16:15:09 2021

@author: egu
"""

from utils.hashing import hash_for_booking_type1

class Reservation(object):
    
    def __init__(self,ev_id,host_id,host_type,res_at,res_from,res_to,res_ene,res_pri):

        self.time              =res_at
        self.start             =res_from
        self.end               =res_to
        self.energy            =res_ene
        self.price             =res_pri
        self.vehicle_id        =ev_id
        self.host_id           =host_id
        self.host_type         =host_type
        self.id                =hash_for_booking_type1(res_at,ev_id,host_id,res_from,res_to,res_ene,res_pri)[0]
        
        self.active            =True
        self.cancelled         =False
        self.executed          =False
        
        self.cancellation_time =None
        self.execution_time    =None
          
    def cancel(self,ts):
        self.active            =False
        self.cancelled         =True
        self.cancellation_time =ts
        
    def execute(self,ts):
        self.active            =False
        self.executed          =True
        self.execution_time    =ts
        

