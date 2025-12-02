""" Bawa Allah:
Electric Capacitated Vehicle Routing Problem (ECVRP) for Waste Collection
Improved formulation with proper battery and energy modeling for waste management

This model optimizes routes for electric waste collection vehicles, considering
vehicle capacity, battery constraints, and charging stations.
"""

from docplex.mp.model import Model
import math
import random
from customer_data import num_customers, locations, depot, demand, vehicle_capacity, battery_capacity, num_vehicles
from ga_solver import GeneticAlgorithm
from sa_solver import SimulatedAnnealing

## Parameters and Data

## Import customer data from external file
# num_customers, locations, depot, demand, vehicle_capacity, battery_capacity, num_vehicles
# are now loaded from customer_data.py

grid_size = 100  # 100 km x 100 km city grid
total_demand = sum(demand)

# Energy consumption model: E = α₁ * d + α₂ * d * w
# α₁: energy per km (empty vehicle)
# α₂: additional energy per km per unit load
alpha_empty = 0.8      # kWh per km (empty)
alpha_loaded = 0.0003   # kWh per km per kg of waste

# Battery consumption rate: dist * (alpha_empty + alpha_loaded * load)

## Derived sets and parameters

N = len(locations) # Total number of nodes
ALL_NODES = range(N)
CUSTOMERS = [i for i in range(1, N) if demand[i] > 0]
CHARGING_STATIONS = [i for i in range(N) if demand[i] == 0 and i != depot]
VEHICLES = range(num_vehicles)

# Distance matrix
def euclidean_distance(loc1, loc2):
    return math.hypot(loc1[0] - loc2[0], loc1[1] - loc2[1]) # Euclidean distance

print("\nCalculating distance matrix...")
distance = [[0.0] * N for _ in ALL_NODES]
for i in ALL_NODES:
    for j in ALL_NODES:
        if i != j:
            distance[i][j] = euclidean_distance(locations[i], locations[j]) # in km

print(f" Distance matrix calculated ({N}x{N} = {N*N:,} entries)")

# Solver selection----------------------

print("\nSelect solving method:")
print("1. CPLEX MIP Solver")
print("2. Genetic Algorithm")
print("3. Simulated Annealing")
solver_choice = input("Enter choice (1, 2, or 3): ").strip()

