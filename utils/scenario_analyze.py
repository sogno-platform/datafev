# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 08:49:55 2022

@author: egu
"""

import numpy as np
import pandas as pd
from datetime import datetime,timedelta
import matplotlib.pyplot as plt 
import matplotlib.dates as md

def analyze_occupation(input_events,sim_period):
    
    scenario=input_events.set_index('ev_id')
   
    pre={}
    arr={}
    dep={}
    for t in sim_period:
        pre[t] =len(scenario[(scenario['Real Arrival Time']<=t)&(scenario['Real Departure Time']>t)])
        arr[t] =len(scenario[(scenario['Real Arrival Time']==t)])
        dep[t] =len(scenario[(scenario['Real Departure Time']==t)])
    presence  =pd.Series(pre)
    
    arr_dep_t =pd.DataFrame(columns=['Arrivals','Departures'])
    arr_dep_t['Arrivals'] =pd.Series(arr)
    arr_dep_t['Departures']=pd.Series(dep)
    arr_dep   =arr_dep_t.resample("1H").sum()
    
    fig1,axs1=plt.subplots(figsize=(4,3),tight_layout=True)
    fig1.suptitle("Number of present EVs")
    presence.plot(color='green',label='Number of EVs')
    
    fig2,ax2=plt.subplots(tight_layout=True)
    fig2.suptitle("Distribution of arrival/departure events")
    arr_dep.plot(ax=ax2,kind='bar')
    
    
    

    
#ax2 = ax1.twinx() 
#(prices/1000).plot(ax=ax2,color='green',label='Time-of-use tariff')
#ax1.set_ylabel("Number of EVs in CPL")
#ax2.set_ylabel("Time-of-use tariff (€/kWh)")
#ax1.set_xlabel("Time")
#fig.legend(loc="upper right",bbox_to_anchor=(0.85, 0.95))
#
#ax1.yaxis.label.set_color('blue')
#ax2.yaxis.label.set_color('green')