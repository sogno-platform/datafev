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


class ElectricVehicle(object):
    """
    Simulation model of electric vehicles.
    """

    def __init__(
        self,
        carID,
        bCapacity,
        p_max_ch=50,
        p_max_ds=50,
        minSoC=0.0,
        maxSoC=1.0,
        pow_soc_table=None,
    ):
        """
        ElectricVehicle objects are initialized by relevant data.
        

        Parameters
        ----------
        carId : str
            Identifier of the EV.
        bCapacity : float
            Energy capacit of EV battery (kWh).
        p_max_ch : float
            Maximum charge power EV battery can handle (kW).
        p_max_ds : float
            Maximum discharge power EV battery can handle (kW).
        minSoC : float
            Minimum SOC that EV battery is allowed to reduce to (0<=minsoc<=1).
        maxSoC : float
            Maximum SOC that EV battery is allowed to reach to (0<=maxsoc<=1).
        pow_soc_table : dataframe
            The table that contains the power capability limits of EV batteries
            In practice, power that can be charged/discharged by EV batteries 
            change.

        Returns
        -------
        None.

        """

        self.type = "Vehicle"
        self.vehicle_id = carID
        self.bCapacity = bCapacity * 3600  # kWh to kWs

        self.p_max_ch = p_max_ch
        self.p_max_ds = p_max_ds
        self.pow_soc_table = pow_soc_table

        self.minSoC = minSoC
        self.maxSoC = maxSoC
        self.soc = {}
        self.v2g = {}
        self.g2v = {}

    def charge(self, ts, tdelta, p_in):
        """
        The method to enter the charging data to EV.

        Parameters
        ----------
        ts : datetime
            Current time.
        tdelta : timedelta
            Length of time step.
        p_in : float
            
            Charge power to starting from ts for tdelta by p_in:
                p_in>0 charging,
                p_in<0 discharging.

        Returns
        -------
        None.

        """

        self.soc[ts + tdelta] = self.soc[ts] + p_in * tdelta.seconds / self.bCapacity
        self.v2g[ts] = -p_in if p_in < 0 else 0
        self.g2v[ts] = p_in if p_in > 0 else 0
