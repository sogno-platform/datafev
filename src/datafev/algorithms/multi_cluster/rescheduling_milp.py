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


from pyomo.environ import SolverFactory
from pyomo.core import *
import numpy as np
import pandas as pd
import pyomo.kernel as pmo
from itertools import product


def reschedule(
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
    unbalance_limits=None,
):
    """
    This function reschedules the charging operations of all clusters in 
    a multicluster system by considering:
        - upper-lower limits of aggregate consumption of the multi-cluster system,
        - upper-lower limits of aggregate consumption of individual clusters,
        - inter-cluster unbalances between aggregate power consumption of clusters,
        - pre-defined reference schedules of the individual EVs in the system.
    This is run typically when some events require deviations from previously 
    determined schedules.
    
    Parameters
    ----------
    solver : pyomo SolverFactory object
        Optimization solver.
    opt_step : int
        Size of one time step in the optimization (seconds).
    opt_horizon : list of integers
        Time step identifiers in the optimization horizon.
    bcap : dict of float
        Battery capactiy of EVs (kWs).
    inisoc : dict of float
        Initial SOCs of EV batteries (0<inisoc[key]<1).
    tarsoc : dict of float
        Target SOCs of EVs (0<inisoc[key]<1).
    minsoc : dict of float
        Minimum allowed SOCs.
    maxsoc : dict of float
        Maximum allowed SOCs.
    ch_eff : dict of float
        Charging efficiency of chargers.
    ds_eff : dict of float
        Discharging efficiency of chargers.
    pmax_pos : dict of float
        Maximum charge power that EV battery can withdraw (kW).
    pmax_neg : dict of float
        Maximum discharge power that EV battery can supply (kW).
    deptime : dict of int
        Number of time steps until departures of EVs.
    location : dict of tuples
        The tuples indicating the location of the EV in the multicluter system.
        'ev_id':(cluster_id,charger_id).
    system_upperlimit: dict of float
        Upper limit of net power consumption of multi-cluster system(kW).
    system_lowerlimit: dict of float
        Lower limit of net power consumption of multi-cluster system(kW).
    clusters : list
        List of clusters in the system.
    cluster_upperlimits : dict of dict
        Soft upper limit of cluster power consumption (kW).
    cluster_lowerlimits : dict of dict
        Soft upper limit of cluster power consumption (kW).
    cluster_violationlimits : dict of float
        Maximum allowed violation of upper-lower limits of clusters (kW).     
    rho_y : dict of float
        Penalty factors for deviation of reference schedules (unitless).
    rho_eps : dict of float
        Penalty factors for violation of upper-lower soft limits (unitless).

    Returns
    -------
    p_schedule : dict
        Power schedule. 
        It contains a dictionary for each EV. Each item in the EV dictionary 
        indicates the power to be supplied to the EV(kW) during a particular 
        time step.
    s_schedule : dict
        SOC schedule.    
        It contains a dictionary for each EV. Each item in the EV dictionary 
        indicates the SOC to be achieved by the EV by a particular time step.

    """

    P_CC_up_lim = cluster_upperlimits
    P_CC_low_lim = cluster_lowerlimits
    P_CC_vio_lim = cluster_violationlimits
    P_IC_unb_max = unbalance_limits
    P_CS_up_lim = system_upperlimit
    P_CS_low_lim = system_lowerlimit

    ev_connected_here = {}
    rho_y_ = {}
    for v in location.keys():
        for c in clusters:
            if c == location[v][0]:
                ev_connected_here[v, c] = 1
                rho_y_[v] = rho_y[c]
            else:
                ev_connected_here[v, c] = 0
    ###########################################################################

    ###########################################################################
    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.C = Set(initialize=clusters)  # Index set for the clusters
    model.V = Set(initialize=list(bcap.keys()))  # Index set for the EVs

    # Time parameters
    model.deltaSec = opt_step  # Time discretization (one time step in seconds)
    model.T = Set(
        initialize=opt_horizon[:-1], ordered=True
    )  # Index set for the time steps in opt horizon
    model.Tp = Set(
        initialize=opt_horizon, ordered=True
    )  # Index set for the time steps in opt horizon for SoC

    # Power capability parameters
    model.P_EV_pos = pmax_pos  # Maximum charging power to EV battery
    model.P_EV_neg = pmax_neg  # Maximum discharging power from EV battery
    model.P_CC_up = (
        P_CC_up_lim  # Upper limit of the power that can be consumed by a cluster
    )
    model.P_CC_low = (
        P_CC_low_lim  # Lower limit of the power that can be consumed by a cluster
    )
    model.P_CC_vio = P_CC_vio_lim  # Cluster upper-lower limit violation tolerance
    model.P_IC_unb = P_IC_unb_max  # Maximum inter-cluster unbalance
    model.P_CS_up = P_CS_up_lim  # Upper limit of the power that can be consumed by the multicluster system
    model.P_CS_low = P_CS_low_lim  # Lower limit of the power that can be consumed by the multicluster system

    # Charging efficiency
    model.eff_ch = ch_eff  # Charging efficiency
    model.eff_ds = ds_eff  # Discharging efficiency
    model.E = bcap  # Battery capacities

    # Reference SOC parameters
    model.s_ini = inisoc  # SoC when the optimization starts
    model.s_tar = tarsoc  # Target SOC
    model.s_min = minsoc  # Minimum SOC
    model.s_max = maxsoc  # Maximum SOC

    # EV Variables
    model.p_ev = Var(
        model.V, model.T, within=Reals
    )  # Net charging power of EV indexed by
    model.p_ev_pos = Var(
        model.V, model.T, within=NonNegativeReals
    )  # Charging power of EV
    model.p_ev_neg = Var(
        model.V, model.T, within=NonNegativeReals
    )  # Disharging power of EV
    model.x_ev = Var(model.V, model.T, within=pmo.Binary)  # Whether EV is charging
    model.s = Var(model.V, model.Tp, within=NonNegativeReals)  # EV SOC variable

    # System variables
    model.p_cc = Var(model.C, model.T, within=Reals)  # Power flows into the cluster c
    model.p_cs = Var(model.T, within=Reals)  # Total system power

    # Penalty parameters
    model.rho_y = rho_y_
    model.rho_eps = rho_eps

    # Deviation
    model.eps = Var(
        model.C, within=NonNegativeReals
    )  # Deviation from aggregate conspumtion limit
    model.y = Var(
        model.V, within=NonNegativeReals
    )  # Deviation from individual schedules

    # model.eps.pprint()
    # CONSTRAINTS
    def initialsoc(model, v):
        return model.s[v, 0] == model.s_ini[v]

    model.inisoc = Constraint(model.V, rule=initialsoc)

    def minimumsoc(model, v, t):
        return model.s_min[v] <= model.s[v, t]

    model.minsoc_con = Constraint(model.V, model.T, rule=minimumsoc)

    def maximumsoc(model, v, t):
        return model.s_max[v] >= model.s[v, t]

    model.maxsoc_con = Constraint(model.V, model.T, rule=maximumsoc)

    def storageConservation(
        model, v, t
    ):  # SOC of EV batteries will change with respect to the charged power and battery energy capacity
        return model.s[v, t + 1] == (
            model.s[v, t]
            + (model.p_ev_pos[v, t] - model.p_ev_neg[v, t]) / bcap[v] * model.deltaSec
        )

    model.socconst = Constraint(model.V, model.T, rule=storageConservation)

    def chargepowerlimit(
        model, v, t
    ):  # Net power into EV decoupled into positive and negative parts
        return model.p_ev[v, t] == model.p_ev_pos[v, t] - model.p_ev_neg[v, t]

    model.chrpowconst = Constraint(model.V, model.T, rule=chargepowerlimit)

    def combinatorics_ch(
        model, v, t
    ):  # EV indexed by v can charge only when x[v,t]==1 at t
        if t >= deptime[v]:
            return model.p_ev_pos[v, t] == 0
        else:
            return model.p_ev_pos[v, t] <= model.x_ev[v, t] * model.P_EV_pos[v]

    model.combconst1 = Constraint(model.V, model.T, rule=combinatorics_ch)

    def combinatorics_ds(
        model, v, t
    ):  # EV indexed by v can discharge only when x[v,t]==0 at t
        if t >= deptime[v]:
            return model.p_ev_neg[v, t] == 0
        else:
            return model.p_ev_neg[v, t] <= (1 - model.x_ev[v, t]) * model.P_EV_neg[v]

    model.combconst2 = Constraint(model.V, model.T, rule=combinatorics_ds)

    def ccpower(model, c, t):  # Mapping EV powers to CC power
        return model.p_cc[c, t] == sum(
            ev_connected_here[v, c]
            * (
                model.p_ev_pos[v, t] / model.eff_ch[v]
                - model.p_ev_neg[v, t] * model.eff_ds[v]
            )
            for v in model.V
        )

    model.ccpowtotal = Constraint(model.C, model.T, rule=ccpower)

    def cspower(model, t):  # Mapping CC powers to CS power
        return model.p_cs[t] == sum(model.p_cc[c, t] for c in model.C)

    model.stapowtotal = Constraint(model.T, rule=cspower)

    def cluster_limit_violation(model, c):
        return model.eps[c] <= model.P_CC_vio[c]

    model.viol_clust = Constraint(model.C, rule=cluster_limit_violation)

    def cluster_upper_limit(model, c, t):  # Import constraint for CC
        return model.p_cc[c, t] <= model.eps[c] + model.P_CC_up[c][t]

    if model.P_CC_up != None:
        model.ccpowcap_pos = Constraint(model.C, model.T, rule=cluster_upper_limit)

    def cluster_lower_limit(model, c, t):  # Export constraint for CC
        return -model.eps[c] + model.P_CC_low[c][t] <= model.p_cc[c, t]

    if model.P_CC_low != None:
        model.ccpowcap_neg = Constraint(model.C, model.T, rule=cluster_lower_limit)

    def cluster_unbalance_limit(model, c1, c2, t):
        return model.p_cc[c1, t] <= model.p_cc[c2, t] + model.P_IC_unb[c1, c2][t]

    if model.P_IC_unb != None:
        model.inter_clust = Constraint(
            model.C, model.C, model.T, rule=cluster_unbalance_limit
        )

    def clusteredsystem_upper_limit(model, t):  # Import constraint for CS
        return model.p_cs[t] <= model.P_CS_up[t]

    model.cspowcap_pos = Constraint(model.T, rule=clusteredsystem_upper_limit)

    def clusteredsystem_lower_limit(model, t):  # Export constraint for CS
        return model.p_cs[t] >= model.P_CS_low[t]

    model.cspowcap_neg = Constraint(model.T, rule=clusteredsystem_lower_limit)

    def individual_pos_deviation(model, v):
        return model.s_tar[v] - model.s[v, max(opt_horizon)] <= model.y[v]

    model.indev_pos = Constraint(model.V, rule=individual_pos_deviation)

    def individual_neg_deviation(model, v):
        return -model.y[v] <= model.s_tar[v] - model.s[v, max(opt_horizon)]

    model.indev_neg = Constraint(model.V, rule=individual_neg_deviation)

    # OBJECTIVE FUNCTION
    def obj_rule(model):
        return (
            sum(model.rho_y[v] * model.y[v] * model.E[v] / 3600 for v in model.V)
        ) + (sum(model.rho_eps[c] * model.eps[c] for c in model.C))

    model.obj = Objective(rule=obj_rule, sense=minimize)

    ###########################################################################

    ###########################################################################
    ######################Solving the optimization model ######################
    result = solver.solve(model)
    # print(result)
    ###########################################################################

    ###########################################################################
    ################################Saving the results#########################
    p_schedule = {}
    s_schedule = {}
    for v in model.V:
        p_schedule[v] = {}
        s_schedule[v] = {}
        for t in opt_horizon:
            if t < max(opt_horizon):
                p_schedule[v][t] = model.p_ev[v, t]()
            s_schedule[v][t] = model.s[v, t]()
    ###########################################################################

    return p_schedule, s_schedule


