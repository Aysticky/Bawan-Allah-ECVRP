""" Bawa Allah:
Electric Capacitated Vehicle Routing Problem (ECVRP) for Waste Collection
Improved formulation with proper battery and energy modeling for waste management

This model optimizes routes for electric waste collection vehicles, considering
vehicle capacity, battery constraints, and charging stations.
"""

from docplex.mp.model import Model
import math

## Parameters and Data

# Network configuration
num_customers = 5  # Waste collection points
locations = [
    (30, 40),   # 0: Depot (waste processing facility)
    (40, 30),   # 1: Customer
    (20, 10),   # 2: Customer
    (10, 20),   # 3: Customer
    (50, 50),   # 4: Customer
    (25, 25),   # 5: Customer
    (35, 35),   # 6: Charging station A
    (15, 15),   # 7: Charging station B
]
depot = 0

# Waste demands (kg or m³)
demand = [0, 10, 15, 10, 20, 25, 0, 0]

# Vehicle specifications
vehicle_capacity = 50  # Increased capacity to ensure feasibility
battery_capacity = 120.0  # kWh
num_vehicles = 3

# Energy consumption model: E = α₁ * d + α₂ * d * w
# α₁: energy per km (empty vehicle)
# α₂: additional energy per km per unit load
alpha_empty = 0.8      # kWh per km (empty)
alpha_loaded = 0.015   # kWh per km per kg of waste

# Battery consumption rate: dist * (alpha_empty + alpha_loaded * load)
# Service time at nodes
service_time = [0] + [5] * num_customers + [15, 15]  # minutes (15 min charging)

## Derived sets and parameters

N = len(locations) # Total number of nodes
ALL_NODES = range(N)
CUSTOMERS = [i for i in range(1, N) if demand[i] > 0]
CHARGING_STATIONS = [i for i in range(N) if demand[i] == 0 and i != depot]
VEHICLES = range(num_vehicles)

# Distance matrix
def euclidean_distance(loc1, loc2):
    return math.hypot(loc1[0] - loc2[0], loc1[1] - loc2[1]) # Euclidean distance

distance = [[0.0] * N for _ in ALL_NODES]
for i in ALL_NODES:
    for j in ALL_NODES:
        if i != j:
            distance[i][j] = euclidean_distance(locations[i], locations[j]) # in km

# Calculate maximum possible energy consumption for an arc
max_energy_per_arc = {}
for i in ALL_NODES:
    for j in ALL_NODES:
        if i != j:
            # Maximum load scenario
            max_energy = distance[i][j] * (alpha_empty + alpha_loaded * vehicle_capacity) 
            max_energy_per_arc[(i, j)] = max_energy # max energy needed for arc (i,j)

## Model initialization

model = Model(name="ECVRP_Waste_Collection")

## Decision Variables

# Binary: x[i,j,k] = 1 if vehicle k travels from i to j
x = {}
for k in VEHICLES:
    for i in ALL_NODES:
        for j in ALL_NODES:
            if i != j:
                # Only create arcs that are feasible (can be traversed with full battery)
                if max_energy_per_arc[(i, j)] <= battery_capacity:
                    x[i, j, k] = model.binary_var(name=f"x_{i}_{j}_{k}")

# Continuous: load[i,k] = waste load on vehicle k when leaving node i
load = {}
for k in VEHICLES:
    for i in ALL_NODES:
        load[i, k] = model.continuous_var(lb=0, ub=vehicle_capacity, name=f"load_{i}_{k}")

# Continuous: battery[i,k] = battery level of vehicle k when arriving at node i
battery = {}
for k in VEHICLES:
    for i in ALL_NODES:
        battery[i, k] = model.continuous_var(lb=0, ub=battery_capacity, name=f"battery_{i}_{k}")

# Binary: charge[s,k] = 1 if vehicle k charges at station s
charge = {}
for k in VEHICLES:
    for s in CHARGING_STATIONS:
        charge[s, k] = model.binary_var(name=f"charge_{s}_{k}")

