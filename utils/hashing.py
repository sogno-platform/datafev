# -*- coding: utf-8 -*-
"""
Created on Mon Nov  8 16:40:45 2021

@author: egu
"""

import hashlib
import json


def hash_for_booking_type1(request_time,ev_id,host_id,res_from,res_to,energy_demand,energy_price):
    
    block={'EV ID'             :ev_id,
           'Host ID'           :host_id,
           'Reserved At'       :request_time.strftime("%m/%d/%Y, %H:%M:%S"),
           'Reserved From'     :res_from.strftime("%m/%d/%Y, %H:%M:%S"),
           'Reserved To'       :res_to.strftime("%m/%d/%Y, %H:%M:%S"),
           'Demand'            :energy_demand,
           'Price'             :energy_price}
    
    string_object=json.dumps(block,sort_keys=True)
    block_string =string_object.encode()
    
    raw_hash=hashlib.sha256(block_string)
    hex_hash=raw_hash.hexdigest()
    
    return hex_hash,block


def hash_for_booking_(request_time,ev_id,host_id,res_from,res_to,charger_type,charger_power,energy_dem):
       
    block={'EV ID'    :ev_id,
           'Host ID'  :host_id,
           'Booked At':request_time,
           'From'     :res_from,
           'To'       :res_to,
           'CType'    :charger_type,
           'CPower'   :charger_power, 
           'Demand'   :energy_dem}
    
    string_object=json.dumps(block,sort_keys=True)
    block_string =string_object.encode()
    
    raw_hash=hashlib.sha256(block_string)
    hex_hash=raw_hash.hexdigest()
    
    return hex_hash,block