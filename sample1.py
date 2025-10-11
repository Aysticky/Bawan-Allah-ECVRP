from docplex.mp.model import Model
import numpy as np
from collections import defaultdict

num_customers = 5

locations = [(30, 40), (40, 30), (20, 10), (10, 20), (50, 50), (25, 25)]  # depot + 5 customers
depot = 0

demand = [0, 10, 15, 10, 20, 25]  # demand at each node
vehicle_capacity = 40
battery_range = 100  # max distance a vehicle can travel on full charge
num_vehicles = 3

# Compute Euclidean distance matrix
def euclidean(a, b):
    return np.hypot(a[0] - b[0], a[1] - b[1])

distance = np.zeros((len(locations), len(locations)))
for i in range(len(locations)):
    for j in range(len(locations)):
        distance[i][j] = euclidean(locations[i], locations[j])

# Building the model
mdl = Model(name='Electric CVRP')

# Binary variable x[i,j,k]: vehicle k goes from i to j
x = mdl.binary_var_dict(
    [ (i, j, k) for i in range(len(locations))
                  for j in range(len(locations))
                  for k in range(num_vehicles) if i != j ], 
    name='x')

# Load variable: load of vehicle k after visiting customer i
load = mdl.continuous_var_dict(
    [(i, k) for i in range(len(locations)) for k in range(num_vehicles)],
    name='load')

# Battery variable: remaining battery of vehicle k at node i
battery = mdl.continuous_var_dict(
    [(i, k) for i in range(len(locations)) for k in range(num_vehicles)],
    name='battery')

# Minimize total distance
mdl.minimize(
    mdl.sum(x[i, j, k] * distance[i][j]
            for i in range(len(locations))
            for j in range(len(locations))
            for k in range(num_vehicles) if i != j)
)

# Constraints
# Each customer is visited exactly once
for j in range(1, len(locations)):
    mdl.add_constraint(mdl.sum(x[i, j, k]
                               for i in range(len(locations)) if i != j
                               for k in range(num_vehicles)) == 1)

# Vehicle leaves depot
for k in range(num_vehicles):
    mdl.add_constraint(mdl.sum(x[depot, j, k] for j in range(1, len(locations))) <= 1)

# Flow conservation
for k in range(num_vehicles):
    for h in range(1, len(locations)):
        mdl.add_constraint(
            mdl.sum(x[i, h, k] for i in range(len(locations)) if i != h) ==
            mdl.sum(x[h, j, k] for j in range(len(locations)) if j != h)
        )

# Capacity constraints
for i in range(1, len(locations)):
    for k in range(num_vehicles):
        mdl.add_constraint(load[i, k] >= demand[i] * 
                           mdl.sum(x[j, i, k] for j in range(len(locations)) if j != i))
        mdl.add_constraint(load[i, k] <= vehicle_capacity)

# Battery constraints
for i in range(len(locations)):
    for j in range(len(locations)):
        for k in range(num_vehicles):
            if i != j:
                mdl.add_constraint(
                    battery[j, k] >= battery[i, k] - distance[i][j] - 
                    (1 - x[i, j, k]) * battery_range
                )

# Battery and load initialization
for k in range(num_vehicles):
    mdl.add_constraint(battery[depot, k] == battery_range)
    mdl.add_constraint(load[depot, k] == 0)

# Battery must be non-negative
for i in range(len(locations)):
    for k in range(num_vehicles):
        mdl.add_constraint(battery[i, k] >= 0)

# Solving the problem
solution = mdl.solve(log_output=True)

# Reconstruct routes from decision variables
routes = defaultdict(list)

for k in range(num_vehicles):
    current_node = depot
    route = [current_node]
    visited = set()
    while True:
        next_node = None
        for j in range(len(locations)):
            if current_node != j and x.get((current_node, j, k)) and x[current_node, j, k].solution_value > 0.5:
                next_node = j
                break
        if next_node is None or next_node in visited:
            break
        route.append(next_node)
        visited.add(next_node)
        current_node = next_node
    if len(route) > 1:
        routes[k] = route

# Print routes
for k, route in routes.items():
    print(f"Vehicle {k} route: {route}")


# Output Results
if solution:
    print("Total Distance:", solution.objective_value)
    for k in range(num_vehicles):
        route = [depot]
        next_node = None
        while True:
            found = False
            for j in range(len(locations)):
                if depot != j and any(x[i, j, k].solution_value > 0.5 for i in route):
                    route.append(j)
                    found = True
                    break
            if not found:
                break
        if len(route) > 1:
            print(f"Vehicle {k} Route: {route}")
else:
    print("No solution found.")
