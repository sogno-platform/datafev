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


from pyomo.core import *
import pyomo.kernel as pmo


def calculate_G2V_potential(
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
):
    """
    This function reschedules the charging operations of a cluster by considering:
        - upper-lower limits of aggregate power consumption of the cluster,
        - and pre-defined reference schedules of the individual EVs in the system.

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
    c_schedule: dict
        Cluster's net schedule.
        Each item in the dictionary indicates the net power to consumed by the 
        cluster. Negative values indicate V2G injection.
        
    """

    ###########################################################################
    ####################Constructing the optimization model####################
    model = ConcreteModel()
    model.V = Set(initialize=list(bcap.keys()))  # Index set for the EVs

    # Time parameters
    model.deltaSec = opt_step  # Time discretization (Size of one time step in seconds)
    model.T = Set(initialize=opt_horizon[:-1], ordered=True)  # Index set for the time steps in opt horizon
    model.Tp = Set(initialize=opt_horizon, ordered=True)  # Index set for the time steps in opt horizon for SoC

    # Power capability parameters
    model.P_EV_pos = pmax_pos  # Maximum charging power to EV battery
    model.P_EV_neg = pmax_neg  # Maximum discharging power from EV battery

    # Battery and charger parameters
    model.eff_ch = ch_eff  # Charging efficiency
    model.eff_ds = ds_eff  # Discharging efficiency
    model.E = bcap  # Battery capacities

    # Demand parameters
    model.s_ini = inisoc  # SoC when the optimization starts
    model.s_tar = tarsoc  # Target SOC
    model.s_min = minsoc  # Minimum SOC
    model.s_max = maxsoc  # Maximum SOC
    model.t_dep = deptime  # Estimated departure of EVs


    # EV Variables
    model.p_ev = Var(model.V, model.T, within=Reals)  # Net charging power of EV indexed by
    model.p_ev_pos = Var(model.V, model.T, within=NonNegativeReals)  # Charging power of EV
    model.p_ev_neg = Var(model.V, model.T, within=NonNegativeReals)  # Disharging power of EV
    model.x_ev = Var(model.V, model.T, within=pmo.Binary)  # Whether EV is charging
    model.s = Var(model.V, model.Tp, within=NonNegativeReals)  # EV SOC variable

    # System variables
    model.p_cc = Var(model.T, within=Reals)  # Power flows into the cluster c


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

    def storageConservation(model, v, t):  # SOC of EV batteries will change with respect to the charged power and battery energy capacity
        return model.s[v, t + 1] == (
            model.s[v, t]
            + (model.p_ev_pos[v, t] - model.p_ev_neg[v, t])
            / model.E[v]
            * model.deltaSec
        )

    model.socconst = Constraint(model.V, model.T, rule=storageConservation)

    def chargepowerlimit(model, v, t):  # Net power into EV decoupled into positive and negative parts
        return model.p_ev[v, t] == model.p_ev_pos[v, t] - model.p_ev_neg[v, t]

    model.chrpowconst = Constraint(model.V, model.T, rule=chargepowerlimit)

    def combinatorics_ch(model, v, t):  # EV indexed by v can charge only when x[v,t]==1 at t
        if t >= model.t_dep[v]:
            return model.p_ev_pos[v, t] == 0
        else:
            return model.p_ev_pos[v, t] <= model.x_ev[v, t] * model.P_EV_pos[v]

    model.combconst1 = Constraint(model.V, model.T, rule=combinatorics_ch)

    def combinatorics_ds(model, v, t):  # EV indexed by v can discharge only when x[v,t]==0 at t
        if t >= model.t_dep[v]:
            return model.p_ev_neg[v, t] == 0
        else:
            return model.p_ev_neg[v, t] <= (1 - model.x_ev[v, t]) * model.P_EV_neg[v]

    model.combconst2 = Constraint(model.V, model.T, rule=combinatorics_ds)

    def ccpower(model, t):  # Mapping EV powers to CC power
        return model.p_cc[t] == sum(
            model.p_ev_pos[v, t] / model.eff_ch[v]
            - model.p_ev_neg[v, t] * model.eff_ds[v]
            for v in model.V
        )

    model.ccpowtotal = Constraint(model.T, rule=ccpower)

    # OBJECTIVE FUNCTION
    def obj_rule(model):
        return sum(model.p_cc[t] for t in model.T)

    model.obj = Objective(rule=obj_rule, sense=maximize)

    ###########################################################################

    ###########################################################################
    ######################Solving the optimization model ######################
    result = solver.solve(model)
    ###########################################################################

    ###########################################################################
    ################################Saving the results#########################
    p_schedule = {}
    s_schedule = {}
    c_schedule = {}
    for v in model.V:
        p_schedule[v] = {}
        s_schedule[v] = {}
        for t in opt_horizon:
            if t < max(opt_horizon):
                p_schedule[v][t] = model.p_ev[v, t]()
            s_schedule[v][t] = model.s[v, t]()
            
    for t in opt_horizon[:-1]:
        c_schedule[t]=model.p_cc[t]()
    ###########################################################################

    return p_schedule, s_schedule, c_schedule


