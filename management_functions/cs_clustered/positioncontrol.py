from management_algorithms.multicluster.allocation_analytical import minimize_inter_cluster_unabalance,minimize_cluster_capacity_violation
from management_algorithms.multicluster.allocation_optimization import optimal_costdif_cluster

def optimal_allocation_min_unbalance(cs, ts, time_delta, opt_horizon, ev_schedule, cc_schedules):
    """
    This function identifies the candidate clusters and calls the unbalance minimization function before allocation
    """
    cluster_occupation_profile = cs.get_cluster_occupations(ts, time_delta, opt_horizon)
    cluster_occupation_actual = cluster_occupation_profile.iloc[0]  # Current occupation
    candidate_clusters = cluster_occupation_actual[cluster_occupation_actual < cs.cu_numbers].index

    if len(candidate_clusters) > 0:
        optimal_cluster = minimize_inter_cluster_unabalance(cc_schedules, ev_schedule, candidate_clusters,cs.cc_installed_capacities)
    else:
        optimal_cluster = None

    return optimal_cluster

def optimal_allocation_min_violation(cs, ts, time_delta, opt_horizon, ev_schedule, cc_schedules):
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

def optimal_allocation_cluster_cost_diff(cs,ev,ts,time_delta,opt_horizon,solver):
    """
    This function jointly optimizes the cluster allocation and schedule of an incoming EV for given cluster differentiating price signals 
    """
    #TODO: 
    #1) Necessary input parsing to run dynamic pricing_analytical())
    #
    #
    #cluster_cost_series={}
    #for c in cs.clusters.keys():
    #    cluster_cost_series[c]=dynamicpricing_analytical()
    #2) Necessary input parsing to call optimal_costdif_cluster()
    #
    #
    #p_ref,soc_ref,optimal_cluster=optimal_costdif_cluster(solver,arrts,leavets,time_delta,p_ch,p_ds,ecap,inisoc,tarsoc,minsoc,maxsoc,costcoeffs)
    #3) return p_ref,soc_ref,optimal_cluster
    return 0
