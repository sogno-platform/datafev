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

import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pyomo.environ import SolverFactory

from datafev.data_handling.fleet import EVFleet
from datafev.data_handling.cluster import ChargerCluster
from datafev.data_handling.multi_cluster import MultiClusterSystem

from datafev.routines.smart_reservation.reservation import *
from datafev.routines.smart_reservation.arrival import *
from datafev.routines.departure import *
from datafev.routines.charging_control.decentralized_milp import charging_routine


def main():
    """
    This tutorial aims to show the use of datafev framework in an example scenario with:
        - smart reservations where EVs routing to clusters are managed,
        - and smart charging where clusters' power consumption profiles are optimized.
    """

    ########################################################################################################################
    ########################################################################################################################
    # SIMULATION SET-UP

    # Importing the simulation input inputs
    input_file = pd.ExcelFile("inputs/example_03.xlsx")
    input_fleet = pd.read_excel(input_file, "Fleet")
    input_cluster1 = pd.read_excel(input_file, "Cluster1")
    input_capacity1 = pd.read_excel(input_file, "Capacity1")
    input_cluster2 = pd.read_excel(input_file, "Cluster2")
    input_capacity2 = pd.read_excel(input_file, "Capacity2")
    input_cluster3 = pd.read_excel(input_file, "Cluster3")
    input_capacity3 = pd.read_excel(input_file, "Capacity3")
    # Getting the path of the input excel file
    abs_path_input = os.path.abspath(input_file)
    print("Scenario inputs are taken from the xlsx file:", abs_path_input)
    print()

    # Printing the input parameters of the charging infrastructure
    print("The system consists of three charger clusters with the following chargers:")
    print("cluster1")
    print(input_cluster1)
    print("cluster2")
    print(input_cluster2)
    print()
    print(input_cluster3)
    print()

    # Printing the input parameters related to power consumption limits
    print(
        "Net consumption of each  cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print("cluster1")
    print(input_capacity1)
    print("cluster2")
    print(input_capacity2)
    print("cluster3")
    print(input_capacity3)
    print()
    print()

    # Printing the input parameters related to the EV fleet behavior
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

    # Printing the input parameters related to the electricity price
    print(
        "All clusters in the system purchase electricity based on a time-of-use tariff (taken from input xlsx"
    )
    price = pd.read_excel(input_file, "Price")
    price_t_steps = price["TimeStep"].round("S")
    tou_tariff = pd.Series(price["Price (per/kWh)"].values, index=price_t_steps)
    print(tou_tariff)
    print()

    # Simulation parameters
    sim_start = datetime(2022, 1, 8, 7)
    sim_end = datetime(2022, 1, 8, 12)
    sim_length = sim_end - sim_start
    sim_step = timedelta(minutes=5)
    sim_horizon = [sim_start + t * sim_step for t in range(int(sim_length / sim_step))]
    print("Simulation starts at:", sim_start)
    print("Simulation fininshes at:", sim_end)
    print("Length of one time step in simulation:", sim_step)
    print()

    # Optimization parameters
    solver = SolverFactory(
        "cplex"
    )  # Users have to declare an optimization solver that exists their file system
    print(
        "The management strategy tested in this tutorial includes optimization algorithms"
    )
    print(
        "The solver to solve the optimization problems must be defined by the user. This test uses cplex."
    )
    print()
    print()

    # Additional parameters for reservation management
    soc_dev = {"cluster1": 0, "cluster2": 0, "cluster3": 0}
    arr_del = {
        "cluster1": timedelta(seconds=0),
        "cluster2": timedelta(seconds=300),
        "cluster3": timedelta(seconds=0),
    }
    dep_del = {
        "cluster1": timedelta(seconds=0),
        "cluster2": timedelta(seconds=0),
        "cluster3": timedelta(seconds=0),
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
    print("For the EVs driving to cluster 3...")
    print("...the arrival would delay by:", arr_del["cluster3"])
    print("...the departure would delay by:", dep_del["cluster3"])
    print("...the arrival SOC would change by:", soc_dev["cluster3"])
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
    # INITIALIZATION OF THE SIMULATION

    fleet = EVFleet("test_fleet", input_fleet, sim_horizon)
    cluster1 = ChargerCluster("cluster1", input_cluster1)
    cluster2 = ChargerCluster("cluster2", input_cluster2)
    cluster3 = ChargerCluster("cluster3", input_cluster3)
    system = MultiClusterSystem("multicluster")
    system.add_cc(cluster1)
    system.add_cc(cluster2)
    system.add_cc(cluster3)
    cluster1.enter_power_limits(sim_start, sim_end, sim_step, input_capacity1)
    cluster2.enter_power_limits(sim_start, sim_end, sim_step, input_capacity2)
    cluster3.enter_power_limits(sim_start, sim_end, sim_step, input_capacity3)
    system.enter_tou_price(tou_tariff, sim_step)

    print("Simulation scenario has been initalized")
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # DYNAMIC SIMULATION

    print("Simulation started...")

    for ts in sim_horizon:
        print("Simulating time step:", ts)
        
        # The departure routine for the EVs leaving the chargerg clusters
        departure_routine(ts, fleet)

        # The reservation routine (including routing to a cluster in the multicluster system) for the EVs
        reservation_routine(
            ts, sim_step, system, fleet, solver, traffic_forecast, arbitrage_coeff=0.1
        )

        # The arrival routine for the EVs incoming to the charger clusters
        arrival_routine(ts, sim_step, fleet)

        # Real-time charging control of the charger clusters is based on the decentralized MILP-based protocol
        charging_routine(
            ts, sim_step, timedelta(minutes=10), system, solver, penalty_parameters
        )

    print("Simulation finished...")
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # ANALYSIS OF THE SIMULATION RESULTS

    # Print the cluster and fleet results to excel
    system.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example03_cluster.xlsx"
    )
    fleet.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example03_fleet.xlsx"
    )
    # Path of the output excel file
    abs_path_output_cluster = os.path.abspath("results/example03_cluster.xlsx")
    abs_path_output_fleet = os.path.abspath("results/example03_fleet.xlsx")
    print("Scenario results are saved to the following xlsx files:")
    print(abs_path_output_cluster)
    print(abs_path_output_fleet)
    print()

    # Line charts to visualize cluster loading profiles
    fig1 = system.visualize_cluster_loading(sim_start, sim_end, sim_step)

    # Parallel coordinate plots to visualise fulfillment metrics
    fig2 = system.visualize_fulfillment_rates(fleet)
    plt.show()

    ########################################################################################################################
    ########################################################################################################################


if __name__ == "__main__":
    main()
