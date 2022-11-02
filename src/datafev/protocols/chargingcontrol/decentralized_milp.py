import pandas as pd
from src.datafev.algorithms.cluster.rescheduling_milp import reschedule


def charging_protocol(ts, t_delta, horizon, system, solver, penalty_parameters):
    """
    This protocol is executed periodically during operation of charger clusters.

    It addresses the scenarios where EVs connected in clusters have previously defined charging schedules that may
    require deviations due to the local power consumption constraints of clusters. The control architecture is
    decentralized; therefore, each cluster applies its own control. The applied control is based on MILP rescheduling.

    :param ts:                      Current time                                            datetime
    :param t_delta:                 Control horizon                                         timedelta
    :param horizon:                 Optimization horizon of rescheduling                    timedelta
    :param system:                  Multi-cluster system object                             datahandling.multicluster
    :param solver:                  Optimization solver                                     pyomo SolverFactory object
    :param penalty_parameters:      Cost parameters for capacity violation / devations      dict

    """

    schedule_horizon = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    opt_horizon = list(range(len(schedule_horizon)))
    opt_step = t_delta.seconds

    # Loop through the clusters
    for cc_id in system.clusters.keys():

        cluster = system.clusters[cc_id]

        if cluster.number_of_connected_chargers(ts) > 0:
            # The cluster includes connected EVs

            ################################################################################################
            # Step 1: Identification of charging demand

            # Parameters defining the upper/lower limits of (soft) power consumption constraints of cluster
            upperlimit = dict(
                enumerate(cluster.upper_limit[schedule_horizon[:-1]].values)
            )
            lowerlimit = dict(
                enumerate(cluster.lower_limit[schedule_horizon[:-1]].values)
            )

            # Parameter defining how much the upperlimit/lowerlimit can be violated
            tolerance = cluster.violation_tolerance

            # Cost parameter penalizing deviation from individual optimal charging schedules of EVs
            rho_y = penalty_parameters["rho_y"][cc_id]

            # Cost parameter penalizing violation of (soft) power consumption constraints of clusters
            rho_eps = penalty_parameters["rho_eps"][cc_id]

            # Dictionary containing EV charging demand parameters
            pmax_pos = (
                {}
            )  # Will contain the maximum power that can be withdrawn by the EVs
            pmax_neg = (
                {}
            )  # Will contain the maximum power that can be injected by the EVs
            ch_eff = (
                {}
            )  # Will contain charging efficiencies of the chargers hosting EVs
            ds_eff = (
                {}
            )  # Will contain discharging efficiencies of the chargers hosting EVs
            bcap = {}  # Will contain battery capacities of EVs
            tarsoc = {}  # Will contain target SOCs (at the end of rescheduling horizon)
            deptime = {}  # Will contain time until departures (in number of time steps)
            inisoc = {}  # Will contain current SOCs of EVs
            minsoc = {}  # Will contain maximum SOCs allowed by EVs
            maxsoc = {}  # Will contain minimum SOCs allowed by EVs

            # Loop through the chargers
            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    # There is an EV connected in this charger
                    ev_id = ev.vehicle_id

                    # with a schedule of
                    sch_inst = cu.active_schedule_instance
                    cu_sch = cu.schedule_soc[sch_inst]
                    cu_sch = cu_sch.reindex(schedule_horizon)
                    cu_sch = cu_sch.fillna(method="ffill")

                    # parameters defining the charging demand/urgency
                    bcap[ev_id] = ev.bCapacity
                    deptime[ev_id] = (ev.t_dep_est - ts) / t_delta
                    inisoc[ev_id] = ev.soc[ts]
                    minsoc[ev_id] = ev.minSoC
                    maxsoc[ev_id] = ev.maxSoC
                    tarsoc[ev_id] = cu_sch[ts + horizon]
                    ch_eff[ev_id] = cu.eff
                    ds_eff[ev_id] = cu.eff

                    # maximum power that can be withdrawn/injected by the connected EV
                    pmax_pos[ev_id] = min(ev.p_max_ch, cu.p_max_ch)
                    pmax_neg[ev_id] = min(ev.p_max_ds, cu.p_max_ds)

            ################################################################################################

            ################################################################################################
            # Step 2: Solving (MILP-based) rescheduling problem to optimize the power distribution in cluster
            p_schedule, s_schedule = reschedule(
                solver,
                opt_step,
                opt_horizon,
                upperlimit,
                lowerlimit,
                tolerance,
                bcap,
                inisoc,
                tarsoc,
                minsoc,
                maxsoc,
                ch_eff,
                ds_eff,
                pmax_pos,
                pmax_neg,
                deptime,
                rho_y,
                rho_eps,
            )
            ################################################################################################

            ################################################################################################
            # Step 3: Charging
            for cu_id in system.clusters[cc_id].chargers.keys():
                cu = system.clusters[cc_id].chargers[cu_id]
                if cu.connected_ev != None:
                    ev_id = cu.connected_ev.vehicle_id
                    cu.supply(ts, t_delta, p_schedule[ev_id][0])
            ################################################################################################
