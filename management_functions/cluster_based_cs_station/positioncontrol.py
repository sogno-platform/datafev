from management_algorithms.multicluster.unbalance_analytical import minimize_cluster_unabalance

def optimal_allocation_min_unbalance(cs, ts, time_delta, opt_horizon, ev_schedule, cc_schedules):
    """
    This function identifies the candidate clusters and calls the unbalance minimization function before allocation
    """
    cluster_occupation_profile = cs.get_cluster_occupations(ts, time_delta, opt_horizon)
    cluster_occupation_actual = cluster_occupation_profile.iloc[0]  # Current occupation
    candidate_clusters = cluster_occupation_actual[cluster_occupation_actual < cs.cu_numbers].index

    if len(candidate_clusters) > 0:
        optimal_cluster = minimize_cluster_unabalance(cc_schedules, ev_schedule, candidate_clusters)
    else:
        optimal_cluster = None

    return optimal_cluster
