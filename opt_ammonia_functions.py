import gurobipy as gp
import pandas as pd 
import time
import logging

from config import (CC_METHOD, NAME_REF_DB, T_DAY,
                    MJ_KG_H2, MJ_kWh,
                    CC_IMPACT_NG_NH3) # import global vars

ASSESSMENT_YEAR = 2025

def opt_amm_electric_hb(df_data, w_cost, w_env, parm, dict_ghg, dict_limits, sec_db = NAME_REF_DB,
                        credit_env_export=False, autonomous_elect=False, export_results=False,
                        eps_ghg_constraint = False, euro_ton_co2 = 0,
                        consider_down_times = True, heuristics=False, export_alias = "",
                        mip_gap=0.005, int_feas_tol = 1e-7, logger=True,
                        time_limit = 10*3600, size_nh3_system=T_DAY*365, no_renewables=False, LOC_ELECT='GLO',
                        grid_inj=False, hybrid_green=False, CC_IMPACT_NG_NH3=CC_IMPACT_NG_NH3, h2_price = 0,
                        save_operation_output = False):
    """
    Solve a (single- or multi-objective) mixed-integer linear optimization problem 
    for an electrified Haber–Bosch ammonia production system.

    The model simultaneously minimizes cost and environmental impacts (e.g., GHG emissions)
    using weighted or epsilon-constraint formulations. It supports various system configurations,
    including grid-connected, off-grid, and hybrid renewable systems, and can optionally 
    export intermediate and final results.

    Args:
        df_data (pd.DataFrame): Hourly input data (e.g., renewable availability, electricity prices).
        w_cost (float): Weight of the cost objective (between 0 and 1).
        w_env (float): Weight of the environmental objective (between 0 and 1).
        parm (dict): Dictionary of techno-economic parameters for all technologies.
        dict_ghg (dict): Dictionary containing greenhouse gas emission factors (kg CO₂-eq per unit).
        dict_limits (dict): Dictionary with capacity, operational, and technical limits of technologies.

        sec_db (str, optional): Reference database for life-cycle inventory calculations. 
            Default is `NAME_REF_DB`.
        credit_env_export (bool, optional): If True, apply environmental credits for exporting 
            surplus electricity or other energy carriers. Default is False.
        autonomous_elect (bool, optional): If True, optimize as an autonomous system without 
            a grid connection. Default is False.
        export_results (bool, optional): If True, export results to Excel. Default is True.
        eps_ghg_constraint (bool or float, optional): If True (or a float), include an 
            ε-constraint on life-cycle GHG emissions. Default is False.
        euro_ton_co2 (float, optional): Carbon price in €/t CO₂. Default is 0.
        consider_down_times (bool, optional): Whether to enforce minimum up- and downtimes 
            for relevant technologies. Default is True.
        heuristics (bool, optional): Apply heuristic initialization or solving strategies 
            to improve performance. Default is False.
        export_alias (str, optional): String appended to exported filenames. Default is "".
        mip_gap (float, optional): Relative MIP optimality gap. Default is 0.005.
        int_feas_tol (float, optional): Integrality feasibility tolerance. Default is 1e-7.
        time_limit (int, optional): Solver time limit in seconds. Default is 36,000 (10 hours).
        calc_all_lca_impacts (bool, optional): If True, calculate additional life-cycle impact 
            categories beyond GHG. Default is False.
        size_nh3_system (float, optional): Nominal ammonia production capacity (t NH₃/year). 
            Default is `T_DAY * 365`.
        no_renewables (bool, optional): If True, exclude renewable generation from the system. 
            Default is False.
        LOC_ELECT (str, optional): Geographic location code for electricity data or impact factors. 
            Default is 'GLO'.
        grid_inj (bool, optional): If True, allow electricity export to the grid. Default is False.
        hybrid_green (bool, optional): If True, enable hybrid configurations combining grid 
            and renewables. Default is False.
        CC_IMPACT_NG_NH3 (float, optional): Default carbon intensity of conventional 
            natural-gas-based ammonia production (kg CO₂-eq/kg NH₃). Default is 2.8.

    Returns:
        overview_totals (pd.DataFrame): Summary table with key aggregated techno-economic and 
            environmental results.
        lca_results (pd.DataFrame): Life-cycle assessment results by impact category.
        df_out (pd.DataFrame): Hourly operational results of all modeled technologies.
    """
    start = time.time()
    delta_t = 1
    
    dict_limits['max_hb'] = size_nh3_system #Hourly capacity max, large value for big M, but not too large to keep the model tight.
    dict_limits['min_hb'] = 0 #Minimum size, anyway needed more than zero but to avoid additional binary.
    
    # If no credit assumed for injection of grid electrciy, then replace that with zeros
    if credit_env_export == False:
        df_data.ghg_impact_cons = 0
        dict_ghg['ghg_imp_smr'] = 0
        
    T=len(df_data)    
    
    # Decide to install micro wind turbines or not:
    wind_MW_array_on = df_data.wind_MW_array_on
    
    """
    Step 1: Create a model and specify parameters of the model
    """

    m = gp.Model("obj")

    if not logger:
        m.Params.OutputFlag = 0
        m.Params.LogFile = ""
        #logging.getLogger("gurobipy").setLevel(logger.WARNING)
    
    # Set parameters of model, tighten or relax
    m.setParam('MIPGap', mip_gap )
    m.setParam('IntFeasTol', int_feas_tol)
    m.setParam('TimeLimit', time_limit )
    m.setParam('Presolve', 2)
    m.setParam('MIPFocus', 1)
    m.setParam('Threads', 1)
    
    if heuristics:
        m.setParam('NormAdjust', 2)
        m.setParam('Heuristics', 0.1)

    """
    Step 2: Define variables
    """
    # Grid variables
    p_grid_inj = m.addVars(T, name='p_grid_inj', ub = dict_limits['max_grid_cap'] if grid_inj==True else 0)
    p_grid_abs = m.addVars(T, name='p_grid_abs', ub = dict_limits['max_grid_cap'])
    bin_grid = m.addVars(T, vtype=gp.GRB.BINARY, name="bin_grid")

    # Battery variables
    p_battdis = m.addVars(T, name='p_battdis', ub=dict_limits['max_bat']) 
    p_battch = m.addVars(T, name='p_battch', ub=dict_limits['max_bat']) 
    E_batt = m.addVars(T, name="E_batt", ub=dict_limits['max_bat'])
    bin_bat = m.addVars(T, vtype=gp.GRB.BINARY, name='bin_bat') 

    # Hydrogen modelling
    e_h2_ves = m.addVars(T, name='e_h2_ves', ub=dict_limits['max_h2_storage'])
    p_h2_ves = m.addVars(T, name='p_h2_ves', lb=-dict_limits['max_h2_storage'], ub=dict_limits['max_h2_storage'])
    f_elect = m.addVars(T, name='f_elect', ub=dict_limits['st_max']) 
    p_elect = m.addVars(T, name="p_elect", ub=dict_limits['st_max'])

    # Wind electricity production
    p_solar_pv = m.addVars(T, name="p_solar_pv", ub=dict_limits['st_max'])
    p_wind_on = m.addVars(T, name="p_wind_on", ub=dict_limits['st_max'])

    # HB synthesis
    p_hb = m.addVars(T, name='p_hb', ub=dict_limits['st_max']) #kg NH3 produced
    h2_export = m.addVars(T, name='h2_export', ub=dict_limits['st_max']) #kg NH3 produced

    if consider_down_times:
        #variables to model start-up and down times of HB unit
        x_hb = m.addVars(T, vtype=gp.GRB.BINARY, name="x_hb")
        y_hb = m.addVars(T, vtype=gp.GRB.BINARY, name="y_hb")
        z_hb = m.addVars(T, vtype=gp.GRB.BINARY, name="z_hb")
        aux_hb = m.addVars(T, name="aux_hb", ub=dict_limits['st_max'])

    ###### SINGLE VARS ######
    cap_wind_on = m.addVar(name="cap_wind_on", ub=0 if no_renewables else dict_limits['max_wind_on'])
    cap_pv = m.addVar(name="cap_pv", ub=0 if no_renewables else dict_limits['max_pv'])
    cap_bat_en = m.addVar(name="cap_bat_en", ub = dict_limits['max_bat'])
    cap_bat_p = m.addVar(name="cap_bat_p", ub = dict_limits['max_bat'])
    cap_h2_ves = m.addVar(name="cap_h2_ves", ub = dict_limits['max_h2_storage']) 
    cap_electrolyzer = m.addVar(name="cap_electrolyzer", ub = dict_limits['max_electrolyzer'])
    cap_hb = m.addVar(name="cap_hb", ub = dict_limits['max_hb']) #kg NH3/h
    cap_asu = m.addVar(name="cap_asu", ub = dict_limits['max_hb']) #kg N2/h
    cap_grid = m.addVar(name="cap_grid", ub=0 if autonomous_elect else dict_limits['max_grid_cap']) # The grid connection is zero capacity in case there cannot per a grid power exchange

    """
    Step 3: Add constraints
    """
        
    """3.1. Local balance electricity"""
    # demand for power comes from hydrogen production, the ASU (N), and HB process.
    for t in range(T):
        m.addConstr( (p_grid_abs[t] - p_grid_inj[t]) + 
                      (p_battdis[t] - p_battch[t]) + p_solar_pv[t]
                     + p_wind_on[t] 
                     == f_elect[t] + #electrolyzer
                        parm['HB_kwh_per_kgNH3'] * p_hb[t] + #HB process
                        parm['asu_power_demand'] * parm['N_per_kgNH3'] * p_hb[t] #ASU 
                        )
    
    """ Local balance Hydrogen"""
    # Here, we link the amount of hydrogen needed for HB synthesis, 
    # considering direct H2 productin and from the storage
    for t in range(T):
        m.addConstr( p_elect[t] == parm['kg_H2_per_kgNH3'] * (MJ_KG_H2/MJ_kWh/delta_t) * p_hb[t] + p_h2_ves[t] + h2_export[t] )

    #make sure we produce the amount of NH3 as specified
    m.addConstr( gp.quicksum(p_hb[t] for t in range (T)) == size_nh3_system)

    # ASU unit, note it is directly coupled to the HB process
    for t in range(T):
        m.addConstr(parm['N_per_kgNH3'] * p_hb[t] <= cap_asu) #kg N2 produced   

    """Haber-Bosch synthesis"""  
    # If considering detailed modelling, otherwise simplified
    if consider_down_times:
        """
        x_hb[t] → binary on/off status of the plant at time t
        x_hb[t] = 1 if the HB plant is running

        y_hb[t] → startup variable
        y_hb[t] = 1 if the plant starts up at time t
        y_hb[t] = 0 otherwise

        z_hb[t] → shutdown variable
        z_hb[t] = 1 if the plant shuts down at time t
        z_hb[t] = 0 otherwise
        """
        hb_TU = int(parm['hb_TU'])
        hb_TD = int(parm['hb_TD'])
        
        # Add linearization constraints aux_hb <= cap_hb * x_hb[t]
        # to avoid m.addConstrs(p_hb[t] <= cap_hb * x_hb[t] for t in range(T))
        for t in range(T):  
            # Consider part load ratio
            m.addConstr(p_hb[t] <= aux_hb[t]) 
            m.addConstr(p_hb[t] >= parm['hb_pl_min'] * aux_hb[t]) 

            # Add linearization constraints for p_hb[t] <= cap_hb * x_hb[t]:
            m.addConstr(aux_hb[t] <= dict_limits['max_hb'] * x_hb[t])
            m.addConstr(dict_limits['min_hb'] * x_hb[t] <= aux_hb[t])

            m.addConstr(cap_hb - dict_limits['max_hb'] * (1-x_hb[t]) <= aux_hb[t])
            m.addConstr(aux_hb[t] <= cap_hb)

        for t in range(0,1):       
            # For timestep 0, we assume same or less output as t+1
            #2b
            m.addConstr(p_hb[0] <= p_hb[t+1])

        for t in range(1,T):       
            # Skip timestep 0, otherwise keyError issue
            #2b
            if parm['hb_ramp']>1:
                m.addConstr(p_hb[t] - p_hb[t-1] <= (cap_hb/parm['hb_ramp']) )
                #2c
                m.addConstr(p_hb[t-1] - p_hb[t] <= (cap_hb/parm['hb_ramp']) )

            # Logical constraint, 2d:
            m.addConstr(x_hb[t] - x_hb[t-1] == y_hb[t] - z_hb[t])

        if hb_TU>1:
            # 2e Minimum up- and downtimes, constraint 6 for uptimes:
            for t in range(hb_TU, T):   
                m.addConstr(gp.quicksum(y_hb[i] for i in range(t-hb_TU+1,t+1)
                                       ) <= x_hb[t])

        if hb_TD>1:
            # 2f Minimum up- and downtimes, constraint 6 for uptimes:
            for t in range(hb_TD, T):
                m.addConstr(gp.quicksum(z_hb[i] for i in range(t-hb_TD+1,t+1)
                                    ) <= 1 - x_hb[t])   
                
        #startup_cost_term = parm['hb_startup_cost'] * gp.quicksum(y_hb[t] for t in range(T) )
        startup_cost_term = 0
    else:
        # HB capacity limit
        for t in range(T):
            # assume the unit is always on, indeed, simplified approach but considering inflexibolity.
            m.addConstr(p_hb[t] >= parm['hb_pl_min'] * cap_hb)
            m.addConstr(p_hb[t] <= cap_hb)

        # We will not assume ramp-up and -down, as this was indicated as 60% of capacity
        # Meaning, that if already on 30% non-fliebxle part load (always on), this does not
        # Add much usefulness.
        #if parm['hb_ramp']>1:
        #    for t in range(1,T):       
        #        m.addConstr(p_hb[t] - p_hb[t-1] <= (cap_hb/parm['hb_ramp']) )
        #        #2c
        #        m.addConstr(p_hb[t-1] - p_hb[t] <= (cap_hb/parm['hb_ramp']) )

        startup_cost_term = 0 

    """3.2. Power boundaries"""
    if grid_inj:
        for t in range(T):
            m.addConstr(p_grid_abs[t] <= dict_limits['max_grid_cap'] * bin_grid[t])
            # Use GUROBI indicator constraint instead
            m.addGenConstrIndicator(bin_grid[t], True, p_grid_inj[t], gp.GRB.EQUAL, 0)
            m.addConstr(p_grid_inj[t] <= cap_grid)

    # Get the maximum abs or inj peak and store in var to be used for demand charge
    for t in range(T):
        m.addConstr(p_grid_abs[t] <= cap_grid)    
    
    """3.3. Battery model"""
    # Battery dynamics
    for t in range(0,1):
        m.addConstr(E_batt[t] == E_batt[0] * (1-parm['bat_dis_loss']*delta_t) + 
                    (parm['bat_eff_ch']*p_battch[t]*delta_t) - ((p_battdis[t]*delta_t)/parm['bat_eff_dis']))

    for t in range(1,T):
        m.addConstr(E_batt[t] == E_batt[t-1] * (1-parm['bat_dis_loss']*delta_t) + 
                    (parm['bat_eff_ch']*p_battch[t]*delta_t) - ((p_battdis[t]*delta_t)/parm['bat_eff_dis']))

    # Periodicity constraint
    m.addConstr(E_batt[T-1] >= E_batt[0]) 
    
    for t in range(T):
        # Use generator constraint instead, to improve performance https://www.gurobi.com/documentation/9.5/refman/py_model_agc_xxx.html
        m.addConstr(p_battch[t] <= dict_limits['max_bat'] * bin_bat[t] )
        m.addGenConstrIndicator(bin_bat[t], True, p_battdis[t], gp.GRB.EQUAL, 0)
        
        m.addConstr(p_battch[t] <= cap_bat_p )
        m.addConstr(p_battdis[t] <= cap_bat_p )
        
        # respect SoC
        m.addConstr(E_batt[t] >= cap_bat_en * parm['bat_soc_min'])
        m.addConstr(E_batt[t] <= cap_bat_en * parm['bat_soc_max'])

    """3.4. Hydrogen storage, electrolyzer"""
    for t in range(T):
        m.addConstr(p_elect[t] == f_elect[t] * parm['electr_eff'])  
        m.addConstr(f_elect[t] <= cap_electrolyzer)  
    
    # Periodicity constraint
    m.addConstr(e_h2_ves[T-1] >= e_h2_ves[0]) 
    
    # Within this balance
    for t in range(0,1):
        m.addConstr(e_h2_ves[t] == e_h2_ves[0] + p_h2_ves[t])

    for t in range(1,T):
        m.addConstr(e_h2_ves[t] == e_h2_ves[t-1] + p_h2_ves[t])
        
    for t in range(T):
        m.addConstr(e_h2_ves[t] <= cap_h2_ves) 

    # consider ramp rates h2_stor_ramp
    for t in range(T):
        m.addConstr(p_h2_ves[t] <= (cap_h2_ves/parm['h2_ramp_ves']) )
        m.addConstr( -(cap_h2_ves/parm['h2_ramp_ves']) <= p_h2_ves[t] )

    """3.2. Wind and PV supply as well as curtailment"""
    for t in range(T): 
        m.addConstr(p_wind_on[t] <= cap_wind_on * wind_MW_array_on.iloc[t])
        m.addConstr(p_solar_pv[t] <= cap_pv * df_data.pv_MW_array.iloc[t])

    """
    Step 4: Set objective one of multi-objective function
    """

    """Objective 1: Costs"""
    """Operation (variable OPEX)"""
    an_op_grid_abs = gp.quicksum(p_grid_abs[t] * df_data.grid_abs_price.iloc[t] for t in range(T))
    an_op_grid_inj = gp.quicksum(p_grid_inj[t] * df_data.rev_inj.iloc[t] for t in range(T))
    an_op_h2_export = gp.quicksum(h2_export[t] * h2_price for t in range(T)) if abs(h2_price) > 0 else 0

    an_op = startup_cost_term + an_op_grid_abs - an_op_grid_inj - an_op_h2_export

    """Investments (CAPEX)"""
    an_capex_electrolyzer = calc_crf(parm['dr'],parm['project_lt']) * (cap_electrolyzer * parm['electr_capex'])
    an_capex_h2_ves = calc_crf(parm['dr'],parm['project_lt']) * (cap_h2_ves * parm['h2_ves_capex']) 
    an_capex_pv = calc_crf(parm['dr'],parm['project_lt']) * (cap_pv * parm['pv_capex']) 
    an_capex_wind_on = calc_crf(parm['dr'],parm['project_lt']) * (cap_wind_on * parm['wind_on_capex'])
    an_capex_bat_en = calc_crf(parm['dr'],parm['project_lt']) * (cap_bat_en * parm['bat_en_capex']) 
    an_capex_bat_p = calc_crf(parm['dr'],parm['project_lt']) * (cap_bat_p * parm['bat_p_capex'])
    an_capex_hb = calc_crf(parm['dr'],parm['project_lt']) * (cap_hb * parm['hb_capex'])
    an_capex_asu = calc_crf(parm['dr'],parm['project_lt']) * (cap_hb * parm['asu_capex'])
    an_capex_grid_ins = calc_crf(parm['dr'],parm['project_lt']) * (cap_grid * parm['grid_capex'])

    an_capex  = (an_capex_electrolyzer +
                an_capex_h2_ves + 
                an_capex_pv  + an_capex_wind_on +
                an_capex_bat_en + an_capex_bat_p +
                an_capex_hb + an_capex_asu +
                 an_capex_grid_ins 
               )

    """Replacements"""
    an_rep = (
         rep_annual_int((cap_h2_ves * parm['h2_ves_capex']),parm['project_lt'],parm['dr'],parm['h2_ves_lt'])
        + rep_annual_int((cap_electrolyzer * parm['electr_capex']),parm['project_lt'],parm['dr'],parm['electr_lt']) 
        + rep_annual_int((cap_pv * parm['pv_capex']),parm['project_lt'],parm['dr'],parm['pv_lt'])
        + rep_annual_int((cap_wind_on * parm['wind_on_capex']),parm['project_lt'],parm['dr'],parm['wind_on_lt'])
        + rep_annual_int((cap_bat_en * parm['bat_en_capex']),parm['project_lt'],parm['dr'],parm['bat_en_lt'])
        + rep_annual_int((cap_bat_p * parm['bat_p_capex']),parm['project_lt'],parm['dr'],parm['bat_p_lt'])
        + rep_annual_int((cap_hb * parm['hb_capex']),parm['project_lt'],parm['dr'],parm['hb_lt'])
        + rep_annual_int((cap_asu * parm['asu_capex']),parm['project_lt'],parm['dr'],parm['asu_lt'])
        + rep_annual_int((cap_grid * parm['grid_capex']),parm['project_lt'],parm['dr'],parm['grid_lt'])  
             )

    """Fixed O&M (without replacements)"""
    an_om = (
             (cap_h2_ves * parm['h2_ves_capex'] * parm['h2_ves_om'])          
            + (cap_electrolyzer * parm['electr_capex'] * parm['electr_om'])
            + (cap_pv * parm['pv_capex'] * parm['pv_om']) 
            + (cap_wind_on * parm['wind_on_capex'] * parm['wind_on_om']) 
            + (cap_bat_en * parm['bat_en_capex'] * parm['bat_en_om']) 
            + (cap_bat_p * parm['bat_p_capex'] * parm['bat_p_om'])
            + (cap_hb * parm['hb_capex'] * parm['hb_om']) 
            + (cap_asu * parm['asu_capex'] * parm['asu_om']) 
            + (cap_grid * parm['grid_capex'] * parm['grid_om']) 
            )

    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    """Objective 2: life cycle GHG emissions"""
    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    """Operation"""
    an_ghg_op_grid_abs = gp.quicksum( (p_grid_abs[t] * df_data.ghg_impact.iloc[t]) for t in range(T)) 
    an_ghg_op_grid_inj = gp.quicksum( (p_grid_inj[t] * df_data.ghg_impact_cons.iloc[t]) for t in range(T))

    # No purchase of heat as it will be balanced in the optimal design
    an_op_ghg = (an_ghg_op_grid_abs - an_ghg_op_grid_inj)

    """Production and replacements"""    
    an_ghg_electrolyzer = (cap_electrolyzer * dict_ghg['ghg_imp_electr'] * (parm['project_lt']/parm['electr_lt'])) / parm['project_lt']   
    an_ghg_h2_ves = (cap_h2_ves * dict_ghg['ghg_imp_h2_ves'] * (parm['project_lt']/parm['h2_ves_lt'])) / parm['project_lt']     
    an_ghg_pv = (cap_pv * dict_ghg['ghg_imp_pv'] * (parm['project_lt']/parm['pv_lt'])) / parm['project_lt']  
    an_ghg_wind_on = (cap_wind_on * dict_ghg['ghg_imp_wind_on'] * (parm['project_lt']/parm['wind_on_lt'])) / parm['project_lt']   
    an_ghg_bat_en = (cap_bat_en * dict_ghg['ghg_imp_bat_cap'] * (parm['project_lt']/parm['bat_en_lt'])) / parm['project_lt'] 
    an_ghg_grid_ins = (cap_grid * dict_ghg['ghg_impact_grid_network'] * (parm['project_lt']/parm['grid_lt'])) / parm['project_lt'] 
    #an_ghg_bat_p = (cap_bat_p * dict_ghg['ghg_imp_bat_p'] * (parm['project_lt']/parm['bat_p_lt'])) / parm['project_lt']  

    ammonia_prod = gp.quicksum( p_hb[t] for t in range(T) )  
    an_ghg_hb =  dict_ghg['ghg_imp_hb'] * ammonia_prod
    nitrogen_demand = gp.quicksum( (parm['N_per_kgNH3'] * p_hb[t]) for t in range(T)) 
    an_ghg_asu = dict_ghg['ghg_imp_asu'] * nitrogen_demand

    an_op_ghg_inv = (an_ghg_electrolyzer +
                    an_ghg_h2_ves +
                    an_ghg_pv + an_ghg_wind_on +
                    an_ghg_bat_en + an_ghg_grid_ins + 
                    an_ghg_hb + an_ghg_asu)

    obj2 = an_op_ghg + an_op_ghg_inv

    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    """Total costs, including possible costs for CO2"""
    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    an_op_co2 = obj2 * (euro_ton_co2/1e3) if euro_ton_co2!=0 else 0  
    obj1 = an_op + an_capex + an_rep + an_om + an_op_co2
        
    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    """Set objectives"""
    """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    
    # add constraint to have x % less GHG emissions, implemented as inequality constraints to have a faster acceptable solution
    if eps_ghg_constraint:
        m.addConstr(obj2 <= eps_ghg_constraint)
        m.setObjective(obj1)    
    elif w_cost==1 and w_env==0:
        m.setObjective(obj1) 
    elif w_cost==0 and w_env==1:
        m.setObjective(obj2)         
    else:
        # Multi-objective problem with weights
        m.setObjectiveN(obj1, index = 0, weight = w_cost)
        m.setObjectiveN(obj2, index = 1, weight = w_env)

    if hybrid_green:
        red=0.6 #Certifhy GHG reduction assumed as for hydrogen, updated in 2050
        m.addConstr(obj2 <= (size_nh3_system*CC_IMPACT_NG_NH3*(1-red)))

    """
    Step 5: Solve model
    """

    # Add error handling for optimization
    try:
        m.optimize()

        # Check optimization status
        if logger:
            if m.status == gp.GRB.OPTIMAL:
                print("Optimization successful. Objective value:", m.objVal)
            elif m.status == gp.GRB.INFEASIBLE:
                print("Optimization failed: The model is infeasible.")
            elif m.status == gp.GRB.UNBOUNDED:
                print("Optimization failed: The model is unbounded.")
            else:
                print("Optimization failed with status:", m.status)
        
        # if model is infeasible, which can for example happen in off-grid situations
        # still provide something:
        if m.status == gp.GRB.INFEASIBLE:
            if logger:
                print(f"[Warning] Model infeasible for {export_alias} ({LOC_ELECT})")
            #print("Optimization failed: The model is infeasible.")
            # Create empty or placeholder outputs so the workflow continues
            overview_totals = pd.DataFrame()
            lca_results = pd.DataFrame()
            df_out = pd.DataFrame()
            return overview_totals, lca_results, df_out

    except gp.GurobiError as e:
        if logger:
            print("Gurobi Error:", e)

    """
    Step 6: Store variables values from optimal solution
    """ 

    """Get and store results in df"""     
    df_out = pd.DataFrame({
                            "time": df_data.index,
                            "p_grid_inj": m.getAttr('x',p_grid_inj).values(),
                            "p_grid_abs": m.getAttr('x',p_grid_abs).values(),
                            "bin_grid": m.getAttr('x',bin_grid).values(),
                            "p_battdis": m.getAttr('x',p_battdis).values(),
                            "p_battch": m.getAttr('x',p_battch).values(),
                            "E_batt": m.getAttr('x',E_batt).values(),
                            "bin_bat": m.getAttr('x',bin_bat).values(),
                            "e_h2_ves": m.getAttr('x',e_h2_ves).values(),
                            "p_h2_ves": m.getAttr('x',p_h2_ves).values(),
                            "f_elect": m.getAttr('x',f_elect).values(),
                            "p_elect": m.getAttr('x',p_elect).values(),
                            "p_solar_pv": m.getAttr('x',p_solar_pv).values(),
                            "p_wind_on": m.getAttr('x',p_wind_on).values(),
                            "p_hb": m.getAttr('x',p_hb).values(),
                            "x_hb": m.getAttr('x',x_hb).values() if consider_down_times else [0] * len(df_data),
                            "y_hb": m.getAttr('x',y_hb).values() if consider_down_times else [0] * len(df_data),
                            "z_hb": m.getAttr('x',z_hb).values() if consider_down_times else [0] * len(df_data),
                            "aux_hb": m.getAttr('x',aux_hb).values() if consider_down_times else [0] * len(df_data)
                                                       }).set_index("time")

    # Get single variables values
    cap_wind_on = cap_wind_on.x
    cap_pv = cap_pv.x
    cap_bat_en = cap_bat_en.x
    cap_bat_p = cap_bat_p.x
    cap_h2_ves = cap_h2_ves.x
    cap_electrolyzer = cap_electrolyzer.x
    cap_hb = cap_hb.x
    cap_asu = cap_asu.x
    cap_grid = cap_grid.x

    cf_hb = round(df_out.p_hb.sum()/(cap_hb*8760),3)
    if logger:
        print(f"Load factor HB unit: {cf_hb}")

    # Check whether obj function is same as expectations in formula
    end = time.time()
    
    # Get calculation time
    total_time = (end-start)/3600 #hours

    # Curtailment of renewables       
    if ( sum(cap_wind_on *  wind_MW_array_on) - sum(df_out.p_wind_on) ) > 0:
        curtailed_wind_on = (cap_wind_on * wind_MW_array_on) - df_out.p_wind_on
        ratio_wind_curtailed_on = curtailed_wind_on.sum() / sum(cap_wind_on * wind_MW_array_on)
    else:
        curtailed_wind_on =[0] * len(df_data)
        ratio_wind_curtailed_on = 0
        
    if ( sum(cap_pv * df_data.pv_MW_array) - sum(df_out.p_solar_pv) ) > 0:   
        curtailed_pv = (cap_pv * df_data.pv_MW_array) - df_out.p_solar_pv
        ratio_pv_curtailed = curtailed_pv.sum() / sum(cap_pv * df_data.pv_MW_array)
    else:
        curtailed_pv = [0] * len(df_data)
        ratio_pv_curtailed = 0     
    
    # Only get the optimized CO2 costs when required
    an_op_co2 = an_op_co2.getValue() if euro_ton_co2!=0 else 0

    # Printing Cost Weight
    if logger:
        print(f"Cost weight '{w_cost}'")

    # Printing Annual Costs and GHG Emissions
    annual_costs_keuro = round(obj1.getValue(), 2)
    annual_ghg_emissions_kt_co2_eq = round(obj2.getValue() / 1e3, 2)

    if logger:
        print(f"Annual costs are '{annual_costs_keuro}' k€")
        print(f"Specific ammonia production costs are: '{round(annual_costs_keuro*1e3/size_nh3_system,4)}' €/tNH3")
        print(f"Annual GHG emissions are '{annual_ghg_emissions_kt_co2_eq}' kt CO2-eq.")
        print(f"Specific ammonia CO2-intensity: '{round(annual_ghg_emissions_kt_co2_eq*1e3/size_nh3_system,4)}' tCO2/tNH3")
        
    #Create overview of electricity loads
    overview_totals = pd.DataFrame({
                # Capacities
                 "cap_pv": cap_pv,
                 "cap_bat_en": cap_bat_en,
                 "cap_bat_p": cap_bat_p,   
                 "cap_wind_on": cap_wind_on,   
                 "cap_h2_ves": cap_h2_ves,
                 "cap_electrolyzer": cap_electrolyzer, 
                 "cap_hb": cap_hb,
                 "cap_asu": cap_asu,
                 "cap_grid":cap_grid,
                 "total_time_h":total_time, #hours
                 "mip_gap":m.MIPGap*100, # in %
                 "total_costs": obj1.getValue(), 
                 "tCO2_tNH3": round(annual_ghg_emissions_kt_co2_eq*1e3/size_nh3_system,4),
                 "euro_tNH3": round(annual_costs_keuro*1e3/size_nh3_system,4),
                 #Operation
                 "operation_costs": an_op.getValue(), 
                 "an_costs_op_grid_abs": an_op_grid_abs.getValue(),  
                 "an_costs_op_grid_inj": -an_op_grid_inj.getValue(),
                 "an_costs_op_co2": an_op_co2,

                 # Investment
                 "investment_costs": an_capex.getValue(), 
                 "an_costs_capex_pv": an_capex_pv.getValue(), 
                 "an_costs_capex_bat_en": an_capex_bat_en.getValue(),
                 "an_costs_capex_bat_p": an_capex_bat_p.getValue(),

                 "an_costs_capex_hb": an_capex_hb.getValue(),
                 "an_costs_capex_asu": an_capex_asu.getValue(),
                 "an_costs_capex_grid": an_capex_grid_ins.getValue(), 
                 "an_costs_capex_wind_on": an_capex_wind_on.getValue(),

                 "an_costs_capex_electrolyzer": an_capex_electrolyzer.getValue(),
                 "an_costs_capex_h2_ves": an_capex_h2_ves.getValue(), 

                 # Replacement and O&M
                 "an_costs_rep": an_rep.getValue(), 
                 "an_costs_om": an_om.getValue(),

                 #GHG emissions
                 "total_ghg":obj2.getValue(), 
                 "operational_ghg": an_op_ghg.getValue(), 
                 "an_ghg_op_grid_abs":an_ghg_op_grid_abs.getValue(),
                 "an_ghg_op_grid_inj": -an_ghg_op_grid_inj.getValue(),
                 "an_ghg_pv": an_ghg_pv.getValue(), 
                 "an_ghg_bat_en": an_ghg_bat_en.getValue(),
                 #"an_ghg_bat_p": an_ghg_bat_p.getValue(),
                 "an_ghg_hb": an_ghg_hb.getValue(),
                 "an_ghg_asu": an_ghg_asu.getValue(),
                 "an_ghg_wind_on": an_ghg_wind_on.getValue(),
                 "an_ghg_electrolyzer": an_ghg_electrolyzer.getValue(),
                 "an_ghg_h2_ves": an_ghg_h2_ves.getValue(),      
                 "an_ghg_grid_ins": an_ghg_grid_ins.getValue(), 
                    
                 "share_ghg_prod": an_op_ghg_inv.getValue()/obj2.getValue(),
                 "share_inv_total": an_capex.getValue()/obj1.getValue(),
        
                "ratio_pv_curtailed": ratio_pv_curtailed,   
                "ratio_wind_curtailed_on": ratio_wind_curtailed_on,    
        
                 "ghg_grid_mean": df_data.ghg_impact.mean(),
                 "cost_grid_mean":df_data.grid_abs_price.mean(),   
                 "dr": parm['dr'],
                 "grid_elect_demand": sum(df_out.p_grid_abs) - sum(df_out.p_grid_inj), 
                                   }, index=[ "opt_results_{}_{}_{}".format(ASSESSMENT_YEAR,w_cost,
                                                                                              round(eps_ghg_constraint,2))])
    if export_results:
        overview_totals.T.to_excel(r"results\opt_results_{}_{}_{}_{}_{}_{}.xlsx".format(ASSESSMENT_YEAR,w_cost,autonomous_elect, round(eps_ghg_constraint,2),euro_ton_co2,
                                                                                                                                              export_alias))       
        df_out.to_excel(r"results\result_{}_{}_{}_{}_{}_{}.xlsx".format(ASSESSMENT_YEAR,w_cost,autonomous_elect, round(eps_ghg_constraint,2),euro_ton_co2, 
                                                                                                                                                    export_alias))
    # Checks for simultaneous operations and raises an error if found.
    check_simultaneous_operations(df_out)
    
    # Define input variables for LCA
    input_vars = {
                "parm": parm,
                "loc_elect": LOC_ELECT,
                "cap_wind_on": cap_wind_on,
                "cap_pv": cap_pv,
                "cap_bat_en": cap_bat_en,
                #"cap_bat_p": cap_bat_p,
                "cap_h2_ves": cap_h2_ves,
                "cap_electrolyzer": cap_electrolyzer,
                "cap_hb": ammonia_prod.getValue() * 1e3, #kg NH3
                "cap_asu": nitrogen_demand.getValue() * 1e3, #kg N2
                "cap_grid": cap_grid,
                "summed_grid_abs": sum(df_out.p_grid_abs),
                "summed_grid_inj": sum(df_out.p_grid_inj),
                #"summed_hb": sum(df_out.p_hb),
                "ghgs_opt": obj2.getValue() * 1000, # it is in tonnes, convert to kg
                "w_cost": w_cost,
                "sec_db": sec_db,
                "credit_env_export": credit_env_export,
                "lcia_method": CC_METHOD,
                "epsilon_constraint": eps_ghg_constraint,
            }

    # Call environmental_lca function with input variables
    lca_results = ""       

    # Separator Line
    if logger:
        print("***************************************************************")
        # Printing Calculation Time and MIP Gap
        calculation_time_hours = round(total_time, 2)
        mip_gap_percentage = round(m.MIPGap * 100, 2)
        print(f"Calculation time is '{calculation_time_hours}' hours")
        print(f"Final MIP gap value: '{mip_gap_percentage}%'")
    
    if save_operation_output:
        return overview_totals, lca_results, input_vars, df_out
    else:
        return overview_totals, lca_results, input_vars
    
def calc_crf(r: float, lt: float) -> float:
    """
    Calculates capital recovery factor.

    Args:
        r (float): dicount rate/WACC [-].
        lt (float): lifetime [years].
    Returns:
        float: capital recovery factor.
    """
    return (r * (1 + r) ** lt) / ((1 + r) ** lt - 1)

def rep_annual_int(unit_inv_cost: float, lt: int, r: float, ry: float, rep_factor=0.75) -> float:
    """
    Calculates replacement costs for a technology.

    Args:
        unit_inv_cost (float): Replacement cost [CHF/euro/...].
        lt (int): Lifetime of the project or system [years].
        r (float): Interest rate [%].
        ry (float): Replacement year [year].
        rep_factor (float): share of replacement costs compared to full investment [-].

    Returns:
        float: Total replacement cost.
    """
    c_rep_total = 0
    
    # 75% of initial costs for replacement, assuming some components can be used and due to technological improvement
    unit_inv_cost = rep_factor * unit_inv_cost
    
    # 1. If the lifetime of the system is bigger than the replacement year, there is a residual value
    if ry > lt:
        # Check the amount left over, i.e. how much of the component is left after the system lifetime
        rest = 1 - (lt/ry)
        crf = calc_crf(r, lt)
        c_rep_a = crf*((unit_inv_cost * rest) / ((1+r)**lt)) 
        # Reduce the replacement costs
        c_rep_total -= c_rep_a
        
    # 2. If the replacement year of a component is smaller than the system lifetime, then there are replacement costs
    elif ry < lt:
        replacement_times = (lt/ry)
        counter_ry = ry
        crf = calc_crf(r, lt)
        
        # Iterate through replacement times
        for _ in range(int(replacement_times)):
            # Calculate replacement costs
            c_rep_a = crf*(unit_inv_cost / ((1+r)**ry))
            
            # Add to the total replacement costs
            c_rep_total += c_rep_a
            
            # Update counters
            ry += counter_ry
                
        # Calculate residual value
        rest = 1 - (replacement_times % 1)
        c_rep_a = crf*((unit_inv_cost * rest) / ((1+r)**lt))
                
        # Reduce the replacement costs
        c_rep_total -= c_rep_a
    
    # 3. Lifetime of a system component is exactly the lifetime of the system   
    else:
        c_rep_total = 0
    
    return c_rep_total

def check_simultaneous_operations(df_out):
    """
    Checks for simultaneous operations and raises an error if found.

    Args:
        df_out (DataFrame): DataFrame containing the relevant columns for the checks (from the optimization).
        error_message (str): The error message to be raised if a simultaneous operation is found.
    """
    checks = [
        ('Battery', df_out['p_battch'], df_out['p_battdis']),
        ('Grid', df_out['p_grid_abs'], df_out['p_grid_inj'])
    ]

    for label, charge, discharge in checks:
        simultaneous = charge[(charge > 10**-4) & (discharge > 10**-4)]
        if simultaneous.sum() > 0:
            df_out.to_excel("error_file.xlsx")
            raise ValueError(f"WARNING: {label} is charging and discharging at the same time")