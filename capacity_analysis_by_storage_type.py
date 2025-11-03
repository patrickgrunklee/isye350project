"""
Capacity Analysis by Storage Type and Facility
Analyzes current capacity, demand requirements, and shortfalls for Set Packing model
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

# Load data
print("="*100)
print("WAREHOUSE CAPACITY ANALYSIS BY STORAGE TYPE")
print("="*100)

demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

# Parse functions
def parse_dimension(dim_str):
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        return tuple(float(p.strip()) / 12 for p in parts)
    except:
        return (1.0, 1.0, 1.0)

def parse_weight(wt_str):
    try:
        return float(str(wt_str).replace('lbs', '').replace('lb', '').strip())
    except:
        return 1.0

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

# Parse SKU details
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])

    # Inbound pack
    inbound_dims = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_volume = inbound_dims[0] * inbound_dims[1] * inbound_dims[2]
    inbound_weight = parse_weight(row['Inbound Pack Weight'])
    inbound_qty = parse_quantity(row['Inbound Pack Quantity'])

    # Storage type
    storage_method = str(row['Storage Method']).strip().lower()
    if 'bin' in storage_method:
        storage_type = 'Bins'
    elif 'hazmat' in storage_method:
        storage_type = 'Hazmat'
    elif 'rack' in storage_method:
        storage_type = 'Racking'
    elif 'pallet' in storage_method:
        storage_type = 'Pallet'
    else:
        storage_type = 'Bins'

    can_consolidate = 1 if str(row['Can be packed out in a box with other materials (consolidation)?']).strip().lower() == 'yes' else 0

    sku_data[sku] = {
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'inbound_volume': inbound_volume,
        'inbound_weight': inbound_weight,
        'inbound_qty': inbound_qty,
        'storage_type': storage_type,
        'can_consolidate': can_consolidate,
        'supplier': row['Supplier Type'].strip()
    }

# Calculate demand stats
print("\n[1/4] Calculating demand requirements by SKU...")
skus = list(sku_details_df['SKU Number'].unique())
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

# Total demand and peak demand per SKU
demand_stats = {}
for sku in skus:
    total_demand = demand_df[sku].sum()
    peak_demand = demand_df[sku].max()
    avg_demand = demand_df[sku].mean()
    avg_daily_demand = avg_demand / 21  # 21 business days per month

    demand_stats[sku] = {
        'total': total_demand,
        'peak_month': peak_demand,
        'avg_month': avg_demand,
        'avg_daily': avg_daily_demand
    }

# Calculate required inventory by DoH scenario
print("\n[2/4] Calculating inventory requirements for different DoH scenarios...")

DOH_SCENARIOS = {
    'Scenario 1: 1 day domestic, 3 day international': {'domestic': 1, 'international': 3},
    'Scenario 2: 2 day domestic, 5 day international': {'domestic': 2, 'international': 5},
    'Scenario 3: 3 day domestic, 7 day international': {'domestic': 3, 'international': 7},
}

# Parse current shelving capacity
print("\n[3/4] Loading current shelving capacity...")
curr_shelves = {}
shelf_vol = {}
shelf_weight = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st_raw = row['Shelving Type'].strip()

    if 'Pallet' in st_raw:
        st = 'Pallet'
    elif 'Bin' in st_raw:
        st = 'Bins'
    elif 'Rack' in st_raw:
        st = 'Racking'
    elif 'Hazmat' in st_raw:
        st = 'Hazmat'
    else:
        st = st_raw

    curr_shelves[(fac, st)] = int(row['Number of Shelves'])
    shelf_weight[(fac, st)] = float(row['Weight Max / Shelf'])

for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']
    dims_str = str(row['Dimensions (l,w,h)(ft)'])

    if dims_str.strip().lower() != 'auto':
        dims = parse_dimension(dims_str.replace(',', ' x '))
        shelf_vol[(fac, st)] = dims[0] * dims[1] * dims[2]
    else:
        shelf_vol[(fac, st)] = 999999.0

print("\n[4/4] Analyzing capacity by storage type...")
print("\n" + "="*100)

# Analyze each storage type
for st in storage_types:
    print(f"\n{'='*100}")
    print(f"STORAGE TYPE: {st}")
    print(f"{'='*100}")

    # Find SKUs using this storage type
    skus_using_st = [s for s in skus if sku_data[s]['storage_type'] == st]

    if not skus_using_st:
        print(f"  No SKUs assigned to {st} storage")
        continue

    print(f"\n  SKUs using {st} storage: {len(skus_using_st)}")
    print(f"    {', '.join(skus_using_st)}")

    # Current capacity by facility
    print(f"\n  CURRENT CAPACITY BY FACILITY:")
    print(f"  {'Facility':<15} {'Shelves':<15} {'Total Volume (cu ft)':<25} {'Total Weight (lbs)':<20}")
    print(f"  {'-'*80}")

    total_shelves_st = 0
    total_volume_st = 0
    total_weight_st = 0

    for fac in facilities:
        shelves = curr_shelves.get((fac, st), 0)
        vol = shelf_vol.get((fac, st), 0)
        weight = shelf_weight.get((fac, st), 0)

        total_vol = shelves * vol
        total_weight = shelves * weight

        total_shelves_st += shelves
        total_volume_st += total_vol
        total_weight_st += total_weight

        print(f"  {fac:<15} {shelves:>10,} shv   {total_vol:>15,.0f} cu ft     {total_weight:>15,.0f} lbs")

    print(f"  {'-'*80}")
    print(f"  {'TOTAL':<15} {total_shelves_st:>10,} shv   {total_volume_st:>15,.0f} cu ft     {total_weight_st:>15,.0f} lbs")

    # Calculate demand requirements for each scenario
    for scenario_name, doh_config in DOH_SCENARIOS.items():
        print(f"\n  {scenario_name.upper()}")
        print(f"  {'-'*80}")

        total_required_volume_repacked = 0
        total_required_volume_inbound = 0
        total_required_weight_repacked = 0
        total_required_weight_inbound = 0

        sku_details_list = []

        for sku in skus_using_st:
            supplier = sku_data[sku]['supplier']
            doh_days = doh_config['domestic'] if supplier == 'Domestic' else doh_config['international']

            avg_daily = demand_stats[sku]['avg_daily']
            required_units = avg_daily * doh_days

            # Calculate storage if repacked to sell packs
            sell_vol = sku_data[sku]['sell_volume']
            sell_weight = sku_data[sku]['sell_weight']
            vol_repacked = required_units * sell_vol
            weight_repacked = required_units * sell_weight

            # Calculate storage if stored as inbound packs
            inbound_vol = sku_data[sku]['inbound_volume']
            inbound_weight = sku_data[sku]['inbound_weight']
            inbound_qty = sku_data[sku]['inbound_qty']
            num_inbound_packs = np.ceil(required_units / inbound_qty)
            vol_inbound = num_inbound_packs * inbound_vol
            weight_inbound = num_inbound_packs * inbound_weight

            can_consolidate = sku_data[sku]['can_consolidate']

            total_required_volume_repacked += vol_repacked
            total_required_volume_inbound += vol_inbound
            total_required_weight_repacked += weight_repacked
            total_required_weight_inbound += weight_inbound

            sku_details_list.append({
                'SKU': sku,
                'Supplier': supplier,
                'DoH (days)': doh_days,
                'Avg Daily Demand': avg_daily,
                'Required Units': required_units,
                'Volume if Repacked (cu ft)': vol_repacked,
                'Volume if Inbound (cu ft)': vol_inbound,
                'Can Consolidate': 'Yes' if can_consolidate else 'No'
            })

        # Print SKU details
        print(f"\n    SKU-LEVEL REQUIREMENTS:")
        sku_df = pd.DataFrame(sku_details_list)
        sku_df = sku_df.sort_values('Required Units', ascending=False)
        print(f"    {sku_df.to_string(index=False)}")

        # Summary
        print(f"\n    TOTAL REQUIREMENTS ACROSS ALL {len(skus_using_st)} SKUs:")
        print(f"      If ALL repacked to sell packs:")
        print(f"        Volume needed:  {total_required_volume_repacked:>15,.0f} cu ft")
        print(f"        Weight needed:  {total_required_weight_repacked:>15,.0f} lbs")
        print(f"      If ALL stored as inbound packs:")
        print(f"        Volume needed:  {total_required_volume_inbound:>15,.0f} cu ft")
        print(f"        Weight needed:  {total_required_weight_inbound:>15,.0f} lbs")

        # Compare to capacity
        print(f"\n    CAPACITY ANALYSIS:")
        print(f"      Current total capacity:")
        print(f"        Volume:         {total_volume_st:>15,.0f} cu ft")
        print(f"        Weight:         {total_weight_st:>15,.0f} lbs")

        # Best case (all repacked)
        vol_shortfall_repacked = total_required_volume_repacked - total_volume_st
        weight_shortfall_repacked = total_required_weight_repacked - total_weight_st
        vol_utilization_repacked = (total_required_volume_repacked / total_volume_st * 100) if total_volume_st > 0 else 999999
        weight_utilization_repacked = (total_required_weight_repacked / total_weight_st * 100) if total_weight_st > 0 else 999999

        print(f"\n      BEST CASE (all items repacked to sell packs):")
        print(f"        Volume utilization: {vol_utilization_repacked:>6.1f}%")
        print(f"        Weight utilization: {weight_utilization_repacked:>6.1f}%")
        if vol_shortfall_repacked > 0:
            print(f"        Volume SHORTFALL:   {vol_shortfall_repacked:>15,.0f} cu ft [X] OVER CAPACITY")
        else:
            print(f"        Volume EXCESS:      {-vol_shortfall_repacked:>15,.0f} cu ft [OK]")
        if weight_shortfall_repacked > 0:
            print(f"        Weight SHORTFALL:   {weight_shortfall_repacked:>15,.0f} lbs [X] OVER CAPACITY")
        else:
            print(f"        Weight EXCESS:      {-weight_shortfall_repacked:>15,.0f} lbs [OK]")

        # Worst case (all inbound)
        vol_shortfall_inbound = total_required_volume_inbound - total_volume_st
        weight_shortfall_inbound = total_required_weight_inbound - total_weight_st
        vol_utilization_inbound = (total_required_volume_inbound / total_volume_st * 100) if total_volume_st > 0 else 999999
        weight_utilization_inbound = (total_required_weight_inbound / total_weight_st * 100) if total_weight_st > 0 else 999999

        print(f"\n      WORST CASE (all items stored as inbound packs):")
        print(f"        Volume utilization: {vol_utilization_inbound:>6.1f}%")
        print(f"        Weight utilization: {weight_utilization_inbound:>6.1f}%")
        if vol_shortfall_inbound > 0:
            print(f"        Volume SHORTFALL:   {vol_shortfall_inbound:>15,.0f} cu ft [X] OVER CAPACITY")
        else:
            print(f"        Volume EXCESS:      {-vol_shortfall_inbound:>15,.0f} cu ft [OK]")
        if weight_shortfall_inbound > 0:
            print(f"        Weight SHORTFALL:   {weight_shortfall_inbound:>15,.0f} lbs [X] OVER CAPACITY")
        else:
            print(f"        Weight EXCESS:      {-weight_shortfall_inbound:>15,.0f} lbs [OK]")

        # Determine bottleneck
        bottleneck_repacked = "VOLUME" if vol_shortfall_repacked > weight_shortfall_repacked else "WEIGHT"
        bottleneck_inbound = "VOLUME" if vol_shortfall_inbound > weight_shortfall_inbound else "WEIGHT"

        if vol_shortfall_repacked > 0 or weight_shortfall_repacked > 0:
            print(f"\n      [!] INFEASIBLE even with optimal repacking!")
            print(f"          Bottleneck: {bottleneck_repacked}")
        else:
            print(f"\n      [OK] FEASIBLE with repacking")

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
