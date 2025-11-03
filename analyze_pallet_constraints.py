"""
ANALYZE: What constraints are limiting pallet capacity?

For each pallet SKU, identify:
1. Peak demand
2. Days-on-hand requirement → Required inventory
3. Capacity per shelf (from 3D packing configs)
4. Number of shelves needed
5. Which constraint is binding (volume, weight, package count, DoH)
"""

import pandas as pd
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")

print("="*100)
print("PALLET SKU CONSTRAINT ANALYSIS")
print("="*100)

# Load data
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_14_3_business_days.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')

# Identify pallet SKUs
pallet_skus = []
for _, row in sku_details_df.iterrows():
    storage = str(row['Storage Method']).lower()
    if 'pallet' in storage:
        pallet_skus.append(row['SKU Number'])

print(f"\nPallet SKUs: {', '.join(pallet_skus)}\n")

# Get Columbus pallet shelf specs
columbus_pallet_shelves = shelving_count_df[
    (shelving_count_df['Facility'].str.strip() == 'Columbus') &
    (shelving_count_df['Shelving Type'].str.contains('Pallet'))
]

if len(columbus_pallet_shelves) > 0:
    max_items_per_shelf = int(columbus_pallet_shelves['Max Items / Shelf'].values[0])
    weight_per_item = float(columbus_pallet_shelves['Weight Max / Item (lbs)'].values[0])
    weight_per_shelf = float(columbus_pallet_shelves['Weight Max / Shelf'].values[0])
    print("Columbus Pallet Shelf Specifications:")
    print("-" * 80)
    print(f"  Max items per shelf: {max_items_per_shelf}")
    print(f"  Weight limit per item: {weight_per_item} lbs")
    print(f"  Weight limit per shelf: {weight_per_shelf} lbs")
    print(f"  Volume per item slot: 64 cu ft (48x48x48 inches)")
    print(f"  Total shelf volume: {max_items_per_shelf * 64} cu ft")

# Get shelf dimensions
columbus_pallet_dims = shelving_dims_df[
    (shelving_dims_df['Location'].str.strip() == 'Columbus') &
    (shelving_dims_df['Storage Type'].str.contains('Pallet'))
]

if len(columbus_pallet_dims) > 0:
    shelf_dims = columbus_pallet_dims['Dimensions (l,w,h)(ft)'].values[0]
    print(f"  Shelf dimensions: {shelf_dims}")

print("\n" + "="*100)
print("SKU-LEVEL ANALYSIS")
print("="*100)

