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

from datafev.routines.simple_reservation.reservation import *
from datafev.routines.simple_reservation.arrival import *
from datafev.routines.departure import *
from datafev.routines.charging_control.decentralized_llf import charging_routine


def main():
    """
    This tutorial aims to show the use of datafev framework in an example scenario with:
        - simple reservations where EVs reserve chargers before their arrival to clusters,
        - and smart charging where clusters' power consumption profiles are controlled based on least-laxity-first algorithm.
    """

    ########################################################################################################################
    ########################################################################################################################
    # SIMULATION SET-UP

    # Importing the simulation input inputs
    input_file = pd.ExcelFile("inputs/example_02.xlsx")
    input_fleet = pd.read_excel(input_file, "Fleet")
    input_cluster1 = pd.read_excel(input_file, "Cluster1")
    input_capacity1 = pd.read_excel(input_file, "Capacity1")
    # Getting the path of the input excel file
    abs_path_input = os.path.abspath(input_file)
    print("Scenario inputs are taken from the xlsx file:", abs_path_input)
    print()

    # Printing the input parameters of the charging infrastructure
    print("The system consists of one charger cluster with the following chargers:")
    print(input_cluster1)
    print()

    # Printing the input parameters related to power consumption limits
    print(
        "Net consumption of the cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print(input_capacity1)
    print()

    # Printing the input parameters related to the EV fleet behavior
    print(
        "The reservation requests of the EVs (as declared in reservation) are given in the following:"
    )
    print(
        input_fleet[
            [
                "ev_id",
                "Reservation Time",
                "Estimated Arrival Time",
                "Estimated Departure Time",
            ]
        ]
    )
    print()
    print()

    # Additional parameters for reservation management
    soc_dev = {"cluster1": 0}
    arr_del = {"cluster1": timedelta(seconds=0)}
    dep_del = {"cluster1": timedelta(seconds=0)}
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
    print()

    # Simulation parameters
    sim_start = datetime(2022, 1, 8, 7)
    sim_end = datetime(2022, 1, 8, 9)
    sim_length = sim_end - sim_start
    sim_step = timedelta(minutes=5)
    sim_horizon = [sim_start + t * sim_step for t in range(int(sim_length / sim_step))]
    print("Simulation starts at:", sim_start)
    print("Simulation fininshes at:", sim_end)
    print("Length of one time step in simulation:", sim_step)
    print()
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # INITIALIZATION OF THE SIMULATION

    fleet = EVFleet("test_fleet", input_fleet, sim_horizon)
    cluster1 = ChargerCluster("cluster1", input_cluster1)
    system = MultiClusterSystem("multicluster")
    system.add_cc(cluster1)
    cluster1.enter_power_limits(sim_start, sim_end, sim_step, input_capacity1)

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
        reservation_routine(ts, sim_step, system, fleet, traffic_forecast)

        # The arrival routine for the EVs incoming to the charger clusters
        arrival_routine(ts, sim_step, fleet)

        # Real-time charging control of the charger clusters is based on the decentralized least laxity first
        charging_routine(ts, sim_step, system)

    print("Simulation finished...")
    print()
    print()
    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # ANALYSIS OF THE SIMULATION RESULTS

    # Displaying reservation and connection data of cluster1
    print("Reservation data")
    print(cluster1.re_dataset.iloc[:, 1:6])
    print()

    print("Connection data")
    print(cluster1.cc_dataset[["EV ID", "Arrival Time", "Leave Time"]])
    print()

    # Printing the results to excel files
    system.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example02_clusters.xlsx"
    )
    fleet.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example02_fleet.xlsx"
    )
    # Path of the output excel file
    abs_path_output_cluster = os.path.abspath("results/example02_clusters.xlsx")
    abs_path_output_fleet = os.path.abspath("results/example02_fleet.xlsx")
    print("Scenario results are saved to the following xlsx files:")
    print(abs_path_output_cluster)
    print(abs_path_output_fleet)
    print()

    # Line charts to visualize cluster loading and occupation profiles
    fig1 = system.visualize_cluster_loading(sim_start, sim_end, sim_step)
    fig2 = system.visualize_cluster_occupation(sim_start, sim_end, sim_step)
    plt.show()

    ########################################################################################################################
    ########################################################################################################################


if __name__ == "__main__":
    main()
