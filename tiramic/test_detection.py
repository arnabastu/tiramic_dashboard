
import pandas as pd

from detection import (
    calculate_flow_differences,
    smooth_flow_differences,
    detect_possible_leaks,
    confirm_leaks
)

data = {
    "q1": [10, 10, 10, 10, 10, 10],
    "q2": [9, 9, 9, 9, 9, 9],
    "q3": [8, 8, 8, 8, 8, 8],
    "q4": [7, 7, 7, 7, 7, 7]
}

df = pd.DataFrame(data)

df = calculate_flow_differences(df)
df = smooth_flow_differences(df, window=1)
df = detect_possible_leaks(df, threshold=0.5)
df = confirm_leaks(df, persistence=5)

print(df[["zone1", "zone1_leak", "zone1_alarm"]])
