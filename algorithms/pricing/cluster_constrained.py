# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 11:19:46 2021

@author: egu
"""

def penalize_violation(cc_schedule,cc_limit_upper,cc_limit_lower,tou_price):#,f=0.5):
    """
    #This function 
    #1) checks the existing commitments of the cluster
    #2) compares the commitments with the power limit of the cluster
    #3) the coefficients of the steps where the commitments limit of the cluster must be twice as tou_price     
    #returns cc_cost_coeff
    """

    cc_cost_coeff     = tou_price.copy()
    cc_cost_coeff_max = cc_cost_coeff.max()*1.01
    cc_cost_coeff_min = cc_cost_coeff.min()*0.99
     
    
    overloadedsteps   = cc_schedule[cc_schedule>=cc_limit_upper].index
    underloadedsteps  = cc_schedule[cc_schedule<=cc_limit_lower].index
    
    if len(overloadedsteps)>0:
        excess      = cc_schedule[overloadedsteps]-cc_limit_upper[overloadedsteps]
        excess_max  = max(excess)
        if excess_max>0.01:
            excess_norm = excess/excess_max
            cc_cost_coeff[overloadedsteps] = cc_cost_coeff_max*(1+excess_norm)
        else:
            cc_cost_coeff[overloadedsteps] = cc_cost_coeff_max
    
    if len(underloadedsteps)>0:
        deficit     = cc_limit_lower[underloadedsteps]-cc_schedule[underloadedsteps]
        deficit_max = max(deficit)
        if deficit_max>0.01:
            deficit_norm= deficit/deficit_max
            cc_cost_coeff[underloadedsteps]= cc_cost_coeff_min*(1-deficit_norm)
        else:
            cc_cost_coeff[underloadedsteps]= cc_cost_coeff_min
    
#    cc_cost_coeff[overloadedsteps] = cc_cost_coeff[overloadedsteps] * (1+f*excess)
#    cc_cost_coeff[underloadedsteps] = cc_cost_coeff[underloadedsteps] * (1-f*deficit)
    
    return cc_cost_coeff