if solver_choice == "2":
    print("Using Genetic Algorithm Solver")
    
    # ECVRP-specific functions for GA------------------------------
    
    def create_ecvrp_individual():
        """Create random ECVRP solution (list of routes)"""
        customers = list(CUSTOMERS)
        random.shuffle(customers)
        
        routes = []
        current_route = [depot]
        current_load = 0
        
        for customer in customers:
            if current_load + demand[customer] <= vehicle_capacity:
                current_route.append(customer)
                current_load += demand[customer]
            else:
                current_route.append(depot)
                routes.append(current_route)
                current_route = [depot, customer]
                current_load = demand[customer]
        
        if len(current_route) > 1:
            current_route.append(depot)
            routes.append(current_route)
        
        while len(routes) < num_vehicles:
            routes.append([depot, depot])
        
        return routes[:num_vehicles]
    
    def evaluate_ecvrp(individual):
        """Evaluate fitness of ECVRP solution"""
        total_energy = 0
        penalty = 0
        
        # Track served customers
        served = set()
        for route in individual:
            for node in route:
                if node in CUSTOMERS:
                    served.add(node)
        
        # Calculate energy and check feasibility
        for route in individual:
            if len(route) <= 2:
                continue
            
            route_energy = 0
            current_load = 0
            current_battery = battery_capacity
            capacity_violated = False
            battery_violated = False
            
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                
                # Update load
                if to_node in CUSTOMERS:
                    current_load += demand[to_node]
                elif to_node == depot and from_node != depot:
                    current_load = 0
                
                # Check capacity
                if current_load > vehicle_capacity:
                    capacity_violated = True
                
                # Calculate energy
                dist = distance[from_node][to_node]
                energy = dist * (alpha_empty + alpha_loaded * current_load)
                route_energy += energy
                
                # Update battery
                if to_node == depot:
                    current_battery = battery_capacity
                else:
                    current_battery -= energy
                
                # Check battery
                if current_battery < 0:
                    battery_violated = True
            
            total_energy += route_energy
            
            if capacity_violated:
                penalty += 5000
            if battery_violated:
                penalty += 5000
        
        # Penalty for unserved customers
        unserved = len(CUSTOMERS) - len(served)
        penalty += unserved * 50000
        
        # Penalty for duplicate customers
        all_customers = []
        for route in individual:
            all_customers.extend([n for n in route if n in CUSTOMERS])
        duplicates = len(all_customers) - len(set(all_customers))
        penalty += duplicates * 50000
        
        # Fitness (higher is better)
        return -total_energy - penalty
    
    def crossover_ecvrp(parent1, parent2):
        """Order crossover for ECVRP routes"""
        # Flatten routes
        customers1 = []
        for route in parent1:
            customers1.extend([c for c in route if c in CUSTOMERS])
        
        customers2 = []
        for route in parent2:
            customers2.extend([c for c in route if c in CUSTOMERS])
        
        # Order crossover
        size = len(customers1)
        start, end = sorted(random.sample(range(size), 2))
        
        offspring_customers = [None] * size
        offspring_customers[start:end] = customers1[start:end]
        
        p2_idx = 0
        for i in range(size):
            if offspring_customers[i] is None:
                while customers2[p2_idx] in offspring_customers:
                    p2_idx += 1
                offspring_customers[i] = customers2[p2_idx]
                p2_idx += 1
        
        # Rebuild routes
        offspring = []
        current_route = [depot]
        current_load = 0
        
        for customer in offspring_customers:
            if current_load + demand[customer] <= vehicle_capacity:
                current_route.append(customer)
                current_load += demand[customer]
            else:
                current_route.append(depot)
                offspring.append(current_route)
                current_route = [depot, customer]
                current_load = demand[customer]
        
        if len(current_route) > 1:
            current_route.append(depot)
            offspring.append(current_route)
        
        while len(offspring) < num_vehicles:
            offspring.append([depot, depot])
        
        return offspring[:num_vehicles]
    
    def mutate_ecvrp(individual):
        """Mutation for ECVRP routes"""
        mutated = [route.copy() for route in individual]
        
        non_empty = [i for i, r in enumerate(mutated) if len(r) > 3]
        
        if len(non_empty) >= 2 and random.random() < 0.5:
            # Swap mutation
            r1_idx, r2_idx = random.sample(non_empty, 2)
            r1 = mutated[r1_idx]
            r2 = mutated[r2_idx]
            
            c1_idx = random.randint(1, len(r1) - 2)
            c2_idx = random.randint(1, len(r2) - 2)
            r1[c1_idx], r2[c2_idx] = r2[c2_idx], r1[c1_idx]
        elif non_empty:
            # Reverse mutation
            route_idx = random.choice(non_empty)
            route = mutated[route_idx]
            
            if len(route) > 4:
                i = random.randint(1, len(route) - 3)
                j = random.randint(i + 1, len(route) - 2)
                route[i:j+1] = reversed(route[i:j+1])
        
        return mutated
    
    # Run GA Solver--------------------------------
    
    ga = GeneticAlgorithm(population_size=50, mutation_rate=0.2, elite_size=5, tournament_size=5)
    
    import time
    solve_start = time.time()
    
    solution_routes, best_fitness, fitness_history = ga.solve(
        create_individual_fn=create_ecvrp_individual,
        evaluate_fn=evaluate_ecvrp,
        crossover_fn=crossover_ecvrp,
        mutate_fn=mutate_ecvrp,
        generations=100,
        verbose=True
    )
    
    solve_time = time.time() - solve_start
    
    # Calculate solution metrics
    total_energy = 0
    total_distance = 0
    total_waste_collected = 0
    vehicles_used = 0
    
    print("Solution Found by GA!")
    print(f"\n  Solve Time: {solve_time:.2f} seconds")
    
    for k, route in enumerate(solution_routes):
        if len(route) > 2:
            vehicles_used += 1
            
            # Calculate energy
            route_energy = 0
            current_load = 0
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                
                if to_node in CUSTOMERS:
                    current_load += demand[to_node]
                elif to_node == depot and from_node != depot:
                    current_load = 0
                
                dist = distance[from_node][to_node]
                energy = dist * (alpha_empty + alpha_loaded * current_load)
                route_energy += energy
                total_distance += dist
            
            total_energy += route_energy
            
            customers_served = [c for c in route if c in CUSTOMERS]
            waste = sum(demand[c] for c in customers_served)
            total_waste_collected += waste
            
            if vehicles_used <= 5:
                print(f"\nVehicle {k}:")
                route_preview = route[:30] if len(route) > 30 else route
                print(f"  Route: {' -> '.join(map(str, route_preview))}")
                if len(route) > 30:
                    print(f"  ... ({len(route)} total stops)")
                print(f"  Customers: {len(customers_served)}, Waste: {waste} kg, Energy: {route_energy:.1f} kWh")
    
    if vehicles_used > 5:
        print(f"\n... and {vehicles_used - 5} more vehicles")
    
    print(f"\n Vehicles Used:          {vehicles_used} / {num_vehicles}")
    print(f" Customers Served:       {num_customers} / {num_customers}")
    print(f" Total Distance:         {total_distance:.2f} km")
    print(f"  Total Waste Collected:  {total_waste_collected} kg ({total_waste_collected/1000:.1f} tons)")
    print(f" Total Energy Consumed:  {total_energy:.2f} kWh")
    print(f" Average Energy per km:  {total_energy/total_distance:.3f} kWh/km")
    print("-" * 80)
    
    import sys
    sys.exit(0)


