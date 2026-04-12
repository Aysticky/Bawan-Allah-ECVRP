"""
Batch Runner for All ECVRP Instances
Runs all instances from ALL_mavrovouniotis_ecvrp_customer_data_files and saves results to a single file
    
python run_all_instances.py 

Read  BATCH_RUN_INSTRUCTIONS.md for more
"""

import os
import sys
import time
import glob
import importlib.util
import math
import random
from datetime import datetime

# Default parameters
SOLVER_CHOICE = "4"  # GASA by default
OUTPUT_FILE = "results_all_instances.txt"

# Parse command line arguments
if len(sys.argv) > 1:
    SOLVER_CHOICE = sys.argv[1]
if len(sys.argv) > 2:
    OUTPUT_FILE = sys.argv[2]

# Validate solver choice
if SOLVER_CHOICE not in ["1", "2", "3", "4"]:
    print(f"Invalid solver choice: {SOLVER_CHOICE}")
    print("Please use 1 (CPLEX), 2 (GA), 3 (SA), or 4 (GASA)")
    sys.exit(1)

SOLVER_NAMES = {
    "1": "CPLEX MIP",
    "2": "Genetic Algorithm",
    "3": "Simulated Annealing",
    "4": "Hybrid GASA"
}

print("-" * 80)
print("ECVRP Batch Runner - All Mavrovouniotis Instances")
print("-" * 80)
print(f"Solver: {SOLVER_NAMES[SOLVER_CHOICE]}")
print(f"Output: {OUTPUT_FILE}")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 80)

# Get all instance files
instance_dir = "ALL_mavrovouniotis_ecvrp_customer_data_files"
instance_files = sorted(glob.glob(os.path.join(instance_dir, "*.py")))

if not instance_files:
    print(f"No instance files found in {instance_dir}")
    sys.exit(1)

print(f"\nFound {len(instance_files)} instances to run\n")

# Open output file
with open(OUTPUT_FILE, 'w') as f:
    f.write("=" * 100 + "\n")
    f.write("ECVRP Benchmark Results - Mavrovouniotis Instances\n")
    f.write("=" * 100 + "\n")
    f.write(f"Solver: {SOLVER_NAMES[SOLVER_CHOICE]}\n")
    f.write(f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 100 + "\n\n")

