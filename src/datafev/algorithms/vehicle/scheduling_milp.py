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


def minimize_cost(
    solver,
    opt_step,
    opt_horizon,
    ecap,
    v2gall,
    tarsoc,
    minsoc,
    maxsoc,
    crtsoc,
    crttime,
    inisoc,
    p_ch,
    p_ds,
    g2v_dps,
    v2g_dps,
):
    """
    This function optimizes the charging schedule of a single EV with the 
    objective of charging cost minimization for the given G2V and V2G price 
    signals. The losses in power transfer are considered.
    
    Parameters
    ----------
    opt_step : float
        Size of one time step in the optimization (seconds).
    opt_horizon : list of integers
        Time step identifiers in the optimization horizon.
    ecap : float
        Energy capacity of battery (kWs).
    v2gall : float
        V2G allowance discharge (kWs).
    tarsoc : float
        Target final soc (0<inisoc<1).
	minsoc : float
        Minimum soc.
    maxsoc : float 
        Maximum soc.
    crtsoc : float
        Target soc at crttime.
    crttime : int
        Critical time s.t. s(srttime)> crtsoc.
    inisoc : dict of float
        Initial soc \in [0,1).
    p_ch : dict of float
        Nominal charging power (kW).
    p_ds : dict of float
        Nominal charging power (kW).
    g2v_dps : dict of float
        G2V dynamic price signal (Eur/kWh).
    v2g_dps : dict of float 
        V2G dynamic price signal (Eur/kWh).
    
    Returns
    -------
    p_schedule : dict
        Power schedule. 
        Each item in the EV dictionary indicates the power to be supplied to 
        the EV(kW) during a particular time step.
    s_schedule : dict
        SOC schedule.    
        Each item in the EV dictionary indicates the SOC to be achieved by the 
        EV by a particular time step.
        
    """

    conf_period = {}
    for t in opt_horizon:
        if t < crttime:
            conf_period[t] = 0
        else:
            conf_period[t] = 1

    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.T = Set(initialize=opt_horizon, ordered=True)  # Time index set
    model.dt = opt_step  # Step size
    model.E = ecap  # Battery capacity in kWs
    model.P_CH = p_ch  # Maximum charging power in kW
    model.P_DS = p_ds  # Maximum discharging power in kW
    model.W_G2V = g2v_dps  # Time-variant G2V cost coefficients
    model.W_V2G = v2g_dps  # Time-variant V2G cost coefficients
    model.SoC_F = tarsoc  # SoC to be achieved at the end
    model.conf = conf_period  # Confidence period where SOC must be larger than crtsoc
    model.SoC_R = crtsoc  # Minimim SOC must be ensured in the confidence period
    model.V2G_ALL = v2gall  # Maximum energy that can be discharged V2G

    model.xp = Var(
        model.T, within=pmo.Binary
    )  # Binary variable having 1/0 if v is charged/discharged at t
    model.p = Var(model.T, within=Reals)  # Net charge power at t
    model.p_pos = Var(model.T, within=NonNegativeReals)  # Charge power at t
    model.p_neg = Var(model.T, within=NonNegativeReals)  # Discharge power at t
    model.SoC = Var(
        model.T, within=NonNegativeReals, bounds=(minsoc, maxsoc)
    )  # SOC to be achieved  at time step t

    # CONSTRAINTS
    def initialsoc(model):
        return model.SoC[0] == inisoc

    model.inisoc = Constraint(rule=initialsoc)

    def storageConservation(
        model, t
    ):  # SOC of EV batteries will change with respect to the charged power and battery energy capacity
        if t < max(model.T):
            return model.SoC[t + 1] == (model.SoC[t] + model.p[t] * model.dt / model.E)
        else:
            return model.SoC[t] == model.SoC_F

    model.socconst = Constraint(model.T, rule=storageConservation)

    def socconfidence(model, t):
        return model.SoC[t] >= model.SoC_R * model.conf[t]

    model.socconfi = Constraint(model.T, rule=socconfidence)

    def supplyrule(model):
        return model.p[max(model.T)] == 0.0

    model.supconst = Constraint(rule=supplyrule)

    def netcharging(model, t):
        return model.p[t] == model.p_pos[t] - model.p_neg[t]

    model.netchr = Constraint(model.T, rule=netcharging)

    def combinatorics31_pos(model, t):
        return model.p_pos[t] <= model.xp[t] * model.P_CH

    model.comb31pconst = Constraint(model.T, rule=combinatorics31_pos)

    def combinatorics31_neg(model, t):
        return model.p_neg[t] <= (1 - model.xp[t]) * model.P_DS

    model.comb31nconst = Constraint(model.T, rule=combinatorics31_neg)

    def v2g_limit(model):
        return sum(model.p_neg[t] * model.dt for t in model.T) <= model.V2G_ALL

    model.v2gconst = Constraint(rule=v2g_limit)

    # OBJECTIVE FUNCTION
    def obj_rule(model):
        return (
            sum(
                (
                    model.W_G2V[t] * model.p_pos[t] - model.W_V2G[t] * model.p_neg[t]
                    for t in opt_horizon[:-1]
                )
            )
            * opt_step
            / 3600
        )

    model.obj = Objective(rule=obj_rule, sense=minimize)

    solver.solve(model)

    p_schedule = {}
    s_schedule = {}

    for t in model.T:
        p_schedule[t] = model.p[t]()
        s_schedule[t] = model.SoC[t]()

    return p_schedule, s_schedule