if __name__ == "__main__":

    import pandas as pd
    import numpy as np
    from pyomo.environ import SolverFactory

    ###########################################################################
    # Input parameters
    PCU = 11
    eff = 1.0
    N = 4
    PPL = 0.5
    CAP = 55 * 3600
    PC = PPL * N * PCU
    nb_of_ts = 12

    solver = SolverFactory("cplex")
    opt_step = 300
    opt_horizon = list(range(nb_of_ts + 1))


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
    for n in range(1, N + 1):
        evid = "EV" + str(n)
        pmax_pos[evid] = PCU
        pmax_neg[evid] = PCU
        ch_eff[evid] = eff
        ds_eff[evid] = eff
        bcap[evid] = CAP
        inisoc[evid] = np.random.uniform(low=0.4, high=0.8)
        tarsoc[evid] = inisoc[evid] + PCU * opt_step * int(nb_of_ts / 2) / CAP
        minsoc[evid] = 0.3
        maxsoc[evid] = 0.75
        deptime[evid] = np.random.randint(low=int(nb_of_ts / 2), high=int(nb_of_ts * 1.5))

    ###########################################################################

    # To show only two decimals in the table
    pd.options.display.float_format = "{:,.2f}".format

    print("The cluster with total installed capacity of:", N * PCU)
    print("...estimates the net G2V potential of the EVs with:")
    demand_data = pd.DataFrame(columns=["Battery Capacity", "Initial SOC", "Target SOC", "Estimated Departure"])
    demand_data["Battery Capacity"] = pd.Series(bcap) / 3600
    demand_data["Initial SOC"] = pd.Series(inisoc)
    demand_data["Target SOC"] = pd.Series(tarsoc)
    demand_data["Estimated Departure"] = pd.Series(deptime)
    print(demand_data)
    print()

    print("Solving the optimization problem...")
    p_ref, s_ref,c_ref= calculate_V2G_potential(
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
    print()

    print("Printing G2V-maximizing schedules of EVs:")
    results = {}
    for v in demand_data.index:
        results[v] = pd.DataFrame(
            columns=["P (kW)", "SOC (%)"], index=sorted(s_ref[v].keys())
        )
        results[v]["P (kW)"] = pd.Series(p_ref[v])
        results[v]["SOC (%)"] = pd.Series(s_ref[v]) * 100
    
    result_df=pd.concat(results, axis=1)
    print(result_df)
    #print(result_df.xs('P (kW)', level=1, axis=1))
    print()
    
    
    print("Net G2V consumption profile of the cluster:")
    print(pd.Series(c_ref))
    print()
    
    print("Minimum G2V consumption of the cluster within horizon:",(pd.Series(c_ref).sum())*opt_step/3600,"kWh")
    
    
    
    
    
