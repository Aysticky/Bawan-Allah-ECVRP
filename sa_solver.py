"""
SA implementation that can optimize any problem via cost function
"""
import random
import math
import time

class SimulatedAnnealing:
   
    def __init__(self, max_iterations=250, max_sub_iterations=15, 
                 initial_temp=0.025, alpha=0.99):
        """
        Initialize SA with algorithm parameters
        """
        self.max_iterations = max_iterations
        self.max_sub_iterations = max_sub_iterations
        self.initial_temp = initial_temp
        self.alpha = alpha
    
    def solve(self, create_solution_fn, cost_fn, create_neighbor_fn, 
              verbose=True):
        """
        Run SA to optimize problem
        """
        # Initialize
        if verbose:
            print(f"\nInitializing Simulated Annealing...")
            print(f"Max Iterations: {self.max_iterations}, Temp: {self.initial_temp}, Alpha: {self.alpha}")
        
        # Create and evaluate initial solution
        current_solution = create_solution_fn()
        current_cost = cost_fn(current_solution)
        
        # Initialize best solution
        best_solution = current_solution
        best_cost = current_cost
        
        # History tracking
        best_cost_history = []
        
        # Initialize temperature
        temperature = self.initial_temp
        
        if verbose:
            print(f"Initial Cost: {current_cost:.2f}")
            print("-" * 70)
        
        # Main SA loop
        for iteration in range(self.max_iterations):
            iter_start = time.time()
            
            for sub_iteration in range(self.max_sub_iterations):
                # Create and evaluate neighbor
                neighbor_solution = create_neighbor_fn(current_solution)
                neighbor_cost = cost_fn(neighbor_solution)
                
                # Decide whether to accept neighbor
                if neighbor_cost <= current_cost:
                    # Accept better solution
                    current_solution = neighbor_solution
                    current_cost = neighbor_cost
                else:
                    # Accept worse solution with probability
                    delta = (neighbor_cost - current_cost) / current_cost
                    probability = math.exp(-delta / temperature)
                    
                    if random.random() <= probability:
                        current_solution = neighbor_solution
                        current_cost = neighbor_cost
                
                # Update best solution
                if current_cost <= best_cost:
                    best_solution = current_solution
                    best_cost = current_cost
            
            # Store best cost
            best_cost_history.append(best_cost)
            
            # Print progress
            if verbose and (iteration % 10 == 0 or iteration == self.max_iterations - 1):
                iter_time = time.time() - iter_start
                print(f"Iter {iteration:3d} | Best Cost: {best_cost:10.2f} | "
                      f"Current: {current_cost:10.2f} | Temp: {temperature:.6f} | "
                      f"Time: {iter_time:.3f}s")
            
            # Update temperature (cooling)
            temperature = self.alpha * temperature
        
        if verbose:
            print("-" * 70)
        
        return best_solution, best_cost, best_cost_history


if __name__ == "__main__":
    # Simple test: minimize sum of squares (target = all zeros)
    print("SA Test: Minimize Sum of Squares")
    print("Goal: Find sequence of 10 numbers close to zero")
    
    sequence_length = 10
    
    def create_solution():
        return [random.uniform(-10, 10) for _ in range(sequence_length)]
    
    def cost(solution):
        return sum(x**2 for x in solution)
    
    def create_neighbor(solution):
        neighbor = solution.copy()
        idx = random.randint(0, sequence_length - 1)
        neighbor[idx] += random.uniform(-1, 1)
        return neighbor
    
    sa = SimulatedAnnealing(max_iterations=100, max_sub_iterations=10, 
                           initial_temp=1.0, alpha=0.95)
    
    solution, cost_value, history = sa.solve(
        create_solution_fn=create_solution,
        cost_fn=cost,
        create_neighbor_fn=create_neighbor,
        verbose=True
    )
    
    print("Solution Test Complete")
    print(f"Best solution: {[f'{x:.3f}' for x in solution]}")
    print(f"Best cost (sum of squares): {cost_value:.6f}")
    print("-" * 70)
