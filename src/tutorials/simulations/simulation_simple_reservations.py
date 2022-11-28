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

from datafev.routines.simple_reservation.reservation import *
from datafev.routines.simple_reservation.arrival import *
from datafev.routines.departure import *
from datafev.routines.charging_control.decentralized_llf import charging_routine


def main():
    """
    This tutorial aims to show the use of datafev framework in an example scenario with
    simple reservations where EVs reserve chargers before their arrival to clusters
    smart charging where clusters' power consumption profiles are controlled based on least-laxity-first algorithm.
    """

    ########################################################################################################################
    ########################################################################################################################
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
    inputs = pd.ExcelFile("scenario_simple_reservation.xlsx")
    input_fleet = pd.read_excel(inputs, "Fleet")
    input_cluster1 = pd.read_excel(inputs, "Cluster1")
    input_capacity1 = pd.read_excel(inputs, "Capacity1")

    print("The system consists of one charger cluster with the following chargers:")
    print(input_cluster1)
    print()
    print(
        "Aggregate net consumption of the cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)"
    )
    print(input_capacity1)
    print()

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

    ########################################################################################################################
    ########################################################################################################################
    # Initialization of the simulation model

    # Fleet behavior
    fleet = EVFleet("test_fleet", input_fleet, sim_horizon)

    # Multicluster charging system and EV fleet
    cluster1 = ChargerCluster("cluster1", input_cluster1)
    system = MultiClusterSystem("multicluster")
    system.add_cc(cluster1)
    cluster1.enter_power_limits(sim_start, sim_end, sim_step, input_capacity1)

    # Same random behavior (if randomness exists) in all runs
    np.random.seed(0)

    print("Simulation scenario has been initalized")
    print()

    ########################################################################################################################
    ########################################################################################################################

    #######################################################################

    #######################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Simulation

    print("Simulation started...")

    for ts in sim_horizon:
        print("Simulating time step:", ts)

        # The departure protocol for the EVs leaving the chargerg clusters
        departure_routine(ts, fleet)

        # The reservation protocol (including routing to a cluster in the multicluster system) for the EVs
        reservation_routine(ts, sim_step, system, fleet, traffic_forecast)

        # The arrival protocol for the EVs incoming to the charger clusters
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

    # Displaying reservation and connection date of cluster1
    print("Reservation data")
    print(cluster1.re_dataset.iloc[:, 1:6])
    print()

    print("Connection data")
    print(cluster1.cc_dataset[["EV ID", "Arrival Time", "Leave Time"]])
    print()

    ########################################################################################################################
    ########################################################################################################################

    ########################################################################################################################
    ########################################################################################################################
    # Printing the results to excel files
    system.export_results(
        sim_start, sim_end, sim_step, "results/result_simplereservation_clusters.xlsx"
    )
    fleet.export_results(
        sim_start, sim_end, sim_step, "results/result_simplereservation_fleet.xlsx"
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
    clu1_occ = cluster1.analyze_occupation_profile(sim_start, sim_end, sim_step).sum(
        axis=1
    )

    fig1, ax1 = plt.subplots(2, 1, tight_layout=True)
    fig1.suptitle("cluster1")
    clu1_occ.plot(ax=ax1[0], title="Number of connceted EVs")
    clu1_pow.plot(ax=ax1[1], title="Aggregate consumption")
    cluster1.upper_limit[sim_start:sim_end].plot(ax=ax1[1], label="Constraint")
    plt.show()

    print("Aggregate consumption and occupation profiles of the clusters are plotted")
    ########################################################################################################################
    ########################################################################################################################


if __name__ == "__main__":
    main()
