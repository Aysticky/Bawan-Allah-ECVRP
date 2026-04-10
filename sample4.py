from docplex.mp.model import Model
import math

# -----------------------------
# Sample data
# -----------------------------
num_customers = 5
locations = [
    (30, 40),  # 0 depot
    (40, 30),
    (20, 10),
    (10, 20),
    (50, 50),
    (25, 25),
    # optional stations (can remove to test baseline feasibility)
    (35, 35),  # 6: station A
    (15, 15),  # 7: station B
]
depot = 0

demand = [0, 10, 15, 10, 20, 25, 0, 0]   # 0 for depot and stations
vehicle_capacity = 40
battery_range = 100.0
num_vehicles = 3

# Energy model params: E = distance * (a + b * avg_load)
a_fixed = 1.0
b_load  = 0.02

# Indices
N = len(locations)
ALL = range(N)
CUST = [i for i in range(1, N) if demand[i] > 0]
STATIONS = [i for i in range(N) if demand[i] == 0 and i != depot]  # set [] to disable charging nodes
VEH = range(num_vehicles)

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
            dist[i][j] = float('inf')

# -----------------------------
# Model
# -----------------------------
mdl = Model(name="Electric CVRP + Recharging, Energy Objective (fixed)")

# x[i,j,k] = 1 if vehicle k goes i -> j
x = mdl.binary_var_dict(
    [(i, j, k) for i in ALL for j in ALL for k in VEH if i != j and dist[i][j] < float('inf')],
    name="x"
)

# load[i,k]  : load AFTER leaving node i by vehicle k
load = mdl.continuous_var_dict([(i, k) for i in ALL for k in VEH], lb=0, ub=vehicle_capacity, name="load")

# Battery split: b_in[v,k] = before node v; b_out[v,k] = after node v
b_in  = mdl.continuous_var_dict([(i, k) for i in ALL for k in VEH], lb=0, ub=battery_range, name="b_in")
b_out = mdl.continuous_var_dict([(i, k) for i in ALL for k in VEH], lb=0, ub=battery_range, name="b_out")

# Vehicle use indicator
z = mdl.binary_var_dict(VEH, name="z")

# y[i,j,k] = load[i,k] * x[i,j,k]  (for energy linearization)
y = mdl.continuous_var_dict([(i, j, k) for (i, j, k) in x.keys()], lb=0, ub=vehicle_capacity, name="y")

# r[s,k] = 1 if we CHARGE at station s when we visit it
r = mdl.binary_var_dict([(s, k) for s in STATIONS for k in VEH], name="r")

# -----------------------------
# Objective: minimize total ENERGY
# E_ijk = dist[i][j] * (a_fixed*x + b_load*( y[i,j,k] + 0.5*demand[j]*x ))
# avg_load ≈ load[i,k] + 0.5*demand[j]
# -----------------------------
mdl.minimize(
    mdl.sum(
        dist[i][j] * (a_fixed * x[i, j, k] + b_load * (y[i, j, k] + 0.5 * demand[j] * x[i, j, k]))
        for (i, j, k) in x.keys()
    )
)

# -----------------------------
# Constraints
# -----------------------------

# 1) Each customer visited exactly once
for j in CUST:
    mdl.add_constraint(mdl.sum(x[i, j, k] for k in VEH for i in ALL if i != j and (i, j, k) in x) == 1, f"visit_{j}")

# 2) Flow conservation + degree caps per vehicle (customers and stations)
for k in VEH:
    for v in range(1, N):
        inbound = mdl.sum(x[i, v, k] for i in ALL if i != v and (i, v, k) in x)
        outbound = mdl.sum(x[v, j, k] for j in ALL if j != v and (v, j, k) in x)
        mdl.add_constraint(inbound == outbound, f"flow_{v}_{k}")
        mdl.add_constraint(inbound <= 1, f"deg_in_{v}_{k}")
        mdl.add_constraint(outbound <= 1, f"deg_out_{v}_{k}")

# 3) Depot balance and vehicle-use linking
for k in VEH:
    depart = mdl.sum(x[depot, j, k] for j in range(1, N) if (depot, j, k) in x)
    arrive = mdl.sum(x[i, depot, k] for i in range(1, N) if (i, depot, k) in x)
    mdl.add_constraint(depart == arrive, f"depot_balance_{k}")
    mdl.add_constraint(depart <= z[k], f"use_link_dep_{k}")
    mdl.add_constraint(arrive <= z[k], f"use_link_arr_{k}")

# 4) Capacity propagation (MTZ) with "after leaving node" load
for k in VEH:
    mdl.add_constraint(load[depot, k] == 0, f"load_depot_{k}")
    for (i, j, kk) in x.keys():
        if kk != k: 
            continue
        # Big-M equality: load[j] == load[i] + demand[j] when x=1
        mdl.add_constraint(load[j, k] >= load[i, k] + demand[j] - vehicle_capacity * (1 - x[i, j, k]))
        mdl.add_constraint(load[j, k] <= load[i, k] + demand[j] + vehicle_capacity * (1 - x[i, j, k]))

# -----------------------------
# Battery model (fixed)
# -----------------------------
M = battery_range

# Depot: full battery before and after
for k in VEH:
    mdl.add_constraint(b_in[depot, k]  == battery_range, f"bin_depot_{k}")
    mdl.add_constraint(b_out[depot, k] == battery_range, f"bout_depot_{k}")

# Arc propagation: arriving battery BEFORE node j equals previous node's AFTER minus distance
for (i, j, k) in x.keys():
    mdl.add_constraint(b_in[j, k] >= b_out[i, k] - dist[i][j] - M * (1 - x[i, j, k]))
    mdl.add_constraint(b_in[j, k] <= b_out[i, k] - dist[i][j] + M * (1 - x[i, j, k]))