# Binary: visit[i,k] = 1 if vehicle k visits node i
visit = {}
for k in VEHICLES:
    for i in range(1, N):  # Exclude depot
        visit[i, k] = model.binary_var(name=f"visit_{i}_{k}")

# Auxiliary variable for energy linearization: u[i,j,k] = load[i,k] * x[i,j,k]
u = {}
for (i, j, k) in x.keys():
    u[i, j, k] = model.continuous_var(lb=0, ub=vehicle_capacity, name=f"u_{i}_{j}_{k}")

## Objective Function

# Minimize total energy consumption
# Energy for arc (i,j) with vehicle k = distance[i][j] * (alpha_empty * x + alpha_loaded * u)
energy_cost = model.sum(
    distance[i][j] * (alpha_empty * x[i, j, k] + alpha_loaded * u[i, j, k])
    for (i, j, k) in x.keys()
)

model.minimize(energy_cost)

## Constraints

# 1. Customer visit constraints

# Each customer must be visited exactly once
for j in CUSTOMERS:
    model.add_constraint(
        model.sum(x[i, j, k] for k in VEHICLES for i in ALL_NODES if (i, j, k) in x) == 1,
        ctname=f"visit_customer_{j}"
    )

# 2. Flow conservation constraints

# For each vehicle and node, inflow = outflow
for k in VEHICLES:
    for i in range(1, N):  # All nodes except depot
        inflow = model.sum(x[j, i, k] for j in ALL_NODES if (j, i, k) in x)
        outflow = model.sum(x[i, j, k] for j in ALL_NODES if (i, j, k) in x)
        model.add_constraint(
            inflow == outflow,
            ctname=f"flow_conservation_{i}_{k}"
        )

# Depot flow: vehicles can leave and return multiple times (for waste dumping)
for k in VEHICLES:
    depot_outflow = model.sum(x[depot, j, k] for j in range(1, N) if (depot, j, k) in x)
    depot_inflow = model.sum(x[j, depot, k] for j in range(1, N) if (j, depot, k) in x)
    
    # Must start and end at depot
    model.add_constraint(depot_outflow >= 1, ctname=f"depot_start_{k}")
    model.add_constraint(depot_inflow >= 1, ctname=f"depot_end_{k}")
    model.add_constraint(depot_outflow == depot_inflow, ctname=f"depot_balance_{k}")

# 3. Visit indicator linking constraints

# Link visit variable to x variables
for k in VEHICLES:
    for i in range(1, N):
        incoming = model.sum(x[j, i, k] for j in ALL_NODES if (j, i, k) in x)
        model.add_constraint(visit[i, k] == incoming, ctname=f"visit_link_{i}_{k}")

# 4. Capacity constraints

# Load at depot is zero (vehicles start empty after dumping)
for k in VEHICLES:
    model.add_constraint(load[depot, k] == 0, ctname=f"depot_load_{k}")

# Load propagation: when traveling from i to j, load increases by demand[j]
# But only if j is a customer. If returning to depot or visiting station, load resets/stays
for k in VEHICLES:
    for i in ALL_NODES:
        for j in ALL_NODES:
            if (i, j, k) in x:
                if j == depot:
                    # Returning to depot: unload everything
                    model.add_constraint(
                        load[j, k] <= vehicle_capacity * (1 - x[i, j, k]),
                        ctname=f"depot_unload_{i}_{j}_{k}"
                    )
                elif j in CHARGING_STATIONS:
                    # Visiting charging station: load stays the same
                    model.add_constraint(
                        load[j, k] >= load[i, k] - vehicle_capacity * (1 - x[i, j, k]),
                        ctname=f"station_load_lb_{i}_{j}_{k}"
                    )
                    model.add_constraint(
                        load[j, k] <= load[i, k] + vehicle_capacity * (1 - x[i, j, k]),
                        ctname=f"station_load_ub_{i}_{j}_{k}"
                    )
                else:
                    # Visiting customer: load increases by demand
                    model.add_constraint(
                        load[j, k] >= load[i, k] + demand[j] - vehicle_capacity * (1 - x[i, j, k]),
                        ctname=f"load_increase_lb_{i}_{j}_{k}"
                    )
                    model.add_constraint(
                        load[j, k] <= load[i, k] + demand[j] + vehicle_capacity * (1 - x[i, j, k]),
                        ctname=f"load_increase_ub_{i}_{j}_{k}"
                    )

