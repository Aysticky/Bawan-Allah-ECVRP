"""
Customer data for ECVRP - Waste Collection Problem
Static data file with 100 customers spread across 100km x 100km grid
"""

num_customers = 100  # Waste collection points

# Node locations: (x, y) coordinates in km
# Structure: Depot, Customers (1-100), Charging Stations (101-115)
locations = [
    (50, 50),   # 0: Depot (waste processing facility at city center)
    
    # Cluster 1: Northwest area (20, 20) - 10 customers
    (17, 23), (20, 14), (26, 21), (16, 17), (23, 25),
    (14, 21), (22, 17), (19, 26), (25, 19), (18, 15),
    
    # Cluster 2: North area (50, 20) - 10 customers
    (47, 23), (50, 14), (56, 21), (46, 17), (53, 25),
    (44, 21), (52, 17), (49, 26), (55, 19), (48, 15),
    
    # Cluster 3: Northeast area (80, 20) - 10 customers
    (77, 23), (80, 14), (86, 21), (76, 17), (83, 25),
    (74, 21), (82, 17), (79, 26), (85, 19), (78, 15),
    
    # Cluster 4: West area (20, 50) - 10 customers
    (17, 53), (20, 44), (26, 51), (16, 47), (23, 55),
    (14, 51), (22, 47), (19, 56), (25, 49), (18, 45),
    
    # Cluster 5: Center area (50, 50) - 10 customers
    (47, 53), (50, 44), (56, 51), (46, 47), (53, 55),
    (44, 51), (52, 47), (49, 56), (55, 49), (48, 45),
    
    # Cluster 6: East area (80, 50) - 10 customers
    (77, 53), (80, 44), (86, 51), (76, 47), (83, 55),
    (74, 51), (82, 47), (79, 56), (85, 49), (78, 45),
    
    # Cluster 7: Southwest area (20, 80) - 10 customers
    (17, 83), (20, 74), (26, 81), (16, 77), (23, 85),
    (14, 81), (22, 77), (19, 86), (25, 79), (18, 75),
    
    # Cluster 8: South area (50, 80) - 10 customers
    (47, 83), (50, 74), (56, 81), (46, 77), (53, 85),
    (44, 81), (52, 77), (49, 86), (55, 79), (48, 75),
    
    # Cluster 9: Southeast area (80, 80) - 10 customers
    (77, 83), (80, 74), (86, 81), (76, 77), (83, 85),
    (74, 81), (82, 77), (79, 86), (85, 79), (78, 75),
    
    # Cluster 10: Additional distributed customers - 10 customers
    (30, 35), (70, 35), (30, 65), (70, 65), (35, 30),
    (65, 30), (35, 70), (65, 70), (40, 60), (60, 40),
    
    # Charging stations (15 stations strategically placed)
    (30, 30), (70, 30), (30, 70), (70, 70), (50, 50),  # 101-105: Main corners and center
    (40, 40), (60, 40), (40, 60), (60, 60),             # 106-109: Inner grid
    (25, 50), (75, 50), (50, 25), (50, 75),             # 110-113: Cardinal directions
    (35, 65), (65, 35),                                  # 114-115: Additional coverage
]

depot = 0

# Waste demands (kg) - realistic range for urban waste collection
# Depot and charging stations have 0 demand, customers have 50-300 kg
demand = [
    0,  # Depot
    # 100 customers with varying demands
    50, 57, 64, 71, 78, 85, 92, 99, 106, 113,
    120, 127, 134, 141, 148, 155, 162, 169, 176, 183,
    190, 197, 204, 211, 218, 225, 232, 239, 246, 253,
    260, 267, 274, 281, 288, 295, 50, 57, 64, 71,
    78, 85, 92, 99, 106, 113, 120, 127, 134, 141,
    148, 155, 162, 169, 176, 183, 190, 197, 204, 211,
    218, 225, 232, 239, 246, 253, 260, 267, 274, 281,
    288, 295, 50, 57, 64, 71, 78, 85, 92, 99,
    106, 113, 120, 127, 134, 141, 148, 155, 162, 169,
    176, 183, 190, 197, 204, 211, 218, 225, 232, 239,
    # 15 charging stations with 0 demand
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
]

# Vehicle specifications (realistic for electric waste trucks)
vehicle_capacity = 3000  # kg (3 tons) - typical for urban waste collection
battery_capacity = 150.0  # kWh - realistic for electric trucks
num_vehicles = 12  # Calculated based on total demand ~16,000 kg
