"""
Converted from Mavrovouniotis et al. (2020) E-CVRP benchmark instance: E-n30-k3-s7
Format: compatible with your GASA loader (customer_data.py schema).

Structure:
  - Node 0 is the depot (depot = 0)
  - Customers are nodes with demand > 0
  - Charging stations are nodes with demand == 0 (excluding depot)
"""

num_customers = 22

# Node locations: (x, y)
locations = [
    (266.0, 235.0),
    (295.0, 272.0),
    (301.0, 258.0),
    (309.0, 260.0),
    (217.0, 274.0),
    (218.0, 278.0),
    (282.0, 267.0),
    (242.0, 249.0),
    (230.0, 262.0),
    (249.0, 268.0),
    (256.0, 267.0),
    (265.0, 257.0),
    (267.0, 242.0),
    (259.0, 265.0),
    (315.0, 233.0),
    (329.0, 252.0),
    (318.0, 252.0),
    (329.0, 224.0),
    (267.0, 213.0),
    (275.0, 192.0),
    (303.0, 201.0),
    (208.0, 217.0),
    (326.0, 181.0),
    (228.0, 217.0),
    (233.0, 265.0),
    (270.0, 253.0),
    (284.0, 203.0),
    (313.0, 264.0),
    (314.0, 191.0),
    (316.0, 237.0),
]

depot = 0

# Demand per node (customers > 0; depot/stations = 0)
demand = [
    0,
    125,
    84,
    60,
    500,
    300,
    175,
    350,
    150,
    1100,
    4100,
    225,
    300,
    250,
    500,
    150,
    100,
    250,
    120,
    600,
    500,
    175,
    75,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

vehicle_capacity = 4500
battery_capacity = 162
num_vehicles = 3
