# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 11:19:46 2021

@author: egu
"""

def penalize_violation(cu_schedules,cc_limit,tou_price):
    """
    #This function 
    #1) checks the existing commitments of the cluster
    #2) compares the commitments with the power limit of the cluster
    #3) the coefficients of the steps where the commitments limit of the cluster must be twice as tou_price     
    #returns cc_cost_coeff
    """

    cc_cost_coeff = tou_price.copy()
    cc_schedule   = cu_schedules.sum(axis=1)
    overloadedsteps = cc_schedule[cc_schedule>=cc_limit].index
    cc_cost_coeff[overloadedsteps] = cc_cost_coeff[overloadedsteps] * 2
    
    return cc_cost_coeff

