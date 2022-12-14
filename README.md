# datafev

Python package datafev is a framework for the development, testing, and assessment of managemant algorithms for EV charging scenarios. The framework allows to develop scenario-oriented management strategies. It includes a portfolio of optimization- and rule-based algorithms to coordinate charging and routing operations in clustered charging systems. Furthermore, it provides statistical scenario generation tool to create EV fleet demand profiles.
Its target users are researchers in the field of smart grid applications and the deployment of operational flexibility for local energy systems.


## Contribution

1. Clone repository via SSH (`git clone git@git.rwth-aachen.de:acs/public/automation/datafev.git`) or clone repository via HTTPS (`git clone https://git.rwth-aachen.de/acs/public/automation/datafev.git`)
2. Open an issue at [https://git.rwth-aachen.de/acs/public/automation/datafev/-/issues](https://git.rwth-aachen.de/acs/public/automation/datafev/-/issues)
3. Checkout the development branch: `git checkout development` 
4. Update your local development branch (if necessary): `git pull origin development`
5. Create your feature/issue branch: `git checkout -b issueXY_explanation`
6. Commit your changes: `git commit -m "Add feature #XY"`
7. Push to the branch: `git push origin issueXY_explanation`
8. Submit a merge request from issueXY_explanation to development branch via [https://git.rwth-aachen.de/acs/public/automation/datafev/-/merge_requests](https://git.rwth-aachen.de/acs/public/automation/datafev/-/merge_requests)
9. Wait for approval or revision of the new implementations.

## Installation

datafev requires at least the following Python packages:
- matplotlib==3.5.1
- numpy==1.21.5
- openpyxl==3.0.9
- pandas==1.4.2
- pyomo==6.4.1

as well as the installation of at least one mathematical programming solver for convex and/or non-convex problems, which is supported by the [Pyomo](http://www.pyomo.org/) optimisation modelling library.
We recommend one of the following solvers:

- [Gurobi (gurobipy)](https://www.gurobi.com/products/gurobi-optimizer/) (default)
- [IBM ILOG CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio)
- [GLPK (GNU Linear Programming Kit)](https://www.gnu.org/software/glpk/)

If all the above-mentioned dependencies are installed, you should be able to install package datafev via [PyPI](https://pypi.org/) (using Python 3.X) as follows:

`pip install datafev`

or:

`pip install -e '<your_path_to_datafev_git_folder>/src'`

or:

`<path_to_your_python_binary> -m pip install -e '<your_path_to_datafev_git_folder>/src'`

Another option rather than installing via PyPI would be installing via setup.py:

`py <your_path_to_datafev_git_folder>/setup.py install`

or:

`pyton <your_path_to_datafev_git_folder>/setup.py install`


You can check if the installation has been successful by trying to import package datafev into your Python environment.
This import should be possible without any errors.

`import datafev`


## Documentation

The documentation for the latest datafev release can be found in folder ./docs and on [this](https://acs.pages.rwth-aachen.de/public/simulation/pycity_scheduling/) GitLab page.

For further information, please also visit the [FEIN Aachen association website](https://fein-aachen.org/en/projects/pycity_scheduling/).


## Example usage

```python
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
    print("Scenario inputs  are taken from the xlsx file:",input_file)
    print()


    #Printing the input parameters related to the EV fleet 
    print("The charging demands of the EVs in the simulation scenario are given in the following:")
    print(input_fleet[["Battery Capacity (kWh)", "Real Arrival Time", "Real Arrival SOC"]])
    print()
    
    # Printing the input parameters of the charging infrastructure
    print("The system consists of one charger cluster with the following chargers:")
    print(input_cluster1)
    print()
    print("Aggregate net consumption of the cluster is limited in the scenario (i.e., LB-UB indicating lower-upper bounds)")
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

        # The departure protocol for the EVs leaving the charger clusters
        departure_routine(ts, fleet)

        # The arrival protocol for the EVs incoming to the charger clusters
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
    system.export_results_to_excel(sim_start, sim_end, sim_step, "results/example01_clusters.xlsx")
    fleet.export_results_to_excel(sim_start, sim_end, sim_step, "results/example01_fleet.xlsx")
    
    #Line charts to visualize cluster loading and occupation profiles
    fig1=system.visualize_cluster_loading(sim_start, sim_end, sim_step)   
    fig2=system.visualize_cluster_occupation(sim_start, sim_end, sim_step)   
    plt.show()


    ########################################################################################################################
    ########################################################################################################################

if __name__ == "__main__":
    main()
```


## License

The datafev package is released by the Institute for Automation of Complex Power Systems (ACS), E.ON Energy Research Center (E.ON ERC), RWTH Aachen University under the [MIT License](https://opensource.org/licenses/MIT).


## Contact

- Erdem Gumrukcu, M.Sc. <erdem.guemruekcue@eonerc.rwth-aachen.de>
- Amir Ahmadifar, M.Sc. <aahmadifar@eonerc.rwth-aachen.de>
- Aytug Yavuzer, B.Sc. <aytug.yavuzer@rwth-aachen.de>
- Univ.-Prof. Antonello Monti, Ph.D. <post_acs@eonerc.rwth-aachen.de>

[Institute for Automation of Complex Power Systems (ACS)](http://www.acs.eonerc.rwth-aachen.de) \
[E.ON Energy Research Center (E.ON ERC)](http://www.eonerc.rwth-aachen.de) \
[RWTH Aachen University, Germany](http://www.rwth-aachen.de)


<img src="https://fein-aachen.org/img/logos/eonerc.png"/>
