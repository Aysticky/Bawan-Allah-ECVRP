# Running All ECVRP Instances

## Overview
This guide explains how to run all Mavrovouniotis ECVRP benchmark instances and collect results in a single file.

## Instance Files
All instance files are located in: `ALL_mavrovouniotis_ecvrp_customer_data_files/`

Total: **24 benchmark instances**

## Instance Format
All instances follow the same format as `customer_data.py`:
```python
num_customers = ...      # Number of customers
locations = [...]        # (x, y) coordinates for all nodes
depot = 0                # Depot index (always 0)
demand = [...]           # Demand at each node
vehicle_capacity = ...   # Maximum vehicle capacity
battery_capacity = ...   # Maximum battery capacity
num_vehicles = ...       # Number of available vehicles
```

## Running All Instances

### Basic Usage
```bash
# Activate virtual environment (if using one)
source .venv/Scripts/activate  # Windows Git Bash
# or
.venv\Scripts\activate.bat     # Windows CMD

# Run with default settings (GASA solver)
python run_all_instances.py
```

This will:
1. Run all 24 instances using the GASA solver
2. Save results to `results_all_instances.txt`
3. Display progress in the terminal

### Customizing the Run

#### Choose Different Solver
```bash
# Use Genetic Algorithm
python run_all_instances.py 2

# Use Simulated Annealing
python run_all_instances.py 3

# Use Hybrid GASA (default)
python run_all_instances.py 4
```

Solver Options:
- `1` - CPLEX MIP (not recommended for batch mode - too slow)
- `2` - Genetic Algorithm (GA)
- `3` - Simulated Annealing (SA)
- `4` - Hybrid GASA (recommended)

#### Specify Output File
```bash
# Custom output filename
python run_all_instances.py 4 my_results.txt

# Different solver and custom output
python run_all_instances.py 2 ga_results.txt
```

## Instance Characteristics

### E-Series (Easier instances)
- 29-112 customers
- 3-8 vehicles
- 4-11 charging stations

### F-Series (Fixed routes)
- 49-140 customers
- 4-5 vehicles
- 4-8 charging stations

### M-Series (Medium instances)
- 110-212 customers
- 7-16 vehicles
- 5-12 charging stations

### X-Series (Extra large instances)
- 147-1006 customers
- 7-207 vehicles
- 4-13 charging stations

## Troubleshooting

### Import Errors
Make sure all required files are in the same directory:
- `ga_solver.py`
- `sa_solver.py`
- `gasa_solver.py`

### Memory Issues (Large Instances)
If you run out of memory on very large instances (X-n1006), consider:
- Reducing population size in the solver
- Reducing number of generations
- Running large instances separately

### Slow Execution
To speed up execution:
- Use GASA or GA (faster than SA for large instances)
- Reduce `generations` parameter
- Skip very large instances initially

## Tips for Best Results

1. **Start Small**: Test with a few instances first
   ```python
   # Edit run_all_instances.py to limit instances
   instance_files = sorted(glob.glob(os.path.join(instance_dir, "E-*.py")))
   ```

2. **Compare Solvers**: Run with different solvers and compare results
   ```bash
   python run_all_instances.py 2 ga_results.txt
   python run_all_instances.py 3 sa_results.txt
   python run_all_instances.py 4 gasa_results.txt
   ```

3. **Monitor Progress**: The script prints progress in real-time

4. **Check Intermediate Results**: The output file is updated after each instance

## Running Single Instances

To run a single instance, use the original `ecvrp_waste_improved.py`:

```python
# Edit customer_data.py or create symlink
import sys
sys.path.insert(0, 'ALL_mavrovouniotis_ecvrp_customer_data_files')

# Then import the specific instance
from E_n29_k4_s7 import *  # Note: hyphens need to be underscores for import
```

Or copy the instance file to `customer_data.py`:
```bash
cp ALL_mavrovouniotis_ecvrp_customer_data_files/E-n29-k4-s7.py customer_data.py
python ecvrp_waste_improved.py
```