# Node update:
# - For stations s: if r[s,k]=1 then b_out[s,k] = battery_range; else b_out[s,k] = b_in[s,k]
# - For customers v: force r[v,k]=0 and b_out[v,k] = b_in[v,k]
for v in range(1, N):
    for k in VEH:
        if v in STATIONS:
            # Can only charge if we actually visit s (both in and out)
            in_v  = mdl.sum(x[i, v, k] for i in ALL if i != v and (i, v, k) in x)
            out_v = mdl.sum(x[v, j, k] for j in ALL if j != v and (v, j, k) in x)
            mdl.add_constraint(r[v, k] <= in_v)
            mdl.add_constraint(r[v, k] <= out_v)
            # If r=1 => b_out = full; if r=0 => b_out = b_in
            mdl.add_constraint(b_out[v, k] >= battery_range - M * (1 - r[v, k]))
            mdl.add_constraint(b_out[v, k] <= battery_range + M * (1 - r[v, k]))
            mdl.add_constraint(b_out[v, k] >= b_in[v, k] - M * r[v, k])
            mdl.add_constraint(b_out[v, k] <= b_in[v, k] + M * r[v, k])
        else:
            # Not a station: no charging
            # Create a dummy r=0 by equality (keeps model simpler than defining separate r for customers)
            mdl.add_constraint(b_out[v, k] == b_in[v, k])

# Safety: forbid arcs longer than one full charge (already filtered above)
for (i, j, k) in x.keys():
    if dist[i][j] > battery_range:
        mdl.add_constraint(x[i, j, k] == 0)

# -----------------------------
# Linearization for y = load[i,k] * x[i,j,k]
# -----------------------------
for (i, j, k) in x.keys():
    mdl.add_constraint(y[i, j, k] <= load[i, k])
    mdl.add_constraint(y[i, j, k] <= vehicle_capacity * x[i, j, k])
    mdl.add_constraint(y[i, j, k] >= load[i, k] - vehicle_capacity * (1 - x[i, j, k]))

# -----------------------------
# Solve
# -----------------------------
solution = mdl.solve(log_output=True)

if not solution:
    print("No solution found.")
else:
    print("Objective (total energy):", solution.objective_value)
    for k in VEH:
        succ = {}
        for (i, j, kk) in x.keys():
            if kk == k and x[i, j, k].solution_value > 0.5:
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
                break
        if len(route) > 2:
            charges = [v for v in route if v in STATIONS and r[v, k].solution_value > 0.5]
            print(f"Vehicle {k} route: {route} ; charges at: {charges}")


"""
Output from command line:
(cplex_env) 
User@Meadows-Ay MINGW64 ~/Desktop/Study/BawaAllah/codes/New_codes (main)
$ python sample4.py
Version identifier: 22.1.1.0 | 2022-11-27 | 9160aff4d
CPXPARAM_Read_DataCheck                          1
Tried aggregator 1 time.
MIP Presolve eliminated 348 rows and 99 columns.
MIP Presolve modified 672 coefficients.
Reduced MIP has 935 rows, 294 columns, and 2898 nonzeros.
Reduced MIP has 126 binaries, 0 generals, 0 SOSs, and 0 indicators.
Presolve time = 0.00 sec. (2.00 ticks)
Probing fixed 18 vars, tightened 93 bounds.
Probing time = 0.00 sec. (1.52 ticks)
Tried aggregator 1 time.
MIP Presolve eliminated 114 rows and 36 columns.
MIP Presolve modified 90 coefficients.
Reduced MIP has 821 rows, 258 columns, and 2502 nonzeros.
Reduced MIP has 108 binaries, 0 generals, 0 SOSs, and 0 indicators.
Presolve time = 0.00 sec. (2.01 ticks)
Probing time = 0.00 sec. (1.41 ticks)
Tried aggregator 1 time.
Detecting symmetries...
Reduced MIP has 821 rows, 258 columns, and 2502 nonzeros.
Reduced MIP has 108 binaries, 0 generals, 0 SOSs, and 0 indicators.
Presolve time = 0.00 sec. (1.81 ticks)
Probing fixed 3 vars, tightened 3 bounds.
Probing time = 0.00 sec. (1.56 ticks)
Clique table members: 1178.
MIP emphasis: balance optimality and feasibility.
MIP search method: dynamic search.
Parallel mode: deterministic, using up to 4 threads.
Root relaxation solution time = 0.00 sec. (1.87 ticks)

        Nodes                                         Cuts/
   Node  Left     Objective  IInf  Best Integer    Best Bound    ItCnt     Gap

      0     0      136.9563    17                    136.9563       40
      0     0      136.9563    21                    Cuts: 28       80
      0     0      136.9563    12                    Cuts: 14      117
      0     0      136.9563    12                    Cuts: 37      142
      0     0        cutoff                                        142
Elapsed time = 0.25 sec. (75.48 ticks, tree = 0.01 MB, solutions = 0)

Clique cuts applied:  3
Implied bound cuts applied:  30
Flow cuts applied:  4
Mixed integer rounding cuts applied:  15
Gomory fractional cuts applied:  1

Root node processing (before b&c):
  Real time             =    0.25 sec. (75.49 ticks)
Parallel b&c, 4 threads:
  Real time             =    0.00 sec. (0.00 ticks)
  Sync time (average)   =    0.00 sec.
  Wait time (average)   =    0.00 sec.
                          ------------
Total (root+branch&cut) =    0.25 sec. (75.49 ticks)
No solution found.
(cplex_env) 
"""
