from src.datafev.algorithms.cluster.prioritization_llf import leastlaxityfirst


def charging_protocol(ts, t_delta, system):
    """
    This protocol is executed periodically during operation of charger clusters.

    It addresses the scenarios where each cluster has a local power consumption constraint and therefore has to control
    the power distribution to the chargers. The control architecture is decentralized; therefore, each cluster applies
    its own control. The applied control is based on "least-laxity-first" logic.

    :param ts:          Current time                    datetime
    :param t_delta:     Control horizon                 timedelta
    :param system:      Multi-cluster system object     datahandling.multicluster

    """

    step = t_delta.seconds

    # Loop through the clusters
    for cc_id in system.clusters.keys():

        cluster = system.clusters[cc_id]

        if cluster.number_of_connected_chargers(ts) > 0:
            # The cluster includes connected EVs

            ################################################################################################
            # Step 1: Identification of charging demand

            inisoc = {}  # Will contain the current SOC values of EV batteries
            tarsoc = (
                {}
            )  # Will contain the target SOC values of EV batteries (at estimate departure time)
            bcap = {}  # Will contain the EV battery capacities
            eff = {}  # Will contain the power conversion efficiencies during
            p_socdep = {}  # Will contain the data of SOC dependency of charge power
            p_chmax = (
                {}
            )  # Will contain the maximum charge power that can be handled by EV-charger pair
            p_re = {}  # Will contain the charge powers that EVs request
            leadtime = (
                {}
            )  # Will contain the lead time for charging from now arrial until estimate departure)

            # Loop through the chargers
            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    # There is an EV connected in this charger
                    ev_id = ev.vehicle_id

                    # Current SOC of EV
                    ev_soc = ev.soc[ts]
                    inisoc[ev_id] = ev_soc

                    # Target SOC of EV (for estimated departure time)
                    ev_tarsoc = ev.soc_tar_at_t_dep_est
                    tarsoc[ev_id] = ev_tarsoc

                    # Energy capactiy of the EV battery
                    ev_bcap = ev.bCapacity
                    bcap[ev_id] = ev_bcap

                    # Power conversion efficiency of charger
                    eff[ev_id] = cu.eff

                    # Maximum charge power that can be handled by EV-charger pair (for the whole SOC curve)
                    p_chmax[ev_id] = min(ev.p_max_ch, cu.p_max_ch)

                    # How long EV will stay connected to the charger (seconds)
                    leadtime[ev_id] = (
                        (ev.t_dep_est - ts).seconds if ts < ev.t_dep_est else 0.001
                    )

                    if ev_soc >= ev_tarsoc:

                        # The EV connected here has already reached its target SOC
                        p_re[ev_id] = 0.0

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
                            p_socdep[ev_id] = table.to_dict()

                        else:

                            # The power transfer is only limited by the charger's power and battery capacity
                            e_max = min(lim_ev_batcap, lim_ch_pow)
                            p_socdep[ev_id] = None

                        # Charge powers requested by EVs during the control horizon
                        p_re[ev_id] = e_max / step

            ################################################################################################

            ################################################################################################
            # Step 2: Power distribution based on first-come-first-serve algorithm
            upperlimit = cluster.upper_limit[ts]  # Cluster level constraint
            p_charge = leastlaxityfirst(
                inisoc, tarsoc, bcap, eff, p_socdep, p_chmax, p_re, leadtime, upperlimit
            )
            ################################################################################################

            ################################################################################################
            # Step 3: Charging
            for cu_id in system.clusters[cc_id].chargers.keys():
                cu = system.clusters[cc_id].chargers[cu_id]
                if cu.connected_ev != None:
                    ev_id = cu.connected_ev.vehicle_id
                    cu.supply(ts, t_delta, p_charge[ev_id])
            ################################################################################################
