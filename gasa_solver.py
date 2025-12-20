"""
Hybrid GASA (Genetic algorithm + Simulated annealing) 
We combined population-based search (GA) with local search refinement (SA)
"""

import random
import math
import time


class HybridGASA:
    
    def __init__(self, population_size=30, generations=100, 
                 mutation_rate=0.2, elite_size=3, tournament_size=5,
                 sa_iterations=10, initial_temp=0.1, alpha=0.95):
        """
        Initialize hybrid GASA with parameters from both algorithms
        """
        # GA parameters
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
        
        # SA parameters for local search
        self.sa_iterations = sa_iterations
        self.initial_temp = initial_temp
        self.alpha = alpha
    
    def _sa_local_search(self, solution, cost_fn, create_neighbor_fn, temperature):
        """
        Apply SA local search to refine a solution
        """
        current_solution = solution
        current_cost = cost_fn(current_solution)
        best_solution = current_solution
        best_cost = current_cost
        
        for _ in range(self.sa_iterations):
            # Create neighbor
            neighbor = create_neighbor_fn(current_solution)
            neighbor_cost = cost_fn(neighbor)
            
            # SA acceptance criterion
            if neighbor_cost <= current_cost:
                # Accept better solution
                current_solution = neighbor
                current_cost = neighbor_cost
                
                if current_cost < best_cost:
                    best_solution = current_solution
                    best_cost = current_cost
            else:
                # Accept worse solution with probability
                delta = (neighbor_cost - current_cost) / (current_cost + 1e-10)
                probability = math.exp(-delta / temperature)
                
                if random.random() <= probability:
                    current_solution = neighbor
                    current_cost = neighbor_cost
        
        return best_solution, best_cost
    
    def _tournament_selection(self, population, fitness_scores):
        """GA tournament selection for parent selection"""
        tournament_indices = random.sample(range(len(population)), self.tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[tournament_fitness.index(max(tournament_fitness))]
        return population[winner_idx]
    
    def solve(self, create_individual_fn, evaluate_fn, crossover_fn, mutate_fn,
              create_neighbor_fn, verbose=True):
        """
        Run hybrid GASA to optimize problem
        """
        if verbose:
            print("-" * 70)
            print(f"GA: pop={self.population_size}, gens={self.generations}, "
                  f"mut_rate={self.mutation_rate}")
            print(f"SA: iters={self.sa_iterations}, temp={self.initial_temp}, "
                  f"alpha={self.alpha}")
        
        # Initialize population
        population = [create_individual_fn() for _ in range(self.population_size)]
        
        # Convert fitness to cost for SA (negate since SA minimizes)
        def cost_fn(individual):
            return -evaluate_fn(individual)
        
        best_fitness_history = []
        avg_fitness_history = []
        
        # Initial temperature for SA
        temperature = self.initial_temp
        
        if verbose:
            print(f"Running Hybrid GASA for {self.generations} generations...")
        
        for gen in range(self.generations):
            gen_start = time.time()
            
            # Phase 1: Evaluate population using fitness function
            fitness_scores = [evaluate_fn(ind) for ind in population]
            
            # Phase 2: Apply SA local search to promising individuals
            # Focus SA on top 50% of population to save computation
            sorted_indices = sorted(range(len(fitness_scores)), 
                                  key=lambda i: fitness_scores[i], 
                                  reverse=True)
            
            num_to_refine = max(1, self.population_size // 2)
            for idx in sorted_indices[:num_to_refine]:
                refined_solution, refined_cost = self._sa_local_search(
                    population[idx], cost_fn, create_neighbor_fn, temperature
                )
                population[idx] = refined_solution
                fitness_scores[idx] = -refined_cost  # Convert back to fitness
            
            # Track best
            best_idx = fitness_scores.index(max(fitness_scores))
            best_fitness = fitness_scores[best_idx]
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            
            best_fitness_history.append(best_fitness)
            avg_fitness_history.append(avg_fitness)
            
            # Print progress
            if verbose and (gen % 10 == 0 or gen == self.generations - 1):
                gen_time = time.time() - gen_start
                print(f"Gen {gen:3d} | Best Fitness: {best_fitness:12.2f} | "
                      f"Avg Fitness: {avg_fitness:12.2f} | Temp: {temperature:.4f} | "
                      f"Time: {gen_time:.3f}s")
            
            # Phase 3: GA reproduction (create new generation)
            new_population = []
            
            # Elitism: preserve best individuals
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i], 
                                 reverse=True)[:self.elite_size]
            for idx in elite_indices:
                new_population.append(population[idx])
            
            # Generate offspring using GA operators
            while len(new_population) < self.population_size:
                # Selection
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                # Crossover
                offspring = crossover_fn(parent1, parent2)
                
                # Mutation
                if random.random() < self.mutation_rate:
                    offspring = mutate_fn(offspring)
                
                new_population.append(offspring)
            
            population = new_population
            
            # Cool temperature for SA (adaptive cooling)
            temperature = self.alpha * temperature
        
        if verbose:
            print("-" * 70)
        
        # Return best solution
        fitness_scores = [evaluate_fn(ind) for ind in population]
        best_idx = fitness_scores.index(max(fitness_scores))
        best_solution = population[best_idx]
        best_fitness = fitness_scores[best_idx]
        
        return best_solution, best_fitness, best_fitness_history


