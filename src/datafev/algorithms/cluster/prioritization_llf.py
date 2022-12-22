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


def leastlaxityfirst(
    inisoc, tarsoc, bcap, efficiency, p_socdep, p_chmax, p_re, leadtime, upperlimit
):
    """
    This is a control algorithm that manages the real-time charging rates of
    the EV chargers in a cluster under given power limits. The control is 
    based on the least-laxity-first rule prioritizing urgent demands.

    Parameters
    ----------
    inisoc : dict of float
        Initial SOCs of EV batteries (0<inisoc[key]<1).
    tarsoc : dict of float
        Target SOCs of EVs (0<inisoc[key]<1).
    bcap : dict of float
        Battery capactiy of EVs (kWs).
    efficiency : dict of float
        Power conversion efficiencies of chargers.
    p_socdep : dict of dict
        SOC dependency of power capability of EV batteries. Dictionary values
        are dictionaries for a single EV in the cluster. In the EV dictionaries
        a key indicates a particular SOC range. An SOC range is defined by 
        lower (SOC_LB) and upper bound of the SOC range(SOC_UB). The power that 
        the EV battery can accept (kW) in a particular SOC range is indicated
        by the value of 'P_UB'. 
    p_chmax : dict of float
        Maximum charge power capabilities of EVs (kW).
    p_re : dict of float
        Power requested by EVs (kW).
    leadtime : dict of int
        How long EVs are expected to stay connected (seconds).
    upperlimit : dict of float
        Upper limit of cluster power consumption (kW).

    Returns
    -------
    p_charge : dict of float
        Dictionary containing the charge power (kW) to each EV connected
        in the cluster.

    """

    # This will contain the laxity of EVs
    laxity = {}

    # Laxity is defined with the formula LAX=1-T_MIN/T_LEAD
    # T_MIN  : Minimum time required to achieve target SOC (T_MIN>=0)
    # T_LEAD : Time until estimated departure (T_LEAD>0)

    for ev_id in inisoc.keys():

        # Lead time until estimated departure
        T_LEAD = leadtime[ev_id]

        if inisoc[ev_id] >= tarsoc[ev_id]:

            # Minimum time required to acheive taget SOC is 0 if target SOC is already achieved
            T_MIN = 0

        else:

            # Target SOC has not been achieved yet: T_MIN will have a postive value

            if p_socdep[ev_id] == None:

                # The EV battery does not have a specific charger power-SOC dependency limiting the power transfer
                # T_MIN is determined by p_chmax (max power that charger-EV pair can handle for whole SOC range
                T_MIN = (tarsoc[ev_id] - inisoc[ev_id]) * bcap[ev_id] / p_chmax[ev_id]

            else:

                # The EV battery has a specific charger power-SOC dependency limiting the power transfer
                table = pd.DataFrame(p_socdep[ev_id]).T

                # Current SOC range of the EV
                I = (
                    table[
                        (table["SOC_LB"] <= inisoc[ev_id])
                        & (inisoc[ev_id] < table["SOC_UB"])
                    ]
                ).index[0]

                # Target SOC range of the EV
                F = (
                    table[
                        (table["SOC_LB"] <= tarsoc[ev_id])
                        & (tarsoc[ev_id] < table["SOC_UB"])
                    ]
                ).index[0]

                if I == F:

                    # The current SOC is in the same range as the target SOC
                    # The EV can be charged with a constant power until target SOC is reached
                    p_max_in_range = table.loc[I, "P_UB"]

                    # Maximum feasible power input to EV can be smaller though (taking into account the charger rating)
                    p_max_feassible = min(p_max_in_range, p_chmax[ev_id])

                    # T_MIN is determined by considering only p_max_feasible
                    T_MIN = (
                        (tarsoc[ev_id] - inisoc[ev_id]) * bcap[ev_id] / p_max_feassible
                    )

                else:

                    # T_MIN is determined by taking into account the variations in charge power capability with SOC change
                    # T_MIN will be summation of the minimum time spent in each SOC range
                    time_in_range = (
                        {}
                    )  # Will contain the minimum time spent within a particular SOC range

                    # Loop through all SOC ranges to calculate the minimum time spent in each SOC range
                    for r in range(I, F + 1):

                        # Parameters for the specific SOC range
                        soc_ub_in_range = table.loc[r, "SOC_UB"]
                        soc_lb_in_range = table.loc[r, "SOC_LB"]
                        p_max_in_range = table.loc[r, "P_UB"]

                        # Maximum feasible power input to EV in this SOC range (taking into account the charger rating)
                        p_max_feassible = min(p_max_in_range, p_chmax[ev_id])

                        # Calculation of minimum time spent in specific SOC range through charging
                        if r == I:
                            # From initial SOC to upper bound of this particular range
                            time_in_range[r] = (
                                (soc_ub_in_range - inisoc[ev_id])
                                * bcap[ev_id]
                                / p_max_feassible
                            )
                        elif r < F:
                            # From lower to upper bound of this particular range
                            time_in_range[r] = (
                                (soc_ub_in_range - soc_lb_in_range)
                                * bcap[ev_id]
                                / p_max_feassible
                            )
                        else:  # r==F
                            # From lower bound of this particular range to target SOC
                            time_in_range[r] = (
                                (tarsoc[ev_id] - soc_lb_in_range)
                                * bcap[ev_id]
                                / p_max_feassible
                            )

                    T_MIN = sum(time_in_range[r] for r in range(I, F + 1))

        # Laxity of this EV's charging demand
        LAX = 1 - T_MIN / T_LEAD

        # Store in the laxity dictionary
        laxity[ev_id] = LAX

    # Sorting EVs according to their laxity (least laxity first)
    vehicles_sorted = (pd.Series(laxity).sort_values(ascending=True)).index

    p_charge = {}  # Will contain the charge power consumed by the EVs
    free_margin = upperlimit  # Cluster level constraint

    for ev in vehicles_sorted:

        # The power that charger wants to withdraw from grid to meet EV's request
        p_max_to_cu = p_re[ev] / efficiency[ev]

        if p_max_to_cu <= free_margin:

            # The grid has enough margin to suppy the requested amount
            p_to_ev = p_max_to_cu * efficiency[ev]

        else:

            # The grid does not have enough margin to supply the requested amount
            p_to_ev = free_margin * efficiency[ev]

        # This EV will get p_to_ev amount of power in this control horizon
        p_charge[ev] = p_to_ev

        # Available margin is closed after dedicating certain capacity to the EVs
        free_margin -= p_to_ev / efficiency[ev]

    return p_charge


