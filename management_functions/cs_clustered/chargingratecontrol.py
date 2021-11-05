import pandas as pd
from management_algorithms.multicluster.intervention import short_term_rescheduling

def optimal_intervention_v1g(cs, ts, t_delta, horizon, solver):
    opt_horizon_t_steps = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    occ = cs.get_cluster_occupations(ts, t_delta, t_delta)
    if occ.iloc[0].sum() > 0:

        parkdata = {}
        parkdata['clusters'] = [*sorted(cs.clusters.keys())]
        parkdata['opt_horizon'] = opt_horizon_t_steps
        parkdata['opt_step'] = t_delta
        parkdata['chrunit_cap'] = cs.cu_capacities
        parkdata['cluster_cap'] = cs.cc_capacities
        parkdata['station_cap'] = cs.cs_capacity

        reference_soc = {}
        battery_cap = {}
        departure_ti = {}
        initial_soc = {}
        desired_soc = {}
        location = {}

        for cc_id, cc in cs.clusters.items():

            for cu_id, cu in cc.cu.items():
                connected_car = cu.connected_car

                if connected_car != None:
                    ev_id = connected_car.vehicle_id
                    location[ev_id] = (cc_id, cu_id)
                    battery_cap[ev_id] = connected_car.bCapacity
                    departure_ti[ev_id] = connected_car.estimated_leave
                    initial_soc[ev_id] = connected_car.soc[ts]

                    sch_inst = cu.active_schedule_instance
                    cu_sch = cu.schedule_soc[sch_inst]  # TODO: Interpolate
                    cu_sch = cu_sch.reindex(opt_horizon_t_steps)
                    cu_sch = cu_sch.fillna(method="ffill")

                    reference_soc[ev_id] = cu_sch
                    desired_soc[ev_id] = reference_soc[ev_id][ts + horizon]

        connections = {}
        connections['battery_cap'] = battery_cap
        connections['reference_soc'] = reference_soc
        connections['departure_time'] = departure_ti
        connections['initial_soc'] = initial_soc
        connections['desired_soc'] = desired_soc
        connections['location'] = location

        set_points = short_term_rescheduling(parkdata, connections, solver)

        for cc_id in cs.clusters.keys():
            for cu_id in cs.clusters[cc_id].cu.keys():
                cu = cs.clusters[cc_id].cu[cu_id]
                if cu.connected_car != None:
                    cu.supply(ts, t_delta, set_points[cc_id, cu_id])
                else:
                    cu.idle(ts, t_delta)

    else:
        for cc_id in cs.clusters.keys():
            for cu_id in cs.clusters[cc_id].cu.keys():
                cu = cs.clusters[cc_id].cu[cu_id]
                cu.idle(ts, t_delta)


def simple_intervention_v1g(cs, ts, t_delta):
    occ = cs.get_cluster_occupations(ts, t_delta, t_delta)
    if occ.iloc[0].sum() > 0:

        set_points = {}
        for cc_id, cc in cs.clusters.items():
            P_Ref_CU = pd.Series(index=sorted(cc.cu.keys()))
            for cu_id, cu in cc.cu.items():
                car = cu.connected_car
                if car != None:
                    P_Ref_CU[cu_id] = cu.calc_p_max_ch(ts, t_delta)
                else:
                    P_Ref_CU[cu_id] = 0.0

            P_Ref_Arm = P_Ref_CU.sum()
            if P_Ref_Arm < cc.power_import_max:
                set_points[cc_id] = P_Ref_CU.to_dict()
            else:
                set_points[cc_id] = (P_Ref_CU * cc.power_import_max / P_Ref_Arm).to_dict()

            for cu_id, cu in cc.cu.items():
                if cu.connected_car != None:
                    cu.supply(ts, t_delta, set_points[cc_id][cu_id])
                else:
                    cu.idle(ts, t_delta)
    else:
        for cc_id in cs.clusters.keys():
            for cu_id in cs.clusters[cc_id].cu.keys():
                cu = cs.clusters[cc_id].cu[cu_id]
                cu.idle(ts, t_delta)