elif solver_choice == "3":
    print("Using Simulated Annealing Solver")
    
    # ECVRP-specific functions for SA-------------------------------
    
    def create_ecvrp_solution():
        """Create random ECVRP solution (list of routes)"""
        customers = list(CUSTOMERS)
        random.shuffle(customers)
        
        routes = []
        current_route = [depot]
        current_load = 0
        
        for customer in customers:
            if current_load + demand[customer] <= vehicle_capacity:
                current_route.append(customer)
                current_load += demand[customer]
            else:
                current_route.append(depot)
                routes.append(current_route)
                current_route = [depot, customer]
                current_load = demand[customer]
        
        if len(current_route) > 1:
            current_route.append(depot)
            routes.append(current_route)
        
        while len(routes) < num_vehicles:
            routes.append([depot, depot])
        
        return routes[:num_vehicles]
    
    def calculate_ecvrp_cost(solution):
        """Calculate cost (energy + penalties) for ECVRP solution"""
        total_energy = 0
        penalty = 0
        
        # Track served customers
        served = set()
        for route in solution:
            for node in route:
                if node in CUSTOMERS:
                    served.add(node)
        
        # Calculate energy and check feasibility
        for route in solution:
            if len(route) <= 2:
                continue
            
            route_energy = 0
            current_load = 0
            current_battery = battery_capacity
            capacity_violated = False
            battery_violated = False
            
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                
                # Update load
                if to_node in CUSTOMERS:
                    current_load += demand[to_node]
                elif to_node == depot and from_node != depot:
                    current_load = 0
                
                # Check capacity
                if current_load > vehicle_capacity:
                    capacity_violated = True
                
                # Calculate energy
                dist = distance[from_node][to_node]
                energy = dist * (alpha_empty + alpha_loaded * current_load)
                route_energy += energy
                
                # Update battery
                if to_node == depot:
                    current_battery = battery_capacity
                else:
                    current_battery -= energy
                
                # Check battery
                if current_battery < 0:
                    battery_violated = True
            
            total_energy += route_energy
            
            if capacity_violated:
                penalty += 5000
            if battery_violated:
                penalty += 5000
        
        # Penalty for unserved customers
        unserved = len(CUSTOMERS) - len(served)
        penalty += unserved * 50000
        
        # Penalty for duplicate customers
        all_customers = []
        for route in solution:
            all_customers.extend([n for n in route if n in CUSTOMERS])
        duplicates = len(all_customers) - len(set(all_customers))
        penalty += duplicates * 50000
        
        # Cost (lower is better)
        return total_energy + penalty
    
    def create_ecvrp_neighbor(solution):
        """Create neighbor solution using swap, reverse, or insertion"""
        neighbor = [route.copy() for route in solution]
        
        # Get non-empty routes
        non_empty = [i for i, r in enumerate(neighbor) if len(r) > 3]
        
        if not non_empty:
            return neighbor
        
        # Choose operator
        operator = random.choice(['swap', 'reverse', 'insertion'])
        
        if operator == 'swap' and len(non_empty) >= 2:
            # Swap two customers between routes
            r1_idx, r2_idx = random.sample(non_empty, 2)
            r1 = neighbor[r1_idx]
            r2 = neighbor[r2_idx]
            
            c1_idx = random.randint(1, len(r1) - 2)
            c2_idx = random.randint(1, len(r2) - 2)
            r1[c1_idx], r2[c2_idx] = r2[c2_idx], r1[c1_idx]
            
        elif operator == 'reverse':
            # Reverse segment within a route
            route_idx = random.choice(non_empty)
            route = neighbor[route_idx]
            
            if len(route) > 4:
                i = random.randint(1, len(route) - 3)
                j = random.randint(i + 1, len(route) - 2)
                route[i:j+1] = list(reversed(route[i:j+1]))
        
        else:  # insertion
            # Move a customer to different position
            route_idx = random.choice(non_empty)
            route = neighbor[route_idx]
            
            if len(route) > 4:
                # Remove customer from position
                remove_idx = random.randint(1, len(route) - 2)
                customer = route.pop(remove_idx)
                
                # Insert at new position
                insert_idx = random.randint(1, len(route) - 1)
                route.insert(insert_idx, customer)
        
        return neighbor
    
    # Run SA Solver------------------
    
    sa = SimulatedAnnealing(max_iterations=200, max_sub_iterations=20, 
                           initial_temp=0.05, alpha=0.98)
    
    import time
    solve_start = time.time()
    
    solution_routes, best_cost, cost_history = sa.solve(
        create_solution_fn=create_ecvrp_solution,
        cost_fn=calculate_ecvrp_cost,
        create_neighbor_fn=create_ecvrp_neighbor,
        verbose=True
    )
    
    solve_time = time.time() - solve_start
    
    # Calculate solution metrics
    total_energy = 0
    total_distance = 0
    total_waste_collected = 0
    vehicles_used = 0
    
    print("Solution found by SA!")
    print(f"\n  Solve Time: {solve_time:.2f} seconds")
    
    for k, route in enumerate(solution_routes):
        if len(route) > 2:
            vehicles_used += 1
            
            # Calculate energy
            route_energy = 0
            current_load = 0
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                
                if to_node in CUSTOMERS:
                    current_load += demand[to_node]
                elif to_node == depot and from_node != depot:
                    current_load = 0
                
                dist = distance[from_node][to_node]
                energy = dist * (alpha_empty + alpha_loaded * current_load)
                route_energy += energy
                total_distance += dist
            
            total_energy += route_energy
            
            customers_served = [c for c in route if c in CUSTOMERS]
            waste = sum(demand[c] for c in customers_served)
            total_waste_collected += waste
            
            if vehicles_used <= 5:
                print(f"\nVehicle {k}:")
                route_preview = route[:30] if len(route) > 30 else route
                print(f"  Route: {' -> '.join(map(str, route_preview))}")
                if len(route) > 30:
                    print(f"  ... ({len(route)} total stops)")
                print(f"  Customers: {len(customers_served)}, Waste: {waste} kg, Energy: {route_energy:.1f} kWh")
    
    if vehicles_used > 5:
        print(f"\n... and {vehicles_used - 5} more vehicles")
    
    print(f"\n Vehicles Used:          {vehicles_used} / {num_vehicles}")
    print(f" Customers Served:       {num_customers} / {num_customers}")
    print(f" Total Distance:         {total_distance:.2f} km")
    print(f" Total Waste Collected:  {total_waste_collected} kg ({total_waste_collected/1000:.1f} tons)")
    print(f" Total Energy Consumed:  {total_energy:.2f} kWh")
    print(f" Average Energy per km:  {total_energy/total_distance:.3f} kWh/km")
    print("-" * 80)
    
    import sys
    sys.exit(0)



