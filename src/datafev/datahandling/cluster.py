import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.datafev.datahandling.charger import ChargingUnit


class ChargerCluster(object):
    def __init__(self, cluster_id, topology_data):

        self.type = "CC"
        self.id = cluster_id

        self.power_installed = 0  # Total installed power of the CUs in the cluster

        self.cc_dataset = pd.DataFrame(
            columns=[
                "EV ID",
                "EV Battery [kWh]",
                "Arrival Time",
                "Arrival SOC",
                "Scheduled G2V [kWh]",
                "Scheduled V2G [kWh]",
                "Connected CU",
                "Leave Time",
                "Leave SOC",
                "Net G2V [kWh]",
                "Total V2G [kWh]",
            ]
        )

        self.re_dataset = pd.DataFrame(
            columns=[
                "Active",
                "EV ID",
                "CU ID",
                "Reserved At",
                "From",
                "Until",
                "Cancelled At",
                "Scheduled G2V",
                "Scheduled V2G",
                "Price",
            ]
        )

        self.chargers = {}

        for _, i in topology_data.iterrows():

            cuID = i["cu_id"]
            pch = i["cu_p_ch_max"]
            pds = i["cu_p_ds_max"]
            eff = i["cu_eff"]
            cu = ChargingUnit(cuID, pch, pds, eff)
            self.add_cu(cu)

    def add_cu(self, charging_unit):
        """
        To add charging units to the cluster. This method is run before running the simulations.
        """
        self.power_installed += charging_unit.p_max_ch
        self.chargers[charging_unit.id] = charging_unit

    def set_peak_limits(self, start, end, step, peaklimits, violation_tolerance=0):
        """
        Method to enter peak power constraint as time series
        """

        roundedts = peaklimits["TimeStep"].dt.round("S")

        capacity_lb = pd.Series(peaklimits["LB"].values, index=roundedts)
        capacity_ub = pd.Series(peaklimits["UB"].values, index=roundedts)

        n_of_steps = int((end - start) / step)
        timerange = [start + t * step for t in range(n_of_steps + 1)]

        upper = capacity_ub.reindex(timerange)
        lower = capacity_lb.reindex(timerange)
        self.upper_limit = upper.fillna(upper.fillna(method="ffill"))
        self.lower_limit = lower.fillna(lower.fillna(method="ffill"))
        self.violation_tolerance = violation_tolerance

    def reserve(self, ts, res_from, res_until, ev, cu, contract=None):

        reservation_id = len(self.re_dataset) + 1
        ev.reservation_id = reservation_id
        ev.reserved_cluster = self
        ev.reserved_charger = cu

        # TODO: Add check for overlap
        self.re_dataset.loc[reservation_id, "Active"] = True
        self.re_dataset.loc[reservation_id, "EV ID"] = ev.vehicle_id
        self.re_dataset.loc[reservation_id, "CU ID"] = cu.id
        self.re_dataset.loc[reservation_id, "Reserved At"] = ts
        self.re_dataset.loc[reservation_id, "From"] = res_from
        self.re_dataset.loc[reservation_id, "Until"] = res_until

        if contract != None:

            tdelta = contract["Resolution"]

            if contract["Schedule"]:

                p_ref = pd.Series(contract["P Schedule"])
                s_ref = pd.Series(contract["S Schedule"])
                cu.set_schedule(ts, p_ref, s_ref)

                scheduled_g2v = p_ref.sum() * tdelta / 3600
                scheduled_v2g = -(p_ref[p_ref < 0].sum()) * tdelta / 3600

                self.re_dataset.loc[reservation_id, "Scheduled G2V"] = scheduled_g2v
                self.re_dataset.loc[reservation_id, "Scheduled V2G"] = scheduled_v2g

                if contract["Payment"]:

                    pr_g2v = pd.Series(contract["G2V Price"])
                    pr_v2g = pd.Series(contract["V2G Price"])
                    payment_for_g2v = (
                        ((p_ref[p_ref >= 0] * pr_g2v[p_ref >= 0]).sum()) * tdelta / 3600
                    )
                    payment_for_v2g = (
                        ((p_ref[p_ref < 0] * pr_v2g[p_ref < 0]).sum()) * tdelta / 3600
                    )

                    self.re_dataset.loc[reservation_id, "Price"] = (
                        payment_for_g2v + payment_for_v2g
                    )

    def unreserve(self, ts, reservation_id):
        self.re_dataset.loc[reservation_id, "Cancelled At"] = ts
        self.re_dataset.loc[reservation_id, "Active"] = False

    def enter_data_of_incoming_vehicle(self, ts, ev, cu):
        """
        To add an entry in cc_dataset for the incoming EV. This method is run when a car is allocated to a charger.
        """
        cc_dataset_id = len(self.cc_dataset) + 1
        ev.cc_dataset_id = cc_dataset_id
        ev.connected_cc = self

        self.cc_dataset.loc[cc_dataset_id, "EV ID"] = ev.vehicle_id
        self.cc_dataset.loc[cc_dataset_id, "EV Battery [kWh]"] = ev.bCapacity / 3600
        self.cc_dataset.loc[cc_dataset_id, "Arrival Time"] = ts
        self.cc_dataset.loc[cc_dataset_id, "Arrival SOC"] = ev.soc[ts]
        self.cc_dataset.loc[cc_dataset_id, "Connected CU"] = cu.id
        self.cc_dataset.loc[cc_dataset_id, "Reservation ID"] = ev.reservation_id

        reservation = self.re_dataset.loc[ev.reservation_id]
        self.cc_dataset.loc[cc_dataset_id, "Scheduled G2V [kWh]"] = (
            reservation["Scheduled G2V"]
            if pd.notna(reservation["Scheduled G2V"])
            else 0
        )
        self.cc_dataset.loc[cc_dataset_id, "Scheduled V2G [kWh]"] = (
            reservation["Scheduled V2G"]
            if pd.notna(reservation["Scheduled V2G"])
            else 0
        )

    def enter_data_of_outgoing_vehicle(self, ts, ev):

        self.cc_dataset.loc[ev.cc_dataset_id, "Leave Time"] = ts
        self.cc_dataset.loc[ev.cc_dataset_id, "Leave SOC"] = ev.soc[ts]
        self.cc_dataset.loc[ev.cc_dataset_id, "Net G2V [kWh]"] = (
            (ev.soc[ts] - ev.soc_arr_real) * ev.bCapacity / 3600
        )

        ev_v2x_ = pd.Series(ev.v2g)
        resolution = ev_v2x_.index[1] - ev_v2x_.index[0]
        ev_v2x = ev_v2x_[ev.t_arr_real : ev.t_dep_real - resolution]
        self.cc_dataset.loc[ev.cc_dataset_id, "Total V2G [kWh]"] = (
            ev_v2x.sum() * resolution.seconds / 3600
        )

        ev.cc_dataset_id = None
        ev.connected_cc = None

    def aggregate_schedule_for_actual_connections(self, start, end, step):
        """
        To retrieve the actual schedules of the charging units for the specified period 
        """
        time_index = pd.date_range(start=start, end=end, freq=step)
        cu_sch_df = pd.DataFrame(index=time_index)

        for cu in self.chargers.values():

            if cu.connected_ev == None:
                cu_sch = pd.Series(0, index=time_index)
            else:
                sch_inst = cu.active_schedule_instance
                cu_sch = (cu.schedule_pow[sch_inst].reindex(time_index)).fillna(
                    method="ffill"
                )
                # if end>cu.connected_ev.estimated_leave:
                if end > cu.connected_ev.t_dep_est:
                    # steps_after_disconnection=time_index[time_index>cu.connected_ev.estimated_leave]
                    steps_after_disconnection = time_index[
                        time_index > cu.connected_ev.t_dep_est
                    ]
                    cu_sch[steps_after_disconnection] = 0
                cu_sch[cu_sch > 0] = cu_sch[cu_sch > 0] / cu.eff
                cu_sch[cu_sch < 0] = cu_sch[cu_sch < 0] * cu.eff

            cu_sch_df[cu.id] = cu_sch.copy()

        cc_sch = cu_sch_df.sum(axis=1)

        return cc_sch

    def number_of_connected_chargers(self, ts):
        """
        This function identifies chargers with occupancy for the specified period 
        """
        nb_of_connected_cu = 0
        for cu_id, cu in self.chargers.items():
            if cu.connected_ev != None:
                nb_of_connected_cu += 1
        return nb_of_connected_cu

    def query_availability(self, start, end, step):
        """
        This function creates a dataframe containing the data of the available chargers within a specific period.

        Inputs
        ------------------------------------------------------------------------------------------------------------
        start    : start of queried period (EV's estimated arrival at this cluster)              datetime
        end      : end of queried period (EV's estimated departure from this cluster)            datetime
        step     : time resolution of query                                                      timedelta
        ------------------------------------------------------------------------------------------------------------
        """

        available_chargers = pd.DataFrame(
            columns=["max p_ch", "max p_ds", "eff"], dtype=np.float16
        )
        all_active_reservations = self.re_dataset[
            self.re_dataset["Active"] == True
        ]  # Reservations that are not cancelled

        for cu in self.chargers.values():

            active_reservations = all_active_reservations[
                all_active_reservations["CU ID"] == cu.id
            ]
            period = pd.date_range(start=start, end=end, freq=step)

            if len(active_reservations) == 0:
                cu_availability_series = pd.Series(True, index=period)
            else:

                start_of_first_reservation = active_reservations["From"].min()
                end_of_last_reservation = active_reservations["Until"].max()

                index_set = pd.date_range(
                    start=min(start, start_of_first_reservation),
                    end=max(end, end_of_last_reservation),
                    freq=step,
                )

                test_per_reservation = pd.DataFrame(index=index_set)
                test_per_reservation.loc[:, :] = True

                for res in active_reservations.index:
                    res_start = self.re_dataset.loc[res, "From"]
                    res_until = self.re_dataset.loc[res, "Until"]
                    test_per_reservation.loc[res_start : res_until - step, step] = False

                cu_availability_series = (test_per_reservation.all(axis="columns")).loc[
                    period
                ]

            is_cu_available = cu_availability_series.all()
            if is_cu_available == True:
                available_chargers.loc[cu.id] = {
                    "max p_ch": cu.p_max_ch,
                    "max p_ds": cu.p_max_ds,
                    "eff": cu.eff,
                }

        return available_chargers

    def uncontrolled_supply(self, ts, step):
        for cu_id, cu in self.chargers.items():
            if cu.connected_ev != None:
                cu.uncontrolled_supply(ts, step)

    def import_profile(self, start, end, step):
        df = pd.DataFrame(index=pd.date_range(start=start, end=end, freq=step))
        for cu_id, cu in self.chargers.items():
            df[cu_id] = (cu.consumed_power.reindex(df.index)).fillna(0)
        return df

    def occupation_profile(self, start, end, step):
        df = pd.DataFrame(index=pd.date_range(start=start, end=end, freq=step))
        for cu_id, cu in self.chargers.items():
            df[cu_id] = (
                cu.occupation_record(start, end, step).reindex(df.index)
            ).fillna(0)
        return df

    def export_results(self, start, end, step, xlfile):

        with pd.ExcelWriter(xlfile) as writer:

            ds = self.cc_dataset
            ds.to_excel(writer, sheet_name="ClusterDataset")

            p_cu = self.import_profile(start, end, step)
            p_cu["Total"] = p_cu.sum(axis=1)
            p_cu.to_excel(writer, sheet_name="UnitConsumption")

            o_cu = self.occupation_profile(start, end, step)
            o_cu["Total"] = o_cu.sum(axis=1)
            o_cu.to_excel(writer, sheet_name="UnitOccupation")

            unfulfilled_g2v_ser = ds["Scheduled G2V [kWh]"] - ds["Net G2V [kWh]"]
            unscheduled_v2g_ser = ds["Total V2G [kWh]"] - ds["Scheduled V2G [kWh]"]

            overall = pd.Series()
            overall["Unfulfilled G2V"] = (
                unfulfilled_g2v_ser[unfulfilled_g2v_ser > 0]
            ).sum()
            overall["Unscheduled V2G"] = (
                unscheduled_v2g_ser[unscheduled_v2g_ser > 0]
            ).sum()
            overall["Net Consumption"] = p_cu["Total"].sum() * step.seconds / 3600
            overall.to_excel(writer, sheet_name="Overall")
