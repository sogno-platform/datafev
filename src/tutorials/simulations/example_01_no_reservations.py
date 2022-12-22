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

from datafev.routines.arrival import *
from datafev.routines.departure import *
from datafev.routines.charging_control.decentralized_fcfs import charging_routine


def main():
    """
    This tutorial aims to show the use of datafev framework in a small example scenario
    in the following the steps to set up a simulation instance will be given.
    """

    ########################################################################################################################
    ########################################################################################################################
    # SIMULATION SET-UP

    # Simulation inputs
    input_file = pd.ExcelFile("inputs/example_01.xlsx")
    input_fleet = pd.read_excel(input_file, "Fleet")
    input_cluster1 = pd.read_excel(input_file, "Cluster1")
    input_capacity1 = pd.read_excel(input_file, "Capacity1")
    # Getting the path of the input excel file
    abs_path_input = os.path.abspath(input_file)
    print("Scenario inputs are taken from the xlsx file:", abs_path_input)
    print()

    # Printing the input parameters related to the EV fleet
    print(
        "The charging demands of the EVs in the simulation scenario are given in the following:"
    )
    print(
        input_fleet[["Battery Capacity (kWh)", "Real Arrival Time", "Real Arrival SOC"]]
    )
    print()

    # Printing the input parameters of the charging infrastructure
    print("The system consists of one charger cluster with the following chargers:")
    print(input_cluster1)
    print()
    print(
        "Aggregate net consumption of the cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print(input_capacity1)
    print()
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

    cluster1 = ChargerCluster("cluster1", input_cluster1)
    system = MultiClusterSystem("multicluster")
    system.add_cc(cluster1)
    fleet = EVFleet("test_fleet", input_fleet, sim_horizon)
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
        print("     Simulating time step:", ts)

        # The departure routine for the EVs leaving the charger clusters
        departure_routine(ts, fleet)

        # The arrival routine for the EVs incoming to the charger clusters
        arrival_routine(ts, sim_step, fleet, system)

        # Real-time charging control of the charger clusters
        charging_routine(ts, sim_step, system)

    print("Simulation finished...")
    print()
    print()
    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # ANALYSIS OF THE SIMULATION RESULTS

    # Displaying connection data of cluster
    print("Connection data")
    print(cluster1.cc_dataset[["EV ID", "Arrival Time", "Leave Time"]])
    print()

    # Printing the results to excel files
    system.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example01_clusters.xlsx"
    )
    fleet.export_results_to_excel(
        sim_start, sim_end, sim_step, "results/example01_fleet.xlsx"
    )
    # Path of the output excel file
    abs_path_output_cluster = os.path.abspath("results/example01_clusters.xlsx")
    abs_path_output_fleet = os.path.abspath("results/example01_fleet.xlsx")
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
