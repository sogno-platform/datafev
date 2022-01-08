# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 16:14:52 2021

@author: egu
"""

import pandas as pd
import numpy as np

from pyomo.environ import SolverFactory
from pyomo.core import *
from datetime import datetime,timedelta
import matplotlib.pyplot as plt

from algorithms.coordination.multicluster_optimization import minimize_deviation_from_schedules

ch_eff=0.95
ds_eff=0.95
def p_out(x): 
   if x>0:
       return x/ch_eff
   if x==0:
       return 0
   if x<0:
       return x*ds_eff
   

solver=SolverFactory("cplex")
color_top={'min':'w','max':'r','opt':'k'}
np.random.seed(1)

parkdata={}                             
parkdata['clusters']=['CC1','CC2']     #System has only two clusters   
parkdata['opt_horizon'] =list(range(13)) #1 hour
parkdata['con_horizon'] =list(range(13)) #1 hour   
parkdata['opt_step']=timedelta(minutes=5) #5 minutes 

powlimits={}
powlimits['P_CC_pos_max']={'CC1':dict(enumerate(np.ones(12)*44)),'CC2':dict(enumerate(np.ones(12)*44))}     #The clusters are allowed to import half as the installed capacity 
powlimits['P_CC_neg_max']={'CC1':dict(enumerate(np.ones(12)*44)),'CC2':dict(enumerate(np.ones(12)*44))}     #The clusters are allowed to export half as the installed capacity 
powlimits['P_CS_pos_max']=dict(enumerate(np.ones(12)*88))                                                   #Aggregate import of the station is limited by 44kW  
powlimits['P_CS_neg_max']=dict(enumerate(np.ones(12)*88))                                                   #Aggregate export of the station is limited by 44kW

powlimits_unbconstrained=powlimits.copy()
powlimits_unbconstrained['P_IC_unb_max']={}
for c1 in ['CC1','CC2']:
    for c2 in ['CC1','CC2']:
        powlimits_unbconstrained['P_IC_unb_max'][c1,c2]={}
        for t in parkdata['opt_horizon']:
            powlimits_unbconstrained['P_IC_unb_max'][c1,c2][t]=11
            
connections={}
connections['P_EV_pos_max']={}
connections['P_EV_neg_max']={}
connections['charge_eff']={}
connections['discharge_eff']={}
connections['battery_cap']={}
connections['target_soc']={}
connections['departure_time']={}
connections['initial_soc']={}
connections['minimum_soc']={}
connections['maximum_soc']={}
connections['location']={}
for v in ['v11','v12','v21','v22']: 
    connections['P_EV_pos_max'][v]  =22*ch_eff
    connections['P_EV_neg_max'][v]  =22
    connections['battery_cap'][v]   =55*3600
    connections['minimum_soc'][v]   =0.2
    connections['maximum_soc'][v]   =1.0
    connections['initial_soc'][v]   =np.random.uniform(low=0.2,high=0.6)
    connections['target_soc'][v]    =connections['initial_soc'][v]+0.4
    connections['charge_eff'][v]    =ch_eff
    connections['discharge_eff'][v] =ch_eff
    connections['departure_time'][v]=6 if v=='v12' else 15
connections['location']['v11']      =('CC1',1)
connections['location']['v12']      =('CC1',2)
connections['location']['v21']      =('CC2',1)
connections['location']['v22']      =('CC2',2)


case1='Unbalance unconstrained'
case2='Unbalance constrained'

#unbalance=pd.DataFrame(columns=['Unbalance Limit',case1,case2])
#unbalance['Unbalance Limit']=pd.Series(powlimits_unbconstrained['P_IC_unb_max'][c1,c2]).iloc[:-1]

for case in [case1,case2]:

    if case==case1:    
        p_ref,s_ref=minimize_deviation_from_schedules(parkdata,powlimits,connections,solver)
    if case==case2:
        p_ref,s_ref=minimize_deviation_from_schedules(parkdata,powlimits_unbconstrained,connections,solver)
        
    p_ref_={}
    s_ref_={}
    for v in ['v11','v12','v21','v22']:
        p_ref_[v]=p_ref[connections['location'][v]]
        s_ref_[v]=s_ref[connections['location'][v]]      
    p_ref_df=pd.DataFrame(p_ref_)
    s_ref_df=pd.DataFrame(s_ref_)
    s_ref_df['v11_ref']=connections['target_soc']['v11']
    s_ref_df['v12_ref']=connections['target_soc']['v12']
    s_ref_df['v21_ref']=connections['target_soc']['v21']
    s_ref_df['v22_ref']=connections['target_soc']['v22']
      
    c1_df=pd.DataFrame(columns=['min','max','opt'])
    c2_df=pd.DataFrame(columns=['min','max','opt'])
    c1_df['max']=pd.Series(powlimits['P_CC_pos_max']['CC1'])
    c1_df['min']=-pd.Series(powlimits['P_CC_neg_max']['CC1'])
    c1_df['opt']=p_ref_df['v11'].apply(p_out)+p_ref_df['v12'].apply(p_out)
    c2_df['max']=c2_pos_max=pd.Series(powlimits['P_CC_pos_max']['CC2'])
    c2_df['min']=-pd.Series(powlimits['P_CC_neg_max']['CC2'])        
    c2_df['opt']=p_ref_df['v21'].apply(p_out)+p_ref_df['v22'].apply(p_out)
    
    
    
    fig1,axs1=plt.subplots(3,2,sharex=True,sharey='row')
    axs1[2,0].sharey=False
    axs1[2,1].sharey=False
    
    fig1.suptitle(case)
    
    c1_df.plot(ax=axs1[0,0],color=color_top)
    c2_df.plot(ax=axs1[0,1],color=color_top)
    
    p_ref_df[['v11','v12']].plot(ax=axs1[1,0],color=['b','g'])
    p_ref_df[['v21','v22']].plot(ax=axs1[1,1],color=['b','g'])
    
    s_ref_df[['v11','v12']].plot(ax=axs1[2,0],color=['b','g'])
    s_ref_df[['v21','v22']].plot(ax=axs1[2,1],color=['b','g'])
    s_ref_df[['v11_ref','v12_ref']].plot(ax=axs1[2,0],color=['b','g'],linestyle='dashed')
    s_ref_df[['v21_ref','v22_ref']].plot(ax=axs1[2,1],color=['b','g'],linestyle='dashed')
          
    axs1[0,0].set_title("Cluster 1 Aggregate")
    axs1[0,1].set_title("Cluster 2 Aggregate")
    axs1[1,0].set_title('Cluster 1 Power')
    axs1[1,1].set_title('Cluster 2 Power')
    axs1[2,0].set_title('Cluster 1 SOC')
    axs1[2,1].set_title('Cluster 2 SOC')
    axs1[2,0].set_xlabel('Time')
    axs1[2,1].set_xlabel('Time')
    
    
    fig2,axs2=plt.subplots(1,1,sharex=True,sharey='row')
    fig2.suptitle(case)
    (c1_df['opt']-c2_df['opt']).plot(ax=axs2,label='Cluster1-Cluster2',color='r')
    (pd.Series(powlimits_unbconstrained['P_IC_unb_max'][c1,c2]).iloc[:-1]).plot(ax=axs2,linestyle='dashed',color='k')
    (-pd.Series(powlimits_unbconstrained['P_IC_unb_max'][c1,c2]).iloc[:-1]).plot(ax=axs2,linestyle='dashed',color='k')
    axs2.legend()
    axs2.set_ylim([-30,30])
    axs2.set_ylabel("kW")
