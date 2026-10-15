<<<<<<< HEAD
=======
"""Shared constants. Change numbers HERE and nowhere else."""

SAMPLE_PERIOD_S = 1.0
N_METERS = 4
N_ZONES = 3

METER_NAMES = ["F1", "F2", "F3", "F4"]
ZONE_NAMES = [
    "Zone 1 (F1-F2)",
    "Zone 2 (F2-F3)",
    "Zone 3 (F3-F4)"
]

SUPPLY_STATES = [
    "OFF",
    "STARTUP",
    "REFILLING",
    "STABLE",
    "SHUTDOWN"
]

# Simulator assumptions (SIMULATION ONLY)
NOMINAL_FLOW_LPM = 5.0
METER_NOISE_LPM = 0.08
METER_GAIN_SPREAD = 0.02

# Detection settings
>>>>>>> 97ecc4a8012d7482cb92e8b84a8337661ac8cf08
SMOOTH_WINDOW = 10
K_SIGMA = 4.0
PERSISTENCE = 5
MIN_STD_LPM = 0.02
MIN_LEAK_LPM = 0.15
STUCK_WINDOW = 8
MAX_VALID_LPM = 30.0