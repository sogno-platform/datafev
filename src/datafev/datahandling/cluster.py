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
import numpy as np
from datetime import datetime, timedelta
from datafev.datahandling.charger import ChargingUnit


class ChargerCluster(object):
    """
    A charger cluster consists of X number of charging units. It is considered 
    to be the lower aggregation level in the datafev framework. A single entity 
    (e.g., a charging station operator, micro-grid controller, aggregator) is 
    responsible for management of a cluster. 
    """
    
    def __init__(self, cluster_id, topology_data):
        """
        Clusters are defined by the EV chargers that they consist of.

        Parameters
        ----------
        cluster_id : str
            String identifier of the cluster.
        topology_data : pandas.DataFrame
            A table containing 1) string identifiers, 2) maximum charge powers,
            3) maximum discharge powers, 4) power conversion efficiencies of
            charging units in the cluster.

        Returns
        -------
        None.

        """

        self.type = "CC"
        self.id = cluster_id

        self.power_installed = 0  # Total installed power of the CUs 

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
        This method is run at initialization of the cluster object.
        It adds charging units to the cluster.

        Parameters
        ----------
        charging_unit : ChargingUnit
            A charging unit object.

        Returns
        -------
        None.

        """
        
        self.power_installed += charging_unit.p_max_ch
        self.chargers[charging_unit.id] = charging_unit

    def enter_power_limits(self, start, end, step, limits, tolerance=0):
        """
        This method enters limits (lower and upper) for aggregate net power
        consumption of the cluster within a specific period.
        It is often run at the begining of simulation. However, it is possible
        to call this method multiple times during the simulation to update 
        the peak power limits of the cluster.
        
        Parameters
        ----------
        start : datetime.datetime 
            Start of the period for which the limits are set.
        end : datetime.datetime
            End of the period for which the limits are set.
        step : datetime.timedelta
            Time resolution of the target period.
        limits : pandas.DataFrame
            Time indexed table indicating the lower and upper limits.
            index --> Identifier of time steps
            LB --> Lower bound of consumption limit at a particular time step
            UB --> Lower bound of consumption limit at a particular time step
        tolerance : float, optional
            It is possible to specify a tolerance range (kW) for violation of
            the given limits. If specified, the net consumption of the cluster
            is allowed to be larger than the upper limit or smaller than the 
            lower limit but such violation should not exceed 'tolerance'. The
            default is 0.

        Returns
        -------
        None.

        """

        roundedts = limits["TimeStep"].dt.round("S")

        _lb = pd.Series(limits["LB"].values, index=roundedts)
        _ub = pd.Series(limits["UB"].values, index=roundedts)

        n_of_steps = int((end - start) / step)
        timerange = [start + t * step for t in range(n_of_steps + 1)]

        lower = _lb.reindex(timerange)        
        upper = _ub.reindex(timerange)
        
        self.upper_limit = upper.fillna(upper.fillna(method="ffill"))
        self.lower_limit = lower.fillna(lower.fillna(method="ffill"))
        self.violation_tolerance = tolerance

    def reserve(self, ts, res_from, res_until, ev, cu, contract=None):
        """
        This method reserves a charging unit for an EV for a specific period.
        It is usually called in execution of reservation protocol. However, it 
        is called also in execution of arrival protocol in scenarios without
        advance reservations.
        

        Parameters
        ----------
        ts : datetime.datetime
            Current time (i.e., when the reservation is placed).
        res_from : datetime.datetime
            Start of the reservation period.
        res_until : datetime.datetime
            End of the reservation period.
        ev : ElectricVehicle
            Reserving electric vehicle.
        cu : ChargingUNit
            Reserved charging unit.
        contract : dictionary, optional
            datafev framework distinguishes two types of reservations.
            Simple reservations only indicate a reservation period. 
            Smart reservations include schedules and optionally price details.
            The default is None.

        Returns
        -------
        None.

        """

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
        """
        This method cancels a particular reservation. It is usually called 
        in execution of departure protocols. 

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        reservation_id : str
            Identifier of the reservation to be cancelled.

        Returns
        -------
        None.

        """
        self.re_dataset.loc[reservation_id, "Cancelled At"] = ts
        self.re_dataset.loc[reservation_id, "Active"] = False
        
    def uncontrolled_supply(self, ts, step):
        """
        This method is run to execute the uncontrolled charging behavior.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        step : datetime.timedelta
            Length of time step..

        Returns
        -------
        None.
        """
        
        for cu_id, cu in self.chargers.items():
            if cu.connected_ev != None:
                cu.uncontrolled_supply(ts, step)

    def enter_data_of_incoming_vehicle(self, ts, ev, cu):
        """
        This method adds an entry in cc_dataset for the incoming EV. It is 
        called in execution of arrival protocols.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        ev : ElectricVehicle
            Electric vehicle object.
        cu : ChargingUnit
            Charging unit object.

        Returns
        -------
        None.

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
        """
        This method enters the data about the charging event to the cc_dataset 
        for an outgoing EV. It is usually called in execution of departure 
        protocols.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        ev : ElectricVehicle
            Electric vehicle object.

        Returns
        -------
        None.

        """

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

    def query_actual_schedule(self, start, end, step):
        """
        This method retrieves the aggregate schedule of the cluster for a 
        specific query (future) period considering actual schedules of the 
        charging units. It is usually run in execution of reservation protocol.
        

        Parameters
        ----------
        start : datetime.datetime
            Start of queried period (EV's estimated arrival at this cluster).
        end : datetime.datetime
            End of queried period (EV's estimated arrival at this cluster).
        step : datetime.timedelta
            Time resolution in the queried period.

        Returns
        -------
        cc_sch : pandas.Series
            Time indexed power schedule of cluster.
            Each index indicates a time step in the queried period.
            Each value indicates how much power the cluster should consume
            (kW) during a particular time step (i.e. index value).

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

    def query_actual_occupation(self, ts):
        """
        This function identifies currently occupied chargers. It  is usually
        called in execution of arrival protocols.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.

        Returns
        -------
        nb_of_connected_cu : int
            Number of occupied chargers.

        """

        nb_of_connected_cu = 0
        for cu_id, cu in self.chargers.items():
            if cu.connected_ev != None:
                nb_of_connected_cu += 1
        return nb_of_connected_cu

    def query_availability(self, start, end, step):
        """
        This function creates a dataframe containing the data of the 
        available chargers for a specific period. It is usually called in 
        execution of reservation protocols.
        

        Parameters
        ----------
        start : datetime.datetime
            Start of queried period (EV's estimated arrival at this cluster).
        end : datetime.datetime
            End of queried period (EV's estimated arrival at this cluster).
        step : datetime.timedelta
            Time resolution in the queried period.

        Returns
        -------
        available_chargers : pandas.DataFrame
            Table containing the data of available chargers.
            index--> string identifier 
            max p_ch --> maximum charge power
            max p_ds --> maximum discharge power
            eff --> power conversion efficiency of the charger.

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


    def analyze_import_profile(self, start, end, step):
        """
        This method is run after simulation to analyze the power consumption
        profile of the chargers in the cluster.

        Parameters
        ----------
        start : datetime
            Start of the period of investigation.
        end : datetime
            End of the period of investigation.
        step : timedelta
            Time resolution of the period of investiation.

        Returns
        -------
        df : pandas.DataFrame
            Table contining the power consumption profiles of chargers.
            Each index indicates a time step in the investigated period.
            Columns indicate the charger identifiers.
            The value of a single cell in this table indicates the power (kW) 
            that the a particular charger imports (p>0) or exports (p<0) from 
            or to the grid in a particular time step.

        """
        
        df = pd.DataFrame(index=pd.date_range(start=start, end=end, freq=step))
        for cu_id, cu in self.chargers.items():
            df[cu_id] = (cu.consumed_power.reindex(df.index)).fillna(0)
        return df

    def analyze_occupation_profile(self, start, end, step):
        """
        This method is run after simulation to analyze the occupation profile 
        of the cluster.

        Parameters
        ----------
        start : datetime
            Start of the period of investigation.
        end : datetime
            End of the period of investigation.
        step : timedelta
            Time resolution of the period of investiation.

        Returns
        -------
        record : pandas.Series
            Time indexed occupation record.
            Each index indicates a time step in the investigated period.
            Columns indicate the charger identifiers
            The value of a single cell in this table indicates whether a 
            particular charger has (1) or has no (0) connected EV a particular 
            time step.

        """
              
        df = pd.DataFrame(index=pd.date_range(start=start, end=end, freq=step))
        for cu_id, cu in self.chargers.items():
            df[cu_id] = (
                cu.occupation_record(start, end, step).reindex(df.index)
            ).fillna(0)
        return df

    def export_results(self, start, end, step, xlfile):
        """
        This method is run after simulation to analyze the simulation results 
        related to the  cluster. It exports simulation results to an xlsx file.

        Parameters
        ----------
        start : datetime.datetime
            Start of the period of investigation.
        end : datetime.datetime
            End of the period of investigation.
        step : datetime.timedelta
            Time resolution of the period of investiation.
        xlfile : str
            The name of the xlsx file to export results.

        Returns
        -------
        None.

        """

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
