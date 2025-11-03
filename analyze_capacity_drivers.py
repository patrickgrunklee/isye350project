"""
ANALYZE: What is driving high shelf requirements?

Break down capacity consumption by:
1. SKU-level demand and inventory requirements
2. Packing efficiency per SKU
3. Contribution of each SKU to total shelf needs
4. Identify top bottlenecks
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")

print("="*100)
print("CAPACITY DRIVER ANALYSIS - WHY DO WE NEED 6,511+ SHELVES?")
print("="*100)

# Load data
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_3_1_business_days.csv")  # 3/1 DoH policy
configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_pure_sku.csv')

WORKING_DAYS_PER_MONTH = 21

def parse_dimension(dim_str):
    """Parse dimension string to tuple in inches"""
    parts = dim_str.strip().replace('x', ' x ').split(' x ')
    return tuple(float(p.strip()) for p in parts)

def parse_weight(weight_str):
    """Parse weight string to float"""
    return float(str(weight_str).split()[0])

print("\n[1] DEMAND ANALYSIS - Which SKUs have highest demand?")
print("="*100)

# Get pallet SKUs
pallet_skus = []
sku_info = {}

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    storage = str(row['Storage Method']).lower()

    if 'pallet' in storage:
        pallet_skus.append(sku)

        # Parse dimensions
        sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
        sell_volume = (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728  # cu ft
        sell_weight = parse_weight(row['Sell Pack Weight'])

        sku_info[sku] = {
            'sell_volume': sell_volume,
            'sell_weight': sell_weight,
            'sell_dims': sell_dims
        }

print(f"\nPallet SKUs: {len(pallet_skus)} SKUs")
print(f"SKUs: {', '.join(pallet_skus)}\n")

# Analyze demand for each pallet SKU
demand_analysis = []

for sku in pallet_skus:
    if sku not in demand_df.columns:
        continue

    peak_demand = demand_df[sku].max()
    avg_demand = demand_df[sku].mean()
    total_demand = demand_df[sku].sum()

    # Get DoH for each facility
    doh_row = lead_time_df[lead_time_df['SKU Number'] == sku]
    if len(doh_row) == 0:
        continue

    # Average DoH across facilities
    col_doh = doh_row['Columbus - Days on Hand'].values[0]
    sac_doh = doh_row['Sacramento - Days on Hand'].values[0]
    aus_doh = doh_row['Austin Days on Hand'].values[0]
    avg_doh = np.mean([col_doh, sac_doh, aus_doh])

    # Calculate required inventory (peak demand scenario)
    daily_demand = peak_demand / WORKING_DAYS_PER_MONTH
    required_inventory = daily_demand * avg_doh

    demand_analysis.append({
        'SKU': sku,
        'Peak_Demand': peak_demand,
        'Avg_Demand': avg_demand,
        'Total_Demand': total_demand,
        'Avg_DoH': avg_doh,
        'Required_Inventory': required_inventory
    })

demand_df_analysis = pd.DataFrame(demand_analysis)
demand_df_analysis = demand_df_analysis.sort_values('Required_Inventory', ascending=False)

print("Top 10 SKUs by Required Inventory (peak demand × DoH):")
print("-" * 100)
print(f"{'SKU':<10} {'Peak Demand':<15} {'Avg DoH':<12} {'Required Inv':<20} {'% of Total':<15}")
print("-" * 100)

total_required_inv = demand_df_analysis['Required_Inventory'].sum()

for _, row in demand_df_analysis.head(10).iterrows():
    pct = (row['Required_Inventory'] / total_required_inv * 100)
    print(f"{row['SKU']:<10} {row['Peak_Demand']:<15,.0f} {row['Avg_DoH']:<12.1f} {row['Required_Inventory']:<20,.0f} {pct:<15.1f}%")

print("-" * 100)
print(f"{'TOTAL':<10} {'':<15} {'':<12} {total_required_inv:<20,.0f} {'100.0%':<15}")

print("\n" + "="*100)
print("[2] PACKING EFFICIENCY - How many units fit per shelf?")
print("="*100)

# Get best capacity for each SKU
sku_capacities = {}

for sku in pallet_skus:
    sku_configs = configs_df[
        (configs_df['SKU'] == sku) &
        (configs_df['Storage_Type'] == 'Pallet')
    ]

    if len(sku_configs) == 0:
        continue

    # Get best configuration (max packages per shelf)
    best_config = sku_configs.loc[sku_configs['Total_Packages_per_Shelf'].idxmax()]

    sku_capacities[sku] = {
        'packages_per_shelf': best_config['Total_Packages_per_Shelf'],
        'units_per_package': best_config['Units_per_Package'],
        'units_per_shelf': best_config['Total_Packages_per_Shelf'] * best_config['Units_per_Package'],
        'weight_per_shelf': best_config['Total_Weight'],
        'config_type': best_config.get('Config_Type', 'Unknown')
    }

print("\nBest Packing Configuration by SKU:")
print("-" * 100)
print(f"{'SKU':<10} {'Units/Shelf':<15} {'Packages/Shelf':<20} {'Config Type':<25} {'Weight (lbs)':<15}")
print("-" * 100)

for sku in pallet_skus:
    if sku not in sku_capacities:
        print(f"{sku:<10} {'NO CONFIG':<15}")
        continue

    cap = sku_capacities[sku]
    print(f"{sku:<10} {cap['units_per_shelf']:<15,.0f} {cap['packages_per_shelf']:<20,.0f} {cap['config_type']:<25} {cap['weight_per_shelf']:<15,.1f}")

print("\n" + "="*100)
print("[3] SHELF REQUIREMENTS - Required Inventory ÷ Capacity per Shelf")
print("="*100)

shelf_requirements = []

for _, row in demand_df_analysis.iterrows():
    sku = row['SKU']
    required_inv = row['Required_Inventory']

    if sku not in sku_capacities:
        continue

    units_per_shelf = sku_capacities[sku]['units_per_shelf']

    if units_per_shelf > 0:
        shelves_needed = required_inv / units_per_shelf
    else:
        shelves_needed = 0

    shelf_requirements.append({
        'SKU': sku,
        'Required_Inventory': required_inv,
        'Units_per_Shelf': units_per_shelf,
        'Shelves_Needed': shelves_needed,
        'Config_Type': sku_capacities[sku]['config_type']
    })

shelf_req_df = pd.DataFrame(shelf_requirements)
shelf_req_df = shelf_req_df.sort_values('Shelves_Needed', ascending=False)

print("\nShelves Needed by SKU (sorted by highest requirement):")
print("-" * 100)
print(f"{'SKU':<10} {'Required Inv':<20} {'Units/Shelf':<15} {'Shelves':<15} {'% of Total':<15}")
print("-" * 100)

total_shelves = shelf_req_df['Shelves_Needed'].sum()

for _, row in shelf_req_df.iterrows():
    pct = (row['Shelves_Needed'] / total_shelves * 100) if total_shelves > 0 else 0
    print(f"{row['SKU']:<10} {row['Required_Inventory']:<20,.0f} {row['Units_per_Shelf']:<15,.0f} {row['Shelves_Needed']:<15,.0f} {pct:<15.1f}%")

print("-" * 100)
print(f"{'TOTAL':<10} {'':<20} {'':<15} {total_shelves:<15,.0f} {'100.0%':<15}")

print("\n" + "="*100)
print("[4] ROOT CAUSE ANALYSIS - Top 5 Bottlenecks")
print("="*100)

print("\nTop 5 SKUs driving shelf requirements:\n")

for i, (_, row) in enumerate(shelf_req_df.head(5).iterrows(), 1):
    sku = row['SKU']
    shelves = row['Shelves_Needed']
    required_inv = row['Required_Inventory']
    units_per_shelf = row['Units_per_Shelf']
    pct = (shelves / total_shelves * 100)

    # Get SKU details
    sku_detail = sku_info.get(sku, {})
    dims = sku_detail.get('sell_dims', (0,0,0))
    volume = sku_detail.get('sell_volume', 0)
    weight = sku_detail.get('sell_weight', 0)

    # Get demand details
    demand_row = demand_df_analysis[demand_df_analysis['SKU'] == sku]
    if len(demand_row) > 0:
        peak_demand = demand_row.iloc[0]['Peak_Demand']
        avg_doh = demand_row.iloc[0]['Avg_DoH']
    else:
        peak_demand = 0
        avg_doh = 0

    print(f"#{i} - {sku}: {shelves:,.0f} shelves ({pct:.1f}% of total)")
    print(f"    Package: {dims[0]:.0f}×{dims[1]:.0f}×{dims[2]:.0f} inches, {volume:.2f} cu ft, {weight:.1f} lbs")
    print(f"    Peak demand: {peak_demand:,.0f} units/month")
    print(f"    DoH requirement: {avg_doh:.1f} business days")
    print(f"    Required inventory: {required_inv:,.0f} units")
    print(f"    Packing efficiency: {units_per_shelf:,.0f} units/shelf")
    print(f"    → Need {shelves:,.0f} shelves to hold inventory")
    print()

print("="*100)
print("SUMMARY: What's driving high requirements?")
print("="*100)

print("\n1. HIGH DEMAND:")
top_5_demand = shelf_req_df.head(5)
top_5_pct = (top_5_demand['Shelves_Needed'].sum() / total_shelves * 100)
print(f"   - Top 5 SKUs account for {top_5_pct:.1f}% of shelf requirements")
print(f"   - Peak monthly demand for these SKUs is very high")

print("\n2. DAYS-ON-HAND MULTIPLIER:")
print(f"   - Safety stock formula: (Peak Demand / 21 days) × DoH")
print(f"   - With 3/1 DoH: International needs 3 days, Domestic needs 1 day")
print(f"   - This multiplies storage requirements by DoH factor")

print("\n3. PACKING EFFICIENCY:")
low_efficiency = shelf_req_df[shelf_req_df['Units_per_Shelf'] < 100]
if len(low_efficiency) > 0:
    print(f"   - {len(low_efficiency)} SKUs have <100 units/shelf capacity")
    print(f"   - Large/bulky items (furniture, large electronics) pack inefficiently")

print("\n4. SYSTEM CONSTRAINT:")
print(f"   - Columbus at 100% (3,080 shelves)")
print(f"   - Sacramento at 100% (1,100 shelves)")
print(f"   - Total system capacity: 4,180 shelves")
print(f"   - Total requirement: {total_shelves:,.0f} shelves")
print(f"   - Austin must absorb: {total_shelves - 4180:,.0f} shelves")

print("\n" + "="*100)
print("CONCLUSION")
print("="*100)
print("\nThe high shelf requirements are driven by:")
print("  1. Peak demand levels (especially for furniture and large items)")
print("  2. Days-on-hand safety stock multiplier (3 days intl, 1 day domestic)")
print("  3. Packing inefficiency for large/bulky items")
print("  4. Columbus + Sacramento at max capacity (forcing overflow to Austin)")
print("\nTo reduce requirements, consider:")
print("  - Lower DoH (but 3/1 already minimal with buffer)")
print("  - Improve packing efficiency (already using pure-SKU continuous)")
print("  - Reduce demand (not within control)")
print("  - Expand Columbus (not allowed per project constraints)")
print("="*100)
