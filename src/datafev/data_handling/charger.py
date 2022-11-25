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


class ChargingUnit(object):
    """
    Simulation model of EV chargers.
    """

    def __init__(self, cu_id, p_max_ch, p_max_ds, efficiency):
        """
        EV chargers are defined by power capability parameters.

        Parameters
        ----------
        cu_id : str
            Identifier of the charger.
        p_max_ch : float
            Maximum charge power that can be supplied to EV battery (kW).
        p_max_ds : float
            Maximum discharge power that can be withdrawn from EV battery (kW).
        efficiency : float
            Power conversion efficiency (0<efficiency<1).
            This affects the power that the charger withdraw/injects from/to
            grid.

        Returns
        -------
        None.

        """

        self.type = "CU"
        self.id = cu_id
        self.p_max_ch = p_max_ch
        self.p_max_ds = p_max_ds
        self.eff = efficiency

        self.connected_ev = None
        self.connection_dataset = pd.DataFrame(
            columns=["EV ID", "Connection", "Disconnection"]
        )
        self.supplied_power = pd.Series(dtype=float)
        self.consumed_power = pd.Series(dtype=float)

        self.schedule_pow = {}
        self.schedule_soc = {}

    def connect(self, ts, ev):
        """
        This method connects an EV to the charger. It is called in 
        execution of arrival routines.

        Parameters
        ----------
        ts : datetime.datetime
            Connection time.
        ev : ElectricVehicle
            Connected EV object.

        Returns
        -------
        None.

        """
        self.connected_ev = ev
        ev.connected_cu = self

        dataset_ind = len(self.connection_dataset) + 1
        self.connection_dataset.loc[dataset_ind, "EV ID"] = ev.vehicle_id
        self.connection_dataset.loc[dataset_ind, "Connection"] = ts

    def disconnect(self, ts):
        """
        This method disconnects the connected EV from the charger. It is called
        in execution of departure routines.

        Parameters
        ----------
        ts : datetime.datetime
            Disconnection time.

        Returns
        -------
        None.

        """
        self.connected_ev.connected_cu = None
        self.connected_ev = None
        dataset_ind = max(self.connection_dataset.index)
        self.connection_dataset.loc[dataset_ind, "Disconnection"] = ts

    def supply(self, ts, tdelta, p):
        """
        This method triggers 'charge' method of the connected EV. 
        The connected EV charges with 'p' power during current time step.
        The charger consumes (for p>0) or inject (for p<0) from/to grid.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        tdelta : datetime.timedelta
            Length of time step.
        p : float 
            Charge power (kW).
            p>0 indicates EV charging and power consumption from the grid.
            p<0 indicates EV discharging and power injection to the grid.

        Returns
        -------
        None.

        """
        self.connected_ev.charge(ts, tdelta, p)
        self.supplied_power[ts] = p
        self.consumed_power[ts] = p / self.eff if p > 0 else p * self.eff

    def set_schedule(self, ts, schedule_pow, schedule_soc):
        """
        This method assigns a charging schedule to the charger.

        Parameters
        ----------
        ts : datetime.datetime
            Current time.
        schedule_pow : pandas.Series
            Time indexed power schedule.
            Each index indicates a time step in the scheduling horizon.
            Each value indicates how much power the charger should supply
            (kW) during a particular time step (i.e. index value). 
        schedule_soc : pandas.Series
            Time indexed SOC schedule.
            Each index indicates a time step in the scheduling horizon.
            Each value indicates the SOC (0<soc<1) that the connected EV 
            battery should achieve by a partiuclar time step (i.e. index). 

        Returns
        -------
        None.

        """

        self.schedule_pow[ts] = schedule_pow
        self.schedule_soc[ts] = schedule_soc
        self.set_active_schedule(ts)

    def set_active_schedule(self, ts):
        """
        A single charger may be assigned with multiple schedules. For instance,
        it may have a schedule for the connected vehicle and another schedule
        for an EV that has reservation in the future. This method marks the one 
        that has been set at 'ts' as the 'active schedule' so that it is 
        considered to be 'the schedule' for the current charging event.

        Parameters
        ----------
        ts : datetime.datetime
            Time at which the schedule that should be activated was set.

        Returns
        -------
        None.

        """
        self.active_schedule_instance = ts

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

        # Current SOC of the EV
        ev_soc = self.connected_ev.soc[ts]

        # If the current SOC is smaller than 1
        # Then EV would charge with max feasible power
        if ev_soc < 1:

            # EV battery capacity
            ev_bcap = self.connected_ev.bCapacity

            # Limit due to the battery capacity of EV
            lim_ev_batcap = (1 - ev_soc) * ev_bcap

            # Limit due to the charger power capability
            lim_ch_pow = self.p_max_ch * step.seconds

            if type(self.connected_ev.pow_soc_table) != type(None):

                # The EV battery has a specific charger power-SOC dependency
                # limiting the power transfer
                table = self.connected_ev.pow_soc_table
                soc_range = (
                    table[(table["SOC_LB"] <= ev_soc) & (ev_soc < table["SOC_UB"])]
                ).index[0]

                # Limit due to the SOC dependency of charge power
                p_max = table.loc[soc_range, "P_UB"]
                lim_ev_socdep = p_max * step.seconds
                e_max = min(lim_ev_batcap, lim_ch_pow, lim_ev_socdep)

            else:
                # The power transfer is only limited by the charger's power
                # and battery capacity
                e_max = min(lim_ev_batcap, lim_ch_pow)

            # Average charge power during the simulation step
            p_avr = e_max / step.seconds

        # If the current SOC is 1
        # Then the EV would not charge
        else:
            p_avr = 0

        # Execution of the uncontrolled behavior in the simulation
        self.supply(ts, step, p_avr)

    def occupation_record(self, start, end, step):
        """
        This method is run after simulation to analyze the occupation profile 
        of the charger.

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
            Each value indicates the number of connected EVs (0 or 1) during 
            a particular time step (i.e. index value).

        """
        period = pd.date_range(start=start, end=end, freq=step)
        connections = pd.DataFrame(index=period)
        connections.loc[:, :] = 0
        for _id, con in self.connection_dataset.iterrows():
            con_start = con["Connection"]
            con_end = con["Disconnection"]
            connections.loc[con_start:con_end, _id] = 1
        record = connections.sum(axis=1)
        return record
