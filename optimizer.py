import numpy as np
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory


def optimize_transit(
    demand,
    loop_time,
    B=40,
    tau=120,
    capacity=35,
    cost_A=150,
    alpha=0.5,
    beta=0.5,
    delta=0.1,
):
    """
    Run the transit bus allocation optimization.

    Parameters
    ----------
    demand : numpy.ndarray
        Route x time demand matrix.

    loop_time : numpy.ndarray
        Route x time loop-time matrix.

    B : int
        Number of buses available.

    tau : float
        Time/headway parameter used in effective capacity.

    capacity : float
        Capacity of one bus.

    cost_A : float
        Activation cost per bus.

    alpha : float
        Weight on bus activation cost.

    beta : float
        Weight on demand allocation penalty.

    delta : float
        Small positive value used in the reciprocal penalty.

    Returns
    -------
    dict
        Optimization results and derived output tables.
    """

    # Convert inputs to numpy arrays
    demand = np.asarray(demand, dtype=float)
    loop_time = np.asarray(loop_time, dtype=float)

    # Validate dimensions
    if demand.ndim != 2:
        raise ValueError("Demand must be a 2-dimensional matrix.")

    if loop_time.ndim != 2:
        raise ValueError("Loop time must be a 2-dimensional matrix.")

    if demand.shape != loop_time.shape:
        raise ValueError(
            f"Demand shape {demand.shape} does not match "
            f"loop-time shape {loop_time.shape}."
        )

    if B < 1:
        raise ValueError("Number of buses must be at least 1.")

    if capacity <= 0:
        raise ValueError("Bus capacity must be greater than 0.")

    if tau <= 0:
        raise ValueError("Tau must be greater than 0.")

    if cost_A < 0:
        raise ValueError("Activation cost cannot be negative.")

    if delta <= 0:
        raise ValueError("Delta must be greater than 0.")

    if np.any(demand < 0):
        raise ValueError("Demand cannot contain negative values.")

    if np.any(loop_time <= 0):
        raise ValueError("Loop times must be greater than 0.")

    R, T = demand.shape

    # ---------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------

    model = pyo.ConcreteModel()

    # SETS
    model.BUSES = pyo.Set(initialize=range(B))
    model.ROUTES = pyo.Set(initialize=range(R))
    model.TIME = pyo.Set(initialize=range(T))

    # ---------------------------------------------------------
    # DECISION VARIABLES
    # ---------------------------------------------------------

    # Whether bus b is activated
    model.y = pyo.Var(
        model.BUSES,
        domain=pyo.Binary
    )

    # Whether bus b serves route r during time t
    model.x = pyo.Var(
        model.BUSES,
        model.ROUTES,
        model.TIME,
        domain=pyo.Binary
    )

    # Whether bus b is in service during time t
    model.U = pyo.Var(
        model.BUSES,
        model.TIME,
        domain=pyo.Binary
    )

    # Number of buses assigned to route r during time t
    model.z = pyo.Var(
        model.ROUTES,
        model.TIME,
        domain=pyo.NonNegativeIntegers,
        bounds=(0, B)
    )

    # Binary variables used to linearize reciprocal penalty
    model.w = pyo.Var(
        model.ROUTES,
        model.TIME,
        range(B + 1),
        domain=pyo.Binary
    )

    # ---------------------------------------------------------
    # CONSTRAINTS
    # ---------------------------------------------------------

    model.constraints = pyo.ConstraintList()

    # Each bus may serve at most one route per time block
    for b in range(B):
        for t in range(T):
            model.constraints.add(
                sum(
                    model.x[b, r, t]
                    for r in range(R)
                ) <= 1
            )

    # A bus may only be assigned if activated
    for b in range(B):
        for r in range(R):
            for t in range(T):
                model.constraints.add(
                    model.x[b, r, t] <= model.y[b]
                )

    # Demand coverage constraints
    for r in range(R):
        for t in range(T):

            effective_capacity = (
                capacity *
                (tau / loop_time[r, t])
            )

            coverage = sum(
                model.x[b, r, t] *
                effective_capacity
                for b in range(B)
            )

            model.constraints.add(
                coverage >= demand[r, t]
            )

    # Bus utilization
    for b in range(B):
        for t in range(T):
            model.constraints.add(
                model.U[b, t] ==
                sum(
                    model.x[b, r, t]
                    for r in range(R)
                )
            )

    # Number of buses assigned to each route/time
    for r in range(R):
        for t in range(T):
            model.constraints.add(
                model.z[r, t] ==
                sum(
                    model.x[b, r, t]
                    for b in range(B)
                )
            )

    # Linearization of reciprocal term
    for r in range(R):
        for t in range(T):

            model.constraints.add(
                sum(
                    model.w[r, t, k]
                    for k in range(B + 1)
                ) == 1
            )

            model.constraints.add(
                model.z[r, t] ==
                sum(
                    k * model.w[r, t, k]
                    for k in range(B + 1)
                )
            )

    # ---------------------------------------------------------
    # OBJECTIVE FUNCTION
    # ---------------------------------------------------------

    recip = {
        k: 1.0 / (k + delta)
        for k in range(B + 1)
    }

    def objective_rule(model):

        activation_cost = alpha * sum(
            cost_A * model.y[b]
            for b in range(B)
        )

        nonlinear_penalty = beta * sum(
            demand[r, t] *
            sum(
                recip[k] * model.w[r, t, k]
                for k in range(B + 1)
            )
            for r in range(R)
            for t in range(T)
        )

        return activation_cost + nonlinear_penalty

    model.objective = pyo.Objective(
        rule=objective_rule,
        sense=pyo.minimize
    )

    # ---------------------------------------------------------
    # SOLVE
    # ---------------------------------------------------------

    solver = SolverFactory("cbc")

    if not solver.available(exception_flag=False):
        raise RuntimeError(
            "CBC solver is not available. "
            "Install coinor-cbc before running the application."
        )

    results = solver.solve(model, tee=False)

    # ---------------------------------------------------------
    # SOLVER STATUS
    # ---------------------------------------------------------

    solver_status = str(results.solver.status)
    termination_condition = str(
        results.solver.termination_condition
    )

    # ---------------------------------------------------------
    # EXTRACT RESULTS
    # ---------------------------------------------------------

    objective_value = pyo.value(model.objective)

    # Activated buses
    activated_buses = []

    for b in range(B):
        if pyo.value(model.y[b]) > 0.5:
            activated_buses.append(b + 1)

    # Assignment table
    assignments = []

    for b in range(B):
        for t in range(T):
            for r in range(R):

                if pyo.value(model.x[b, r, t]) > 0.5:

                    assignments.append({
                        "Bus": b + 1,
                        "Route": r + 1,
                        "Time": t + 1,
                        "Assigned": 1
                    })

    assignments_df = pd.DataFrame(assignments)

    # Route/time summary
    route_summary = []

    for r in range(R):
        for t in range(T):

            buses_assigned = int(
                round(pyo.value(model.z[r, t]))
            )

            effective_capacity = (
                capacity *
                (tau / loop_time[r, t])
            )

            coverage = (
                buses_assigned *
                effective_capacity
            )

            route_summary.append({
                "Route": r + 1,
                "Time Block": t + 1,
                "Demand": demand[r, t],
                "# Buses Assigned": buses_assigned,
                "Effective Capacity per Bus": effective_capacity,
                "Coverage (Total Capacity)": coverage,
                "Surplus Capacity": coverage - demand[r, t],
                "Headway": (
                    tau / buses_assigned
                    if buses_assigned > 0
                    else np.nan
                )
            })

    route_summary_df = pd.DataFrame(route_summary)

    # Bus utilization
    utilization = []

    for b in range(B):

        active = int(
            round(pyo.value(model.y[b]))
        )

        time_blocks_in_service = sum(
            int(round(pyo.value(model.U[b, t])))
            for t in range(T)
        )

        utilization.append({
            "Bus Number": b + 1,
            "Activated? (0 = No, 1 = Yes)": active,
            "# Time Blocks in Service": time_blocks_in_service,
        })

    utilization_df = pd.DataFrame(utilization)

    return {
        "model": model,
        "objective_value": objective_value,
        "solver_status": solver_status,
        "termination_condition": termination_condition,
        "activated_buses": activated_buses,
        "num_activated_buses": len(activated_buses),
        "assignments": assignments_df,
        "route_summary": route_summary_df,
        "utilization": utilization_df,
    }