if __name__ == "__main__":

    from pyomo.environ import SolverFactory
    import pandas as pd
    import numpy as np

    ###########################################################################
    # Input parameters
    solver = SolverFactory("gurobi")
    step = 300  # Time step size= 300 seconds = 5 minutes
    horizon = list(range(13))  # Optimization horizon= 12 steps = 60 minutes
    ecap = 55 * 3600  # Battery capacity= 55 kWh
    v2gall = 10 * 3600  # V2G allowance = 10 kWh
    tarsoc = 0.8  # Target SOC
    minsoc = 0.2  # Minimum SOC
    maxsoc = 1.0  # Maximum SOC
    crtsoc = 0.6  # Critical SOC
    crttime = 4  # Critical time
    inisoc = 0.5  # Initial SOC
    pch = 22  # Maximum charge power
    pds = 22  # Maximum discharge power

    g2v_tariff = np.random.uniform(low=0.4, high=0.8, size=12)
    g2v_dps = dict(enumerate(g2v_tariff))  # grid-to-vehicle tariff
    v2g_dps = dict(enumerate(g2v_tariff * 0.9))  # vehicle-to-grid tariff
    ###########################################################################

    print("Size of one time step:", step, "seconds")
    print("Optimization horizon covers", max(horizon), "time steps")
    print("Battery capacity of the EV:", ecap / 3600, "kWh")
    print("Initial SOC of the EV:", inisoc)
    print("Target SOC (at the end of optimization horizon):", tarsoc)
    print(
        "Critical SOC condition: SOC",
        crtsoc,
        "must be achieved by",
        crttime,
        "and must be maintained afterwards",
    )
    print("V2G allowance:", v2gall / 3600, "kWh")
    print()

    print("Optimization is run G2V-V2G distinguishing price signals")
    p, soc = minimize_cost(
        solver,
        step,
        horizon,
        ecap,
        v2gall,
        tarsoc,
        minsoc,
        maxsoc,
        crtsoc,
        crttime,
        inisoc,
        pch,
        pds,
        g2v_dps,
        v2g_dps,
    )
    print()

    print("Results are written in table")
    print("SOC (%): SOC trajectory in optimized schedule")
    print("P (kW): Power supply to the EV in optimized schedule")
    print()
    results = pd.DataFrame(
        columns=["G2V Tariff", "V2G Tariff", "P (kW)", "SOC (%)",],
        index=sorted(soc.keys()),
    )
    results["G2V Tariff"] = pd.Series(g2v_dps)
    results["V2G Tariff"] = pd.Series(v2g_dps)
    results["P (kW)"] = pd.Series(p)
    results["SOC (%)"] = pd.Series(soc) * 100
    print(results)