# Function to load instance data
def load_instance(instance_file):
    """Dynamically load instance data from Python file"""
    spec = importlib.util.spec_from_file_location("instance_module", instance_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return {
        'num_customers': module.num_customers,
        'locations': module.locations,
        'depot': module.depot,
        'demand': module.demand,
        'vehicle_capacity': module.vehicle_capacity,
        'battery_capacity': module.battery_capacity,
        'num_vehicles': module.num_vehicles
    }

# Function to calculate distance matrix
def euclidean_distance(loc1, loc2):
    return math.hypot(loc1[0] - loc2[0], loc1[1] - loc2[1])

# Function to run solver on an instance
def run_instance(instance_file, solver_choice):
    """Run solver on a single instance and return results"""
    
    instance_name = os.path.basename(instance_file).replace('.py', '')
    
    print(f"\n{'='*80}")
    print(f"Running: {instance_name}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    # Load instance data
    try:
        data = load_instance(instance_file)
    except Exception as e:
        return {
            'instance': instance_name,
            'status': 'LOAD_FAILED',
            'error': str(e),
            'time': 0
        }
    
    num_customers = data['num_customers']
    locations = data['locations']
    depot = data['depot']
    demand = data['demand']
    vehicle_capacity = data['vehicle_capacity']
    battery_capacity = data['battery_capacity']
    num_vehicles = data['num_vehicles']
    
    N = len(locations)
    ALL_NODES = range(N)
    CUSTOMERS = [i for i in range(1, N) if demand[i] > 0]
    CHARGING_STATIONS = [i for i in range(N) if demand[i] == 0 and i != depot]
    VEHICLES = range(num_vehicles)
    
    # Energy parameters
    alpha_empty = 0.8
    alpha_loaded = 0.0003
    
    # Calculate distance matrix
    distance = [[0.0] * N for _ in ALL_NODES]
    for i in ALL_NODES:
        for j in ALL_NODES:
            if i != j:
                distance[i][j] = euclidean_distance(locations[i], locations[j])
    
    print(f"  Customers: {num_customers}")
    print(f"  Vehicles: {num_vehicles}")
    print(f"  Nodes: {N}")
    
    # Run appropriate solver
    try:
        if solver_choice == "2":  # GA
            from ga_solver import GeneticAlgorithm
            solution, fitness, history = solve_with_ga(
                CUSTOMERS, depot, demand, distance, vehicle_capacity, 
                battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                ALL_NODES, CHARGING_STATIONS, VEHICLES
            )
        elif solver_choice == "3":  # SA
            from sa_solver import SimulatedAnnealing
            solution, cost, history = solve_with_sa(
                CUSTOMERS, depot, demand, distance, vehicle_capacity,
                battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                ALL_NODES, CHARGING_STATIONS, VEHICLES
            )
        elif solver_choice == "4":  # GASA
            from gasa_solver import HybridGASA
            solution, fitness, history = solve_with_gasa(
                CUSTOMERS, depot, demand, distance, vehicle_capacity,
                battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                ALL_NODES, CHARGING_STATIONS, VEHICLES
            )
        else:  # CPLEX
            print("  CPLEX solver not supported in batch mode (too slow)")
            return {
                'instance': instance_name,
                'status': 'SKIPPED',
                'error': 'CPLEX not supported in batch mode',
                'time': 0
            }
    except Exception as e:
        return {
            'instance': instance_name,
            'status': 'SOLVE_FAILED',
            'error': str(e),
            'time': time.time() - start_time
        }
    
    # Calculate metrics
    total_energy = 0
    total_distance = 0
    total_waste = 0
    vehicles_used = 0
    
    for route in solution:
        if len(route) > 2:
            vehicles_used += 1
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
                total_energy += energy
                total_distance += dist
            
            customers_in_route = [c for c in route if c in CUSTOMERS]
            total_waste += sum(demand[c] for c in customers_in_route)
    
    solve_time = time.time() - start_time
    
    print(f"\n  Results:")
    print(f"    Vehicles Used: {vehicles_used}/{num_vehicles}")
    print(f"    Total Distance: {total_distance:.2f} km")
    print(f"    Total Energy: {total_energy:.2f} kWh")
    print(f"    Total Waste: {total_waste} kg")
    print(f"    Solve Time: {solve_time:.2f} seconds")
    
    return {
        'instance': instance_name,
        'status': 'SUCCESS',
        'num_customers': num_customers,
        'num_vehicles': num_vehicles,
        'vehicles_used': vehicles_used,
        'total_distance': total_distance,
        'total_energy': total_energy,
        'total_waste': total_waste,
        'solve_time': solve_time,
        'energy_per_km': total_energy / total_distance if total_distance > 0 else 0
    }

# Solver implementations

def create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles):
    """Create random ECVRP solution"""
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
            # Only start new route if we haven't exceeded vehicle limit
            if len(routes) < num_vehicles - 1:
                current_route.append(depot)
                routes.append(current_route)
                current_route = [depot, customer]
                current_load = demand[customer]
            else:
                # Must fit in current/last route even if over capacity
                current_route.append(customer)
                current_load += demand[customer]
    
    if len(current_route) > 1:
        current_route.append(depot)
        routes.append(current_route)
    
    # Pad with empty routes if needed
    while len(routes) < num_vehicles:
        routes.append([depot, depot])
    
    return routes

def evaluate_ecvrp(individual, CUSTOMERS, depot, demand, distance, vehicle_capacity, 
                   battery_capacity, alpha_empty, alpha_loaded):
    """Evaluate ECVRP solution fitness"""
    total_energy = 0
    penalty = 0
    
    served = set()
    for route in individual:
        for node in route:
            if node in CUSTOMERS:
                served.add(node)
    
    for route in individual:
        if len(route) <= 2:
            continue
        
        route_energy = 0
        current_load = 0
        current_battery = battery_capacity
        
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            
            if to_node in CUSTOMERS:
                current_load += demand[to_node]
            elif to_node == depot and from_node != depot:
                current_load = 0
            
            if current_load > vehicle_capacity:
                penalty += 5000
            
            dist = distance[from_node][to_node]
            energy = dist * (alpha_empty + alpha_loaded * current_load)
            route_energy += energy
            
            if to_node == depot:
                current_battery = battery_capacity
            else:
                current_battery -= energy
            
            if current_battery < 0:
                penalty += 5000
        
        total_energy += route_energy
    
    unserved = len(CUSTOMERS) - len(served)
    penalty += unserved * 50000
    
    all_customers = []
    for route in individual:
        all_customers.extend([n for n in route if n in CUSTOMERS])
    duplicates = len(all_customers) - len(set(all_customers))
    penalty += duplicates * 50000
    
    return -total_energy - penalty

def crossover_ecvrp(parent1, parent2, CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles):
    """Order crossover for ECVRP"""
    customers1 = []
    for route in parent1:
        customers1.extend([c for c in route if c in CUSTOMERS])
    
    customers2 = []
    for route in parent2:
        customers2.extend([c for c in route if c in CUSTOMERS])
    
    size = len(customers1)
    # Safety check: if parents have different customer counts or too few customers
    if size < 2 or len(customers2) != size:
        return create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles)
    
    start, end = sorted(random.sample(range(size), 2))
    
    offspring_customers = [None] * size
    offspring_customers[start:end] = customers1[start:end]
    
    p2_idx = 0
    for i in range(size):
        if offspring_customers[i] is None:
            # Add bounds checking to prevent index out of range
            while p2_idx < len(customers2) and customers2[p2_idx] in offspring_customers:
                p2_idx += 1
            
            # If we've exhausted customers2, regenerate a new individual
            if p2_idx >= len(customers2):
                return create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles)
            
            offspring_customers[i] = customers2[p2_idx]
            p2_idx += 1
    
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
    """Mutation for ECVRP"""
    mutated = [route.copy() for route in individual]
    non_empty = [i for i, r in enumerate(mutated) if len(r) > 3]
    
    if len(non_empty) >= 2 and random.random() < 0.5:
        r1_idx, r2_idx = random.sample(non_empty, 2)
        r1 = mutated[r1_idx]
        r2 = mutated[r2_idx]
        
        c1_idx = random.randint(1, len(r1) - 2)
        c2_idx = random.randint(1, len(r2) - 2)
        r1[c1_idx], r2[c2_idx] = r2[c2_idx], r1[c1_idx]
    elif non_empty:
        route_idx = random.choice(non_empty)
        route = mutated[route_idx]
        
        if len(route) > 4:
            i = random.randint(1, len(route) - 3)
            j = random.randint(i + 1, len(route) - 2)
            route[i:j+1] = list(reversed(route[i:j+1]))
    
    return mutated

