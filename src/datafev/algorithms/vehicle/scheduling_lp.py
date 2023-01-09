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


def minimize_cost(
    solver,
    opt_step,
    opt_horizon,
    ecap,
    tarsoc,
    minsoc,
    maxsoc,
    crtsoc,
    crttime,
    inisoc,
    p_ch,
    p_ds,
    dps,
):
    """
    This function optimizes the charging schedule of a single EV with the objective of charging cost minimization
    for the given price signal. The losses in power transfer are neglected.

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
        Critical time s.t. s(srttime) > crtsoc.
    inisoc : dict of float
        Initial soc \in [0,1).
    p_ch : dict of float
        Nominal charging power (kW).
    p_ds : dict of float
        Nominal charging power (kW).
    dps : dict of float
        Dynamic price signal (Eur/kWh).
    
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
    model.price = dps  # Energy price series
    model.SoC_F = tarsoc  # SoC to be achieved at the end
    model.conf = conf_period  # Confidence period where SOC must be larger than crtsoc
    model.SoC_R = crtsoc  # Minimim SOC must be ensured in the confidence period

    model.p = Var(model.T, bounds=(-model.P_DS, model.P_CH))
    model.SoC = Var(model.T, within=NonNegativeReals, bounds=(minsoc, maxsoc))

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

    # OBJECTIVE FUNCTION
    def obj_rule(model):
        return (
            sum(model.p[t] * model.price[t] for t in opt_horizon[:-1]) * opt_step / 3600
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

    ###########################################################################
    # Input parameters
    solver = SolverFactory("gurobi")
    step = 600  # Time step size= 600 seconds = 10 minutes
    horizon = list(range(7))  # Optimization horizon= 6 steps = 60 minutes
    ecap = 55 * 3600  # Battery capacity= 55 kWh
    tarsoc = 0.8  # Target SOC
    minsoc = 0.2  # Minimum SOC
    maxsoc = 1.0  # Maximum SOC
    crtsoc = 0.6  # Critical SOC
    crttime = 4  # Critical time
    inisoc = 0.5  # Initial SOC
    pch = 22  # Maximum charge power
    pds = 22  # Maximum discharge power
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
    print()
    print("Optimization is run for three dynamic price signals")
    print()

    dps1 = dict(enumerate([1, 1, 1, 0, 0, 0]))  # Dynamic price signal 1
    dps2 = dict(enumerate([0, 0, 1, 1, 1, 0]))  # Dynamic price signal 2
    dps3 = dict(enumerate([0, 0, 0, 1, 1, 1]))  # Dynamic price signal 3

    print("For the profile dps1:")
    print(dps1)
    p1, s1 = minimize_cost(
        solver,
        step,
        horizon,
        ecap,
        tarsoc,
        minsoc,
        maxsoc,
        crtsoc,
        crttime,
        inisoc,
        pch,
        pds,
        dps1,
    )

    print("For the profile dps2:")
    print(dps2)
    p2, s2 = minimize_cost(
        solver,
        step,
        horizon,
        ecap,
        tarsoc,
        minsoc,
        maxsoc,
        crtsoc,
        crttime,
        inisoc,
        pch,
        pds,
        dps2,
    )

    print("For the profile dps2:")
    print(dps2)
    p3, s3 = minimize_cost(
        solver,
        step,
        horizon,
        ecap,
        tarsoc,
        minsoc,
        maxsoc,
        crtsoc,
        crttime,
        inisoc,
        pch,
        pds,
        dps3,
    )

    print()

    print("Printing optimization results in tables:")
    sched1 = pd.DataFrame(columns=["DPS", "SOC (%)"])
    sched2 = pd.DataFrame(columns=["DPS", "SOC (%)"])
    sched3 = pd.DataFrame(columns=["DPS", "SOC (%)"])
    print("SOC (%): SOC trajectory in optimized schedule")
    print("P (kW): Power supply to the EV in optimized schedule")
    print()

    print("dps1")
    sched1["P (kW)"] = pd.Series(p1)
    sched1["SOC (%)"] = pd.Series(s1) * 100
    sched1["DPS"] = pd.Series(dps1)
    print(sched1)
    print()

    print("dps2")
    sched2["P (kW)"] = pd.Series(p2)
    sched2["SOC (%)"] = pd.Series(s2) * 100
    sched2["DPS"] = pd.Series(dps2)
    print(sched2)
    print()

    print("dps3")
    sched3["P (kW)"] = pd.Series(p3)
    sched3["SOC (%)"] = pd.Series(s3) * 100
    sched3["DPS"] = pd.Series(dps3)
    print(sched3)
    print()
