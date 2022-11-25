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

from datetime import datetime, timedelta
from itertools import product
import pandas as pd
import numpy as np


class MultiClusterSystem(object):
    """
    A multi-cluster system consists of X number of charger clusters. It is 
    considered to be the higher aggregation level in the datafev framework. 
    It contains multiple controlling entities each being responsible for 
    management of a cluster. 
    """

    def __init__(self, system_id):
        """
        Multi-cluster systems are defined by the clusters that they consist of.

        Parameters
        ----------
        system_id : str
            String identifier of the multi-cluster system.

        Returns
        -------
        None.

        """
        self.type = "CS"
        self.id = system_id
        self.clusters = {}

    def add_cc(self, cluster):
        """
        This method is run at initialization of the multicluster system object.
        It adds clusters to the self.clusters dictionary.

        Parameters
        ----------
        cluster : ChargerCluster
            A charger clusterobject.

        Returns
        -------
        None.

        """

        self.clusters[cluster.id] = cluster
        cluster.station = self

    def enter_tou_price(self, series, resolution):
        """
        This method enters electricity price data as time series in the desired
        resolution. It is usually called before running simulation.

        Parameters
        ----------
        series : pandas.Series
            Electricity price data.
        resolution : int
            Desired resolution.

        Returns
        -------
        None.
        
        """

        start = min(series.index)
        end = max(series.index) + timedelta(hours=1)
        n_of_steps = int((end - start) / resolution)
        timerange = [start + t * resolution for t in range(n_of_steps + 1)]
        temp_ser = series.reindex(timerange)

        self.tou_price = temp_ser.fillna(temp_ser.fillna(method="ffill"))

    def enter_power_limits(self, start, end, step, peaklimits):
        """
        This method enters limits (lower and upper) for aggregate net power
        consumption of the multi-cluster system within a specific period.
        It is often run at the begining of simulation. However, it is possible
        to call this method multiple times during the simulation to update 
        the peak power limits of the system.
        
        Parameters
        ----------
        start : datetime.datetime 
            Start of the period for which the limits are set.
        end : datetime.datetime
            End of the period for which the limits are set.
        step : datetime.timedelta
            Time resolution of the target period.
        limits : pandas.DataFrame
            Time indexed table indicating the lower and upper limits:
                index --> Identifier of time steps,
                LB --> Lower bound of consumption limit at a particular time step,
                UB --> Upper bound of consumption limit at a particular time step.

        Returns
        -------
        None.
        
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

    def query_actual_schedules(self, ts, t_delta, horizon):
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
        cc_sch : pandas.DataFrame
            Time indexed power schedules of clusters.
            Each index indicates a time step in the queried period.
            Each column indicates a charger cluster.
            A cell value indicateshow much power the cluster should consume
            (kW) during a particular time step (i.e. index value).

        """

        time_index = pd.date_range(start=ts, end=ts + horizon - t_delta, freq=t_delta)
        clusterschedules = pd.DataFrame(index=time_index)

        for cc_id, cc in self.clusters.items():
            cc_sch = cc.query_actual_schedules(ts, t_delta, horizon)
            clusterschedules[cc_id] = (cc_sch.sum(axis=1)).copy()

        return clusterschedules

    def query_availability(self, start, end, step, deviations):
        """
        This function creates a dataframe containing the data of the 
        available chargers for a specific period. It is usually called in 
        execution of reservation routines.
        

        Parameters
        ----------
        start : datetime.datetime
            Start of queried period.
        end : datetime.datetime
            End of queried period.
        step : datetime.timedelta
            Time resolution in the queried period.
        deviations : dict
            Deviations in estimated arrival/departure times. These data are 
            obtained from the traffic forecast if availble. It
            

        Returns
        -------
        available_chargers : pandas.DataFrame
            Table containing the data of available chargers in the system:
                index --> string identifier of the charger
                cluster --> string identifier of the cluster
                max p_ch --> maximum charge power
                max p_ds --> maximum discharge power
                eff --> power conversion efficiency of the charger.

        
        """

        available_chargers = pd.DataFrame(
            columns=["cluster", "max p_ch", "max p_ds", "eff"], dtype=np.float16
        )

        for cc_id, cc in self.clusters.items():

            estimated_arr = (
                start + deviations["arr_del"][cc_id]
            )  # estimated arrival time if ev goes to cc
            estimated_dep = (
                end + deviations["dep_del"][cc_id]
            )  # estimated departure time if ev goes to cc
            cc_available_chargers = cc.query_availability(
                estimated_arr, estimated_dep - step, step
            )

            for cu_id in cc_available_chargers.index:

                available_chargers.loc[cu_id, "cluster"] = cc_id
                available_chargers.loc[
                    cu_id, ["max p_ch", "max p_ds", "eff"]
                ] = cc_available_chargers.loc[cu_id]

        return available_chargers

    def uncontrolled_supply(self, ts, step):
        """
        This method is run to execute the uncontrolled charging behavior.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        step : datetime.timedelta
            Length of time step.

        Returns
        -------
        None.
        """

        for cc_id, cc in self.clusters.items():
            cc.uncontrolled_supply(ts, step)

    def export_results(self, start, end, step, xlfile):
        """
        This method is run after simulation to analyze the simulation results 
        related to the multi-cluster system. It exports simulation results to 
        an xlsx file.

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

            cluster_datasets = []
            con_cu_dict = {}
            occ_cu_dict = {}
            overall = pd.DataFrame(
                columns=[
                    "Net Consumption",
                    "Net G2V",
                    "Total V2G",
                    "Unfulfilled G2V",
                    "Unscheduled V2G",
                ]
            )

            for cc_id, cc in sorted(self.clusters.items()):

                ds = cc.cc_dataset.copy()
                cluster_datasets.append(ds)

                con_cu_dict[cc_id] = cc.analyze_consumption_profile(start, end, step)
                occ_cu_dict[cc_id] = cc.analyze_occupation_profile(start, end, step)

                unfulfilled_g2v_ser = ds["Scheduled G2V [kWh]"] - ds["Net G2V [kWh]"]
                unscheduled_v2g_ser = ds["Total V2G [kWh]"] - ds["Scheduled V2G [kWh]"]
                overall.loc[cc_id, "Unfulfilled G2V"] = (
                    unfulfilled_g2v_ser[unfulfilled_g2v_ser > 0]
                ).sum()
                overall.loc[cc_id, "Unscheduled V2G"] = (
                    unscheduled_v2g_ser[unscheduled_v2g_ser > 0]
                ).sum()
                overall.loc[cc_id, "Net Consumption"] = (
                    (con_cu_dict[cc_id].sum(axis=1)).sum() * step.seconds / 3600
                )
                overall.loc[cc_id, "Net G2V"] = ds["Net G2V [kWh]"].sum()
                overall.loc[cc_id, "Total V2G"] = ds["Total V2G [kWh]"].sum()

            datasets = pd.concat(cluster_datasets, ignore_index=True)
            datasets = datasets.sort_values(by=["Arrival Time"], ignore_index=True)
            datasets.to_excel(writer, sheet_name="Connection Dataset")

            consu_cu_df = pd.concat(con_cu_dict, axis=1)
            consu_cu_df.to_excel(writer, sheet_name="Consumption (Units)")
            (consu_cu_df.sum(level=0, axis=1)).to_excel(
                writer, sheet_name="Consumption (Aggregate)"
            )

            occup_cu_df = pd.concat(occ_cu_dict, axis=1)
            occup_cu_df.to_excel(writer, sheet_name="Occupation (Units)")
            (occup_cu_df.sum(level=0, axis=1)).to_excel(
                writer, sheet_name="Occupation (Aggregate)"
            )

            overall.loc["Total"] = overall.sum()
            overall.to_excel(writer, sheet_name="Overall")
