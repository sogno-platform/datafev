# -*- coding: utf-8 -*-
"""
Created on Tue Jul 20 13:32:12 2021

@author: egu
"""

import pandas as pd
import numpy as np
import time

from pyomo.environ import SolverFactory
from pyomo.core import *
from datetime import datetime,timedelta

from management_algorithms.multicluster.intervention import short_term_rescheduling

solver=SolverFactory("cplex")

sim_start=datetime(2020,1,6,8,00)
sim_len  =timedelta(hours=1)
sim_res  =timedelta(seconds=300)
sim_end  =sim_start+sim_len
horizon=pd.date_range(start=sim_start,end=sim_end,freq=sim_res)
sim_ste=len(horizon)-1

P_CU=11
U   =0.5
b_ca=55*3600
dsoc=P_CU*sim_res.seconds/b_ca

number_of_cu_per_cluster=20
number_of_clusters=6
number_of_cu_total=number_of_cu_per_cluster*number_of_clusters

parkdata={}
parkdata['clusters']=list(range(number_of_clusters))
parkdata['opt_horizon']=horizon
parkdata['opt_step']   =sim_res
parkdata['station_cap']=number_of_cu_total*P_CU*(1-U)
parkdata['cluster_cap']={}
parkdata['chrunit_cap']={}


#Keys are vehicle ids
connections={}
connections['battery_cap']   ={}
connections['reference_soc'] ={}
connections['departure_time']={}
connections['initial_soc']   ={}
connections['desired_soc']   ={}
connections['location']      ={}


for cc in range(number_of_clusters):

    parkdata['cluster_cap'][cc]=number_of_cu_per_cluster*P_CU*(1-U)
    parkdata['chrunit_cap'][cc]={}

    for cu in range(number_of_cu_per_cluster):

        parkdata['chrunit_cap'][cc][cu]=P_CU

        ev_id='{:02d}'.format(int(cc))+'_'+'{:02d}'.format(int(cu))

        fin_soc      =np.random.uniform(low=0.6, high=1.0)
        until_depart =(np.random.randint(low=1,high=36))*sim_res
        dep_time     =sim_start+until_depart

        act_chr_periods  =int(min(until_depart,sim_len)/sim_res)

        soc_ref_=[fin_soc-i*dsoc for i in range(act_chr_periods)]
        soc_ref_.reverse()
        if act_chr_periods<sim_ste:
            soc_ref=soc_ref_+[fin_soc]*(1+sim_ste-act_chr_periods)
        else:
            soc_ref=soc_ref_+[fin_soc]

        soc_ini=min(soc_ref)

        connections['battery_cap'][ev_id]   =b_ca
        connections['reference_soc'][ev_id] =pd.Series(np.array(soc_ref),index=horizon)
        connections['departure_time'][ev_id]=dep_time
        connections['initial_soc'][ev_id]   =soc_ini
        connections['desired_soc'][ev_id]   =fin_soc
        connections['location'][ev_id]      =(cc,cu)


inputs_ref_socs=pd.DataFrame(connections['reference_soc'],columns=connections['reference_soc'].keys())
inputs_fixed   =pd.DataFrame(index=connections['reference_soc'].keys())
inputs_fixed['battery_cap']=pd.Series(connections['battery_cap'])
inputs_fixed['initial_soc']=pd.Series(connections['initial_soc'])
inputs_fixed['desired_soc']=pd.Series(connections['desired_soc'])
inputs_fixed['departure_time']=pd.Series(connections['departure_time'])
print(inputs_fixed)
print()

start_time=time.time()
res=short_term_rescheduling(parkdata,connections,solver)
end_time  =time.time()

print("Results")
print(pd.Series(res))