if __name__ == "__main__":

    import pandas as pd
    import numpy as np

    ###########################################################################
    # Input parameters

    PEV = 50  # Maximum charge power that the EV battery can accept
    ch_eff = 1.0  # Power conversion efficiency of the charger
    N = 16  # Number of connected EVs in the system
    CAP = 55 * 3600  # Battery capacity of EVs
    upperlimit = 0.5 * N * PEV  # Aggregate power consumption constraint of the cluster
    sch_horizon = 300  # Decision taken for the next 300 seconds (5 minutes)

    # SOC dependency of the maximum charge power to the EV battery
    pow_soc_dep_table = {
        0: {"SOC_LB": 0.0, "SOC_UB": 0.5, "P_UB": 50},
        1: {"SOC_LB": 0.5, "SOC_UB": 0.7, "P_UB": 40},
        2: {"SOC_LB": 0.7, "SOC_UB": 1.0, "P_UB": 30},
    }

    # Demand specifications
    np.random.seed(0)

    p_re = {}
    p_chmax = {}
    efficiency = {}
    bcap = {}
    tarsoc = {}
    leadtime = {}
    inisoc = {}
    p_socdep = {}

    for n in range(1, N + 1):

        # EV IDs
        evid = "EV" + str(n)

        # Maximum charge power to EV
        p_chmax[evid] = PEV

        # Conversion efficiency
        efficiency[evid] = ch_eff

        # Battery capacity (given in kWs)
        bcap[evid] = CAP

        # Current SOCs are between 40%-60%
        inisoc[evid] = np.random.uniform(low=0.4, high=0.8)

        # Target SOCs are 90%
        tarsoc[evid] = 0.9

        # EVs have 5-10 min till departure.
        # The values are given in number of time steps until departure times
        leadtime[evid] = int(np.random.uniform(low=sch_horizon, high=sch_horizon * 2))

        # SOC dependency of power capability of EV batteries
        p_socdep[evid] = pow_soc_dep_table

        # EVs want to consume the maximum feasible power in their SOC range
        table = pd.DataFrame(pow_soc_dep_table).T
        inisoc_range = (
            table[(table["SOC_LB"] <= inisoc[evid]) & (inisoc[evid] < table["SOC_UB"])]
        ).index[0]
        p_re[evid] = min(PEV, table.loc[inisoc_range, "P_UB"])

    ###########################################################################

    print("The cluster with total installed capacity of:", N * PEV, "kW")
    print()
    print("...has a power limit of:", upperlimit, "kW")
    print()

    print(
        "...controlling the real-time chaging rates of the EVs with charging demands:"
    )
    inputs = pd.DataFrame(columns=["Current SOC", "Target SOC", "Estimate Departure"])
    inputs["Current SOC"] = pd.Series(inisoc)
    inputs["Target SOC"] = pd.Series(tarsoc)
    inputs["Estimate Departure"] = pd.Series(leadtime)
    print(inputs)
    print()

    print("Executing the control algorithm...")
    p_ref = leastlaxityfirst(
        inisoc, tarsoc, bcap, efficiency, p_socdep, p_chmax, p_re, leadtime, upperlimit
    )

    print("Resulting profile:")
    result = inputs.copy()
    result["Controlled Consumption"] = pd.Series(p_ref)
    print(result)
    print()
