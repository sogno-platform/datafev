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
import matplotlib.pyplot as plt

from management_algorithms.multicluster.intervention import short_term_rescheduling

solver=SolverFactory("cplex")

sim_start=datetime(2020,1,6,8,00)
sim_cut  =timedelta(hours=2)
sim_len  =timedelta(hours=4)
sim_res  =timedelta(seconds=300)
sim_end  =sim_start+sim_len
horizon=pd.date_range(start=sim_start,end=sim_end,freq=sim_res)
sim_ste=len(horizon)-1

P_CU=11
U   =0.5
b_ca=55*3600
ini_soc=0.6
fin_soc=1.0

number_of_cu_per_cluster=3
number_of_clusters=2
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

schedules={}
p_ref=pd.Series(np.zeros(len(horizon)),index=horizon)
p_ref[:sim_start+sim_cut-sim_res]=P_CU
s_ref=p_ref.shift().cumsum()*(sim_res.seconds/b_ca)+ini_soc
s_ref.iloc[0]=ini_soc


for cc in range(number_of_clusters):

    fig, ax=plt.subplots(number_of_cu_per_cluster+1,1,sharex=True)

    parkdata['cluster_cap'][cc]=number_of_cu_per_cluster*P_CU*(1-U)
    parkdata['chrunit_cap'][cc]={}

    schedules[cc]=pd.DataFrame()
    schedules[cc]['Demand']  = p_ref.iloc[:-1]*number_of_cu_per_cluster
    schedules[cc]['Capacity']= np.ones(sim_ste)*number_of_cu_per_cluster*P_CU*(1-U)

    for cu in range(number_of_cu_per_cluster):

        parkdata['chrunit_cap'][cc][cu]=P_CU
        ev_id='{:02d}'.format(int(cc))+'_'+'{:02d}'.format(int(cu))
        dep_time     =sim_start+sim_cut if cu%2==1 else sim_start+sim_len
        color        ='g' #'r' if cu==1 else 'g'

        connections['battery_cap'][ev_id]   =b_ca
        connections['departure_time'][ev_id]=dep_time
        connections['initial_soc'][ev_id]   =ini_soc
        connections['desired_soc'][ev_id]   =fin_soc
        connections['location'][ev_id]      =(cc,cu)
        connections['reference_soc'][ev_id] =s_ref

        s_ref.plot(ax=ax[cu],color=color)
        ax[cu].title.set_text('SOC Reference of '+ev_id)


    schedules[cc].plot(ax=ax[number_of_cu_per_cluster])
    ax[number_of_cu_per_cluster].title.set_text('Cluster Loading')
plt.show()



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