for sku in pallet_skus:
    print(f"\n{'='*100}")
    print(f"SKU: {sku}")
    print('='*100)

    # Get SKU details
    sku_row = sku_details_df[sku_details_df['SKU Number'] == sku]
    if len(sku_row) == 0:
        continue

    sku_row = sku_row.iloc[0]

    # Parse sell pack dimensions
    sell_dims_str = str(sku_row['Sell Pack Dimensions (in)'])
    sell_dims = [float(x.strip()) for x in sell_dims_str.replace('x', ' ').split()]
    sell_volume = (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728  # Convert to cu ft

    # Parse sell pack weight
    sell_weight_str = str(sku_row['Sell Pack Weight'])
    sell_weight = float(sell_weight_str.split()[0])

    print(f"\n[1] SKU Physical Characteristics:")
    print(f"  Sell pack dimensions: {sell_dims[0]:.1f} x {sell_dims[1]:.1f} x {sell_dims[2]:.1f} inches")
    print(f"  Sell pack volume: {sell_volume:.2f} cu ft")
    print(f"  Sell pack weight: {sell_weight} lbs")

    # Get demand
    if sku in demand_df.columns:
        peak_demand = demand_df[sku].max()
        avg_demand = demand_df[sku].mean()

        print(f"\n[2] Demand Profile:")
        print(f"  Peak monthly demand: {peak_demand:,.0f} units")
        print(f"  Average monthly demand: {avg_demand:,.0f} units")
    else:
        peak_demand = 0
        avg_demand = 0

    # Get days-on-hand
    doh_row = lead_time_df[lead_time_df['SKU Number'] == sku]
    if len(doh_row) > 0:
        col_doh = doh_row['Columbus - Days on Hand'].values[0]

        # Calculate required inventory
        daily_demand = peak_demand / 21
        required_inventory = daily_demand * col_doh

        print(f"\n[3] Safety Stock Requirement:")
        print(f"  Columbus days-on-hand: {col_doh} business days")
        print(f"  Daily demand rate: {daily_demand:,.1f} units/day")
        print(f"  Required inventory: {required_inventory:,.0f} units")
    else:
        col_doh = 0
        required_inventory = 0

    # Get configuration capacity
    columbus_configs = configs_df[
        (configs_df['Facility'] == 'Columbus') &
        (configs_df['Storage_Type'] == 'Pallet') &
        (configs_df['SKU'] == sku)
    ]

    if len(columbus_configs) > 0:
        print(f"\n[4] Available Packing Configurations:")
        print("-" * 80)
        print(f"{'Config_ID':<12} {'Pkg/Item':<12} {'Items/Shelf':<12} {'Total Pkg':<12} {'Total Weight':<15} {'Config Type':<20}")
        print("-" * 80)

        for _, config in columbus_configs.iterrows():
            config_id = config['Config_ID']
            pkg_per_item = config['Packages_per_Item']
            items_per_shelf = config['Items_per_Shelf']
            total_pkg = config['Total_Packages_per_Shelf']
            total_weight = config['Total_Weight']

            # Determine config type
            if items_per_shelf == 1 and total_pkg > 15:
                config_type = "Volume-only special"
            else:
                config_type = "3D bin packing"

            print(f"{config_id:<12} {pkg_per_item:<12} {items_per_shelf:<12} {total_pkg:<12} {total_weight:<15.0f} {config_type:<20}")

        # Get best configuration
        best_config = columbus_configs.loc[columbus_configs['Total_Packages_per_Shelf'].idxmax()]
        best_pkg_per_shelf = best_config['Total_Packages_per_Shelf']
        best_weight = best_config['Total_Weight']

        print(f"\n  → Best configuration: {best_pkg_per_shelf} packages/shelf")

        # Calculate shelves needed
        if best_pkg_per_shelf > 0:
            shelves_needed = required_inventory / best_pkg_per_shelf
            print(f"\n[5] Shelf Requirement:")
            print(f"  Required inventory: {required_inventory:,.0f} units")
            print(f"  Best capacity: {best_pkg_per_shelf} packages/shelf")
            print(f"  Shelves needed: {shelves_needed:,.0f}")

        # Analyze what's limiting capacity
        print(f"\n[6] Constraint Analysis (What limits packages per shelf?):")
        print("-" * 80)

        # Theoretical limits
        volume_limit = (max_items_per_shelf * 64) / sell_volume
        weight_limit = weight_per_shelf / sell_weight
        item_count_limit = max_items_per_shelf  # If treating each package as 1 item

        print(f"  Theoretical limits:")
        print(f"    By volume:       {volume_limit:>10,.1f} packages (shelf vol / package vol)")
        print(f"    By weight:       {weight_limit:>10,.1f} packages (shelf weight / package weight)")
        print(f"    By item slots:   {item_count_limit:>10} packages (if 1 pkg = 1 item)")
        print(f"    By 3D packing:   {best_pkg_per_shelf:>10} packages (actual achieved)")

        # Identify binding constraint
        print(f"\n  Binding constraint:")
        if best_weight >= weight_per_shelf * 0.95:
            print(f"    ⚠️  WEIGHT-LIMITED: Using {best_weight:,.0f} / {weight_per_shelf:,.0f} lbs ({best_weight/weight_per_shelf*100:.1f}%)")
        elif best_pkg_per_shelf * sell_volume >= max_items_per_shelf * 64 * 0.95:
            print(f"    ⚠️  VOLUME-LIMITED: Using {best_pkg_per_shelf * sell_volume:,.1f} / {max_items_per_shelf * 64:,.1f} cu ft ({best_pkg_per_shelf * sell_volume / (max_items_per_shelf * 64) * 100:.1f}%)")
        else:
            utilization = best_weight / weight_per_shelf * 100
            vol_util = best_pkg_per_shelf * sell_volume / (max_items_per_shelf * 64) * 100
            print(f"    ⚠️  3D PACKING INEFFICIENCY")
            print(f"        Weight utilization: {utilization:.1f}%")
            print(f"        Volume utilization: {vol_util:.1f}%")
            print(f"        Could theoretically fit more with perfect packing")

print("\n" + "="*100)
print("SUMMARY: What's limiting pallet capacity?")
print("="*100)
print("\n1. DAYS-ON-HAND CONSTRAINT:")
print("   - Model requires inventory = (daily_demand) × (DoH)")
print("   - Current policy: 10 business days for international, 3 for domestic")
print("   - This drives the total inventory requirement")
print()
print("2. PHYSICAL SHELF CONSTRAINTS:")
print("   - Columbus Pallet: 7 item slots per shelf")
print("   - Weight limit: 600 lbs per item (4,200 lbs per shelf)")
print("   - Volume limit: 64 cu ft per item (448 cu ft per shelf)")
print()
print("3. 3D BIN PACKING EFFICIENCY:")
print("   - Irregular package shapes don't pack perfectly")
print("   - Furniture (SKUD3, SKUC1) can use volume-only approach")
print("   - Other items limited by 3D packing algorithm efficiency")
print()
print("4. DEMAND VOLUME:")
print("   - High peak demands for furniture and textbooks")
print("   - Required inventory = demand × (DoH / 21 working days)")
print()
print("="*100)
