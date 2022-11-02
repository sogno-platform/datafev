class ElectricVehicle(object):
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
        This method initializes the car objects.
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
        ts    : datetime
        tdelta: timedelta
        p_in  : float
        
        Charge starting from ts for tdelta by p_in
        p_in>0 charging
        p_in<0 discharging
        """
        self.soc[ts + tdelta] = self.soc[ts] + p_in * tdelta.seconds / self.bCapacity
        self.v2g[ts] = -p_in if p_in < 0 else 0
        self.g2v[ts] = p_in if p_in > 0 else 0


#    def request_available_charger_list(self,server,tdelta,advance_reservation=False):
#
#        if advance_reservation:
#            period_start=self.t_arr_est
#            period_end  =self.t_dep_est
#            period_step =tdelta
#        else:
#            period_start=self.t_arr_real
#            period_end  =self.t_dep_est
#            period_step =tdelta
#
#        available_chargers=server.get_available_chargers(period_start,period_end,period_step)
#
#        return available_chargers