def create_ecvrp_neighbor(solution):
    """Create neighbor solution for SA"""
    neighbor = [route.copy() for route in solution]
    non_empty = [i for i, r in enumerate(neighbor) if len(r) > 3]
    
    if not non_empty:
        return neighbor
    
    operator = random.choice(['swap', 'reverse', 'insertion'])
    
    if operator == 'swap' and len(non_empty) >= 2:
        r1_idx, r2_idx = random.sample(non_empty, 2)
        r1 = neighbor[r1_idx]
        r2 = neighbor[r2_idx]
        
        c1_idx = random.randint(1, len(r1) - 2)
        c2_idx = random.randint(1, len(r2) - 2)
        r1[c1_idx], r2[c2_idx] = r2[c2_idx], r1[c1_idx]
        
    elif operator == 'reverse':
        route_idx = random.choice(non_empty)
        route = neighbor[route_idx]
        
        if len(route) > 4:
            i = random.randint(1, len(route) - 3)
            j = random.randint(i + 1, len(route) - 2)
            route[i:j+1] = list(reversed(route[i:j+1]))
    
    else:
        route_idx = random.choice(non_empty)
        route = neighbor[route_idx]
        
        if len(route) > 4:
            remove_idx = random.randint(1, len(route) - 2)
            customer = route.pop(remove_idx)
            insert_idx = random.randint(1, len(route) - 1)
            route.insert(insert_idx, customer)
    
    return neighbor

