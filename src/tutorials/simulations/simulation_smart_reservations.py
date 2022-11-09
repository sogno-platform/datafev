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

from datafev.data_handling.fleet import EVFleet
from datafev.data_handling.cluster import ChargerCluster
from datafev.data_handling.multi_cluster import MultiClusterSystem

from datafev.protocols.smart_reservation.reservation import *
from datafev.protocols.smart_reservation.arrival import *
from datafev.protocols.departure import *
from datafev.protocols.charging_control.decentralized_milp import charging_protocol


def main():
    """
    This tutorial aims to show the use of datafev framework in an example scenario with
    smart reservations where EVs routing to clusters are managed
    smart charging where clusters' power consumption profiles are optimized.
    """

    ########################################################################################################################
    ########################################################################################################################
    # Simulation parameters
    print("Selecting the simulation parameters...")

    sim_start = datetime(2022, 1, 8, 7)
    sim_end = datetime(2022, 1, 8, 12)
    sim_length = sim_end - sim_start
    sim_step = timedelta(minutes=5)
    sim_horizon = [sim_start + t * sim_step for t in range(int(sim_length / sim_step))]
    print("Simulation starts at:", sim_start)
    print("Simulation fininshes at:", sim_end)
    print("Length of one time step in simulation:", sim_step)
    print()
    print()

    # Simulation inputs
    print("Scenario inputs  are taken from an xlsx file...")
    print()
    inputs = pd.ExcelFile("scenario_smart_reservation.xlsx")
    input_fleet = pd.read_excel(inputs, "Fleet")
    input_cluster1 = pd.read_excel(inputs, "Cluster1")
    input_capacity1 = pd.read_excel(inputs, "Capacity1")
    input_cluster2 = pd.read_excel(inputs, "Cluster2")
    input_capacity2 = pd.read_excel(inputs, "Capacity2")

    print("The system consists of two charger clusters with the following chargers:")
    print("cluster1")
    print(input_cluster1)
    print("cluster2")
    print(input_cluster2)
    print()
    print(
        "Net consumption of each  cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print("cluster1")
    print(input_capacity1)
    print("cluster2")
    print(input_capacity2)
    print()

    print(
        "The reservation requests of the EVs (as declared in reservation) are given in the following:"
    )
    print(
        input_fleet[
            ["Reservation Time", "Estimated Arrival Time", "Estimated Departure Time"]
        ]
    )
    print()
    print()

    print(
        "All clusters in the system purchase electricity based on a time-of-use tariff (taken from input xlsx"
    )
    price = pd.read_excel(inputs, "Price")
    price_t_steps = price["TimeStep"].round("S")
    tou_tariff = pd.Series(price["Price"].values, index=price_t_steps)
    print(tou_tariff)
    print()
    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Optimization parameters
    solver = SolverFactory(
        "gurobi"
    )  # Users have to declare an optimization solver that exists their file system
    print(
        "The management strategy tested in this tutorial includes optimization algorithms"
    )
    print(
        "The solver to solve the optimization problems must be defined by the user. This test uses Gurobi."
    )
    print()
    print()

    # Additional parameters for reservation management
    soc_dev = {"cluster1": 0, "cluster2": -0.01}
    arr_del = {
        "cluster1": timedelta(seconds=0),
        "cluster2": timedelta(seconds=300),
    }
    dep_del = {
        "cluster1": timedelta(seconds=0),
        "cluster2": timedelta(seconds=0),
    }
    traffic_forecast = {"soc_dec": soc_dev, "arr_del": arr_del, "dep_del": dep_del}

    print("The reservation protocol is executed before arrival of EVs.")
    print(
        "EV drivers declare their estimated arrival in the region of the simulated multi-cluster system"
    )
    print(
        "Traffic conditions for arriving at individual clusters may differ from each other. In the simulated case.."
    )
    print("For the EVs driving to cluster 1...")
    print("...the arrival would delay by:", arr_del["cluster1"])
    print("...the departure would delay by:", dep_del["cluster1"])
    print("...the arrival SOC would change by:", soc_dev["cluster1"])
    print("For the EVs driving to cluster 2...")
    print("...the arrival would delay by:", arr_del["cluster2"])
    print("...the departure would delay by:", dep_del["cluster2"])
    print("...the arrival SOC would change by:", soc_dev["cluster2"])
    print()

    # Additional parameters for charging management
    # Cost coefficients defining the trade-off between
    # i) deviating from individual EVs' optimal schedules
    # ii) violating power limits of clusters
    # in charging control
    rho_y = {"cluster1": 1, "cluster2": 1, "cluster3": 1}
    rho_eps = {"cluster1": 1, "cluster2": 1, "cluster3": 1}
    penalty_parameters = {"rho_y": rho_y, "rho_eps": rho_eps}

    print(
        "Cost coefficients of the objective function of charging control algorithm are:"
    )
    print(penalty_parameters)
    print(
        "Please check input parameters of the algorithm in 'algorithms/cluster/rescheduling_milp.py' for details"
    )
    print()
    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Initialization of the simulation model

    # Fleet behavior
    fleet = EVFleet("test_fleet", input_fleet, sim_horizon)

    # Multicluster charging system and EV fleet
    cluster1 = ChargerCluster("cluster1", input_cluster1)
    cluster2 = ChargerCluster("cluster2", input_cluster2)
    system = MultiClusterSystem("multicluster")
    system.add_cc(cluster1)
    system.add_cc(cluster2)

    # Power limits of individual clusters
    cluster1.enter_power_limits(sim_start, sim_end, sim_step, input_capacity1)
    cluster2.enter_power_limits(sim_start, sim_end, sim_step, input_capacity2)

    # TOU price for clusters' electricity consumption
    system.enter_tou_price(tou_tariff, sim_step)

    # Same random behavior (if randomness exists) in all runs
    np.random.seed(0)

    print("Simulation scenario has been initalized")
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Simulation

    print("Simulation started...")

    for ts in sim_horizon:
        print("Simulating time step:", ts)

        # The departure protocol for the EVs leaving the chargerg clusters
        departure_protocol(ts, fleet)

        # The reservation protocol (including routing to a cluster in the multicluster system) for the EVs
        reservation_protocol(
            ts, sim_step, system, fleet, solver, traffic_forecast, arbitrage_coeff=0.1
        )

        # The arrival protocol for the EVs incoming to the charger clusters
        arrival_protocol(ts, sim_step, fleet)

        # Real-time charging control of the charger clusters is based on the decentralized MILP-based protocol
        charging_protocol(
            ts, sim_step, timedelta(minutes=10), system, solver, penalty_parameters
        )

    print("Simulation finished...")
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Printing the results to excel files
    system.export_results(
        sim_start, sim_end, sim_step, "result_smartreservation_clusters.xlsx"
    )
    fleet.export_results(
        sim_start, sim_end, sim_step, "result_smartreservation_fleet.xlsx"
    )
    print("Simulation results have been exported to excel files.")
    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Plotting the results
    clu1_pow = cluster1.analyze_consumption_profile(sim_start, sim_end, sim_step).sum(
        axis=1
    )
    clu2_pow = cluster2.analyze_consumption_profile(sim_start, sim_end, sim_step).sum(
        axis=1
    )

    clu1_occ = cluster1.analyze_occupation_profile(sim_start, sim_end, sim_step).sum(
        axis=1
    )
    clu2_occ = cluster2.analyze_occupation_profile(sim_start, sim_end, sim_step).sum(
        axis=1
    )

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

    print("Aggregate consumption and occupation profiles of the clusters are plotted")

    plt.show()
    ########################################################################################################################
    ########################################################################################################################


if __name__ == "__main__":
    main()
