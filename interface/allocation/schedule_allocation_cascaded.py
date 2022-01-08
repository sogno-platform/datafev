# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 18:59:12 2022

@author: egu
"""

import pandas as pd
from algorithms.allocation.rulebased import minimize_intercluster_unabalance,minimize_cluster_capacity_violation

def allocation_for_min_unbalance(cs, ts, time_delta, opt_horizon, ev_schedule, cc_schedules):
    """
    This function identifies the candidate clusters and calls the unbalance minimization function before allocation
    """
    cluster_occupation_profile = cs.get_cluster_occupations(ts, time_delta, opt_horizon)
    cluster_occupation_actual = cluster_occupation_profile.iloc[0]  # Current occupation
    candidate_clusters = cluster_occupation_actual[cluster_occupation_actual < cs.cu_numbers].index

    if len(candidate_clusters) > 0:
        optimal_cluster = minimize_intercluster_unabalance(cc_schedules, ev_schedule, candidate_clusters,cs.cc_installed_capacities)
    else:
        optimal_cluster = None

    return optimal_cluster

def allocation_for_min_violation(cs, ts, time_delta, opt_horizon, ev_schedule, cc_schedules):
    """
    This function identifies the candidate clusters and calls the unbalance minimization function before allocation
    """

    cluster_occupation_profile = cs.get_cluster_occupations(ts, time_delta, opt_horizon)
    cluster_occupation_actual = cluster_occupation_profile.iloc[0]  # Current occupation
    candidate_clusters = cluster_occupation_actual[cluster_occupation_actual < cs.cu_numbers].index

    if len(candidate_clusters) > 0:
        optimal_cluster = minimize_cluster_capacity_violation(cc_schedules, ev_schedule, candidate_clusters, cs.cc_capacities)
    else:
        optimal_cluster = None
    
    return optimal_cluster