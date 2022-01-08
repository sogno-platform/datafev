# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 14:31:52 2021

@author: egu
"""

from algorithms.scheduling.lp import minimize_charging_cost_lp
from datetime import datetime,timedelta
import numpy as np
import pandas as pd

from pyomo.environ import SolverFactory
from pyomo.core import *

now=datetime(2020,5,15,8)
dT =timedelta(minutes=15)
P_c=11
P_d=11
E  =55*3600
ini_soc=0.2
fin_soc=0.8
min_soc=0.2
max_soc=1.0
leave  =datetime(2020,5,15,14)

cost_coeff_1=pd.Series(np.array([1,1,1,0,0,0,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))
cost_coeff_2=pd.Series(np.array([0,0,1,1,1,0,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))
cost_coeff_3=pd.Series(np.array([0,0,0,1,1,1,0]),index=pd.date_range(start=now,end=leave,freq=timedelta(hours=1)))

optsolver=SolverFactory("cplex")

schedule1,soc1=minimize_charging_cost_lp(optsolver,now,leave,dT,P_c,P_d,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_1)
schedule2,soc2=minimize_charging_cost_lp(optsolver,now,leave,dT,P_c,P_d,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_2)
schedule3,soc3=minimize_charging_cost_lp(optsolver,now,leave,dT,P_c,P_d,E,ini_soc,fin_soc,min_soc,max_soc,cost_coeff_3)

sched1=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)
sched2=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)
sched3=pd.DataFrame(columns=['Pow','SoC','Cost'],index=schedule1.index)

sched1['Pow'] =schedule1/P_c
sched1['SoC'] =soc1
sched1['Cost']=cost_coeff_1.reindex(schedule1.index).fillna(method='ffill')
sched1.plot(title="Schedule1")

sched2['Pow'] =schedule2/P_c
sched2['SoC'] =soc2
sched2['Cost']=cost_coeff_2.reindex(schedule1.index).fillna(method='ffill')
sched2.plot(title="Schedule2")

sched3['Pow'] =schedule3/P_c
sched3['SoC'] =soc3
sched3['Cost']=cost_coeff_3.reindex(schedule1.index).fillna(method='ffill')
sched3.plot(title="Schedule3")
    