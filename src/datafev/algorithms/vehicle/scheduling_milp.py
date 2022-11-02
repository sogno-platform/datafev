
from pyomo.core import *
import pyomo.kernel as pmo

def minimize_cost(solver,opt_step,opt_horizon,ecap,v2gall,tarsoc,minsoc,maxsoc,crtsoc,crttime,inisoc,p_ch,p_ds,g2v_dps,v2g_dps):
    """
    This function optimizes the charging schedule of a single EV with the objective of charging cost minimization
    for the given G2V and V2G price signals. The losses in power transfer are considered.
    
    Inputs
    ------------------------------------------------------------------------------------------------------------------
    opt_step    : size of one time step in the optimization (seconds)   float
    opt_horizon : time step identifiers in the optimization horizon     list of integers
    ecap        : energy capacity of battery (kWs)                      float
    v2gall      : V2G allowance discharge (kWs)                         float
    tarsoc      : target final soc   (0<inisoc<1)                       float
    minsoc      : minimum soc                                           float
    maxsoc      : maximum soc                                           float
    crtsoc      : target soc at crttime                                 float
    crttime     : critical time s.t. s(srttime)> crtsoc                 int
    inisoc      : initial soc (0<inisoc<1)                              float
    p_ch        : nominal charging power     (kW)                       float
    p_ds        : nominal charging power     (kW)                       float
    g2v_dps     : G2V dynamic price signals (Eur/kWh)                   dict of float
    v2g_dps     : V2G dynamic price signals (Eur/kWh) for V2G           dict of float
    ------------------------------------------------------------------------------------------------------------------
    
    Outputs
    ------------------------------------------------------------------------------------------------------------------
    p_schedule  : timeseries of charge power                            dict
    s_schedule  : timeseries of SOC reference                           dict
    ------------------------------------------------------------------------------------------------------------------
    """  

    conf_period={}
    for t in opt_horizon:
        if t<crttime:
            conf_period[t]=0
        else:
            conf_period[t]=1

                    
    ####################Constructing the optimization model####################
    model       = ConcreteModel()
    
    model.T        = Set(initialize=opt_horizon,ordered=True)   #Time index set    
    model.dt       = opt_step                                   #Step size
    model.E        = ecap                                       #Battery capacity in kWs
    model.P_CH     = p_ch                                       #Maximum charging power in kW
    model.P_DS     = p_ds                                       #Maximum discharging power in kW
    model.W_G2V    = g2v_dps                                    #Time-variant G2V cost coefficients
    model.W_V2G    = v2g_dps                                    #Time-variant V2G cost coefficients
    model.SoC_F    = tarsoc                                     #SoC to be achieved at the end
    model.conf     = conf_period                                #Confidence period where SOC must be larger than crtsoc
    model.SoC_R    = crtsoc                                     #Minimim SOC must be ensured in the confidence period  
    model.V2G_ALL  = v2gall                                     # Maximum energy that can be discharged V2G
         
    model.xp       = Var(model.T,within=pmo.Binary)                                        #Binary variable having 1/0 if v is charged/discharged at t 
    model.p        = Var(model.T,within=Reals)                                             #Net charge power at t
    model.p_pos    = Var(model.T,within=NonNegativeReals)                                  #Charge power at t
    model.p_neg    = Var(model.T,within=NonNegativeReals)                                  #Discharge power at t
    model.SoC      = Var(model.T,within=NonNegativeReals,bounds=(minsoc,maxsoc))           #SOC to be achieved  at time step t
    
    #CONSTRAINTS
    def initialsoc(model):
        return model.SoC[0]==inisoc
    model.inisoc=Constraint(rule=initialsoc)
            
    def storageConservation(model,t):#SOC of EV batteries will change with respect to the charged power and battery energy capacity
        if t<max(model.T):
            return model.SoC[t+1]==(model.SoC[t] + model.p[t]*model.dt/model.E)
        else:
            return model.SoC[t] ==model.SoC_F
    model.socconst=Constraint(model.T,rule=storageConservation)
    
    def socconfidence(model,t):
        return model.SoC[t]>=model.SoC_R*model.conf[t]
    model.socconfi=Constraint(model.T,rule=socconfidence)

    def supplyrule(model):
        return model.p[max(model.T)]==0.0
    model.supconst=Constraint(rule=supplyrule)
                  
    def netcharging(model,t):
        return model.p[t]==model.p_pos[t]-model.p_neg[t]
    model.netchr=Constraint(model.T,rule=netcharging)
    
    def combinatorics31_pos(model,t):
        return model.p_pos[t]<=model.xp[t]*model.P_CH
    model.comb31pconst=Constraint(model.T,rule=combinatorics31_pos)
        
    def combinatorics31_neg(model,t):
        return model.p_neg[t]<=(1-model.xp[t])*model.P_DS
    model.comb31nconst=Constraint(model.T,rule=combinatorics31_neg)
      
    def v2g_limit(model):
        return sum(model.p_neg[t]*model.dt for t in model.T)<=model.V2G_ALL
    model.v2gconst   =Constraint(rule=v2g_limit)
    
    #OBJECTIVE FUNCTION
    def obj_rule(model):  
        return sum((model.W_G2V[t]*model.p_pos[t]-model.W_V2G[t]*model.p_neg[t] for t in opt_horizon[:-1]))*opt_step/3600
    model.obj=Objective(rule=obj_rule, sense = minimize)

    solver.solve(model)

    p_schedule = {}
    s_schedule = {}

    for t in model.T:
        p_schedule[t] = model.p[t]()
        s_schedule[t] = model.SoC[t]()

    return p_schedule, s_schedule

