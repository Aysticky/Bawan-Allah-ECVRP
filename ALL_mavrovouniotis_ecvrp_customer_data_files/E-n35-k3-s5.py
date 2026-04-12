"""
Converted from Mavrovouniotis et al. (2020) E-CVRP benchmark instance: E-n35-k3-s5
Format: compatible with your GASA loader (customer_data.py schema).

Structure:
  - Node 0 is the depot (depot = 0)
  - Customers are nodes with demand > 0
  - Charging stations are nodes with demand == 0 (excluding depot)
"""

num_customers = 29

# Node locations: (x, y)
locations = [
    (162.0, 354.0),
    (218.0, 382.0),
    (218.0, 358.0),
    (201.0, 370.0),
    (214.0, 371.0),
    (224.0, 370.0),
    (210.0, 382.0),
    (104.0, 354.0),
    (126.0, 338.0),
    (119.0, 340.0),
    (129.0, 349.0),
    (126.0, 347.0),
    (125.0, 346.0),
    (116.0, 355.0),
    (126.0, 335.0),
    (125.0, 355.0),
    (119.0, 357.0),
    (115.0, 341.0),
    (153.0, 351.0),
    (175.0, 363.0),
    (180.0, 360.0),
    (159.0, 331.0),
    (188.0, 357.0),
    (152.0, 349.0),
    (215.0, 389.0),
    (212.0, 394.0),
    (188.0, 393.0),
    (207.0, 406.0),
    (184.0, 410.0),
    (207.0, 392.0),
    (117.0, 345.0),
    (156.0, 342.0),
    (173.0, 354.0),
    (196.0, 398.0),
    (216.0, 374.0),
]

depot = 0

# Demand per node (customers > 0; depot/stations = 0)
demand = [
    0,
    300,
    3100,
    125,
    100,
    200,
    150,
    150,
    450,
    300,
    100,
    950,
    125,
    150,
    150,
    550,
    150,
    100,
    150,
    400,
    300,
    1500,
    100,
    300,
    500,
    800,
    300,
    100,
    150,
    1000,
    0,
    0,
    0,
    0,
    0,
]

vehicle_capacity = 4500
battery_capacity = 138
num_vehicles = 3
