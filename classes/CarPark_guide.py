# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 09:41:11 2019

@author: egu-cse
"""

from datetime import timedelta
from itertools import product
import pandas as pd
import numpy as np

from classes.Charger import ChargingModule

from optimizationmodels.deterministic.new_models.allocation import choose_an_arm
from optimizationmodels.deterministic.new_models.allocation_peak import choose_an_arm_peakmin
from optimizationmodels.deterministic.new_models.scheduling_mpc_ import mpc_optimize_schedules
from optimizationmodels.deterministic.new_models.singlecar.earliest import find_earliest_schedule
from optimizationmodels.deterministic.new_models.singlecar.cheapest import find_cheapest_schedule
from optimizationmodels.deterministic.new_models.singlecar.smoothest import find_smoothest_schedule
from optimizationmodels.deterministic.new_models.cellpowers.rule_based import intervene_unbalance_for_dummy_charging,let_unbalance_for_dummy_charging
from optimizationmodels.deterministic.new_models.cellpowers.rule_based_single_unit import calculate_p_ref

class CarPark(object):
    
    def __init__(self,timer,nbArmModules,maxP_MMC,maxP_Module,eff_ch=1.0):
        
        #Timer paramters
        self.timer       =timer                 #Timer class for simulation
       
        #Topology parameters
        self.phases=list(range(1,4))            #Phases in MMC 1,2,3
        self.arms  =list(range(1,3))            #Arms of each phase 1,2   
        self.nslots = nbArmModules              #Submodules number
        self.cells =list(range(nbArmModules))   #Arm submodule indices                    
        
        #Power limit parameters
        self.maxP_Module =maxP_Module           #Maximum charging power of each submodule  (kW)
        self.P_MMC_max =maxP_MMC                #Maximum charging power of the MMC         (kW)
        self.P_Arm_max =maxP_MMC/6              #Power capacity of the MMC arms            (kW) 
        self.eff_ch    =eff_ch                  #Charging module efficiency
        
        #One ChargingModule object for each submodule in each arm of each phase
        self.chargingmodules={}  
        for j,k,n in product(self.phases,self.arms,self.cells):
            self.chargingmodules[j,k,n]=ChargingModule(self.timer,self.maxP_Module,self.eff_ch)

        #Power curves
        self.armpower={}
        self.armcarno={}
        self.phspower={}
        self.phscarno={}
        self.idlcarno={}
        self.modpower={}
        for j in self.phases:
            self.phspower[j]={}
            self.phscarno[j]={}
            for k in self.arms:
                self.armpower[j,k]={}
                self.armcarno[j,k]={}
                for n in self.cells:
                    self.modpower[j,k,n]={}
                    
        #Imbalances
        self.optW0 = 1      # Weight of horizontal imbalance
        self.optW1 = 1      # Weight of vertical imbalance
            
        #Data handling attributes
        self.actual_carlist={self.timer.now:[]}
        self.actual_idlecarlist={self.timer.now:[]}      
        self.entryID=1000000
        self.host_dataset=pd.DataFrame(columns=['Car Object','Car ID','Car Model',
                                                'Arrival Time','Arrival SOC','Connected Arm','Connected Slot',
                                                'Estimated Leave','Desired Leave SOC', 'Charging Completed',
                                                'Charged Energy [kWh]','Leave Time','Leave SOC'])
    
        self.car_data_packs={}
        
    def load_price(self,series,resolution):
        """
        Method to load electricity price data as time series
        """
        start=min(series.index)
        end  =max(series.index)+timedelta(hours=1)
        n_of_steps=int((end-start)/resolution)
        timerange =[start+t*resolution for t in range(n_of_steps+1)]
        temp_ser=series.reindex(timerange)
    
        self.elprice=temp_ser.fillna(temp_ser.fillna(method='ffill'))
        
    def enter_cars(self,ts,enteringCars):  
        """ 
        Method to enter the cars into the car park and save their data in a
        dataframe which is updated every instant.
        """
        for car in enteringCars.keys():
            self.car_data_packs[car]={'dataid':self.entryID,
                                      'expDep':enteringCars[car]['Estimated departure'],
                                      'desSoC':enteringCars[car]['Desired SoC'] }
            
            
            self.actual_carlist[self.timer.now] += [car]
            self.actual_idlecarlist[self.timer.now] += [car]
            
            self.host_dataset.loc[self.entryID,'Car Object'] = car 
            self.host_dataset.loc[self.entryID,'Car ID'] = car.id   
            self.host_dataset.loc[self.entryID,'Car Model'] = car.model  
            self.host_dataset.loc[self.entryID,'Entry Date']   = ts.strftime('%d-%m-%Y')           
            self.host_dataset.loc[self.entryID,'Arrival Time'] = ts
            self.host_dataset.loc[self.entryID,'Arrival SOC'] = car.soc[ts]
            self.host_dataset.loc[self.entryID,'Connected Slot']     = None
            self.host_dataset.loc[self.entryID,'Charging Completed'] = None
            self.host_dataset.loc[self.entryID,'Estimated Leave']   = self.car_data_packs[car]['expDep']
            self.host_dataset.loc[self.entryID,'Desired Leave SOC'] = self.car_data_packs[car]['desSoC']
            self.entryID+=1 
             
    def check_cell_states(self,ts,timeindex):
        """
        Method that returns the old schedule and number of cars
        """  
        connections={}
        connections_arm=dict([((p,a),{})        for p in self.phases for a in self.arms])
        for car in self.car_data_packs:               
            if car not in self.actual_idlecarlist[ts]:
                car_datapack=self.car_data_packs[car]
                
                phs,arm,n         =car_datapack['Connected Slot']
                old_soc_trajectory=car_datapack['SOC k-1']
                des_soc           =car_datapack['desSoC']
                leave_ts          =car_datapack['expDep']
                
                soc_reference=old_soc_trajectory.reindex(timeindex)
                soc_reference=soc_reference.interpolate(method='linear',limit_direction='forward')
                
                connections[car.id]={}
                connections[car.id]['Cell']         =phs,arm,n
                connections[car.id]['ReferenceSOC'] =soc_reference
                connections[car.id]['BCap']         =car.bCapacity
                connections[car.id]['P_Max']        =min(self.maxP_Module*self.eff_ch,car.max_ac_charge)
                connections[car.id]['SoC']          =car.soc[ts]
                connections[car.id]['finSoC']       =des_soc
                connections[car.id]['leavets']      =leave_ts

                connections_arm[phs,arm][car.id]=connections[car.id].copy()
        return connections,connections_arm
    
    def check_cell_occupation(self,ts):
        occupation={}
        for j in self.phases:
            for k in self.arms:
                for n in self.cells:
                    if self.chargingmodules[j,k,n].connected_car[ts]!=None:
                        occupation[j,k,n]=1
                    else:
                        occupation[j,k,n]=0
        return occupation
    
    def check_arm_occupation(self,ts):
        armoccupation={}
        for j in self.phases:
            for k in self.arms:
                armoccupation[j,k]=0
                for n in self.cells:
                    if self.chargingmodules[j,k,n].connected_car[ts]!=None:
                        armoccupation[j,k]+=1
        return armoccupation
        
         
    def check_arm_states(self,ts,optStepSize,optHorizon):
        """
        Method that returns the aggregated arm schedule and number of cars
        """       
        timeindex =pd.date_range(start=ts,end=ts+optHorizon-optStepSize,freq=optStepSize)
        zeroseries=pd.Series(np.zeros(len(timeindex)),index=timeindex)

        presence     =dict([((p,a,n),0)        for p in self.phases for a in self.arms for n in self.cells])
        arm_car_nb   =dict([((p,a),0.0)        for p in self.phases for a in self.arms])
        arm_schedule =dict([((p,a),zeroseries.copy()) for p in self.phases for a in self.arms])
        mmc_schedule =zeroseries.copy()
    
        for car in self.car_data_packs:            
            
            if car not in self.actual_idlecarlist[ts]:
                car_datapack=self.car_data_packs[car]
                
                phs,arm,n   =car_datapack['Connected Slot']
                expDep      =car_datapack['expDep']
                
                car_old_schedule=car_datapack['Schedule k-1']
                car_new_schedule=car_old_schedule.reindex(timeindex)
                car_new_schedule.loc[car_new_schedule.index>=expDep]=0
                car_schedule=car_new_schedule.fillna(method='ffill')
                
                presence[phs,arm,n]   =1
                arm_car_nb  [phs,arm]+=1
                arm_schedule[phs,arm]+=car_schedule.copy()
                mmc_schedule         +=car_schedule.copy()
            
        return arm_schedule,arm_car_nb,presence,mmc_schedule
    
    def connect_car(self,ts,car,j,k,n):
        """
        Method that connects the car into the specified charging module in the
        corresponding phase and arm.
        """
        self.host_dataset.loc[self.car_data_packs[car]['dataid'],'Connected Slot']=(j,k,n)
        self.host_dataset.loc[self.car_data_packs[car]['dataid'],'Connected Arm']=int(10*j+k)
        self.chargingmodules[j,k,n].connect(ts,car)
        self.actual_idlecarlist[ts].remove(car)
        self.car_data_packs[car]['Connected Slot']=(j,k,n)
        self.car_data_packs[car]['P_Max']=min(car.max_ac_charge,self.chargingmodules[j,k,n].P_max)
               
    def remove_car(self,ts,car):
        """
        Method that removes the car from the specified charging module in the
        corresponding phase and arm. In addition, it updates the attributes calculated
        when the car leaves.
        """
        # Store the charging data to the park data set.
        dataid=self.car_data_packs[car]['dataid']
        del self.car_data_packs[car]
        
        self.host_dataset.loc[dataid,'Leave Time']=ts
        self.host_dataset.loc[dataid,'Leave SOC']=car.soc[ts]
        self.host_dataset.loc[dataid,'Charged Energy [kWh]']=(self.host_dataset.loc[dataid,'Leave SOC']-self.host_dataset.loc[dataid,'Arrival SOC'])*car.bCapacity/3600
            
        # Stop the charging and disconnect the car from the charging module.
        self.actual_carlist[self.timer.now].remove(car)        
        if car in self.actual_idlecarlist[self.timer.now]:
            self.actual_idlecarlist[self.timer.now].remove(car)
        else:
            slot = self.host_dataset.loc[dataid,'Connected Slot']
            self.chargingmodules[slot[0],slot[1],slot[2]].disconnect(ts)
            
            
    def implement_power_references(self,ts,p_cell_reference):
        """
        Method to implement cell power references for one time step starting by ts
        """
        #Implementation of controlled charging
        for j in self.phases:
            for k in self.arms:
                for n in self.cells:
                    car=self.chargingmodules[j,k,n].connected_car[ts] 
                    if car==None:
                        pass
                    else:
                        completed=self.chargingmodules[j,k,n].supply(ts,p_cell_reference[j,k][n])
                        if completed:
                            dataid=self.car_data_packs[car]['dataid']
                            self.host_dataset.loc[dataid,'Charging Completed']=ts+self.timer.dT
                        
    def individual_scheduling(self,ts,optStepSize,optHorizon,car,optSolver,cheapest=False,priceadapt=False,smoothest=False):
        """
        Scheduling of a single car
        """ 
        #Checking the armstates
        armschedules,armnumbers,presence,mmcschedule=self.check_arm_states(ts,optStepSize,optHorizon)
        overloadedsteps=mmcschedule[mmcschedule>self.P_MMC_max].index

        #First optimization for individual scheduling for the new car
        stepsize=optStepSize
        ecap    =car.bCapacity
        inisoc  =car.soc[ts]
        finsoc  =self.car_data_packs[car]['desSoC']
        leavets =self.car_data_packs[car]['expDep']
        p       =min(self.maxP_Module*self.eff_ch,car.max_ac_charge)
        elprice =self.elprice.copy()
        
        if priceadapt==True:
            elprice[overloadedsteps]=elprice[overloadedsteps]*2
              
        if cheapest==False:   #Fastest charging schedule
            if smoothest==False:
                schedule,soc=find_earliest_schedule(ts,stepsize,p,ecap,inisoc,finsoc,leavets)
            else:
                schedule,soc=find_smoothest_schedule(ts,stepsize,p,ecap,inisoc,leavets,finsoc)
        else: #Cheapest charging schedule
            schedule,soc=find_cheapest_schedule(optSolver,ts,stepsize,p,ecap,inisoc,elprice,leavets,finsoc)
            
        self.car_data_packs[car]['Schedule k-1']=schedule.copy()
        self.car_data_packs[car]['SOC k-1']     =soc.copy()
        
        return armschedules,armnumbers,presence,schedule
    
    def random_allocation_without_scheduling(self,ts):
        """
        Method to allocate the new car to a random arm without scheduling
        """
        occupation     =self.check_cell_occupation(ts)
        candidates=[(key) for key in occupation.keys() if occupation[key]==0]
        phase,arm,module=candidates[np.random.choice(len(candidates))]
        return phase, arm, module
    
    def simple_allocation_without_scheduling(self,ts):
        armoccupation     =self.check_arm_occupation(ts)
        phase,arm=min(armoccupation, key=armoccupation.get)
        n=0
        test=False
        while(test==False):
            if self.chargingmodules[phase,arm,n].connected_car[ts]==None:
                module=n
                test=True
            else:
                if n<(self.nslots-1):
                    n+=1
                else:
                    raise("There is no free slot in the arm")            
        
        return phase,arm,module
    
    def random_allocation(self,ts,optStepSize,optHorizon,car,optSolver,cheapest=False,priceadapt=False):
        """
        Method to allocate the new car to a random arm
        """
        armschedules,armnumbers,presence,schedule=self.individual_scheduling(ts,optStepSize,optHorizon,car,optSolver,cheapest,priceadapt)   
        #Choose the module to connect the car 
        candidates=[(key) for key in presence.keys() if presence[key]==0]
        phase,arm,module=candidates[np.random.choice(len(candidates))]
                
        return phase, arm, module
            
    def simple_allocation(self,ts,optStepSize,optHorizon,car,optSolver,cheapest=False,priceadapt=False):
        """
        Method to allocate the new car to the arm with smallest number of cars (Simple allocation)
        """   
        armschedules,armnumbers,presence,schedule=self.individual_scheduling(ts,optStepSize,optHorizon,car,optSolver,cheapest,priceadapt)  
        #Decision for car allocation 
        phase,arm=min(armnumbers, key=armnumbers.get)    
        #Choose the module to connect the car 
        n=0
        test=False
        while(test==False):
            if self.chargingmodules[phase,arm,n].connected_car[ts]==None:
                module=n
                test=True
            else:
                if n<(self.nslots-1):
                    n+=1
                else:
                    raise("There is no free slot in the arm")            
        
        return phase,arm,module
    
    def optimized_allocation_unb(self,ts,optStepSize,optHorizon,car,optSolver,cheapest=False,priceadapt=False,smoothest=False):
        """
        Method to allocate the new car to the optimal car according to the charging schedules
        """ 
        armschedules,armnumbers,presence,carschedule=self.individual_scheduling(ts,optStepSize,optHorizon,car,optSolver,cheapest,priceadapt,smoothest)
                     
        #Optimization for car allocation 
        opt_horizon=[ts+step*optStepSize for step in range(int(optHorizon/optStepSize))]       
        armsize                =self.nslots 
        optW0                  =self.optW0
        optW1                  =self.optW1
        leavets                =max(carschedule.index)
        allocation_to=choose_an_arm(optSolver,opt_horizon,optW0,optW1,armsize,carschedule,leavets,armschedules,armnumbers)
        phase=allocation_to[0]
        arm  =allocation_to[1]
        
        #Choose the module to connect the car 
        n=0
        test=False
        while(test==False):
            if self.chargingmodules[phase,arm,n].connected_car[ts]==None:
                module=n
                test=True
            else:
                if n<(self.nslots-1):
                    n+=1
                else:
                    raise("There is no free slot in the arm")
                                          
        return phase, arm, module
		
    def optimized_allocation_peak(self,ts,optStepSize,optHorizon,car,optSolver,cheapest=False,priceadapt=False):
        """
        Method to allocate the new car to the optimal car according to the charging schedules
        """ 
        armschedules,armnumbers,presence,carschedule=self.individual_scheduling(ts,optStepSize,optHorizon,car,optSolver,cheapest,priceadapt)
                      
        if sum(armnumbers.values())<1:
            phase,arm=1,1
        else:    
            #Optimization for car allocation 
            opt_horizon=[ts+step*optStepSize for step in range(int(optHorizon/optStepSize))]
            armoverload={}
            for j in self.phases:
                for k in self.arms:
                    if armnumbers[j,k]<self.nslots:
                        armnewloading=armschedules[j,k][opt_horizon]+carschedule[opt_horizon]
                        armoverload[j,k]=armnewloading[armnewloading>self.P_Arm_max].sum()
                    armoverload_ser=pd.Series(armoverload)
            phase,arm=armoverload_ser.idxmin()
		
        #Choose the module to connect the car 
        n=0
        test=False
        while(test==False):
            if self.chargingmodules[phase,arm,n].connected_car[ts]==None:
                module=n
                test=True
            else:
                if n<(self.nslots-1):
                    n+=1
                else:
                    raise("There is no free slot in the arm")
                                          
        return phase, arm, module
    
    def modulate_power(self,ts,optStepSize):
        
        p_ref={}
        for j in self.phases:
            for k in self.arms:
                P_Ref_CU=pd.Series(index=self.cells)
                for n in self.cells:
                    car=self.chargingmodules[j,k,n].connected_car[ts]
                    if car!=None:
                        soc =car.soc[ts]
                        ecap=car.bCapacity
                        p_cu=self.car_data_packs[car]['P_Max']
                        P_Ref_CU[n]=calculate_p_ref(soc,ecap,p_cu,optStepSize)
                    else:
                        P_Ref_CU[n]=0.0 
                                           
                P_Ref_Arm=P_Ref_CU.sum()
                if P_Ref_Arm<self.P_Arm_max:
                    p_ref[j,k]=P_Ref_CU.to_dict()
                else:
                    p_ref[j,k]=P_Ref_CU*self.P_Arm_max/P_Ref_Arm
                        
        return p_ref
        
    
    def get_cell_references_for_unlimited_unbalance(self,ts,optStepSize):
        """
        Method to calculate reference charging powers in case that unbalances are not controlled i.e. charging with full feasible power
        """
        #Calculating the references reduces such that the power of the arms that cause excessive unbalance are reduced
        p_cell_uncontrolled=let_unbalance_for_dummy_charging(ts,optStepSize,self.cells,self.chargingmodules,self.car_data_packs)
        return p_cell_uncontrolled
                
    def get_cell_references_for_limited_unbalance(self,ts,optStepSize,alpha,beta):
        """
        Method to calculate reference charging powers in case that unbalances are controlled according to the alpha-beta constraints
        """
        #Calculating the references reduces such that the power of the arms that cause excessive unbalance are reduced
        p_cell_ver_hor_balanced=intervene_unbalance_for_dummy_charging(ts,optStepSize,self.cells,self.chargingmodules,self.car_data_packs,alpha,beta)
        return p_cell_ver_hor_balanced
    
    def mpc_for_scheduling(self,ts,optStepSize,optHorizon,alpha,beta,optSolver):
        """
        Method to calculate reference charging powers with schedule optimization technique
        """    
        horizon =pd.date_range(start=ts,end=ts+optHorizon,freq=optStepSize)
        connections,arm_connections=self.check_cell_states(ts,horizon)
        
        if connections!={}:
            mmcdata={}
            mmcdata['opt_horizon']=horizon
            mmcdata['opt_step']   =optStepSize
            mmcdata['cells']      =self.cells
            mmcdata['alpha']      =alpha
            mmcdata['beta']       =beta
            mmcdata['eff_ch']     =self.eff_ch
            #mmcdata['price']      =self.elprice[horizon]
            mmcdata['arm_cap']    =self.P_Arm_max
            mmcdata['mmc_cap']    =self.P_MMC_max
            p_to_car_optimized,socs=mpc_optimize_schedules(mmcdata,connections,optSolver)
            p_cell_optimized=dict([((j,k),{}) for j in self.phases for k in self.arms])
            for car_id,power in p_to_car_optimized.items():                
                phs=connections[car_id]['Cell'][0]
                arm=connections[car_id]['Cell'][1]
                n  =connections[car_id]['Cell'][2]
                p_cell_optimized[phs,arm][n]=power
        else:
            p_cell_optimized={}
            socs  ={}
            
        return p_cell_optimized,socs
    
    def mpc_for_scheduling_(self,ts,optStepSize,optHorizon,alpha,beta,optSolver):
        horizon =pd.date_range(start=ts,end=ts+optHorizon,freq=optStepSize)
        connections,arm_connections=self.check_cell_states(ts,horizon)
        
        if connections!={}:
            mmcdata={}
            mmcdata['opt_horizon']=horizon
            mmcdata['opt_step']   =optStepSize
            mmcdata['cells']      =self.cells
            mmcdata['eff_ch']     =self.eff_ch
            mmcdata['arm_cap']    =self.P_Arm_max
            mmcdata['mmc_cap']    =self.P_MMC_max
                
            p_cell_optimized=dict([((j,k),{}) for j in self.phases for k in self.arms])
            for j in self.phases:
                for k in self.arms:
                    if arm_connections!={}:                 
                        p_to_car_optimized,socs=mpc_optimize_schedules(mmcdata,arm_connections[j,k],optSolver)
                        for car_id,power in p_to_car_optimized.items():                
                            phs=connections[car_id]['Cell'][0]
                            arm=connections[car_id]['Cell'][1]
                            n  =connections[car_id]['Cell'][2]
                            p_cell_optimized[phs,arm][n]=power
        else:
            p_cell_optimized={}
        
        return p_cell_optimized,[]
        
                                                
    def save_power_data(self,ts):
        """
        Method to save the power and number of cars in the arms an phases at each instant of the simulation.
        """
        # Arm Power Data
        for j in self.phases:
            self.phspower[j][ts]=0
            self.phscarno[j][ts]=0
            for k in self.arms:
                self.armpower[j,k][ts]=0
                self.armcarno[j,k][ts]=0
                for n in self.cells:
                    if self.chargingmodules[j,k,n].connected_car[ts]!=None:
                        p=self.chargingmodules[j,k,n].supplied_power[ts]
                        self.armpower[j,k][ts]+=p
                        self.armcarno[j,k][ts]+=1
                    else:
                        p=0
                    self.modpower[j,k,n][ts]=self.chargingmodules[j,k,n].supplied_power[ts]
                        
                self.phspower[j][ts]+=self.armpower[j,k][ts]
                self.phscarno[j][ts]+=self.armcarno[j,k][ts]
        self.idlcarno[ts]=len(self.actual_idlecarlist[ts])
                                     
    def simulation_summary(self):
        """
        Method to organize the arm-phase powers-carno as time series in pandas dataframes
        """
        arm_power_time_series = pd.DataFrame(columns=[(j,k) for j in self.phases for k in self.arms])
        arm_carno_time_series = pd.DataFrame(columns=[(j,k) for j in self.phases for k in self.arms])
        phs_power_time_series = pd.DataFrame(columns=[j for j in self.phases])
        phs_carno_time_series = pd.DataFrame(columns=[j for j in self.phases])
        
        for j in self.phases:
            phs_power_time_series[j]=pd.Series(self.phspower[j])
            phs_carno_time_series[j]=pd.Series(self.phscarno[j])
            for k in self.arms:
                arm_power_time_series[j,k]=pd.Series(self.armpower[j,k])
                arm_carno_time_series[j,k]=pd.Series(self.armcarno[j,k])
        arm_carno_time_series['Not Connected'] = pd.Series(self.idlcarno)
        
        return arm_power_time_series, phs_power_time_series, arm_carno_time_series, phs_carno_time_series
    
    def module_history(self):
        
        module_power=pd.DataFrame(columns=[(j,k,n) for j in self.phases for k in self.arms for n in self.cells])
        for j in self.phases:
            for k in self.arms:
                for n in self.cells:
                    module_power[j,k,n]=pd.Series(self.modpower[j,k,n])
        return module_power
            
        
    def update_timer(self):
        """
        Method to update the timer every instant. This should always be done after
        all the required simulation steps have been accomplished.
        """
        self.timer.updateTimer()
        self.actual_carlist[self.timer.now]=self.actual_carlist[self.timer.now-self.timer.dT].copy()
        self.actual_idlecarlist[self.timer.now]=self.actual_idlecarlist[self.timer.now-self.timer.dT].copy()
                       
        for j,k,n in product(self.phases,self.arms,self.cells):
            self.chargingmodules[j,k,n].retrieve_connection_data(self.timer.now)
            
        for car in self.actual_idlecarlist[self.timer.now]:
            car.retrieve_soc_data(self.timer.now)