
import pandas as pd

def idp(schedule,upper_bound,lower_bound,tou_tariff,f_discount,f_markup):
    """
    This is the python implementation of the individual dynamic pricing algorithm introduced in
    Gümrükcü, et al., "Decentralized Energy Management Concept for Urban Charging Hubs with Multiple V2G Aggregators,"
    in IEEE Transactions on Transportation Electrification, 2022, doi: 10.1109/TTE.2022.3208627.

    This function compares the commitments with the desired power consumption range of the cluster to
    #1) increase the charging price for time steps where the schedule exceeds the upper bound of the desired range
    #2) decrease the charging price for time steps where the schedule is below the lower bound of the desired range

    Inputs
    ---------------------------------------------------------------------------
    schedule    : Aggregate schedule of the cluster                                 dict of float
    upper_bound : Upper bound of the desired consumption range                      dict of float
    lower_bound : Lower bound of the desired consumption range                      dict of float
    tou_tariff  : Standard TOU tariff of the cluster operator (Eur/kWh)             dict of float
    f_discount  : Discount factor to compensate each kW of deficit consumption      float
    f_markup    : Markup factor to compensate each kW of excessive consumption      float
    ---------------------------------------------------------------------------

    Outputs
    ---------------------------------------------------------------------------
    omega       : Dynamic price signal                                              dict
    ---------------------------------------------------------------------------
    """

    sc      = pd.Series(schedule)
    ub      = pd.Series(upper_bound)
    lb      = pd.Series(lower_bound)
    kappa   = pd.Series(tou_tariff)
    kappa_L = kappa.min()
    kappa_U = kappa.max()

    overloadedsteps   = sc[sc>=ub].index
    underloadedsteps  = sc[sc<lb].index

    ome = kappa.copy()
    ome[underloadedsteps]= kappa_L - f_discount * (lb[underloadedsteps]- sc[underloadedsteps])
    ome[overloadedsteps] = kappa_U + f_markup * (sc - ub)[overloadedsteps]

    omega=ome.to_dict()

    return omega

if __name__ == '__main__':

    import numpy as np
    import matplotlib.pyplot as plt

    np.random.seed(0)

    schedule= dict(enumerate(np.random.uniform(low=44,high=88,size=12)))
    upper_b = dict(enumerate(np.ones(12)*70))
    lower_b = dict(enumerate(np.zeros(12)))
    tou     = np.random.uniform(low=0.4,high=0.8,size=12)
    f_disc  = .05
    f_mark  = .05

    omega=idp(schedule, upper_b, lower_b, tou, f_disc, f_mark)

    df=pd.DataFrame(columns=['Schedule','UB','LB','TOU','DP'])
    df['Schedule']=pd.Series(schedule)
    df['UB']      =pd.Series(upper_b)
    df['LB']      =pd.Series(lower_b)
    df['TOU']     =pd.Series(tou)
    df['DP']      =pd.Series(omega)

    print(df)











