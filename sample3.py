from docplex.mp.model import Model
import math

# -----------------------------
# Data
# -----------------------------
num_customers = 5
locations = [(30, 40), (40, 30), (20, 10), (10, 20), (50, 50), (25, 25)]  # [0]=depot
depot = 0

demand = [0, 10, 15, 10, 20, 25]     # 0 for depot
vehicle_capacity = 40
battery_range = 100.0                 # max distance per full charge (no recharging modeled yet)
num_vehicles = 3

N = len(locations)
CUST = range(1, N)
VEH = range(num_vehicles)
ALL = range(N)

# -----------------------------
# Distances
# -----------------------------
def euclidean(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

dist = [[0.0]*N for _ in ALL]
for i in ALL:
    for j in ALL:
        if i != j:
            dist[i][j] = euclidean(locations[i], locations[j])

# Pre-forbid arcs longer than battery_range
for i in ALL:
    for j in ALL:
        if i != j and dist[i][j] > battery_range:
            dist[i][j] = float('inf')  # we’ll disallow these arcs

# -----------------------------
# Model
# -----------------------------
mdl = Model(name="Electric CVRP")

# x[i,j,k] = 1 if vehicle k goes i -> j
x = mdl.binary_var_dict(
    [(i, j, k) for i in ALL for j in ALL for k in VEH if i != j and dist[i][j] < float('inf')],
    name="x"
)

# load[i,k]  : load upon arrival at i by k (MTZ-like potential for capacity + subtours)
load = mdl.continuous_var_dict([(i, k) for i in ALL for k in VEH], lb=0, ub=vehicle_capacity, name="load")

# battery[i,k] : remaining battery upon arrival at i by k
battery = mdl.continuous_var_dict([(i, k) for i in ALL for k in VEH], lb=0, ub=battery_range, name="battery")

# vehicle use indicator
z = mdl.binary_var_dict([k for k in VEH], name="z")

# -----------------------------
# Objective: minimize total distance
# -----------------------------
mdl.minimize(mdl.sum(dist[i][j] * x[i, j, k] for (i, j, k) in x.keys()))

# -----------------------------
# Constraints
# -----------------------------

# 1) Each customer visited exactly once (by exactly one vehicle)
for j in CUST:
    mdl.add_constraint(mdl.sum(x[i, j, k]
                               for k in VEH
                               for i in ALL
                               if i != j and (i, j, k) in x) == 1, f"visit_{j}")

# 2) Flow conservation on each vehicle for each non-depot node
for k in VEH:
    for v in CUST:
        inbound = mdl.sum(x[i, v, k] for i in ALL if i != v and (i, v, k) in x)
        outbound = mdl.sum(x[v, j, k] for j in ALL if j != v and (v, j, k) in x)
        mdl.add_constraint(inbound == outbound, f"flow_{v}_{k}")
        # At most one in/out if you want to force simple paths per vehicle:
        mdl.add_constraint(inbound <= 1, f"deg_in_{v}_{k}")
        mdl.add_constraint(outbound <= 1, f"deg_out_{v}_{k}")

# 3) Depot start and end per vehicle, linked to z_k
for k in VEH:
    depart = mdl.sum(x[depot, j, k] for j in CUST if (depot, j, k) in x)
    arrive = mdl.sum(x[i, depot, k] for i in CUST if (i, depot, k) in x)
    mdl.add_constraint(depart == arrive, f"depot_balance_{k}")
    mdl.add_constraint(depart <= z[k], f"use_link_depart_{k}")
    mdl.add_constraint(arrive <= z[k], f"use_link_arrive_{k}")

# 4) Capacity propagation (MTZ style) and bounds
for k in VEH:
    # start empty at depot
    mdl.add_constraint(load[depot, k] == 0, f"load_depot_{k}")
    for i in ALL:
        mdl.add_constraint(load[i, k] <= vehicle_capacity, f"cap_bound_{i}_{k}")
    for i in ALL:
        for j in CUST:
            if i != j and (i, j, k) in x:
                # If arc i->j is used by k, the load increases by demand[j]
                # Big-M with M = vehicle_capacity
                mdl.add_constraint(
                    load[j, k] >= load[i, k] + demand[j] - vehicle_capacity*(1 - x[i, j, k]),
                    f"load_prop_{i}_{j}_{k}"
                )

# 5) Battery propagation and initial battery at depot
M_batt = battery_range
for k in VEH:
    mdl.add_constraint(battery[depot, k] == battery_range, f"batt_depot_{k}")
    for i in ALL:
        mdl.add_constraint(battery[i, k] <= battery_range, f"batt_bound_{i}_{k}")
    for i in ALL:
        for j in ALL:
            if i != j and (i, j, k) in x:
                # If arc i->j is used, battery must drop by dist[i][j]
                mdl.add_constraint(
                    battery[j, k] <= battery[i, k] - dist[i][j] + M_batt*(1 - x[i, j, k]),
                    f"batt_prop_{i}_{j}_{k}"
                )

# 6) Forbid arcs longer than one charge (already filtered); add explicit safety:
for k in VEH:
    for i in ALL:
        for j in ALL:
            if i != j and (i, j, k) in x and dist[i][j] > battery_range:
                mdl.add_constraint(x[i, j, k] == 0, f"ban_long_arc_{i}_{j}_{k}")
"""
 7) Subtour elimination (classic MTZ with node potentials u[i,k])
    We reuse load[i,k] as potential because it strictly increases when visiting customers.
    This is enough to break cycles that don't include the depot.
    (The load propagation above acts as MTZ.)
"""
# -----------------------------
# Solve
# -----------------------------
solution = mdl.solve(log_output=True)

if not solution:
    print("No solution found.")
else:
    print("Objective (total distance):", solution.objective_value)

    # Reconstruct and print routes per vehicle
    for k in VEH:
        # Build adjacency list from solution
        succ = {}
        for i in ALL:
            for j in ALL:
                if i != j and (i, j, k) in x and x[i, j, k].solution_value > 0.5:
                    succ[i] = j
        if depot not in succ:
            continue
        route = [depot]
        while route[-1] in succ:
            nxt = succ[route[-1]]
            route.append(nxt)
            if nxt == depot:
                break
            if len(route) > N + 2:
                break  # safety
        if len(route) > 2:
            print(f"Vehicle {k} used={int(z[k].solution_value > 0.5)} route: {route}")
"""
Problem of “No solution found”
Two things could have over-constrained the model:

1. Battery propagation only with ≤ and applied on every (i,j) can chain tight 
upper bounds and make the battery system inconsistent.

2. No lower bound (≥0) on battery in that file.

Solution:
Replace the battery update with a two-sided big-M equality applied only on existing arcs 
and add explicit 0 ≤ battery ≤ range. That should cure the infeasibility on the data.
"""
