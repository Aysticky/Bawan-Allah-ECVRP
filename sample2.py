from docplex.mp.model import Model           # Import the optimization modeling library
import numpy as np                           # Import numpy for numerical operations
from collections import defaultdict          # Import defaultdict for easy dictionary handling

num_customers = 5                            # Number of customers to visit

# List of coordinates for depot and customers (first is depot)
locations = [(30, 40), (40, 30), (20, 10), (10, 20), (50, 50), (25, 25)]  
depot = 0                                    # Index of the depot in the locations list

demand = [0, 10, 15, 10, 20, 25]             # Demand at each location (0 for depot)
vehicle_capacity = 40                        # Maximum load a vehicle can carry
battery_range = 100                          # Maximum distance a vehicle can travel on a full charge
num_vehicles = 3                             # Number of vehicles available

# Compute Euclidean distance matrix between all locations
def euclidean(a, b):                         # Function to calculate straight-line distance between two points
    return np.hypot(a[0] - b[0], a[1] - b[1])

distance = np.zeros((len(locations), len(locations)))  # Create a matrix to store distances
for i in range(len(locations)):              # Loop through all locations as starting points
    for j in range(len(locations)):          # Loop through all locations as ending points
        distance[i][j] = euclidean(locations[i], locations[j])  # Calculate and store distance

# Building the optimization model
mdl = Model(name='Electric CVRP')            # Create a new model named 'Electric CVRP'

# Define binary decision variables: x[i, j, k] = 1 if vehicle k travels from i to j, else 0
x = mdl.binary_var_dict(
    [ (i, j, k) for i in range(len(locations))
                  for j in range(len(locations))
                  for k in range(num_vehicles) if i != j ], 
    name='x')

# Define continuous variables for load: load[i, k] is the load of vehicle k after visiting node i
load = mdl.continuous_var_dict(
    [(i, k) for i in range(len(locations)) for k in range(num_vehicles)],
    name='load')

# Define continuous variables for battery: battery[i, k] is the remaining battery of vehicle k at node i
battery = mdl.continuous_var_dict(
    [(i, k) for i in range(len(locations)) for k in range(num_vehicles)],
    name='battery')

# Set the objective: minimize total distance traveled by all vehicles
mdl.minimize(
    mdl.sum(x[i, j, k] * distance[i][j]
            for i in range(len(locations))
            for j in range(len(locations))
            for k in range(num_vehicles) if i != j)
)

# Constraints

# Each customer must be visited exactly once by any vehicle
for j in range(1, len(locations)):           # For each customer (excluding depot)
    mdl.add_constraint(mdl.sum(x[i, j, k]
                               for i in range(len(locations)) if i != j
                               for k in range(num_vehicles)) == 1)

# Each vehicle can leave the depot at most once
for k in range(num_vehicles):                # For each vehicle
    mdl.add_constraint(mdl.sum(x[depot, j, k] for j in range(1, len(locations))) <= 1)

# Flow conservation: vehicles entering a node must also leave it
for k in range(num_vehicles):                # For each vehicle
    for h in range(1, len(locations)):       # For each customer (excluding depot)
        mdl.add_constraint(
            mdl.sum(x[i, h, k] for i in range(len(locations)) if i != h) ==
            mdl.sum(x[h, j, k] for j in range(len(locations)) if j != h)
        )

# Capacity constraints: vehicle load after visiting a customer must be at least that customer's demand and not exceed capacity
for i in range(1, len(locations)):           # For each customer
    for k in range(num_vehicles):            # For each vehicle
        mdl.add_constraint(load[i, k] >= demand[i] * 
                           mdl.sum(x[j, i, k] for j in range(len(locations)) if j != i))
        mdl.add_constraint(load[i, k] <= vehicle_capacity)

# Battery constraints: update battery after traveling from i to j
for i in range(len(locations)):              # For each starting node
    for j in range(len(locations)):          # For each ending node
        for k in range(num_vehicles):        # For each vehicle
            if i != j:
                mdl.add_constraint(
                    battery[j, k] >= battery[i, k] - distance[i][j] - 
                    (1 - x[i, j, k]) * battery_range
                )

# Initialize battery and load at depot for each vehicle
for k in range(num_vehicles):                # For each vehicle
    mdl.add_constraint(battery[depot, k] == battery_range)  # Start with full battery
    mdl.add_constraint(load[depot, k] == 0)                 # Start with zero load

# Battery must never be negative at any node
for i in range(len(locations)):              # For each node
    for k in range(num_vehicles):            # For each vehicle
        mdl.add_constraint(battery[i, k] >= 0)

# Solve the optimization problem and store the solution
solution = mdl.solve(log_output=True)

# Reconstruct routes from the solution variables
routes = defaultdict(list)                   # Dictionary to store routes for each vehicle

for k in range(num_vehicles):                # For each vehicle
    current_node = depot                     # Start at the depot
    route = [current_node]                   # Initialize route with depot
    visited = set()                          # Set to keep track of visited nodes
    while True:
        next_node = None                     # Variable to store the next node
        for j in range(len(locations)):      # Check all possible next nodes
            # If there is a route from current_node to j for vehicle k in the solution
            if current_node != j and x.get((current_node, j, k)) and x[current_node, j, k].solution_value > 0.5:
                next_node = j                # Set next_node to j
                break                        # Exit the loop after finding the next node
        if next_node is None or next_node in visited:  # If no next node or already visited
            break                            # End the route
        route.append(next_node)              # Add next node to the route
        visited.add(next_node)               # Mark node as visited
        current_node = next_node             # Move to the next node
    if len(route) > 1:                       # If the route has more than just the depot
        routes[k] = route                    # Store the route for vehicle k

# Print the reconstructed routes for each vehicle
for k, route in routes.items():
    print(f"Vehicle {k} route: {route}")

# Output Results

# If a solution was found, print the total distance and each vehicle's route
if solution:
    print("Total Distance:", solution.objective_value)  # Print the total distance traveled
    for k in range(num_vehicles):                       # For each vehicle
        route = [depot]                                 # Start route from depot
        next_node = None                                # Initialize next node
        while True:
            found = False                               # Flag to check if a next node is found
            for j in range(len(locations)):             # Check all possible next nodes
                # If there is a route from any node in 'route' to j for vehicle k
                if depot != j and any(x[i, j, k].solution_value > 0.5 for i in route):
                    route.append(j)                     # Add node to route
                    found = True                        # Mark as found
                    break                               # Exit inner loop
            if not found:
                break                                   # If no next node, end route
        if len(route) > 1:                              # If route has more than depot
            print(f"Vehicle {k} Route: {route}")        # Print the route
else:
    print("No solution found.")                         # Print if no solution was found