if __name__ == "__main__":

    import pandas as pd
    import numpy as np
    from pyomo.environ import SolverFactory

    ###########################################################################
    # Input parameters
    solver = SolverFactory("gurobi")

    clusters = ["CC1", "CC2"]  # System has two clusters
    opt_horizon = list(range(13))  # 1 hour
    opt_step = 300  # 5 minutes

    # CC1's consumption should not exceed 22 kW and CC2's consumption 33 kW
    cluster_upperlimits = {
        "CC1": dict(enumerate(np.ones(12) * 22)),
        "CC2": dict(enumerate(np.ones(12) * 33)),
    }
    cluster_lowerlimits = {
        "CC1": dict(enumerate(np.zeros(12))),
        "CC2": dict(enumerate(np.zeros(12))),
    }
    # It is not allowed to violate cluster constraints
    cluster_violationlimits = {"CC1": 0.0, "CC2": 0.0}

    # The multi-cluster system's aggregate consumption is not allowed to exceed 44 kW
    system_upperlimit = dict(enumerate(np.ones(12) * 44))
    system_lowerlimit = dict(enumerate(np.zeros(12)))

    np.random.seed(0)
    evdata = {}
    pmax_pos = {}
    pmax_neg = {}
    ch_eff = {}
    ds_eff = {}
    bcap = {}
    tarsoc = {}
    deptime = {}
    inisoc = {}
    minsoc = {}
    maxsoc = {}
    location = {}
    for v in ["v11", "v12", "v21", "v22"]:
        pmax_pos[v] = 22
        pmax_neg[v] = 22
        ch_eff[v] = 1
        ds_eff[v] = 1
        bcap[v] = 55 * 3600
        inisoc[v] = np.random.uniform(low=0.4, high=0.8)
        tarsoc[v] = inisoc[v] + 0.2 if v in ["v11", "v21"] else inisoc[v] + 0.18
        minsoc[v] = 0.2
        maxsoc[v] = 1.0
        deptime[v] = 6 if v in ["v11", "v21"] else 15
    location["v11"] = ("CC1", 1)
    location["v12"] = ("CC1", 2)
    location["v21"] = ("CC2", 1)
    location["v22"] = ("CC2", 2)

    rho_y = {"CC1": 1, "CC2": 1}
    rho_eps = {"CC1": 1, "CC2": 1}
    ###########################################################################

    print("A system with two clusters:", clusters)
    print()
    print("...has power limits of:")
    limit_data = pd.DataFrame()
    limit_data["CC1"] = pd.Series(cluster_upperlimits["CC1"])
    limit_data["CC2"] = pd.Series(cluster_upperlimits["CC2"])
    limit_data["CC1+CC2"] = pd.Series(system_upperlimit)
    print(limit_data)
    print()

    print("...must control the charging profiles of the EVs with the demands:")
    demand_data = pd.DataFrame(
        columns=["Battery Capacity", "Initial SOC", "Target SOC", "Estimated Departure"]
    )
    demand_data["Battery Capacity"] = pd.Series(bcap) / 3600
    demand_data["Initial SOC"] = pd.Series(inisoc)
    demand_data["Target SOC"] = pd.Series(tarsoc)
    demand_data["Estimated Departure"] = pd.Series(deptime)
    demand_data["Location"] = pd.Series(location)
    print(demand_data)
    print()

    print("Solving the optimization problem...")
    p_ref, s_ref = reschedule(
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
    print()

    print("Printing optimal schedules of EVs:")
    results = {}
    for v in demand_data.index:
        results[v] = pd.DataFrame(columns=["P", "S"], index=sorted(s_ref[v].keys()))
        results[v]["P"] = pd.Series(p_ref[v])
        results[v]["S"] = pd.Series(s_ref[v])
    print(pd.concat(results, axis=1))
    print()

    print("Printing optimal schedules of clusters:")
    clust_prof = pd.DataFrame()
    clust_prof["CC1"] = pd.Series(p_ref["v11"]) + pd.Series(p_ref["v12"])
    clust_prof["CC2"] = pd.Series(p_ref["v21"]) + pd.Series(p_ref["v22"])
    clust_prof["CC1+CC2"] = clust_prof.sum(axis=1)
    print(clust_prof)