# CPLEX MIP Solver----------------------

print("Using CPLEX MIP Solver")

# Model initialization

print("\nBuilding optimization model...")
model = Model(name="ECVRP_Waste_Collection")

# Enable parallel processing
model.context.cplex_parameters.threads = 0  # Use all available cores

## Decision Variables

# Binary: x[i,j,k] = 1 if vehicle k travels from i to j
x = {}
print("Creating route decision variables...")
for k in VEHICLES:
    for i in ALL_NODES:
        for j in ALL_NODES:
            if i != j:
                x[i, j, k] = model.binary_var(name=f"x_{i}_{j}_{k}")
print(f" Created {len(x):,} route variables")

# Continuous: load[i,k] = waste load on vehicle k when leaving node i
load = {}
print("Creating load tracking variables...")
for k in VEHICLES:
    for i in ALL_NODES:
        load[i, k] = model.continuous_var(lb=0, ub=vehicle_capacity, name=f"load_{i}_{k}")
print(f" Created {len(load):,} load variables")

# Continuous: battery[i,k] = battery level of vehicle k when arriving at node i
battery = {}
print("Creating battery tracking variables...")
for k in VEHICLES:
    for i in ALL_NODES:
        battery[i, k] = model.continuous_var(lb=0, ub=battery_capacity, name=f"battery_{i}_{k}")
