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


import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
from pyomo.environ import SolverFactory

from datafev.data_handling.fleet import EVFleet
from datafev.data_handling.cluster import ChargerCluster
from datafev.data_handling.multi_cluster import MultiClusterSystem

from datafev.routines.arrival import *
from datafev.routines.departure import *
from datafev.routines.charging_control.decentralized_fcfs import charging_routine

matplotlib.interactive(True)



def main():
    """
    This tutorial aims to show the use of datafev framework in a small example scenario
    in the following the steps to set up a simulation instance will be given.
    """

    # Simulation parameters
    print("Selecting the simulation parameters...")

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

    # Simulation inputs
    print("Scenario inputs  are taken from an xlsx file...")
    print()

    inputs = pd.ExcelFile("scenario_without_reservation.xlsx")
    input_fleet = pd.read_excel(inputs, "Fleet")
    input_cluster1 = pd.read_excel(inputs, "Cluster1")
    input_capacity1 = pd.read_excel(inputs, "Capacity1")

    print(
        "The charging demands of the EVs in the simulation scenario are given in the following:"
    )
    print(
        input_fleet[["Battery Capacity (kWh)", "Real Arrival Time", "Real Arrival SOC"]]
    )
    print()
    print("The system consists of one charger cluster with the following chargers:")
    print(input_cluster1)
    print()
    print(
        "Aggregate net consumption of the cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print(input_capacity1)
    print()
    print()

    print("This scenario is simulated for two cases:")
    print("1) Uncontrolled charging of the EVs")
    print(
        "2) Controlled charging of the EVs --> charging control is based on first-come-first-served"
    )
    print("...")
    print()
    # Dictionaries to store the simulation outputs
    consumption_profiles = {}

    # Simulating the same scenario for three different cases
    for control in ["uncontrolled", "controlled"]:

        print("Simulating the charging control approach:", control)

        #######################################################################
        # Multicluster charging system and EV fleet
        cluster1 = ChargerCluster("cluster1", input_cluster1)
        system = MultiClusterSystem("multicluster")
        system.add_cc(cluster1)

        fleet = EVFleet("test_fleet", input_fleet, sim_horizon)
        #######################################################################

        #######################################################################
        # Additional parameters for charging management protocol
        cluster1.enter_power_limits(sim_start, sim_end, sim_step, input_capacity1)
        #######################################################################

        #######################################################################
        # Simulation starts
        np.random.seed(0)

        for ts in sim_horizon:
            print("     Simulating time step:", ts)

            # The departure protocol for the EVs leaving the charger clusters
            departure_routine(ts, fleet)

            # The arrival protocol for the EVs incoming to the charger clusters
            arrival_routine(ts, sim_step, fleet, system)

            # Real-time charging control of the charger clusters
            if control == "uncontrolled":
                system.uncontrolled_supply(ts, sim_step)
            if control == "controlled":
                charging_routine(ts, sim_step, system)

        # Simulation ends
        #######################################################################

        #######################################################################
        # Printing the results to excel files
        system.export_results(
            sim_start,
            sim_end,
            sim_step,
            "results/result_noreservation_" + control + "_clusters.xlsx",
        )
        fleet.export_results(
            sim_start,
            sim_end,
            sim_step,
            "results/result_noreservation_" + control + "_fleet.xlsx",
        )
        #######################################################################

        #######################################################################
        # Storing the aggregate consumption profiles of individual clusters to dictionaries
        consumption_profiles[control] = (
            cluster1.analyze_consumption_profile(sim_start, sim_end, sim_step)
        ).sum(axis=1)

        print()
        #######################################################################

    print()
    print(
        "Aggregate consumption profile of clusters in each management approach are plotted:"
    )
    fig, axs = plt.subplots(1, 1, tight_layout=True, sharex=True)
    pd.concat(consumption_profiles, axis=1).plot(ax=axs, title="cluster1")
    plt.show()


if __name__ == "__main__":
    main()
