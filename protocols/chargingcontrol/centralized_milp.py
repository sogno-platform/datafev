import pandas as pd
from algorithms.multicluster.rescheduling_milp import reschedule

def charging_protocol(ts, t_delta, horizon, system, solver, penalty_parameters):
    """
    This protocol is executed periodically during operation of charger clusters.

    It addresses the scenarios where EVs connected in clusters have previously defined charging schedules that may
    require deviations due to the local power consumption constraints of clusters. The control architecture is
    centralized; therefore, all clusters are controlled by a single decision-maker. The applied control is based
    on MILP rescheduling.

    :param ts:                      Current time                                            datetime
    :param t_delta:                 Resolution of scheduling                                timedelta
    :param horizon:                 Optimization horizon of rescheduling                    timedelta
    :param system:                  Multi-cluster system object                             datahandling.multicluster
    :param solver:                  Optimization solver                                     pyomo SolverFactory object
    :param penalty_parameters:      Cost parameters for capacity violation / devations      dict

    """

    schedule_horizon = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    opt_horizon = list(range(len(schedule_horizon)))
    opt_step    = t_delta.seconds

    ################################################################################################
    # Step 1: Identification of charging demand

    # Parameters defining the power constraints
    powlimits = {}

    # Clusters' individual power constraints/ violation tolerance
    powlimits['P_CC_up_lim']  = {}          # Will contain the upper limit of (soft) power consumption constraint
    powlimits['P_CC_low_lim'] = {}          # Will contain the lower limit of (soft) power consumption constraint
    powlimits['P_CC_vio_lim'] = {}          # Will contain the violation tolerance of upperlimit/lowerlimits

    # System level constraints power constraints
    powlimits['P_CS_up_lim']  = dict(enumerate(system.upper_limit[schedule_horizon[:-1]].values))
    powlimits['P_CS_low_lim'] = dict(enumerate(system.lower_limit[schedule_horizon[:-1]].values))

    # Dictionary containing EV charging demand parameters
    evdata = {}
    evdata['P_EV_pos_max'] = {}     #Will contain the maximum power that can be withdrawn by the EVs
    evdata['P_EV_neg_max'] = {}     #Will contain the maximum power that can be injected by the EVs
    evdata['charge_eff'] = {}       #Will contain charging efficiencies of the chargers hosting EVs
    evdata['discharge_eff'] = {}    #Will contain discharging efficiencies of the chargers hosting EVs
    evdata['battery_cap'] = {}      #Will contain battery capacities of EVs
    evdata['target_soc'] = {}       #Will contain target SOCs (at the end of rescheduling horizon)
    evdata['departure_time'] = {}   #Will contain time until departures (in number of time steps)
    evdata['initial_soc'] = {}      #Will contain current SOCs of EVs
    evdata['minimum_soc'] = {}      #Will contain maximum SOCs allowed by EVs
    evdata['maximum_soc'] = {}      #Will contain minimum SOCs allowed by EVs
    evdata['location'] = {}         #Will contain the parameters indicating the location of EV in multi-cluster system

    # Dictionaries contianing the penalty factors for the objective function of optimization model
    rho_y  = {} # Will contain cost parameters penalizing deviation from individual schedules of EVs
    rho_eps= {} # Will contain cost parameters penalizing violation of (soft) power consumption constraints of clusters

    #Loop through the clusters
    clusters = []
    for cc_id in system.clusters.keys():

        cluster=system.clusters[cc_id]

        if cluster.number_of_connected_chargers(ts) > 0:

            #There are some connected EVs in this clusters, so this cluster must be taken into account in optimization
            clusters.append(cc_id)

            # Parameters defining the upper/lower limits of (soft) power consumption constraints of cluster
            powlimits['P_CC_up_lim'][cc_id]  = dict(enumerate(cluster.upper_limit[schedule_horizon[:-1]].values))
            powlimits['P_CC_low_lim'][cc_id] = dict(enumerate(cluster.lower_limit[schedule_horizon[:-1]].values))

            # Parameter defining how much the upperlimit/lowerlimit can be violated
            powlimits['P_CC_vio_lim'][cc_id] = cluster.violation_tolerance

            # Cost parameter penalizing deviation from individual optimal charging schedules of EVs
            rho_y[cc_id]=penalty_parameters['rho_y'][cc_id]

            # Cost parameter penalizing violation of (soft) power consumption constraints of clusters
            rho_eps[cc_id]= penalty_parameters['rho_eps'][cc_id]

            # Loop through the chargers
            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    # There is an EV connected in this charger
                    ev_id = ev.vehicle_id

                    # with a schedule of
                    sch_inst = cu.active_schedule_instance
                    cu_sch   = cu.schedule_soc[sch_inst]
                    cu_sch   = cu_sch.reindex(schedule_horizon)
                    cu_sch   = cu_sch.fillna(method="ffill")

                    # maximum power that can be withdrawn/injected by the connected EV
                    p_ev_pos_max = min(ev.p_max_ch, cu.p_max_ch)
                    p_ev_neg_max = min(ev.p_max_ds, cu.p_max_ds)

                    # other parameters defining the charging demand/urgency
                    evdata['battery_cap'][ev_id] = ev.bCapacity
                    evdata['departure_time'][ev_id] = (ev.t_dep_est - ts) / t_delta
                    evdata['initial_soc'][ev_id] = ev.soc[ts]
                    evdata['minimum_soc'][ev_id] = ev.minSoC
                    evdata['maximum_soc'][ev_id] = ev.maxSoC
                    evdata['target_soc'][ev_id] = cu_sch[ts + horizon]
                    evdata['charge_eff'][ev_id] = cu.eff
                    evdata['discharge_eff'][ev_id] = cu.eff
                    evdata['P_EV_pos_max'][ev_id] = p_ev_pos_max
                    evdata['P_EV_neg_max'][ev_id] = p_ev_neg_max
                    evdata['location'][ev_id] = (cc_id, cu_id)
    ################################################################################################

    if len(evdata['battery_cap'])>0:

        # The system includes connected EVs

        ################################################################################################
        # Step 2: Solving (MILP-based) rescheduling problem to centrally decide how the chargers will operate now
        p_schedule, s_schedule= reschedule(solver, opt_step, opt_horizon, powlimits, evdata, clusters, rho_y, rho_eps)
        ################################################################################################

        ################################################################################################
        # Step 3: Charging
        for cc_id in system.clusters.keys():
            for cu_id in system.clusters[cc_id].chargers.keys():
                cu = system.clusters[cc_id].chargers[cu_id]
                if cu.connected_ev != None:
                    ev_id = cu.connected_ev.vehicle_id
                    cu.supply(ts, t_delta, p_schedule[ev_id][0])
        ################################################################################################
