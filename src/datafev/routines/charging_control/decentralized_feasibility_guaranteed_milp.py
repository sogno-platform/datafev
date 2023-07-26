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
from datafev.algorithms.cluster.rescheduling_milp import reschedule
from datafev.algorithms.cluster.potentialEstimationG2V_milp import calculate_G2V_potential
from datafev.algorithms.cluster.potentialEstimationV2G_milp import calculate_V2G_potential

def charging_routine(ts, t_delta, horizon, system, solver, penalty_parameters):
    """
    This routine is executed periodically during operation of charger clusters.

    It addresses the scenarios where EVs connected in clusters have previously 
    defined charging schedules that may require deviations due to the local 
    power consumption constraints of clusters. This routine firstly checks if 
    the power consumption constraint is feasible when the constraint indicates
    negative net consumption (i.e., V2G supply). 
    
    The control architecture is decentralized; therefore, each cluster applies its own control. The applied control is based on MILP rescheduling.

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
        Cost parameters for capacity violation / devations.

    Returns
    -------
    None.

    """

    schedule_horizon = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    opt_horizon = list(range(len(schedule_horizon)))
    opt_step = t_delta.seconds

    # Loop through the clusters
    for cc_id in system.clusters.keys():

        cluster = system.clusters[cc_id]

        if cluster.query_actual_occupation(ts) > 0:
            # The cluster includes connected EVs

            ################################################################################################
            # Step 1: Identification of charging demand

            # Parameters defining the upper/lower limits of (soft) power consumption constraints of cluster
            upperlimit = dict(enumerate(cluster.upper_limit[schedule_horizon[:-1]].values))
            lowerlimit = dict(enumerate(cluster.lower_limit[schedule_horizon[:-1]].values))

            # Parameter defining how much the upperlimit/lowerlimit can be violated
            tolerance = cluster.violation_tolerance

            # Cost parameter penalizing deviation from individual optimal charging schedules of EVs
            rho_y = penalty_parameters["rho_y"][cc_id]

            # Cost parameter penalizing violation of (soft) power consumption constraints of clusters
            rho_eps = penalty_parameters["rho_eps"][cc_id]

            # Dictionary containing EV charging demand parameters
            pmax_pos = {}  # Will contain the maximum power that can be withdrawn by the EVs
            pmax_neg = {}  # Will contain the maximum power that can be injected by the EVs
            ch_eff = {} # Will contain charging efficiencies of the chargers hosting EVs
            ds_eff = {} # Will contain discharging efficiencies of the chargers hosting EVs
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

            ################################################################################################
            
            ################################################################################################
            ################################################################################################
            
            upperlimit_was_infeasible=False
            lowerlimit_was_infeasible=False
            
            
            ################################################################################################
            #If there is a minimum V2G injection constraint
            if any(v < 0 for v in upperlimit.values()):
        
            
                # Step 2.1: Solving (MILP-based) V2G estimation problem to calculate the minimum net consumption of cluster  
                p_ref_min, s_ref_min,c_ref_min= calculate_V2G_potential(
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
                )
                
                upperlimit_adjusted={}
                for t in sorted(c_ref_min.keys()):
                    upperlimit_adjusted[t]=max(c_ref_min[t],upperlimit[t])
                    
                if upperlimit_adjusted!=upperlimit:
                    
                    upperlimit_was_infeasible=True
                
                else:
                    
                    upperlimit_was_infeasible=False
                    
            else:
                
                upperlimit_was_infeasible=False
            ################################################################################################   
                
            
            ################################################################################################
            #If there is a minimum G2V consumption constraint
            if any(v > 0 for v in lowerlimit.values()):       
                
                   
                # Step 2.2: Solving (MILP-based) G2V estimation problem to calculate the maximum net consumption of cluster         
                p_ref_max, s_ref_max,c_ref_max= calculate_G2V_potential(
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
                )
                
                lowerlimit_adjusted={}
                for t in sorted(c_ref_max.keys()):
                    lowerlimit_adjusted[t]=min(c_ref_max[t],lowerlimit[t])
                    
                    
                if lowerlimit_adjusted!=lowerlimit:
                    
                    lowerlimit_was_infeasible=True
                
                else:
                    
                    lowerlimit_was_infeasible=False
                
            else:
                
                lowerlimit_was_infeasible=False    
            ################################################################################################
            
            ################################################################################################
            ################################################################################################
            

            ################################################################################################
            # Step 3: Solving (MILP-based) rescheduling problem to optimize the power distribution in cluster 
            #if V2G potential is sufficient
            #if G2V potential is sufficient
            #Otherwise consider the V2G maximizing schedules
            
            if lowerlimit_was_infeasible and upperlimit_was_infeasible:
                
                if all(lowerlimit_adjusted[t] <= upperlimit_adjusted[t] for t in upperlimit_adjusted):
                

                    p_schedule, s_schedule = reschedule(
                        solver,
                        opt_step,
                        opt_horizon,
                        upperlimit_adjusted,
                        lowerlimit_adjusted,
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
                    
                else:
                    
                    raise ValueError('Some elements of adjusted lower limit are larger or equal to those of adjusted upper limit')
                    
            elif upperlimit_was_infeasible:
                 
                if upperlimit_adjusted==c_ref_min:
                    
                    p_schedule=p_ref_min
                    
                else:
                    
                    p_schedule, s_schedule = reschedule(
                        solver,
                        opt_step,
                        opt_horizon,
                        upperlimit_adjusted,
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
                    
                    
            elif lowerlimit_was_infeasible:
                 
                if lowerlimit_adjusted==c_ref_max:
                    
                    p_schedule=p_ref_max
                    
                else:
                    
                    p_schedule, s_schedule = reschedule(
                        solver,
                        opt_step,
                        opt_horizon,
                        upperlimit,
                        lowerlimit_adjusted,
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
                    
            else:
                              
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