if __name__ == '__main__':

    from pyomo.environ import SolverFactory
    import pandas as pd
    import numpy as np

    solver   = SolverFactory("cplex")
    step     = 300                  #Time step size= 300 seconds = 5 minutes
    horizon  = list(range(13))      #Optimization horizon= 12 steps = 60 minutes
    ecap     = 55 * 3600            #Battery capacity= 55 kWh
    v2gall   = 10 * 3600            #V2G allowance = 10 kWh
    tarsoc   = 0.8                  #Target SOC
    minsoc   = 0.2                  #Minimum SOC
    maxsoc   = 1.0                  #Maximum SOC
    crtsoc   = 0.6                  #Critical SOC
    crttime  = 4                    #Critical time
    inisoc   = 0.5                  #Initial SOC
    pch      = 22                   #Maximum charge power
    pds      = 22                   #Maximum discharge power


    print("Size of one time step:",step,"seconds")
    print("Optimization horizon covers",max(horizon),"time steps")
    print("Battery capacity of the EV:",ecap/3600,"kWh")
    print("Initial SOC of the EV:",inisoc)
    print("Target SOC (at the end of optimization horizon):",tarsoc)
    print("Critical SOC condition: SOC", crtsoc, "must be achieved by",crttime,"and must be maintained afterwards")
    print("V2G allowance:", v2gall / 3600, "kWh")
    print("Optimization is run G2V-V2G distinguishing price signals")
    print()

    g2v_tariff = np.random.uniform(low=0.4, high=0.8, size=12)
    g2v_dps    = dict(enumerate(g2v_tariff))
    v2g_dps    = dict(enumerate(g2v_tariff * 0.9))

    p, soc = minimize_cost(solver, step, horizon, ecap, v2gall,
                           tarsoc, minsoc, maxsoc, crtsoc, crttime, inisoc,
                           pch, pds, g2v_dps, v2g_dps)

    results = pd.DataFrame(columns=['G2V Tariff' , 'V2G Tariff' , 'Optimal Pow Profile', 'Optimal SOC Profile'],
                           index=sorted(soc.keys()))
    results['G2V Tariff'] = pd.Series(g2v_dps)
    results['V2G Tariff'] = pd.Series(v2g_dps)
    results['Optimal Pow Profile'] = pd.Series(p)
    results['Optimal SOC Profile'] = pd.Series(soc)
    print(results)