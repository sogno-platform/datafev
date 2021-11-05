import pandas as pd
from management_algorithms.singlevehicle.scheduling_v2g_det import optimal_schedule_v2g

def pre_allocation_scheduling_fast(cs, ts, t_delta, ev, ev_est_lea, ev_tar_soc):
    """
    This function finds the schedule that completes charging of an EV as fast as possible
    """
    
    ev.estimated_leave = ev_est_lea  # TODO: Store it in a better place
    current_soc = ev.soc[ts]
    hyp_en_input = cs.P_RAT * ((ev_est_lea - ts).seconds)  # Maximum energy that could be supplied within the given time with the given charger rating if the battery capacity was unlimited
    fea_target_soc = min(ev_tar_soc, current_soc + hyp_en_input / ev.bCapacity)
    ev.fea_target_soc = fea_target_soc  # TODO: Store it in a better place

    if fea_target_soc <= ev_tar_soc:
        schedule_pow = pd.Series(cs.P_RAT, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
    else:
        steps = (fea_target_soc - current_soc) * ev.bCapacity / (cs.P_RAT * t_delta.seconds)
        int_s = int(steps)
        schedule_pow = pd.Series(0.0, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
        schedule_pow.iloc[:int_s] = cs.P_RAT
        schedule_pow[int_s] = cs.P_RAT * (steps - int_s)

    schedule_soc = pd.Series(ev.soc[ts], index=pd.date_range(start=ts, end=ev_est_lea, freq=t_delta))
    schedule_soc += (schedule_pow.reindex(schedule_soc.index).cumsum().shift(1).fillna(0.0)) * t_delta.seconds / ev.bCapacity

    return schedule_pow, schedule_soc


def pre_allocation_scheduling(cs, solver, ts, t_delta, ev, ev_est_lea, ev_tar_soc, dyn_cost, minsoc=0.2,maxsoc=1.0, v2g=False):
    """
    This method calculates the individual-optimum schedule for 
    an incoming EV with the given EV parameters and dynamic cost factor       
    """

    ev.estimated_leave = ev_est_lea  # TODO: Store it in a better place
    current_soc = ev.soc[ts]
    hyp_en_input = cs.P_RAT * ((ev_est_lea - ts).seconds)  # Maximum energy that could be supplied within the given time with the given charger rating if the battery capacity was unlimited
    fea_target_soc = min(ev_tar_soc, current_soc + hyp_en_input / ev.bCapacity)
    ev.fea_target_soc = fea_target_soc  # TODO: Store it in a better place

    if fea_target_soc == ev_tar_soc:
            schedule_pow, schedule_soc = optimal_schedule_v2g(solver, ts, ev_est_lea, t_delta, cs.P_RAT, ev.bCapacity,ev.soc[ts], fea_target_soc, minsoc, maxsoc, dyn_cost,v2g)
    else:
        schedule_pow = pd.Series(cs.P_RAT, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
        schedule_soc = pd.Series(ev.soc[ts], index=pd.date_range(start=ts, end=ev_est_lea, freq=t_delta))
        schedule_soc += (schedule_pow.reindex(schedule_soc.index).cumsum().shift(1).fillna(0.0)) * t_delta.seconds / ev.bCapacity

    return schedule_pow, schedule_soc

def pre_allocation_scheduling_selective(cs, solver, ts, t_delta, ev, ev_est_lea, ev_tar_soc, minsoc=0.2,maxsoc=1.0, v2g=False, min_tol_for_optimization=0):

    est_park_duration  =ev_est_lea - ts
    ev.estimated_leave = ev_est_lea  # TODO: Store it in a better place
    current_soc = ev.soc[ts]
    hyp_en_input = cs.P_RAT * (est_park_duration.seconds)  # Maximum energy that could be supplied within the given time with the given charger rating if the battery capacity was unlimited
    fea_target_soc = min(ev_tar_soc, current_soc + hyp_en_input / ev.bCapacity)
    ev.fea_target_soc = fea_target_soc  # TODO: Store it in a better place

    #Refer to 10.1049/els2.12037
    T_M=(fea_target_soc-current_soc)*ev.bCapacity/cs.P_RAT              #The active charging duration (with P_RAt) required to achieve feasible target SOC
    m   =(est_park_duration.seconds-T_M)/est_park_duration.seconds      #The tolerance for charging suspension

    if m>=min_tol_for_optimization:
        #Estimated parking duration is large enough to optimize the charge schedule of this vehicle
        if fea_target_soc == ev_tar_soc:
            dyn_cost, cc_schedules = cs.calculate_cost_coef_for_scheduling(ts, t_delta,est_park_duration)  # Cost coefficient for objective function of individual scheduling
            schedule_pow, schedule_soc = optimal_schedule_v2g(solver, ts, ev_est_lea, t_delta, cs.P_RAT,cs.P_RAT, ev.bCapacity,ev.soc[ts], fea_target_soc, minsoc, maxsoc, dyn_cost, v2g)
        else:
            schedule_pow = pd.Series(cs.P_RAT, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
            schedule_soc = pd.Series(ev.soc[ts], index=pd.date_range(start=ts, end=ev_est_lea, freq=t_delta))
            schedule_soc += (schedule_pow.reindex(schedule_soc.index).cumsum().shift(1).fillna(0.0)) * t_delta.seconds / ev.bCapacity
    else:
        #Estimated parking duration is not large enough (=EV does not have enough tolerance to charging suspension)
        if fea_target_soc <= ev_tar_soc:
            schedule_pow = pd.Series(cs.P_RAT, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
        else:
            steps = (fea_target_soc - current_soc) * ev.bCapacity / (cs.P_RAT * t_delta.seconds)
            int_s = int(steps)
            schedule_pow = pd.Series(0.0, index=pd.date_range(start=ts, end=ev_est_lea - t_delta, freq=t_delta))
            schedule_pow.iloc[:int_s] = cs.P_RAT
            schedule_pow[int_s] = cs.P_RAT * (steps - int_s)
        schedule_soc = pd.Series(ev.soc[ts], index=pd.date_range(start=ts, end=ev_est_lea, freq=t_delta))
        schedule_soc += (schedule_pow.reindex(schedule_soc.index).cumsum().shift(1).fillna(0.0)) * t_delta.seconds / ev.bCapacity

    return schedule_pow, schedule_soc







    