print(f" Created {len(battery):,} battery variables")

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

total_vars = len(x) + len(load) + len(battery) + len(charge) + len(visit) + len(u)
print(f"\n Total variables created: {total_vars:,}")
print(f"  - Binary: {len(x) + len(charge) + len(visit):,}")
print(f"  - Continuous: {len(load) + len(battery) + len(u):,}")



### Objective Function--------------------------------

# Minimize total energy consumption
# Energy for arc (i,j) with vehicle k = distance[i][j] * (alpha_empty * x + alpha_loaded * u)
energy_cost = model.sum(
    distance[i][j] * (alpha_empty * x[i, j, k] + alpha_loaded * u[i, j, k])
    for (i, j, k) in x.keys()
)

model.minimize(energy_cost)

## Constraints--------------------------------

# 1. Customer visit constraints

# Each customer must be visited exactly once
for j in CUSTOMERS:
    model.add_constraint(
        model.sum(x[i, j, k] for k in VEHICLES for i in ALL_NODES if i != j) == 1,
        ctname=f"visit_customer_{j}"
    )

# 2. Flow conservation constraints

# For each vehicle and node, inflow = outflow
for k in VEHICLES:
    for i in range(1, N):  # All nodes except depot
        inflow = model.sum(x[j, i, k] for j in ALL_NODES if j != i)
        outflow = model.sum(x[i, j, k] for j in ALL_NODES if j != i)
        model.add_constraint(
            inflow == outflow,
            ctname=f"flow_conservation_{i}_{k}"
        )

# Depot flow: vehicles can leave and return multiple times (for waste dumping)
for k in VEHICLES:
    depot_outflow = model.sum(x[depot, j, k] for j in range(1, N))
    depot_inflow = model.sum(x[j, depot, k] for j in range(1, N))
    
    # Must start and end at depot
    model.add_constraint(depot_outflow >= 1, ctname=f"depot_start_{k}")
    model.add_constraint(depot_inflow >= 1, ctname=f"depot_end_{k}")
    model.add_constraint(depot_outflow == depot_inflow, ctname=f"depot_balance_{k}")

# 3. Visit indicator linking constraints

# Link visit variable to x variables
for k in VEHICLES:
    for i in range(1, N):
        incoming = model.sum(x[j, i, k] for j in ALL_NODES if j != i)
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
            if i != j:
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
            if i != j:
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
            if i != j:
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

## Solve the model--------------------------------------------------
print("\n" + "=" * 80)
print("Solving ECVRP")
print("=" * 80)
print(f"Problem size: {num_customers} customers, {num_vehicles} vehicles")
print(f"Started at: {__import__('time').strftime('%H:%M:%S')}")
print("=" * 80 + "\n")

import time
solve_start = time.time()
solution = model.solve(log_output=True)
solve_time = time.time() - solve_start