# Capacity limit
for k in VEHICLES:
    for i in ALL_NODES:
        model.add_constraint(load[i, k] <= vehicle_capacity, ctname=f"capacity_limit_{i}_{k}")

# 5. Battery constraints

# Battery at depot is always full
for k in VEHICLES:
    model.add_constraint(battery[depot, k] == battery_capacity, ctname=f"depot_battery_{k}")

# Battery consumption on arcs
# battery[j,k] = battery[i,k] - energy_consumed(i,j) + battery_capacity * charge_indicator
for k in VEHICLES:
    for i in ALL_NODES:
        for j in ALL_NODES:
            if (i, j, k) in x:
                # Energy consumed = distance * (alpha_empty + alpha_loaded * load_at_i)
                energy_consumed = distance[i][j] * (alpha_empty + alpha_loaded * load[i, k])
                
                if j in CHARGING_STATIONS:
                    # If we charge at station j, battery becomes full
                    # battery[j] >= battery[i] - energy - M*(1-x) + battery_capacity * charge
                    
                    M = battery_capacity
                    
                    model.add_constraint(
                        battery[j, k] >= battery[i, k] - distance[i][j] * (alpha_empty + alpha_loaded * vehicle_capacity) 
                        - M * (1 - x[i, j, k]) + battery_capacity * charge[j, k],
                        ctname=f"battery_station_lb_{i}_{j}_{k}"
                    )
                    
                    model.add_constraint(
                        battery[j, k] <= battery[i, k] - distance[i][j] * alpha_empty 
                        + M * (1 - x[i, j, k]) + battery_capacity * charge[j, k],
                        ctname=f"battery_station_ub_{i}_{j}_{k}"
                    )
                    
                    # Can only charge if we visit the station
                    model.add_constraint(
                        charge[j, k] <= visit[j, k],
                        ctname=f"charge_visit_link_{j}_{k}"
                    )
                    
                elif j == depot:
                    # Arriving at depot, battery is recharged to full
                    model.add_constraint(
                        battery[j, k] >= battery_capacity - battery_capacity * (1 - x[i, j, k]),
                        ctname=f"battery_depot_arrival_{i}_{j}_{k}"
                    )
                else:
                    # Regular customer node: battery decreases by energy consumed
                    M = battery_capacity
                    model.add_constraint(
                        battery[j, k] >= battery[i, k] - distance[i][j] * (alpha_empty + alpha_loaded * vehicle_capacity)
                        - M * (1 - x[i, j, k]),
                        ctname=f"battery_decrease_lb_{i}_{j}_{k}"
                    )
                    model.add_constraint(
                        battery[j, k] <= battery[i, k] - distance[i][j] * alpha_empty
                        + M * (1 - x[i, j, k]),
                        ctname=f"battery_decrease_ub_{i}_{j}_{k}"
                    )

# Battery feasibility: must have enough battery to reach next node
for k in VEHICLES:
    for i in ALL_NODES:
        for j in ALL_NODES:
            if (i, j, k) in x:
                # When traversing i->j, battery at i must be sufficient
                max_energy_needed = distance[i][j] * (alpha_empty + alpha_loaded * vehicle_capacity)
                model.add_constraint(
                    battery[i, k] >= max_energy_needed * x[i, j, k],
                    ctname=f"battery_sufficient_{i}_{j}_{k}"
                )

# 6. Linearization of u = load * x

# McCormick linearization: u[i,j,k] = load[i,k] * x[i,j,k]
for (i, j, k) in x.keys():
    model.add_constraint(u[i, j, k] <= vehicle_capacity * x[i, j, k], ctname=f"mccormick_1_{i}_{j}_{k}")
    model.add_constraint(u[i, j, k] <= load[i, k], ctname=f"mccormick_2_{i}_{j}_{k}")
    model.add_constraint(u[i, j, k] >= load[i, k] - vehicle_capacity * (1 - x[i, j, k]), 
                        ctname=f"mccormick_3_{i}_{j}_{k}")

