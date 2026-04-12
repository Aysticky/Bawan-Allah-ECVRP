"""
Converted from Mavrovouniotis et al. (2020) E-CVRP benchmark instance: E-n37-k4-s4
Format: compatible with your GASA loader (customer_data.py schema).

Structure:
  - Node 0 is the depot (depot = 0)
  - Customers are nodes with demand > 0
  - Charging stations are nodes with demand == 0 (excluding depot)
"""

num_customers = 32

# Node locations: (x, y)
locations = [
    (292.0, 495.0),
    (298.0, 427.0),
    (309.0, 445.0),
    (307.0, 464.0),
    (336.0, 475.0),
    (320.0, 439.0),
    (321.0, 437.0),
    (322.0, 437.0),
    (323.0, 433.0),
    (324.0, 433.0),
    (323.0, 429.0),
    (314.0, 435.0),
    (311.0, 442.0),
    (304.0, 427.0),
    (293.0, 421.0),
    (296.0, 418.0),
    (261.0, 384.0),
    (297.0, 410.0),
    (315.0, 407.0),
    (314.0, 406.0),
    (321.0, 391.0),
    (321.0, 398.0),
    (314.0, 394.0),
    (313.0, 378.0),
    (304.0, 382.0),
    (295.0, 402.0),
    (283.0, 406.0),
    (279.0, 399.0),
    (271.0, 401.0),
    (264.0, 414.0),
    (277.0, 439.0),
    (290.0, 434.0),
    (319.0, 433.0),
    (271.0, 411.0),
    (288.0, 391.0),
    (309.0, 416.0),
    (310.0, 473.0),
]

depot = 0

# Demand per node (customers > 0; depot/stations = 0)
demand = [
    0,
    700,
    400,
    400,
    1200,
    40,
    80,
    2000,
    900,
    600,
    750,
    1500,
    150,
    250,
    1600,
    450,
    700,
    550,
    650,
    200,
    400,
    300,
    1300,
    700,
    750,
    1400,
    4000,
    600,
    1000,
    500,
    2500,
    1700,
    1100,
    0,
    0,
    0,
    0,
]

vehicle_capacity = 8000
battery_capacity = 238
num_vehicles = 4
