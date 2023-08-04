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


def maximum_final_soc(
    solver,
    opt_step,
    opt_horizon,
    ecap,
    tarsoc,
    v2gall,
    minsoc,
    maxsoc,
    inisoc,
    p_ch,
    p_ds,
    upperlimit,
    lowerlimit,
    penalty_up,
    penalty_down,  
):
    """
    This function optimizes the charging schedule of a single EV under given
    capacity constraints (upperlimit and lowerlimit) with the objective of 
    minimization of the capacity constraint violation. The losses in power 
    conversion (charging and discharging) are taken into account.
    
    Parameters
    ----------
    opt_step : float
        Size of one time step in the optimization (seconds).
    opt_horizon : list of integers
        Time step identifiers in the optimization horizon.
    ecap : float
        Energy capacity of battery (kWs).
    tarsoc : float
            Target soc \in [0,1).     
	 minsoc : float
        Minimum soc.
    maxsoc : float 
        Maximum soc.
    inisoc : float
            Initial soc \in [0,1).                                          
    p_ch : dict of float
        Nominal charging power (kW).
    p_ds : dict of float
        Nominal charging power (kW).
    upperlimit : dict of float
        Soft upper limit of cluster power consumption (kW).
    lowerlimit : dict of float
        Soft lower limit of cluster power consumption (kW).
    penalty_up: dict of float
        Violation penalty for upperlimit (Eur/kW)
    penalty_down: dict of float
        Violation penalty for lowerlimit (Eur/kW)

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

    ####################Constructing the optimization model####################
    model = ConcreteModel()

    model.Tp = Set(initialize=opt_horizon, ordered=True)  # Time index set
    model.T = Set(initialize=opt_horizon[:-1], ordered=True)
    model.dt = opt_step  # Step size
    model.E = ecap  # Battery capacity in kWs
    model.P_CH = p_ch  # Maximum charging power in kW
    model.P_DS = p_ds  # Maximum discharging power in kW
    model.V2G_ALL = v2gall  # Maximum energy that can be discharged V2G
    model.P_CC_up = upperlimit  # Upper limit of the power that can be consumed by a cluster
    model.P_CC_low = lowerlimit  # Lower limit of the power that can be consumed by a cluster (negative values indicating export limit)
    
    model.pen_up=penalty_up
    model.pen_do=penalty_down

    model.xp = Var(model.T, within=pmo.Binary)              # Binary variable having 1/0 if v is charged/discharged at t
    model.p = Var(model.T, within=Reals)                    # Net charge power at t
    model.p_pos = Var(model.T, within=NonNegativeReals)     # Charge power at t
    model.p_neg = Var(model.T, within=NonNegativeReals)     # Discharge power at t
    model.SoC = Var(model.Tp, within=NonNegativeReals, bounds=(minsoc, maxsoc))  # SOC to be achieved  at time step t
    
    model.viol_up  = Var(model.T, within=NonNegativeReals)  # Variable representing how much the upper limit will be violated
    model.viol_do = Var(model.T, within=NonNegativeReals)   # Variable representing how much the lower limit will be violated  
    
    # CONSTRAINTS
    def initialsoc(model):
        return model.SoC[0] == inisoc
    model.inisoc = Constraint(rule=initialsoc)
    
    def finalsoc(model):
        return model.SoC[max(model.Tp)] == tarsoc
    model.finsoc = Constraint(rule=finalsoc)
    
    def storageConservation(model, t):  # SOC of EV batteries will change with respect to the charged power and battery energy capacity
        return model.SoC[t + 1] == (model.SoC[t] + model.p[t] * model.dt / model.E)
    model.socconst = Constraint(model.T, rule=storageConservation)

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
    
    def clusterlim_up(model, t):
        return model.p[t]<=model.P_CC_up[t]+model.viol_up[t]
    model.clusterlim_up=Constraint(model.T,rule=clusterlim_up)
    
    def clusterlim_low(model, t):
        return model.p[t]>=model.P_CC_low[t]-model.viol_do[t]
    model.clusterlim_low=Constraint(model.T,rule=clusterlim_low)
    
    # OBJECTIVE FUNCTION
    def obj_rule(model):
        return sum(model.pen_up[t]*model.viol_up[t]*model.dt+
                   model.pen_do[t]*model.viol_do[t]*model.dt for t in model.T)+0.0001*sum(tarsoc-model.SoC[t] for t in model.T)
    model.obj = Objective(rule=obj_rule, sense=minimize)

    #print(model.pprint())
    res=solver.solve(model)
    #print(res)

    p_schedule = {}
    s_schedule = {}

    for t in model.T:
        p_schedule[t] = model.p[t]()
        s_schedule[t] = model.SoC[t]()
    s_schedule[max(model.Tp)]=model.SoC[max(model.Tp)]()    
        
    #soc_final=model.SoC[max(model.T)]()

    return p_schedule, s_schedule#,soc_final


if __name__ == "__main__":

    from pyomo.environ import SolverFactory
    import pandas as pd
    import numpy as np

    ###########################################################################
    # Input parameters
    solver = SolverFactory("cplex")
    step = 300  # Time step size= 300 seconds = 5 minutes
    horizon = list(range(13))  # Optimization horizon= 12 steps = 60 minutes
    ecap = 55 * 3600  # Battery capacity= 55 kWh
    v2gall = 10 * 3600  # V2G allowance = 10 kWh
    minsoc = 0.2  # Minimum SOC
    maxsoc = 1.0     # Maximum SOC
    inisoc = 0.5  # Initial SOC
    tarsoc = 1.0
    pch = 44  # Maximum charge power
    pds = 44  # Maximum discharge power
    pen_up_viol= np.ones(12)*0.01/12
    pen_do_viol= np.ones(12)*0.01/12

    upper= np.ones(12)*22
    lower= np.zeros(12)
    upper[3:5]=-22
    lower[3:5]=-22
    ###########################################################################

    print("Size of one time step:", step, "seconds")
    print("Optimization horizon covers", max(horizon), "time steps")
    print("Battery capacity of the EV:", ecap / 3600, "kWh")
    print("Initial SOC of the EV:", inisoc)
    print("Target SOC (at the end of optimization horizon):", tarsoc)
    print("V2G allowance:", v2gall / 3600, "kWh")
    print()

    print("Optimization is run G2V-V2G distinguishing price signals")
    p, soc = maximum_final_soc(
        solver,
        step,
        horizon,
        ecap,
        tarsoc,
        v2gall,
        minsoc,
        maxsoc,
        inisoc,
        pch,
        pds,
        upper,
        lower,
        pen_up_viol,
        pen_do_viol  
    )
        
    print()

    print("Results are written in table")
    print("SOC (%): SOC trajectory in optimized schedule")
    print("P (kW): Power supply to the EV in optimized schedule")
    print()
    results = pd.DataFrame(
        columns=["P_UPPER", "P_LOWER", "P (kW)", "SOC (%)",],
        index=sorted(soc.keys()),
    )
    results["P_UPPER"] = pd.Series(upper)
    results["P_LOWER"] = pd.Series(lower)
    results["P (kW)"] = pd.Series(p)
    results["SOC (%)"] = pd.Series(soc) * 100
    print(results)
