# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 13:08:47 2022

@author: egu
"""

import pandas as pd

def least_laxity_first(demand,capacity_lb,capacity_ub):
    
    injection  =(demand['R'].apply(lambda x: x if x<0  else 0))*demand['f_n']
    consumption=(demand['R'].apply(lambda x: x if x>=0 else 0))/demand['f_p'] 
    demand['Net'] =injection+consumption
      
    if capacity_lb<=demand['Net'].sum()<=capacity_ub:
        setpoints=demand['R']
        
    else:
        
        if capacity_ub<demand['Net'].sum():
 
            dem_sorted    =demand.sort_values('m',ascending=False)
            setpoints_     =dem_sorted['Net'].copy()
            charging_sorted=dem_sorted[dem_sorted['Net']>0]
            
            demand_lb_neg =(demand['lb'].apply(lambda x: x if x<0  else 0))*demand['f_n']
            demand_lb_pos =(demand['lb'].apply(lambda x: x if x>=0  else 0))/demand['f_p']
            demand_lb     =demand_lb_neg+demand_lb_pos
            
            n_first_attempt=0      
            finished_first_attempt=False    
            while(setpoints_.sum()>capacity_ub and finished_first_attempt==False):
            
                ind   =charging_sorted.index[n_first_attempt]
                _ref  =charging_sorted.loc[ind,'Net']
                _min  =demand_lb[ind]
                margin=_ref-max(_min,0.0)
                
                excess=setpoints_.sum()-capacity_ub
                reduct=min(excess,margin)
                
                setpoints_[ind]=_ref-reduct
                
                n_first_attempt+=1
                if n_first_attempt==len(charging_sorted):
                    finished_first_attempt=True
                        
            n=0
            while(setpoints_.sum()>capacity_ub):
                
                ind   =charging_sorted.index[n]
                _ref  =setpoints_[ind]
                _min  =demand_lb[ind]
                margin=_ref-_min
                
                excess=setpoints_.sum()-capacity_ub
                reduct=min(excess,margin)
                setpoints_[ind]=_ref-reduct
                n+=1
                
        if demand['Net'].sum()<capacity_lb:

            dem_sorted    =demand.sort_values('m',ascending=True)
            setpoints_     =dem_sorted['Net'].copy()
            
            demand_ub_neg =(demand['ub'].apply(lambda x: x if x<0  else 0))*demand['f_n']
            demand_ub_pos =(demand['ub'].apply(lambda x: x if x>=0  else 0))/demand['f_p']
            demand_ub     =demand_ub_neg+demand_ub_pos
            
            n=0
            while(setpoints_.sum()<capacity_lb):
                
                ind   =dem_sorted.index[n]
                _ref  =setpoints_[ind]
                _max  =demand_ub[ind]
                margin=_max-_ref
                
                deficit=capacity_lb-setpoints_.sum()
                increas=min(deficit,margin)
                setpoints_[ind]=_ref+increas
                n+=1
                           
        set_injection  =(setpoints_.apply(lambda x: x if x<0  else 0))/demand['f_n']
        set_consumption=(setpoints_.apply(lambda x: x if x>0  else 0))*demand['f_p']
        setpoints=set_injection+set_consumption
    
    return setpoints

        
#%%  
#eff3=0.95
#con3=15
#dem3=pd.DataFrame(index=['A','B','C','D','E','F'])
#dem3['lb'] =[7,-7,-11,-22,-22,-7]
#dem3['ub'] =[7,7,11,22,22,7]    
#dem3['R']  =[7,7,11,22,-11,0]    
#dem3['m']  =[0.32,0.11,0.17,0.83,0.64,0.13]
#dem3['f_p']=[eff3]*6
#dem3['f_n']=[eff3]*6
#sp3=least_laxity_first(dem3,-con3,con3)
#dem3_=dem3[['m','R']]
#dem3_['C']=sp3
#tot3_=((dem3_[dem3_['C']>0]['C']).sum()/eff3)+((dem3_[dem3_['C']<0]['C']).sum()*eff3)

##%%  
#eff4=0.95
#con4=4
#dem4=pd.DataFrame(index=['A','B','C','D','E','F'])
#dem4['lb'] =[7,7,-11,-22,-22,-7]
#dem4['ub'] =[7,7,11,22,22,7]    
#dem4['R']  =[7,7,0,22,-11,0]    
#dem4['m']  =[0.32,0.11,0.17,0.83,0.64,0.13]
#dem4['f_p']=[eff4]*6
#dem4['f_n']=[eff4]*6
#sp4=least_laxity_first(dem4,50,50)
#dem4_=dem4[['m','R']]
#dem4_['C']=sp4
#tot4_=((dem4_[dem4_['C']>0]['C']).sum()/eff4)+((dem4_[dem4_['C']<0]['C']).sum()*eff4)


    
    
    
    