def solve_with_ga(CUSTOMERS, depot, demand, distance, vehicle_capacity, 
                  battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                  ALL_NODES, CHARGING_STATIONS, VEHICLES):
    """Solve using Genetic Algorithm"""
    from ga_solver import GeneticAlgorithm
    
    ga = GeneticAlgorithm(population_size=50, mutation_rate=0.2, elite_size=5, tournament_size=5)
    
    solution, fitness, history = ga.solve(
        create_individual_fn=lambda: create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles),
        evaluate_fn=lambda ind: evaluate_ecvrp(ind, CUSTOMERS, depot, demand, distance, 
                                                vehicle_capacity, battery_capacity, alpha_empty, alpha_loaded),
        crossover_fn=lambda p1, p2: crossover_ecvrp(p1, p2, CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles),
        mutate_fn=mutate_ecvrp,
        generations=100,
        verbose=False
    )
    
    return solution, fitness, history

def solve_with_sa(CUSTOMERS, depot, demand, distance, vehicle_capacity,
                  battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                  ALL_NODES, CHARGING_STATIONS, VEHICLES):
    """Solve using Simulated Annealing"""
    from sa_solver import SimulatedAnnealing
    
    sa = SimulatedAnnealing(max_iterations=200, max_sub_iterations=20, 
                           initial_temp=0.05, alpha=0.98)
    
    def cost_fn(sol):
        return -evaluate_ecvrp(sol, CUSTOMERS, depot, demand, distance,
                              vehicle_capacity, battery_capacity, alpha_empty, alpha_loaded)
    
    solution, cost, history = sa.solve(
        create_solution_fn=lambda: create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles),
        cost_fn=cost_fn,
        create_neighbor_fn=create_ecvrp_neighbor,
        verbose=False
    )
    
    return solution, cost, history

def solve_with_gasa(CUSTOMERS, depot, demand, distance, vehicle_capacity,
                    battery_capacity, num_vehicles, alpha_empty, alpha_loaded,
                    ALL_NODES, CHARGING_STATIONS, VEHICLES):
    """Solve using Hybrid GASA"""
    from gasa_solver import HybridGASA
    
    gasa = HybridGASA(
        population_size=30,
        generations=80,
        mutation_rate=0.2,
        elite_size=3,
        tournament_size=5,
        sa_iterations=15,
        initial_temp=0.1,
        alpha=0.97
    )
    
    solution, fitness, history = gasa.solve(
        create_individual_fn=lambda: create_ecvrp_individual(CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles),
        evaluate_fn=lambda ind: evaluate_ecvrp(ind, CUSTOMERS, depot, demand, distance,
                                                vehicle_capacity, battery_capacity, alpha_empty, alpha_loaded),
        crossover_fn=lambda p1, p2: crossover_ecvrp(p1, p2, CUSTOMERS, depot, demand, vehicle_capacity, num_vehicles),
        mutate_fn=mutate_ecvrp,
        create_neighbor_fn=create_ecvrp_neighbor,
        verbose=False
    )
    
    return solution, fitness, history

# Run all instances
all_results = []
total_start_time = time.time()

