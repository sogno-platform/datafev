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


def charging_routine(ts, t_delta, system):
    """
    This routine is executed periodically during operation of charger clusters.

    It addresses the scenarios where each cluster has a local power consumption constraint and therefore has to control
    the power distribution to the chargers. The control architecture is decentralized; therefore, each cluster applies
    its own control. The applied control is based on "first-come-first-serve" logic.

    Parameters
    ----------
    ts : datetime
        Current time.
    t_delta : timedelta
        Control horizon.
    system : data_handling.multi_cluster
        Multi-cluster system object.

    Returns
    -------
    None.

    """

    step = t_delta.seconds

    # Loop through the clusters
    for cc_id in system.clusters.keys():

        cluster = system.clusters[cc_id]

        if cluster.query_actual_occupation(ts) > 0:
            # The cluster includes connected EVs

            ################################################################################################
            # Step 1: Identification of charging demand
            p_ch = {}  # Will contain the charge powers requested by each EV
            eff = {}  # Will contain the power conversion efficiencies during
            contime = (
                {}
            )  # Will contain the connection time of EVs (from their arrial until now)

            # Loop through the chargers
            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    # There is an EV connected in this charger
                    ev_id = ev.vehicle_id
                    ev_soc = ev.soc[ts]
                    ev_tarsoc = ev.soc_tar_at_t_dep_est
                    ev_bcap = ev.bCapacity

                    if ev_soc >= ev_tarsoc:

                        # The EV connected here has already reached its target SOC
                        p_ch[ev_id] = 0.0

                    else:

                        # The EV connected here wants to keep charging
                        # Calculation of the amount of energy that can be supplied to the EV
                        lim_ev_batcap = (
                            1 - ev_soc
                        ) * ev_bcap  # Limit due to the battery capacity of EV
                        lim_ch_pow = (
                            cu.p_max_ch * step
                        )  # Limit due to the charger power capability

                        if ev.pow_soc_table != None:

                            # The EV battery has a specific charger power-SOC dependency limiting the power transfer
                            table = ev.pow_soc_table
                            soc_range = (
                                table[
                                    (table["SOC_LB"] <= ev_soc)
                                    & (ev_soc < table["SOC_UB"])
                                ]
                            ).index[0]
                            p_max = table.loc[soc_range, "P_UB"]
                            lim_ev_socdep = (
                                p_max * step
                            )  # Limit due to the SOC dependency of charge power
                            e_max = min(lim_ev_batcap, lim_ch_pow, lim_ev_socdep)

                        else:

                            # The power transfer is only limited by the charger's power and battery capacity
                            e_max = min(lim_ev_batcap, lim_ch_pow)

                        p_ch[ev_id] = (
                            e_max / step
                        )  # Average charge power during the simulation step

                    eff[ev_id] = cu.eff  # Charging efficiency
                    contime[ev_id] = (
                        ts - ev.t_arr_real
                    ).seconds  # how long EV has been connected to the charger (seconds)
            ################################################################################################

            ################################################################################################
            # Step 2: Power distribution based on first-come-first-serve algorithm
            upperlimit = cluster.upper_limit[ts]  # Cluster level constraint
            p_charge = {}  # Will contain the charge power consumed by the EVs

            vehicles_sorted = (pd.Series(contime).sort_values(ascending=False)).index
            free_margin = upperlimit
            for ev in vehicles_sorted:

                p_max_to_cu = p_ch[ev] / eff[ev]

                if p_max_to_cu <= free_margin:
                    p_to_ev = p_max_to_cu * eff[ev]
                else:
                    p_to_ev = free_margin * eff[ev]

                free_margin -= p_to_ev / eff[ev]

                p_charge[ev] = p_to_ev
            ################################################################################################

            ################################################################################################
            # Step 3: Charging
            for cu_id in system.clusters[cc_id].chargers.keys():
                cu = system.clusters[cc_id].chargers[cu_id]
                if cu.connected_ev != None:
                    ev_id = cu.connected_ev.vehicle_id
                    cu.supply(ts, t_delta, p_charge[ev_id])
            ################################################################################################
