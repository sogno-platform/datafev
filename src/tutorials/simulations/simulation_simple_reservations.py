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
from pyomo.environ import SolverFactory
import matplotlib.pyplot as plt

from datafev.datahandling.fleet import EVFleet
from datafev.datahandling.cluster import ChargerCluster
from datafev.datahandling.multicluster import MultiClusterSystem

from datafev.protocols.simplereservation.reservation import *
from datafev.protocols.simplereservation.arrival import *
from datafev.protocols.departure import *
from datafev.protocols.chargingcontrol.decentralized_llf import charging_protocol

# Simulation parameters
sim_start = datetime(2022, 1, 8, 7)
sim_end = datetime(2022, 1, 8, 20)
sim_length = sim_end - sim_start
sim_step = timedelta(minutes=5)
sim_horizon = [sim_start + t * sim_step for t in range(int(sim_length / sim_step))]
solver = SolverFactory("gurobi")  # User has to specify the suitable optimization solver
opt_horizon = timedelta(minutes=10)

# Simulation inputs
inputs = pd.ExcelFile("scenario_with_reservation.xlsx")
input_fleet = pd.read_excel(inputs, "Fleet")
input_cluster1 = pd.read_excel(inputs, "Cluster1")
input_capacity1 = pd.read_excel(inputs, "Capacity1")
input_cluster2 = pd.read_excel(inputs, "Cluster2")
input_capacity2 = pd.read_excel(inputs, "Capacity2")
input_cluster3 = pd.read_excel(inputs, "Cluster3")
input_capacity3 = pd.read_excel(inputs, "Capacity3")
input_capacityT = pd.read_excel(inputs, "CapacityT")

price = pd.read_excel(inputs, "Price")
price_t_steps = price["TimeStep"].round("S")
tou_tariff = pd.Series(price["Price"].values, index=price_t_steps)

#######################################################################
# Multicluster charging system and EV fleet
cluster1 = ChargerCluster("cluster1", input_cluster1)
cluster2 = ChargerCluster("cluster2", input_cluster2)
cluster3 = ChargerCluster("cluster3", input_cluster3)
system = MultiClusterSystem("multicluster")
system.add_cc(cluster1)
system.add_cc(cluster2)
system.add_cc(cluster3)
system.set_tou_price(tou_tariff, sim_step)

fleet = EVFleet("test_fleet", input_fleet, sim_horizon)
#######################################################################

#######################################################################
# Additional parameters for charging management protocol
cluster1.set_peak_limits(sim_start, sim_end, sim_step, input_capacity1)
cluster2.set_peak_limits(sim_start, sim_end, sim_step, input_capacity2)
cluster3.set_peak_limits(sim_start, sim_end, sim_step, input_capacity3)
system.set_peak_limits(sim_start, sim_end, sim_step, input_capacityT)

rho_y = {"cluster1": 1, "cluster2": 1, "cluster3": 1}
rho_eps = {"cluster1": 1, "cluster2": 1, "cluster3": 1}
penalty_parameters = {"rho_y": rho_y, "rho_eps": rho_eps}
#######################################################################

#######################################################################
# Additional parameters for reservation management
soc_dev = {"cluster1": 0, "cluster2": 0, "cluster3": 0}
arr_del = {
    "cluster1": timedelta(seconds=0),
    "cluster2": timedelta(seconds=0),
    "cluster3": timedelta(seconds=0),
}
dep_del = {
    "cluster1": timedelta(seconds=0),
    "cluster2": timedelta(seconds=0),
    "cluster3": timedelta(seconds=0),
}
traffic_forecast = {"soc_dec": soc_dev, "arr_del": arr_del, "dep_del": dep_del}
#######################################################################

#######################################################################
# Simulation starts

np.random.seed(0)  # Same random behavior in all runs
for ts in sim_horizon:
    print("Simulating time step:", ts)

    # The departure protocol for the EVs leaving the chargerg clusters
    departure_protocol(ts, fleet)

    # The reservation protocol (including routing to a cluster in the multicluster system) for the EVs
    reservation_protocol(ts, sim_step, system, fleet, traffic_forecast)

    # The arrival protocol for the EVs incoming to the charger clusters
    arrival_protocol(ts, sim_step, fleet)

    # Real-time charging control of the charger clusters is based on the decentralized least laxity first
    charging_protocol(ts, sim_step, system)

# Simulation ends
#######################################################################

#######################################################################
# Printing the results to excel files
system.export_results(
    sim_start, sim_end, sim_step, "result_simplereservation_clusters.xlsx"
)
fleet.export_results(
    sim_start, sim_end, sim_step, "result_simplereservation_fleet.xlsx"
)
#######################################################################

print("Aggregate consumption and occupation profiles of the clusters are plotted")
clu1_pow = cluster1.import_profile(sim_start, sim_end, sim_step).sum(axis=1)
clu2_pow = cluster2.import_profile(sim_start, sim_end, sim_step).sum(axis=1)
clu3_pow = cluster3.import_profile(sim_start, sim_end, sim_step).sum(axis=1)

clu1_occ = cluster1.occupation_profile(sim_start, sim_end, sim_step).sum(axis=1)
clu2_occ = cluster2.occupation_profile(sim_start, sim_end, sim_step).sum(axis=1)
clu3_occ = cluster3.occupation_profile(sim_start, sim_end, sim_step).sum(axis=1)

fig1, ax1 = plt.subplots(2, 1, tight_layout=True)
fig1.suptitle("cluster1")
clu1_occ.plot(ax=ax1[0], title="Number of connceted EVs")
clu1_pow.plot(ax=ax1[1], title="Aggregate consumption")
cluster1.upper_limit[sim_start:sim_end].plot(ax=ax1[1], label="Constraint")

fig2, ax2 = plt.subplots(2, 1, tight_layout=True)
fig2.suptitle("cluster2")
clu2_occ.plot(ax=ax2[0], title="Number of connected EVs")
clu2_pow.plot(ax=ax2[1], title="Aggregate consumption")
cluster2.upper_limit[sim_start:sim_end].plot(ax=ax2[1], label="Constraint")

fig3, ax3 = plt.subplots(2, 1, tight_layout=True)
fig3.suptitle("cluster3")
clu3_occ.plot(ax=ax3[0], title="Number of EVs")
clu3_pow.plot(ax=ax3[1], title="Aggregate Consumption")
cluster3.upper_limit[sim_start:sim_end].plot(ax=ax3[1], label="Constraint")

plt.show()
