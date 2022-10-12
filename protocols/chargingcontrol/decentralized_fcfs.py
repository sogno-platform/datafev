# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 17:24:19 2022

@author: egu
"""

import pandas as pd


def charging_protocol(system,ts, t_delta):

    step = t_delta.seconds

    for cc_id in system.clusters.keys():

        cluster=system.clusters[cc_id]

        if cluster.number_of_connected_chargers(ts) > 0:

            p_ch = {}
            eff  = {}
            contime={}

            for cu_id, cu in cluster.chargers.items():

                ev = cu.connected_ev

                if ev != None:

                    ev_id    = ev.vehicle_id
                    ev_soc   = ev.soc[ts]
                    ev_tarsoc= ev.soc_tar_at_t_dep_est
                    ev_bcap  = ev.bCapacity

                    if ev_soc >= ev_tarsoc:

                        p_ch[ev_id]=0.0

                    else:

                        lim_ev_batcap = (1 - ev_soc) * ev_bcap  # Limit due to the battery capacity of EV
                        lim_ch_pow = cu.p_max_ch * step         # Limit due to the charger power capability

                        if ev.pow_soc_table != None:
                            # The EV battery has a specific charger power-SOC dependency limiting the power transfer
                            table = ev.pow_soc_table
                            soc_range = (table[(table['SOC_LB'] <= ev_soc) & (ev_soc < table['SOC_UB'])]).index[0]
                            p_max = table.loc[soc_range, 'P_UB']
                            lim_ev_socdep = p_max * step # Limit due to the SOC dependency of charge power
                            e_max = min(lim_ev_batcap, lim_ch_pow, lim_ev_socdep)

                        else:
                            # The power transfer is only limited by the charger's power and battery capacity
                            e_max = min(lim_ev_batcap, lim_ch_pow)

                        p_ch[ev_id] = e_max / step  # Average charge power during the simulation step

                    eff[ev_id] = cu.eff                         #Charging efficiency
                    contime[ev_id]=(ts-ev.t_arr_real).seconds   #how long EV has been connected to the charger (seconds)

            upperlimit = cluster.upper_limit[ts]
            free_margin=upperlimit

            p_charge = {}
            vehicles_sorted=(pd.Series(contime).sort_values(ascending=False)).index #First come first served
            for ev in vehicles_sorted:

                p_max_to_cu = p_ch[ev] / eff[ev]

                if p_max_to_cu <= free_margin:
                    p_to_ev = p_max_to_cu*eff[ev]
                else:
                    p_to_ev = free_margin*eff[ev]

                free_margin-=p_to_ev/eff[ev]

                p_charge[ev] = p_to_ev

            for cu_id in system.clusters[cc_id].chargers.keys():
                cu = system.clusters[cc_id].chargers[cu_id]
                if cu.connected_ev!= None:
                    ev_id=cu.connected_ev.vehicle_id
                    cu.supply(ts, t_delta, p_charge[ev_id])
