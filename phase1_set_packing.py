"""
PHASE 1: SET PACKING OPTIMIZATION
==================================

Solves optimal packing configuration for each (facility, storage_type) combination.

Problem: For each shelf type, determine how many packages of each SKU to place
         to minimize wasted space while ensuring all SKUs are represented.

Objective: Maximize volume and weight utilization
Constraints:
  - Total volume ≤ shelf volume capacity
  - Total weight ≤ shelf weight capacity
  - Total items ≤ max items per shelf
  - Each SKU must have at least 1 package on shelf (≥ 1)

Output: packing_configurations.csv showing optimal package counts per shelf
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense
from pathlib import Path
import sys
import os

os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print("PHASE 1: SET PACKING OPTIMIZATION - SHELF CONFIGURATION")
print("="*100)
print("\nObjective: Determine optimal package counts per shelf to minimize wasted space")
print("Constraint: All SKUs using each storage type must be represented\n")

# Utility functions
def parse_dimension(dim_str, in_feet=False):
    """
    Parse dimension string to tuple (L, W, H) in feet
    If in_feet=True, dimensions are already in feet (don't divide by 12)
    If in_feet=False, dimensions are in inches (divide by 12)
    """
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        if in_feet:
            return tuple(float(p.strip()) for p in parts)
        else:
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

# Load data
print("[1/5] Loading data files...")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/5] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack details (what we store on shelves)
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

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

    sku_data[sku] = {
        'sell_volume': sell_volume,  # cu ft per package
        'sell_weight': sell_weight,  # lbs per package
        'sell_qty': sell_qty,        # units per package
        'storage_type': storage_type
    }

print(f"   ✓ Processed {len(sku_data)} SKUs")

# Load shelf capacities
print("\n[3/5] Loading shelf capacities...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

shelf_data = {}

# Get weight capacity
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

    if (fac, st) not in shelf_data:
        shelf_data[(fac, st)] = {}

    shelf_data[(fac, st)]['weight_capacity'] = float(row['Weight Max / Shelf'])

# Get volume capacity and max items
for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']
    dims_str = str(row['Dimensions (l,w,h)(ft)'])

    if (fac, st) not in shelf_data:
        shelf_data[(fac, st)] = {}

    if dims_str.strip().lower() != 'auto':
        dims = parse_dimension(dims_str.replace(',', ' x '), in_feet=True)  # Shelving Dimensions are in feet
        shelf_data[(fac, st)]['volume_capacity'] = dims[0] * dims[1] * dims[2]
        shelf_data[(fac, st)]['max_items'] = int(row['Package Capacity'])
    else:
        # Auto - set very high limits
        shelf_data[(fac, st)]['volume_capacity'] = 999999.0
        shelf_data[(fac, st)]['max_items'] = 999999

print(f"   ✓ Loaded capacity data for {len(shelf_data)} (facility, storage_type) combinations")

# Build packing configurations
print("\n[4/5] Solving set packing optimization for each shelf configuration...")
print("="*100)

all_configurations = []

for (fac, st) in sorted(shelf_data.keys()):
    print(f"\n{'='*100}")
    print(f"FACILITY: {fac} | STORAGE TYPE: {st}")
    print(f"{'='*100}")

    # Find SKUs that use this storage type
    skus_for_st = [sku for sku, data in sku_data.items() if data['storage_type'] == st]

    if not skus_for_st:
        print(f"  ⚠️  No SKUs assigned to {st} at {fac}")
        continue

    print(f"\n  SKUs using this storage: {len(skus_for_st)}")
    print(f"    {', '.join(skus_for_st)}")

    # Get shelf constraints
    vol_cap = shelf_data[(fac, st)].get('volume_capacity', 999999)
    weight_cap = shelf_data[(fac, st)].get('weight_capacity', 999999)
    max_items = shelf_data[(fac, st)].get('max_items', 999999)

    print(f"\n  Shelf Constraints:")
    print(f"    Volume capacity:  {vol_cap:>12,.1f} cu ft")
    print(f"    Weight capacity:  {weight_cap:>12,.1f} lbs")
    print(f"    Max items/shelf:  {max_items:>12,} packages")

    # Build optimization model
    m = Container()

    # Sets
    s = Set(m, name="s", records=skus_for_st)

    # Parameters
    sell_vol_records = [(sku, sku_data[sku]['sell_volume']) for sku in skus_for_st]
    sell_vol = Parameter(m, name="sell_vol", domain=s, records=sell_vol_records)

    sell_weight_records = [(sku, sku_data[sku]['sell_weight']) for sku in skus_for_st]
    sell_weight = Parameter(m, name="sell_weight", domain=s, records=sell_weight_records)

    # Decision variable: number of packages of each SKU on one shelf
    x = Variable(m, name="x", domain=s, type="integer")
    x.lo[s] = 1  # Each SKU must have at least 1 package

    # Objective: Maximize utilization (minimize waste)
    # Use weighted combination of volume and weight utilization
    total_vol_used = Sum(s, x[s] * sell_vol[s])
    total_weight_used = Sum(s, x[s] * sell_weight[s])

    # Normalize to percentages and maximize average utilization
    vol_utilization = total_vol_used / vol_cap
    weight_utilization = total_weight_used / weight_cap
    avg_utilization = (vol_utilization + weight_utilization) / 2

    # Constraints
    vol_constraint = Equation(m, name="vol_constraint")
    vol_constraint[...] = total_vol_used <= vol_cap

    weight_constraint = Equation(m, name="weight_constraint")
    weight_constraint[...] = total_weight_used <= weight_cap

    items_constraint = Equation(m, name="items_constraint")
    items_constraint[...] = Sum(s, x[s]) <= max_items

    # Objective equation
    obj = Equation(m, name="obj")
    obj[...] = avg_utilization == avg_utilization

    # Create and solve model
    packing_model = Model(
        m,
        name=f"packing_{fac}_{st}",
        equations=m.getEquations(),
        problem="MIP",
        sense=Sense.MAX,
        objective=avg_utilization
    )

    print(f"\n  Solving optimization...")
    packing_model.solve()

    if packing_model.status.value in [1, 2, 8]:  # Optimal or feasible
        print(f"  ✓ Solution found: {packing_model.status}")

        # Extract results
        x_results = x.records

        total_vol = 0
        total_weight = 0
        total_items = 0

        print(f"\n  OPTIMAL PACKING CONFIGURATION:")
        print(f"  {'SKU':<10} {'Packages':<12} {'Volume Used (cu ft)':<20} {'Weight Used (lbs)':<20} {'Units per Package':<18}")
        print(f"  {'-'*90}")

        for _, row in x_results.iterrows():
            sku = row['s']
            packages = int(row['level'])
            vol_used = packages * sku_data[sku]['sell_volume']
            weight_used = packages * sku_data[sku]['sell_weight']
            units_per_pkg = sku_data[sku]['sell_qty']

            total_vol += vol_used
            total_weight += weight_used
            total_items += packages

            print(f"  {sku:<10} {packages:>8,} pkg    {vol_used:>12.2f} cu ft     {weight_used:>12.1f} lbs       {units_per_pkg:>8,} units")

            # Save to results list
            all_configurations.append({
                'Facility': fac,
                'Storage_Type': st,
                'SKU': sku,
                'Packages_per_Shelf': packages,
                'Volume_Used_per_Package': sku_data[sku]['sell_volume'],
                'Weight_Used_per_Package': sku_data[sku]['sell_weight'],
                'Units_per_Package': units_per_pkg,
                'Total_Volume_Used': vol_used,
                'Total_Weight_Used': weight_used
            })

        print(f"  {'-'*90}")
        print(f"  {'TOTAL':<10} {total_items:>8,} pkg    {total_vol:>12.2f} cu ft     {total_weight:>12.1f} lbs")

        vol_pct = (total_vol / vol_cap * 100) if vol_cap < 999999 else 0
        weight_pct = (total_weight / weight_cap * 100) if weight_cap < 999999 else 0
        items_pct = (total_items / max_items * 100) if max_items < 999999 else 0

        print(f"\n  UTILIZATION:")
        print(f"    Volume:  {vol_pct:>6.2f}%")
        print(f"    Weight:  {weight_pct:>6.2f}%")
        print(f"    Items:   {items_pct:>6.2f}%")

        # Identify bottleneck
        bottleneck = "Volume" if vol_pct > weight_pct else "Weight"
        if items_pct > max(vol_pct, weight_pct):
            bottleneck = "Item count"
        print(f"    Bottleneck: {bottleneck}")

    else:
        print(f"  ✗ Failed to solve: {packing_model.status}")

# Save results
print(f"\n{'='*100}")
print("[5/5] Saving results...")

config_df = pd.DataFrame(all_configurations)
output_file = RESULTS_DIR / 'packing_configurations.csv'
config_df.to_csv(output_file, index=False)

print(f"  ✓ Saved packing configurations to: {output_file}")

# Create summary
summary_file = RESULTS_DIR / 'PACKING_SUMMARY.txt'
with open(summary_file, 'w') as f:
    f.write("="*100 + "\n")
    f.write("PHASE 1: SET PACKING OPTIMIZATION - SUMMARY\n")
    f.write("="*100 + "\n\n")

    f.write(f"Total configurations generated: {len(config_df)}\n")
    f.write(f"\nConfigurations by storage type:\n")

    for st in storage_types:
        count = len(config_df[config_df['Storage_Type'] == st])
        if count > 0:
            f.write(f"  {st:<15}: {count:>4} SKU configurations\n")

    f.write("\n" + "="*100 + "\n")
    f.write("CONFIGURATION DETAILS\n")
    f.write("="*100 + "\n\n")

    for (fac, st), group in config_df.groupby(['Facility', 'Storage_Type']):
        f.write(f"\n{fac} - {st}:\n")
        f.write(f"  SKUs: {len(group)}\n")
        f.write(f"  Total packages per shelf: {group['Packages_per_Shelf'].sum():.0f}\n")
        f.write(f"  Total volume per shelf: {group['Total_Volume_Used'].sum():.2f} cu ft\n")
        f.write(f"  Total weight per shelf: {group['Total_Weight_Used'].sum():.1f} lbs\n")

print(f"  ✓ Saved summary to: {summary_file}")

print("\n" + "="*100)
print("PHASE 1 COMPLETE")
print("="*100)
print(f"\nNext step: Use {output_file.name} as input to Phase 2 (multiperiod model)")
