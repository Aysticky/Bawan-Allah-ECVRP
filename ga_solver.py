"""
GA implementation that will optimize any problem via fitness function
"""

import random
import time


class GeneticAlgorithm:
    
    def __init__(self, population_size=50, mutation_rate=0.2, elite_size=5, tournament_size=5):
        """
        Initialize GA with algorithm parameters only
        
        Args:
            population_size: Number of individuals in population
            mutation_rate: Probability of mutation
            elite_size: Number of best individuals to preserve
            tournament_size: Size of tournament for selection
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
    
    def _tournament_selection(self, population, fitness_scores):
        """Select parent using tournament selection"""
        tournament_indices = random.sample(range(len(population)), self.tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[tournament_fitness.index(max(tournament_fitness))]
        return population[winner_idx]
    
    def solve(self, create_individual_fn, evaluate_fn, crossover_fn, mutate_fn, 
              generations=100, verbose=True):
        """
        Run GA to optimize problem
        """
        # Initialize population
        if verbose:
            print(f"\nInitializing GA population (size={self.population_size})...")
        
        population = [create_individual_fn() for _ in range(self.population_size)]
        
        best_fitness_history = []
        avg_fitness_history = []
        
        if verbose:
            print(f"Running GA for {generations} generations...")
            print("=" * 70)
        
        for gen in range(generations):
            gen_start = time.time()
            
            # Evaluate population
            fitness_scores = [evaluate_fn(ind) for ind in population]
            
            # Track best
            best_idx = fitness_scores.index(max(fitness_scores))
            best_fitness = fitness_scores[best_idx]
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            
            best_fitness_history.append(best_fitness)
            avg_fitness_history.append(avg_fitness)
            
            # Print progress
            if verbose and (gen % 10 == 0 or gen == generations - 1):
                gen_time = time.time() - gen_start
                print(f"Gen {gen:3d} | Best Fitness: {best_fitness:12.2f} | "
                      f"Avg Fitness: {avg_fitness:12.2f} | Time: {gen_time:.3f}s")
            
            # Create new population
            new_population = []
            
            # Elitism: keep best individuals
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i], 
                                 reverse=True)[:self.elite_size]
            for idx in elite_indices:
                new_population.append(population[idx])
            
            # Generate offspring
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                offspring = crossover_fn(parent1, parent2)
                
                if random.random() < self.mutation_rate:
                    offspring = mutate_fn(offspring)
                
                new_population.append(offspring)
            
            population = new_population
        
        if verbose:
            print("=" * 70)
        
        # Return best solution
        fitness_scores = [evaluate_fn(ind) for ind in population]
        best_idx = fitness_scores.index(max(fitness_scores))
        best_solution = population[best_idx]
        best_fitness = fitness_scores[best_idx]
        
        return best_solution, best_fitness, best_fitness_history


if __name__ == "__main__":
    # Simple test: optimize a list of numbers to sum to target
    print("=" * 70)
    print("GENERIC GA TEST: Number Sequence Optimization")
    print("=" * 70)
    print("Goal: Find sequence of 10 numbers (0-9) that sums close to 45")
    
    target_sum = 45
    sequence_length = 10
    
    def create_individual():
        return [random.randint(0, 9) for _ in range(sequence_length)]
    
    def evaluate(individual):
        total = sum(individual)
        return -abs(total - target_sum)  # Negative distance from target
    
    def crossover(parent1, parent2):
        point = random.randint(1, sequence_length - 1)
        return parent1[:point] + parent2[point:]
    
    def mutate(individual):
        idx = random.randint(0, sequence_length - 1)
        new_ind = individual.copy()
        new_ind[idx] = random.randint(0, 9)
        return new_ind
    
    ga = GeneticAlgorithm(population_size=50, mutation_rate=0.3, elite_size=5)
    
    solution, fitness, history = ga.solve(
        create_individual_fn=create_individual,
        evaluate_fn=evaluate,
        crossover_fn=crossover,
        mutate_fn=mutate,
        generations=50,
        verbose=True
    )
    
    print("\n" + "=" * 70)
    print("SOLUTION")
    print("=" * 70)
    print(f"Best sequence: {solution}")
    print(f"Sum: {sum(solution)}")
    print(f"Target: {target_sum}")
    print(f"Fitness: {fitness}")
    print("=" * 70)

"""
To test GA module, run: python ga_solver.py
"""