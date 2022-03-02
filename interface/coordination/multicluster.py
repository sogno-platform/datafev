import pandas as pd
from algorithms.coordination.multicluster_optimization import minimize_deviation_from_schedules

                              
def ref_tracking_optimization(cs, ts, t_delta, horizon, solver,max_violation=0):
    opt_horizon_t_steps = pd.date_range(start=ts, end=ts + horizon, freq=t_delta)
    occ = cs.number_of_connected_chargers(ts)
    if occ>0:

        parkdata = {}
        parkdata['clusters']    = [*sorted(cs.clusters.keys())]
        parkdata['opt_horizon'] = list(range(len(opt_horizon_t_steps)))
        parkdata['con_horizon'] = [0]
        parkdata['opt_step']    = t_delta

        connections={}
        connections['P_EV_pos_max']={}
        connections['P_EV_neg_max']={}
        connections['charge_eff']={}
        connections['discharge_eff']={}
        connections['battery_cap']={}
        connections['target_soc']={}
        connections['departure_time']={}
        connections['initial_soc']={}
        connections['minimum_soc']={}
        connections['maximum_soc']={}
        connections['location']={}
        
        powlimits={}
        powlimits['P_CC_up_lim'] ={}
        powlimits['P_CC_low_lim']={}
        powlimits['P_CS_up_lim'] =dict(enumerate(cs.upper_limit[opt_horizon_t_steps].values))
        powlimits['P_CS_low_lim']=dict(enumerate(cs.lower_limit[opt_horizon_t_steps].values))
        powlimits['P_CC_vio_lim']={}
        
        for cc_id, cc in cs.clusters.items():
            
            powlimits['P_CC_up_lim'][cc_id] =dict(enumerate(cc.upper_limit[opt_horizon_t_steps].values))
            powlimits['P_CC_low_lim'][cc_id]=dict(enumerate(cc.lower_limit[opt_horizon_t_steps].values))
            powlimits['P_CC_vio_lim'][cc_id]=max_violation
            
            for cu_id, cu in cc.cu.items():
                connected_ev = cu.connected_ev
                
                if connected_ev != None:
                    ev_id = connected_ev.vehicle_id
                    connections['location'] [ev_id]      = (cc_id, cu_id)
                    connections['battery_cap'][ev_id]    = connected_ev.bCapacity
                    connections['departure_time'][ev_id] = (connected_ev.estimated_leave-ts)/t_delta
                    connections['initial_soc'][ev_id]    = connected_ev.soc[ts]
                    connections['minimum_soc'][ev_id]    = connected_ev.minSoC
                    connections['maximum_soc'][ev_id]    = connected_ev.maxSoC
                    sch_inst = cu.active_schedule_instance
                    cu_sch = cu.schedule_soc[sch_inst]  
                    cu_sch = cu_sch.reindex(opt_horizon_t_steps)
                    cu_sch = cu_sch.fillna(method="ffill")
                    connections['target_soc'][ev_id]     = cu_sch[ts + horizon]
                    connections['charge_eff'][ev_id]     = cu.eff       
                    connections['discharge_eff'][ev_id]  = cu.eff 
                                                     
                    if cu.ctype=='ac1':
                        p_ev_pos_max=min(connected_ev.p_max_ac_ph1,cu.P_max_ch)
                        p_ev_neg_max=min(connected_ev.p_max_ac_ph1,cu.P_max_ds) 
                    if cu.ctype=='ac3':
                        p_ev_pos_max=min(connected_ev.p_max_ac_ph3,cu.P_max_ch)
                        p_ev_neg_max=min(connected_ev.p_max_ac_ph3,cu.P_max_ds)
                    if cu.ctype=='dc':
                        p_ev_pos_max=min(connected_ev.p_max_dc,cu.P_max_ch)
                        p_ev_neg_max=min(connected_ev.p_max_dc,cu.P_max_ds)
                    
                    connections['P_EV_pos_max'][ev_id]   =p_ev_pos_max
                    connections['P_EV_neg_max'][ev_id]   =p_ev_neg_max 
                    
        set_points,soc_ref=minimize_deviation_from_schedules(parkdata,powlimits,connections,solver)
        for cc_id in cs.clusters.keys():
            for cu_id in cs.clusters[cc_id].cu.keys():
                cu = cs.clusters[cc_id].cu[cu_id]
                if cu.connected_ev != None:
                    cu.supply(ts, t_delta, set_points[cc_id, cu_id][0])
