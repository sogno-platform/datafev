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
from datafev.algorithms.cluster.pricing_rule import idp
from datafev.algorithms.vehicle.routing_milp import smart_routing


def reservation_routine(
    ts,
    tdelta,
    system,
    fleet,
    solver,
    traffic_forecast,
    f_discount=0.05,
    f_markup=0.05,
    arbitrage_coeff=0.0,
):
    """
    This routine is executed to reserve chargers for the EVs approaching a multi-cluster system.

    The smart reservations specify:
        - which cluster and which charger the approaching EVs must connect to,
        - optimal charging schedule of EVs,
        - and the payment for agreed charging service.

    Parameters
    ----------
    ts : datetime
        Current time.
    tdelta : timedelta
        Resolution of scheduling.
    system : data_handling.multi_cluster
        Multi-cluster system object.
    fleet : data_handling.fleet
        EV fleet object.
    solver : pyomo.SolverFactory
        Optimization solver.
    traffic_forecast : dict of dict
        Traffic forecast data.
    f_discount : dict of float, optional
        Discount factor (to motivate load increase) in dynamic pricing. The default is 0.05.
    f_markup : dict of float, optional
        Markup factor (to motivate load decrease) in dynamic pricing. The default is 0.05.
    arbitrage_coeff : float, optional
        Arbitrage coefficient to distinguish G2V/V2G prices. The default is 0.0.

    Returns
    -------
    None.

    """

    reserving_vehicles = fleet.reserving_vehicles_at(ts)

    for ev in reserving_vehicles:

        ############################################################################
        ############################################################################
        ############################################################################
        # Start reservation protccol

        ############################################################################
        ############################################################################
        # Step 1: Identify available chargers
        available_chargers = system.query_availability(
            ev.t_arr_est, ev.t_dep_est, tdelta, traffic_forecast
        )
        ############################################################################
        ############################################################################

        if len(available_chargers) == 0:
            ev.reserved = False
        else:
            ############################################################################
            ############################################################################
            # Step 2: Apply a specific reservation management strategy
            # Applied one is based on the smart routing strategy introduced in (doi: 10.1109/TTE.2022.3208627)

            ############################################################################
            # Step 2.1: Identify candidate chargers and optimization parameters
            candidate_chargers_df = available_chargers.drop_duplicates()
            candidate_chargers_dc = candidate_chargers_df.T.to_dict()

            for cu_id, row in candidate_chargers_df.iterrows():

                cc_id = row["cluster"]
                ch_rate = row["max p_ch"]
                ds_rate = row["max p_ds"]

                # It is assumed that power capability of EV battery is not SOC dependent
                p_ch = min(ch_rate, ev.p_max_ch)
                p_ds = min(ds_rate, ev.p_max_ds)
                arrsoc = ev.soc_arr_est + traffic_forecast["soc_dec"][cc_id]
                pardur = (ev.t_dep_est + traffic_forecast["dep_del"][cc_id]) - (
                    ev.t_arr_est + traffic_forecast["arr_del"][cc_id]
                )
                soc_max = min(1, arrsoc + (p_ch * pardur.seconds) / ev.bCapacity)
                tarsoc = min(soc_max, ev.soc_tar_at_t_dep_est)

                candidate_chargers_dc[cu_id]["max p_ch"] = p_ch
                candidate_chargers_dc[cu_id]["max p_ds"] = p_ds
                candidate_chargers_dc[cu_id]["arrsoc"] = arrsoc
                candidate_chargers_dc[cu_id]["tarsoc"] = tarsoc
                candidate_chargers_dc[cu_id]["arrtime"] = int(
                    traffic_forecast["arr_del"][cc_id] / tdelta
                )
                candidate_chargers_dc[cu_id]["deptime"] = int(pardur / tdelta)

            candidate_chargers = pd.DataFrame(candidate_chargers_dc).T
            #########################################################################

            ############################################################################
            # Step 2.2: Execute dynamic pricing algorithm for clusters having candidate chargers
            g2v_dps = {}
            v2g_dps = {}
            deptime_max = ts + candidate_chargers["deptime"].max() * tdelta
            for cu_id in candidate_chargers.index:

                cc_id = candidate_chargers.loc[cu_id, "cluster"]
                cc = system.clusters[cc_id]
                cc_power_ub = dict(enumerate(cc.upper_limit[ts:deptime_max].values))
                cc_power_lb = dict(enumerate(cc.lower_limit[ts:deptime_max].values))
                cc_schedule = dict(
                    enumerate(
                        (cc.query_actual_schedule(ts, deptime_max, tdelta)).values
                    )
                )
                tou_tariff = dict(
                    enumerate((system.tou_price.loc[ts:deptime_max]).values)
                )

                dlp = idp(
                    cc_schedule,
                    cc_power_ub,
                    cc_power_lb,
                    tou_tariff,
                    f_discount,
                    f_markup,
                )
                g2v_dps[cu_id] = dlp
                v2g_dps[cu_id] = dict(
                    [(k, dlp[k] * (1 - arbitrage_coeff)) for k in sorted(dlp.keys())]
                )
            ############################################################################

            ############################################################################
            # Step 2.3: Execute smart routing algorithm to find optimal cluster and schedules
            opt_horizon = list(range(int(candidate_chargers["deptime"].max()) + 1))
            opt_step = tdelta.seconds
            ecap = ev.bCapacity
            v2gall = ev.v2g_allow
            tarsoc = candidate_chargers["tarsoc"].max()
            minsoc = ev.minSoC
            maxsoc = ev.maxSoC
            crtsoc = tarsoc
            crttime = int(candidate_chargers["deptime"].max())
            arrtime = candidate_chargers["arrtime"].to_dict()
            deptime = candidate_chargers["deptime"].to_dict()
            arrsoc = candidate_chargers["arrsoc"].to_dict()
            pch = candidate_chargers["max p_ch"].to_dict()
            pds = candidate_chargers["max p_ds"].to_dict()

            p, s, selected_charger_id = smart_routing(
                solver,
                opt_horizon,
                opt_step,
                ecap,
                v2gall,
                tarsoc,
                minsoc,
                maxsoc,
                crtsoc,
                crttime,
                arrtime,
                deptime,
                arrsoc,
                pch,
                pds,
                g2v_dps,
                v2g_dps,
            )
            ############################################################################

            # Outputs of Step 2
            selected_cluster_id = candidate_chargers.loc[selected_charger_id, "cluster"]
            selected_cluster = system.clusters[selected_cluster_id]
            selected_charger = selected_cluster.chargers[selected_charger_id]

            # End: Reservation management strategy
            ############################################################################
            ############################################################################

            ############################################################################
            ############################################################################
            # Step 3: Reserve the selected charger for the EV and assign relevant reservation parameters
            res_at = ts
            res_from = ev.t_arr_est + traffic_forecast["arr_del"][selected_cluster_id]
            res_until = ev.t_dep_est + traffic_forecast["dep_del"][selected_cluster_id]

            contract = {}
            contract["Schedule"] = True
            contract["Payment"] = True
            contract["P Schedule"] = {}
            contract["S Schedule"] = {}
            contract["G2V Price"] = {}
            contract["V2G Price"] = {}
            contract["Resolution"] = opt_step
            for t in opt_horizon:
                contract["P Schedule"][ts + t * tdelta] = p[t]
                contract["S Schedule"][ts + t * tdelta] = s[t]
                contract["G2V Price"][ts + t * tdelta] = g2v_dps[selected_charger_id][t]
                contract["V2G Price"][ts + t * tdelta] = v2g_dps[selected_charger_id][t]

            selected_cluster.reserve(
                res_at, res_from, res_until, ev, selected_charger, contract
            )
            ev.reserved = True
            ############################################################################
            ############################################################################

        ############################################################################
        ############################################################################
        ############################################################################
        # End reservation protccol