# Solve the model
print(f"Customers: {len(CUSTOMERS)}")
print(f"Charging Stations: {len(CHARGING_STATIONS)}")
print(f"Vehicles: {num_vehicles}")
print(f"Vehicle Capacity: {vehicle_capacity} kg")
print(f"Battery Capacity: {battery_capacity} kWh")
print(f"Total Demand: {sum(demand)} kg")
print("=" * 70)

# Set solver parameters for better performance
model.parameters.timelimit = 300  # 5 minutes
model.parameters.mip.tolerances.mipgap = 0.02 

solution = model.solve(log_output=True)

# Results output

if not solution:
    print("NO SOLUTION FOUND")
   
else:
    print("SOLUTION FOUND!")
    print(f"\nObjective Value (Total Energy): {solution.objective_value:.2f} kWh")
    print(f"Solution Status: {solution.solve_status}")
    print(f"MIP Gap: {solution.solve_details.mip_relative_gap * 100:.2f}%")
    
    # Extract and display routes
    print("\n" + "-" * 70)
    print("Vehicle Routes and Statistics:")
    
    total_distance = 0
    total_waste_collected = 0
    
    for k in VEHICLES:
        # Build route from x variables
        route_arcs = [(i, j) for (i, j, kk) in x.keys() 
                      if kk == k and x[i, j, k].solution_value > 0.5]
        
        if not route_arcs:
            print(f"\nVehicle {k}: NOT USED")
            continue
        
        # Reconstruct route
        current = depot
        route = [depot]
        visited_arcs = set()
        
        while True:
            next_node = None
            for (i, j) in route_arcs:
                if i == current and (i, j) not in visited_arcs:
                    next_node = j
                    visited_arcs.add((i, j))
                    break
            
            if next_node is None:
                break
                
            route.append(next_node)
            current = next_node
            
            if current == depot and len(route) > 1:
                # Check if there are more arcs from depot (multiple trips)
                more_trips = any((i, j) for (i, j) in route_arcs 
                               if i == depot and (i, j) not in visited_arcs)
                if not more_trips:
                    break
        
        # Calculate route statistics
        route_distance = sum(distance[route[i]][route[i+1]] 
                           for i in range(len(route)-1))
        
        # Customers served in this route
        customers_served = [node for node in route if node in CUSTOMERS]
        waste_collected = sum(demand[node] for node in customers_served)
        
        # Charging stations used
        charging_stops = [s for s in CHARGING_STATIONS 
                         if visit[s, k].solution_value > 0.5 
                         and charge[s, k].solution_value > 0.5]
        
        print(f"\nVehicle {k}:")
        print(f"  Route: {' -> '.join(map(str, route))}")
        print(f"  Distance: {route_distance:.2f} km")
        print(f"  Waste Collected: {waste_collected} kg")
        print(f"  Customers Served: {customers_served}")
        if charging_stops:
            print(f"  Charging Stations Used: {charging_stops}")
        
        # Show battery levels at key points
        print(f"  Battery levels:")
        for i, node in enumerate(route):
            if node in [depot] + CUSTOMERS + CHARGING_STATIONS:
                batt_level = battery[node, k].solution_value
                print(f"    At node {node}: {batt_level:.2f} kWh", end="")
                if node in CHARGING_STATIONS and charge[node, k].solution_value > 0.5:
                    print(" (CHARGED HERE)", end="")
                print()
        
        total_distance += route_distance
        total_waste_collected += waste_collected
    
    print("\n" + "-" * 70)
    print(f"Total Distance: {total_distance:.2f} km")
    print(f"Total Waste Collected: {total_waste_collected} kg")
    print(f"Total Energy Consumed: {solution.objective_value:.2f} kWh")
    print(f"Average Energy per km: {solution.objective_value/total_distance:.2f} kWh/km")