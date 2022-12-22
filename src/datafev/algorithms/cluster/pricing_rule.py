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


def idp(schedule, upper_bound, lower_bound, tou_tariff, f_discount, f_markup):
    """
    This is the python implementation of the individual dynamic pricing algorithm introduced in
    Gümrükcü, et al., "Decentralized Energy Management Concept for Urban Charging Hubs with Multiple V2G Aggregators,"
    in IEEE Transactions on Transportation Electrification, 2022, doi: 10.1109/TTE.2022.3208627.

    This function compares the commitments with the desired power consumption range of the cluster to:
        - increase the charging price for time steps where the schedule exceeds the upper bound of the desired range,
        - and decrease the charging price for time steps where the schedule is below the lower bound of the desired range.
    
    Parameters
    ----------
    schedule : dict of float
        Aggregate schedule of the cluster. Dictionary values are the scheduled 
        aggregate consumption of the cluster (kW) in particular time steps.    
    upper_bound : dict of float
        Upper bound of the desired consumption range. Dictionary values are 
        the upper limits of net consumption (kW) in particular time steps.
    lower_bound : dict of float
        Lower bound of the desired consumption range. Dictionary values are 
        the lower limits of net consumption (kW) in particular time steps.
    tou_tariff : dict of float
        Standard TOU tariff of the cluster operator. Dictionary values denote
        the normal charging price (Eur/kWh) in a particular time step in case
        the scheduled net consumption of the cluster is within desired range.
    f_discount : float
        Discount factor to compensate each kW of deficit consumption (Eur/kW).
    f_markup : float
        Markup factor to compensate each kW of excessive consumption (Eur/kW).

    Returns
    -------
    omega : dict of float
        Dynamic price signal.
        Key: Time step identifier,
        Value: Charging price (Eur/kWh) for a particular time step.
            
    """

    sc = pd.Series(schedule)
    ub = pd.Series(upper_bound)
    lb = pd.Series(lower_bound)
    kappa = pd.Series(tou_tariff)
    kappa_L = kappa.min()
    kappa_U = kappa.max()

    overloadedsteps = sc[sc >= ub].index
    underloadedsteps = sc[sc < lb].index

    ome = kappa.copy()
    ome[underloadedsteps] = kappa_L - f_discount * (
        lb[underloadedsteps] - sc[underloadedsteps]
    )
    ome[overloadedsteps] = kappa_U + f_markup * (sc - ub)[overloadedsteps]

    omega = ome.to_dict()

    return omega


if __name__ == "__main__":

    import numpy as np
    import matplotlib.pyplot as plt

    ###########################################################################
    # Input parameters

    np.random.seed(0)

    schedule = dict(enumerate(np.random.uniform(low=44, high=88, size=12)))
    upper_b = dict(enumerate(np.ones(12) * 70))
    lower_b = dict(enumerate(np.zeros(12)))
    tou = dict(enumerate(np.random.uniform(low=0.4, high=0.8, size=12)))
    f_disc = 0.05
    f_mark = 0.05
    ###########################################################################

    print("Input parameters of the algorithm are presented in tabular form")
    inputs = pd.DataFrame(
        columns=[
            "Schedule",  # Current consumption schedule (kW)
            "LB",  # Lower bound of desired consumption range (kW)
            "UB",  # Upper bound of desired consumption range (kW)
            "sTOU",  # Standard time-of-use tariff (Eur/kWh)
        ]
    )
    inputs["Schedule"] = pd.Series(schedule)
    inputs["LB"] = pd.Series(lower_b)
    inputs["UB"] = pd.Series(upper_b)
    inputs["sTOU"] = pd.Series(tou)

    print(inputs)
    print()

    print(
        "When the scheduled consumption is within desired range, charging price is equal to the corresponding TOU price"
    )
    print(
        "When the scheduled consumption is larger than upper bound, charging price is incresed by",
        f_mark,
        "Eur for each kW of excessive consumption",
    )
    print(
        "When the scheduled consumption is smaller than upper bound, charging price is decreased by",
        f_disc,
        "Eur for each kW deficit consumption",
    )
    print()
    print()

    print("Execution of individualized dynamic pricing algorithm...")
    omega = idp(schedule, upper_b, lower_b, tou, f_disc, f_mark)
    print(
        "The standar TOU tariff and dynamic price signal calculated for given inputs:"
    )

    results = pd.DataFrame(
        columns=[
            "sTOU",  # Standard time-of-use tariff (Eur/kWh)
            "DP signal",  # Dynamic price calculated by the algorithm (Eur/kWh)
        ]
    )
    results["sTOU"] = pd.Series(tou)
    results["DP signal"] = pd.Series(omega)
    print(results)
