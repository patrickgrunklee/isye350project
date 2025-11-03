"""
Create smoothed demand dataset - remove top 2 peak months per SKU
Replace peak values with average of remaining 118 months
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from pathlib import Path

# Paths
DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
demand_file = DATA_DIR / "Demand Details.csv"
output_file = DATA_DIR / "Demand Details_SMOOTHED.csv"

# Load demand data
print("Loading demand data...")
demand_df = pd.read_csv(demand_file)

# Create copy for smoothing
smoothed_df = demand_df.copy()

# Get SKU columns (exclude Month and Year)
sku_columns = [col for col in demand_df.columns if col not in ['Month', 'Year']]

print(f"\nProcessing {len(sku_columns)} SKUs...")
print("=" * 80)

# Process each SKU
for sku in sku_columns:
    # Get demand values
    demand_values = demand_df[sku].values

    # Find top 2 peak indices
    sorted_indices = demand_values.argsort()[::-1]  # Descending order
    peak1_idx = sorted_indices[0]
    peak2_idx = sorted_indices[1]

    peak1_value = demand_values[peak1_idx]
    peak2_value = demand_values[peak2_idx]

    # Calculate average of remaining 118 months
    remaining_values = [v for i, v in enumerate(demand_values) if i not in [peak1_idx, peak2_idx]]
    avg_value = int(sum(remaining_values) / len(remaining_values))

    # Replace peaks with average
    smoothed_df.loc[peak1_idx, sku] = avg_value
    smoothed_df.loc[peak2_idx, sku] = avg_value

    # Report
    peak1_month = f"{demand_df.loc[peak1_idx, 'Month']} {demand_df.loc[peak1_idx, 'Year']}"
    peak2_month = f"{demand_df.loc[peak2_idx, 'Month']} {demand_df.loc[peak2_idx, 'Year']}"

    reduction1 = peak1_value - avg_value
    reduction2 = peak2_value - avg_value
    total_reduction = reduction1 + reduction2

    print(f"{sku}:")
    print(f"  Peak 1: {peak1_month:20s} {peak1_value:8,} → {avg_value:8,} (reduced by {reduction1:7,})")
    print(f"  Peak 2: {peak2_month:20s} {peak2_value:8,} → {avg_value:8,} (reduced by {reduction2:7,})")
    print(f"  Total reduction: {total_reduction:8,} units")
    print()

# Save smoothed demand
smoothed_df.to_csv(output_file, index=False)
print("=" * 80)
print(f"\nSmoothed demand saved to: {output_file}")
print(f"Original peak demands replaced with average of remaining 118 months")
