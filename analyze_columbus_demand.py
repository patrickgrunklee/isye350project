"""
ANALYZE: What's driving Columbus pallet requirements?

Identify which SKUs need pallet storage and their peak demands
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

# Load data
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")

# Identify pallet SKUs
pallet_skus = []
for _, row in sku_details_df.iterrows():
    storage = str(row['Storage Method']).lower()
    if 'pallet' in storage:
        pallet_skus.append(row['SKU Number'])

print("="*100)
print("COLUMBUS PALLET DEMAND ANALYSIS")
print("="*100)

print(f"\nPallet SKUs: {', '.join(pallet_skus)}")
print(f"Total: {len(pallet_skus)} SKUs\n")

# Analyze demand
print("Peak demand and days-on-hand requirements:")
print("-" * 100)
print(f"{'SKU':<10} {'Peak Demand':<15} {'Columbus DoH':<15} {'Peak Inventory':<20} {'Supplier':<15}")
print("-" * 100)

total_peak_inv = 0

for sku in pallet_skus:
    if sku in demand_df.columns:
        peak_demand = demand_df[sku].max()

        # Get Columbus DoH
        doh_row = lead_time_df[lead_time_df['SKU Number'] == sku]
        if len(doh_row) > 0:
            col_doh = doh_row['Columbus - Days on Hand'].values[0]
            supplier = doh_row['Supplier Type'].values[0]

            # Calculate peak inventory needed
            # Inventory = (peak_demand / 21 working_days) * days_on_hand
            daily_demand = peak_demand / 21
            peak_inv = daily_demand * col_doh

            total_peak_inv += peak_inv

            print(f"{sku:<10} {peak_demand:<15,.0f} {col_doh:<15} {peak_inv:<20,.0f} {supplier:<15}")

print("-" * 100)
print(f"{'TOTAL':<10} {'':<15} {'':<15} {total_peak_inv:<20,.0f}")

print("\n" + "="*100)
print("3D BIN PACKING CAPACITY")
print("="*100)

# Load 3D configurations
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")
configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')

columbus_pallet = configs_df[(configs_df['Facility'] == 'Columbus') &
                              (configs_df['Storage_Type'] == 'Pallet')]

print("\nColumbus pallet configurations:")
print("-" * 100)
print(f"{'SKU':<10} {'Total_Pkg/Shelf':<20} {'Units/Pkg':<15} {'Units/Shelf':<20}")
print("-" * 100)

config_capacity = {}
for sku in pallet_skus:
    sku_config = columbus_pallet[columbus_pallet['SKU'] == sku]
    if len(sku_config) > 0:
        total_pkg = sku_config['Total_Packages_per_Shelf'].values[0]
        units_per_pkg = sku_config['Units_per_Package'].values[0]
        units_per_shelf = total_pkg * units_per_pkg
        config_capacity[sku] = units_per_shelf
        print(f"{sku:<10} {total_pkg:<20} {units_per_pkg:<15} {units_per_shelf:<20,.0f}")
    else:
        print(f"{sku:<10} {'NO CONFIG':<20}")

print("\n" + "="*100)
print("SHELF REQUIREMENTS")
print("="*100)

print("\nShelves needed to hold peak inventory:")
print("-" * 100)
print(f"{'SKU':<10} {'Peak Inventory':<20} {'Units/Shelf':<20} {'Shelves Needed':<20}")
print("-" * 100)

total_shelves = 0
for sku in pallet_skus:
    if sku in demand_df.columns:
        peak_demand = demand_df[sku].max()
        doh_row = lead_time_df[lead_time_df['SKU Number'] == sku]
        if len(doh_row) > 0:
            col_doh = doh_row['Columbus - Days on Hand'].values[0]
            daily_demand = peak_demand / 21
            peak_inv = daily_demand * col_doh

            if sku in config_capacity:
                units_per_shelf = config_capacity[sku]
                shelves_needed = peak_inv / units_per_shelf if units_per_shelf > 0 else 0
                total_shelves += shelves_needed
                print(f"{sku:<10} {peak_inv:<20,.0f} {units_per_shelf:<20,.0f} {shelves_needed:<20,.0f}")

print("-" * 100)
print(f"{'TOTAL':<10} {'':<20} {'':<20} {total_shelves:<20,.0f}")

print(f"\nCurrent Columbus pallet shelves: 3,080")
print(f"Required shelves: {total_shelves:,.0f}")
print(f"Shortfall: {total_shelves - 3080:,.0f} shelves")

print("\n" + "="*100)
print("TOP BOTTLENECKS")
print("="*100)

# Calculate % of total requirement
bottlenecks = []
for sku in pallet_skus:
    if sku in demand_df.columns:
        peak_demand = demand_df[sku].max()
        doh_row = lead_time_df[lead_time_df['SKU Number'] == sku]
        if len(doh_row) > 0:
            col_doh = doh_row['Columbus - Days on Hand'].values[0]
            daily_demand = peak_demand / 21
            peak_inv = daily_demand * col_doh

            if sku in config_capacity:
                units_per_shelf = config_capacity[sku]
                shelves_needed = peak_inv / units_per_shelf if units_per_shelf > 0 else 0
                pct = (shelves_needed / total_shelves * 100) if total_shelves > 0 else 0
                bottlenecks.append((sku, shelves_needed, pct))

bottlenecks.sort(key=lambda x: x[1], reverse=True)

print("\nTop 5 SKUs by shelf requirement:")
print("-" * 60)
print(f"{'SKU':<10} {'Shelves':<20} {'% of Total':<20}")
print("-" * 60)
for sku, shelves, pct in bottlenecks[:5]:
    print(f"{sku:<10} {shelves:<20,.0f} {pct:<20.1f}%")

print("\n" + "="*100)
