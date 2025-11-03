"""
Simple capacity check - identify which constraints are the bottleneck
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

print("="*80)
print("SIMPLE CAPACITY CHECK")
print("="*80)

# Load data
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")

# Get total demand over 12 months
months = 12
demand_subset = demand_df.head(months)

skus = sku_details_df['SKU Number'].tolist()

print(f"\n1. DEMAND OVER {months} MONTHS:")
print("-"*80)
total_units = 0
for sku in skus:
    if sku in demand_subset.columns:
        sku_demand = demand_subset[sku].sum()
        total_units += sku_demand
        print(f"   {sku}: {sku_demand:>10,.0f} units")

print(f"\n   TOTAL: {total_units:>10,.0f} units")

# Get current capacity
print(f"\n2. CURRENT STORAGE CAPACITY:")
print("-"*80)
print("\n   Shelving Count:")
print(shelving_count_df.to_string(index=False))

# Calculate rough capacity utilization
# Assume average of 100 units per shelf (rough estimate)
avg_units_per_shelf = 100

total_shelves = shelving_count_df['Number of Shelves'].sum()
total_capacity_units = total_shelves * avg_units_per_shelf

print(f"\n3. ROUGH CAPACITY ESTIMATE:")
print("-"*80)
print(f"   Total shelves: {total_shelves:,.0f}")
print(f"   Assumed units/shelf: {avg_units_per_shelf}")
print(f"   Total capacity (rough): {total_capacity_units:,.0f} units")
print(f"   Total demand ({months} months): {total_units:,.0f} units")

utilization = (total_units / total_capacity_units * 100) if total_capacity_units > 0 else 999
print(f"   Utilization: {utilization:.1f}%")

if utilization > 100:
    shortfall = total_units - total_capacity_units
    print(f"\n   WARNING: CAPACITY SHORTFALL: {shortfall:,.0f} units")
    print(f"   Need approximately {shortfall / avg_units_per_shelf:,.0f} more shelves")
else:
    print(f"\n   OK: Sufficient capacity (based on rough estimate)")

# Check expansion limits
print(f"\n4. EXPANSION CONSTRAINTS:")
print("-"*80)
print(f"   Sacramento: Max 250,000 sqft expansion")
print(f"   Austin: Max 200,000 sqft expansion")
print(f"   Columbus: CANNOT expand (per project requirements)")

print(f"\n5. LIKELY INFEASIBILITY CAUSES:")
print("-"*80)
print(f"   1. WARNING: COLUMBUS BOTTLENECK: Columbus cannot expand but may be over capacity")
print(f"   2. WARNING: REPACKING CONSTRAINTS: Binary repacking variables may conflict")
print(f"   3. WARNING: DAILY DELIVERY LIMITS: Max 1 truck/supplier/day may be insufficient")
print(f"   4. WARNING: LEAD TIME + DAYS ON HAND: Safety stock requirements too high")

print("\n" + "="*80)
print("RECOMMENDATION:")
print("="*80)
print("Run the model WITHOUT repacking (set all repack variables to 0)")
print("This will identify if repacking is causing the infeasibility.")
print("="*80)