for idx, instance_file in enumerate(instance_files, 1):
    print(f"\n[{idx}/{len(instance_files)}]", end=" ")
    result = run_instance(instance_file, SOLVER_CHOICE)
    all_results.append(result)
    
    # Write result to file immediately
    with open(OUTPUT_FILE, 'a') as f:
        f.write("-" * 100 + "\n")
        f.write(f"Instance: {result['instance']}\n")
        f.write(f"Status: {result['status']}\n")
        
        if result['status'] == 'SUCCESS':
            f.write(f"  Customers: {result['num_customers']}\n")
            f.write(f"  Vehicles Available: {result['num_vehicles']}\n")
            f.write(f"  Vehicles Used: {result['vehicles_used']}\n")
            f.write(f"  Total Distance: {result['total_distance']:.2f} km\n")
            f.write(f"  Total Energy: {result['total_energy']:.2f} kWh\n")
            f.write(f"  Total Waste: {result['total_waste']} kg ({result['total_waste']/1000:.2f} tons)\n")
            f.write(f"  Energy per km: {result['energy_per_km']:.3f} kWh/km\n")
            f.write(f"  Solve Time: {result['solve_time']:.2f} seconds\n")
        else:
            f.write(f"  Error: {result.get('error', 'Unknown error')}\n")
            f.write(f"  Time: {result['time']:.2f} seconds\n")
        
        f.write("\n")

total_time = time.time() - total_start_time

# Write summary
print("\n" + "-" * 80)
print("BATCH RUN COMPLETED")
print("-" * 80)

successful = [r for r in all_results if r['status'] == 'SUCCESS']
failed = [r for r in all_results if r['status'] != 'SUCCESS']

print(f"\nTotal Instances: {len(all_results)}")
print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")
print(f"Total Time: {total_time/60:.2f} minutes")

with open(OUTPUT_FILE, 'a') as f:
    f.write("=" * 100 + "\n")
    f.write("SUMMARY STATISTICS\n")
    f.write("-" * 100 + "\n\n")
    
    f.write(f"Total Instances: {len(all_results)}\n")
    f.write(f"Successful: {len(successful)}\n")
    f.write(f"Failed: {len(failed)}\n")
    f.write(f"Total Time: {total_time/60:.2f} minutes\n\n")
    
    if successful:
        f.write("Detailed Results Table:\n")
        f.write("-" * 100 + "\n")
        f.write(f"{'Instance':<25} {'Customers':>10} {'Veh Used':>10} {'Distance':>12} "
                f"{'Energy':>12} {'Time(s)':>10}\n")
        f.write("-" * 100 + "\n")
        
        for r in successful:
            f.write(f"{r['instance']:<25} {r['num_customers']:>10} {r['vehicles_used']:>10} "
                   f"{r['total_distance']:>12.2f} {r['total_energy']:>12.2f} {r['solve_time']:>10.2f}\n")
        
        f.write("-" * 100 + "\n")
        
        # Aggregate statistics
        total_customers = sum(r['num_customers'] for r in successful)
        total_distance = sum(r['total_distance'] for r in successful)
        total_energy = sum(r['total_energy'] for r in successful)
        avg_energy_per_km = sum(r['energy_per_km'] for r in successful) / len(successful)
        
        f.write(f"\nAggregate Statistics:\n")
        f.write(f"  Total Customers Across All Instances: {total_customers}\n")
        f.write(f"  Total Distance: {total_distance:.2f} km\n")
        f.write(f"  Total Energy: {total_energy:.2f} kWh\n")
        f.write(f"  Average Energy per km: {avg_energy_per_km:.3f} kWh/km\n")
        f.write(f"  Average Solve Time: {sum(r['solve_time'] for r in successful)/len(successful):.2f} seconds\n")
    
    if failed:
        f.write(f"\n\nFailed Instances ({len(failed)}):\n")
        f.write("-" * 100 + "\n")
        for r in failed:
            f.write(f"  {r['instance']}: {r.get('error', 'Unknown error')}\n")
    
    f.write("\n" + "=" * 100 + "\n")
    f.write(f"End of Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 100 + "\n")

print(f"\nResults saved to: {OUTPUT_FILE}")
print("-" * 80)
