# The datafev framework

# Copyright (C) 2022,
# Institute for Automation of Complex Power Systems (ACS),
# E.ON Energy Research Center (E.ON ERC),
# RWTH Aachen University

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import pandas as pd
from datafev.algorithms.multi_cluster.rescheduling_milp import reschedule


def charging_routine(ts, t_delta, horizon, system, solver, penalty_parameters):
    """
    This routine is executed periodically during operation of charger clusters.

    It addresses the scenarios where EVs connected in clusters have previously defined charging schedules that may
    require deviations due to the local power consumption constraints of clusters. The control architecture is
    centralized; therefore, all clusters are controlled by a single decision-maker. The applied control is based
    on MILP rescheduling.

    Parameters
    ----------
    ts : datetime
        Current time.
    t_delta : timedelta
        Control horizon.
    horizon : timedelta
        Optimization horizon of rescheduling.
    system : data_handling.multi_cluster
        Multi-cluster system object.
    solver : pyomo SolverFactory object
        Optimization solver.
    penalty_parameters : dict
        Cost parameters for capacity violation/devations.

    Returns
    -------
    None.

    """

    schedule_horizon = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    opt_horizon = list(range(len(schedule_horizon)))
    opt_step = t_delta.seconds

    ################################################################################################
    # Step 1: Identification of charging demand

    # Clusters' individual power constraints/ violation tolerance
    cluster_upperlimits = (
        {}
    )  # Will contain the upper limit of (soft) power consumption constraint
    cluster_lowerlimits = (
        {}
    )  # Will contain the lower limit of (soft) power consumption constraint
    cluster_violationlimits = (
        {}
    )  # Will contain the violation tolerance of upperlimit/lowerlimits

    # System level constraints power constraints
    system_upperlimit = dict(
        enumerate(system.upper_limit[schedule_horizon[:-1]].values)
    )
    system_lowerlimit = dict(
        enumerate(system.lower_limit[schedule_horizon[:-1]].values)
    )

    # Dictionary containing EV charging demand parameters
    pmax_pos = {}  # Will contain the maximum power that can be withdrawn by the EVs
    pmax_neg = {}  # Will contain the maximum power that can be injected by the EVs
    ch_eff = {}  # Will contain charging efficiencies of the chargers hosting EVs
    ds_eff = {}  # Will contain discharging efficiencies of the chargers hosting EVs
    bcap = {}  # Will contain battery capacities of EVs
    tarsoc = {}  # Will contain target SOCs (at the end of rescheduling horizon)
    deptime = {}  # Will contain time until departures (in number of time steps)
    inisoc = {}  # Will contain current SOCs of EVs
    minsoc = {}  # Will contain maximum SOCs allowed by EVs
    maxsoc = {}  # Will contain minimum SOCs allowed by EVs
    location = (
        {}
    )  # Will contain the parameters indicating the location of EV in multi-cluster system

    # Dictionaries contianing the penalty factors for the objective function of optimization model
    rho_y = (
        {}
    )  # Will contain cost parameters penalizing deviation from individual schedules of EVs
    rho_eps = (
        {}
    )  # Will contain cost parameters penalizing violation of (soft) power consumption constraints of clusters

    # Loop through the clusters
    clusters = []
    for cc_id in system.clusters.keys():

        cluster = system.clusters[cc_id]

        if cluster.query_actual_occupation(ts) > 0:

            # There are some connected EVs in this clusters, so this cluster must be taken into account in optimization
            clusters.append(cc_id)

            # Parameters defining the upper/lower limits of (soft) power consumption constraints of cluster
            cluster_upperlimits[cc_id] = dict(
                enumerate(cluster.upper_limit[schedule_horizon[:-1]].values)
            )
            cluster_lowerlimits[cc_id] = dict(
                enumerate(cluster.lower_limit[schedule_horizon[:-1]].values)
            )

            # Parameter defining how much the upperlimit/lowerlimit can be violated
            cluster_violationlimits[cc_id] = cluster.violation_tolerance

            # Cost parameter penalizing deviation from individual optimal charging schedules of EVs
            rho_y[cc_id] = penalty_parameters["rho_y"][cc_id]

            # Cost parameter penalizing violation of (soft) power consumption constraints of clusters
            rho_eps[cc_id] = penalty_parameters["rho_eps"][cc_id]

            # Loop through the chargers
            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    # There is an EV connected in this charger
                    ev_id = ev.vehicle_id

                    # with a schedule of
                    sch_inst = cu.active_schedule_instance
                    cu_sch = cu.schedule_soc[sch_inst]
                    if cu_sch.index.max() < schedule_horizon.min():
                        cu_sch[schedule_horizon.min()] = cu_sch[cu_sch.index.max()]
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

                    # Parameter indicating the EVs' positions in the multi-cluster system
                    location[ev_id] = (cc_id, cu_id)

    ################################################################################################

    if len(bcap) > 0:

        # The system includes connected EVs

        ################################################################################################
        # Step 2: Solving (MILP-based) rescheduling problem to centrally decide how the chargers will operate now
        p_schedule, s_schedule = reschedule(
            solver,
            opt_step,
            opt_horizon,
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
            location,
            system_upperlimit,
            system_lowerlimit,
            clusters,
            cluster_upperlimits,
            cluster_lowerlimits,
            cluster_violationlimits,
            rho_y,
            rho_eps,
        )
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
