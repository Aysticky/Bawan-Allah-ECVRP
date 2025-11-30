# Electric Capacitated Vehicle Routing Problem (ECVRP) for Waste Collection in China

This repo is confidential and is only to give updates to the stages of the Bawa research. Everything would be deleted and wiped out at the end.

## Project overview

Electric vehicle routing optimization for waste collection trucks in Chinese urban environments. Focus on battery constraints, charging station optimization, and realistic energy consumption modeling.

### Reference Papers
- `papers/` - Contains ECVRP literature for waste collection

### Start

# Activate environment
```bash
source .venv/Scripts/activate
```

# Run model
```bash
python ecvrp_waste_improved.py
```

## Added features

1 Multiple depot returns: Vehicles can dump waste and continue  
2 Load-dependent energy: Realistic battery consumption  
3 Smart charging: Optimize when/where to charge  
4 Waste collection specific: Designed for collection operations