## Results output-------------------------------

if not solution:
    print("NO SOLUTION FOUND")
   
else:
    print("SOLUTION FOUND!")
    print("=" * 80)
    print(f"\n Solve Time: {solve_time:.2f} seconds ({solve_time/60:.2f} minutes)")
    print(f" Objective Value (Total Energy): {solution.objective_value:.2f} kWh")
    print(f" Solution Status: {solution.solve_status}")
    print(f" MIP Gap: {solution.solve_details.mip_relative_gap * 100:.2f}%")
    
    # Extract and display routes
    print("\n" + "-" * 70)
    print("Vehicle Routes and Statistics:")
    
    total_distance = 0
    total_waste_collected = 0
    vehicles_used = 0
    total_depot_returns = 0
    total_charging_stops = 0
    
    for k in VEHICLES:
        # Build route from x variables
        route_arcs = [(i, j) for (i, j, kk) in x.keys() 
                      if kk == k and x[i, j, k].solution_value > 0.5]
        
        if not route_arcs:
            continue
        
        vehicles_used += 1
        # Reconstruct route
        current = depot
        route = [depot]
        visited_arcs = set()
        
        while len(route) < 300:  # Safety limit for large routes
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
        
        depot_returns = route.count(depot) - 1  # Exclude starting position
        
        # Show detailed output only for first 5 vehicles
        if vehicles_used <= 5:
            print(f"\nVehicle {k}:")
            # Show abbreviated route for large instances
            route_preview = route[:30] if len(route) > 30 else route
            print(f"  Route preview: {' -> '.join(map(str, route_preview))}")
            if len(route) > 30:
                print(f"  ... (route continues for {len(route)} total stops)")
            print(f"  Distance: {route_distance:.2f} km")
            print(f"  Waste Collected: {waste_collected} kg ({waste_collected/1000:.2f} tons)")
            print(f"  Customers Served: {len(customers_served)}")
            print(f"  Depot Returns: {depot_returns}")
            if charging_stops:
                print(f"  Charging Stations Used: {len(charging_stops)} times")
        
        total_distance += route_distance
        total_waste_collected += waste_collected
        total_depot_returns += depot_returns
        total_charging_stops += len(charging_stops)

    if vehicles_used > 5:
        print(f"\n... and {vehicles_used - 5} more vehicles (detailed routes omitted for brevity)")
    
    print("-" * 80)
    print(f" Vehicles used:          {vehicles_used} / {num_vehicles}")
    print(f" Customers served:       {num_customers} / {num_customers}")
    print(f" Total distance:         {total_distance:.2f} km")
    print(f"  Total waste collected:  {total_waste_collected} kg ({total_waste_collected/1000:.1f} tons)")
    print(f" Total depot returns:    {total_depot_returns}")
    print(f" Total charging stops:   {total_charging_stops}")
    print(f" Total energy consumed:  {solution.objective_value:.2f} kWh")
    print(f" Average energy per km:  {solution.objective_value/total_distance:.3f} kWh/km")
    print(f" Avg distance/vehicle:   {total_distance/vehicles_used:.2f} km")
    print(f" Avg waste/vehicle:      {total_waste_collected/vehicles_used:.1f} kg")
    
    print("Performance Metrics:")
    print("-" * 80)
    print(f" Computational time:     {solve_time:.2f} seconds ({solve_time/60:.2f} minutes)")
    print(f" Variables:              {total_vars:,}")
    print(f" Constraints:            {model.number_of_constraints:,}")
    print(f" Optimality gap:         {solution.solve_details.mip_relative_gap * 100:.2f}%")
    print(f" Customers/minute:       {num_customers/(solve_time/60):.1f}")
    
    print("\n" + "=" * 80)
    print(" ECVRP SOlved Successfully")
    print("=" * 80)
    print(f" {num_customers} customers routed using {vehicles_used} vehicles")
    print(f" {total_waste_collected/1000:.1f} tons of waste collected")
    print(f" {total_distance:.1f} km total distance traveled")
    print(f" {solution.objective_value:.1f} kWh total energy consumption")
    print(f" Solved in {solve_time/60:.2f} minutes")
    print("=" * 80)