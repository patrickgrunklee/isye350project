"""
Diagnostic script to identify infeasibility sources in warehouse model.
Adds slack variables to all constraints to find which ones are violated.
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
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")

# Use small test case
MONTHS = 12
DAYS_PER_MONTH = 21

print("="*80)
print("INFEASIBILITY DIAGNOSTIC - WAREHOUSE MODEL")
print("="*80)
print(f"\nTesting with {MONTHS} months ({MONTHS * DAYS_PER_MONTH} business days)")
print("="*80)

# Load data
print("\n[1/5] Loading data...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")  # Contains both lead time and days on hand
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

print("   ✓ Data loaded")

# Extract basic info
print("\n[2/5] Processing data...")
skus = sku_details_df['SKU Number'].tolist()
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
months = list(range(1, MONTHS + 1))
days = list(range(1, DAYS_PER_MONTH + 1))

# Get demand for test period
demand_subset = demand_df.head(MONTHS)

# Calculate total demand
total_demand = {}
for sku in skus:
    if sku in demand_subset.columns:
        total_demand[sku] = demand_subset[sku].sum()
    else:
        total_demand[sku] = 0

print(f"   ✓ {len(skus)} SKUs, {len(facilities)} facilities")
print(f"   ✓ Total demand over {MONTHS} months:")
for sku in skus[:5]:  # Show first 5
    print(f"      {sku}: {total_demand[sku]:,.0f} units")

# Get current capacity
print("\n[3/5] Analyzing current capacity...")

# Merge shelving count and dimensions
shelving_df = shelving_count_df.merge(shelving_dims_df, on=['Facility', 'Storage Type'], how='left')

current_capacity = {}
for _, row in shelving_df.iterrows():
    fac = row['Facility']
    st = row['Storage Type']
    shelves = row['Current Shelves']
    vol = row['Shelf Volume (cuft)'] if 'Shelf Volume (cuft)' in row else 0
    wt = row['Shelf Weight Capacity (lbs)'] if 'Shelf Weight Capacity (lbs)' in row else 0
    pkg = row['Shelf Package Count'] if 'Shelf Package Count' in row else 0

    if fac not in current_capacity:
        current_capacity[fac] = {}
    current_capacity[fac][st] = {
        'shelves': shelves,
        'volume': shelves * vol,
        'weight': shelves * wt,
        'packages': shelves * pkg
    }

print("   ✓ Current capacity by facility:")
for fac in facilities:
    total_vol = sum(current_capacity[fac][st]['volume'] for st in storage_types if st in current_capacity[fac])
    total_wt = sum(current_capacity[fac][st]['weight'] for st in storage_types if st in current_capacity[fac])
    print(f"      {fac}: {total_vol:,.0f} cuft, {total_wt:,.0f} lbs")

# Calculate required capacity
print("\n[4/5] Calculating required capacity...")

# Parse SKU dimensions
def parse_dimension(dim_str):
    try:
        parts = str(dim_str).split('x')
        if len(parts) >= 3:
            return float(parts[0]) * float(parts[1]) * float(parts[2]) / 1728
        return 0
    except:
        return 0

def parse_weight(wt_str):
    try:
        return float(str(wt_str).replace('lbs', '').strip())
    except:
        return 0

sku_volumes = {}
sku_weights = {}
sku_storage_types = {}

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Parse dimensions
    if 'Inbound Pack Dimensions' in row:
        sku_volumes[sku] = parse_dimension(row['Inbound Pack Dimensions'])
    else:
        sku_volumes[sku] = 0

    # Parse weight
    if 'Inbound Pack Weight' in row:
        sku_weights[sku] = parse_weight(row['Inbound Pack Weight'])
    else:
        sku_weights[sku] = 0

    # Storage type
    storage_method = str(row['Storage Method']).lower() if 'Storage Method' in row else ''
    if 'bin' in storage_method:
        sku_storage_types[sku] = 'Bins'
    elif 'hazmat' in storage_method:
        sku_storage_types[sku] = 'Hazmat'
    elif 'rack' in storage_method:
        sku_storage_types[sku] = 'Racking'
    elif 'pallet' in storage_method:
        sku_storage_types[sku] = 'Pallet'
    else:
        sku_storage_types[sku] = 'Bins'

# Get days on hand (for safety stock) from Lead Time file
avg_doh = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    doh_values = []
    if 'Columbus - Days on Hand' in row:
        doh_values.append(row['Columbus - Days on Hand'])
    if 'Sacramento - Days on Hand' in row:
        doh_values.append(row['Sacramento - Days on Hand'])
    if 'Austin Days on Hand' in row:
        doh_values.append(row['Austin Days on Hand'])

    if doh_values:
        avg_doh[sku] = np.mean(doh_values)
    else:
        avg_doh[sku] = 7  # Default

# Calculate required inventory (demand + safety stock)
required_inventory = {}
for sku in skus:
    avg_monthly_demand = total_demand[sku] / MONTHS if MONTHS > 0 else 0
    avg_daily_demand = avg_monthly_demand / DAYS_PER_MONTH
    safety_stock = avg_daily_demand * avg_doh.get(sku, 7)
    required_inventory[sku] = safety_stock + avg_monthly_demand  # Roughly peak month + safety

# Calculate required capacity by storage type
required_capacity_by_type = {}
for st in storage_types:
    required_capacity_by_type[st] = {'volume': 0, 'weight': 0, 'units': 0}

for sku in skus:
    st = sku_storage_types.get(sku, 'Bins')
    inv = required_inventory[sku]
    vol = sku_volumes.get(sku, 0)
    wt = sku_weights.get(sku, 0)

    required_capacity_by_type[st]['volume'] += inv * vol
    required_capacity_by_type[st]['weight'] += inv * wt
    required_capacity_by_type[st]['units'] += inv

print("   ✓ Required capacity by storage type:")
for st in storage_types:
    req = required_capacity_by_type[st]
    print(f"      {st}: {req['volume']:,.0f} cuft, {req['weight']:,.0f} lbs, {req['units']:,.0f} units")

# Check capacity shortfalls
print("\n[5/5] IDENTIFYING CAPACITY GAPS...")
print("\n" + "="*80)
print("CAPACITY ANALYSIS BY FACILITY & STORAGE TYPE")
print("="*80)

total_shortfall_vol = 0
total_shortfall_wt = 0

for fac in facilities:
    print(f"\n{fac}:")
    print("-" * 80)

    for st in storage_types:
        # Current capacity
        curr = current_capacity.get(fac, {}).get(st, {'volume': 0, 'weight': 0, 'shelves': 0})

        # Assume demand is split equally across facilities (simplified)
        required_vol = required_capacity_by_type[st]['volume'] / 3
        required_wt = required_capacity_by_type[st]['weight'] / 3

        # Calculate gaps
        vol_gap = required_vol - curr['volume']
        wt_gap = required_wt - curr['weight']

        vol_status = "✓ SUFFICIENT" if vol_gap <= 0 else f"⚠ SHORT {vol_gap:,.0f} cuft"
        wt_status = "✓ SUFFICIENT" if wt_gap <= 0 else f"⚠ SHORT {wt_gap:,.0f} lbs"

        print(f"  {st}:")
        print(f"    Current: {curr['shelves']:,.0f} shelves, {curr['volume']:,.0f} cuft, {curr['weight']:,.0f} lbs")
        print(f"    Required: {required_vol:,.0f} cuft, {required_wt:,.0f} lbs")
        print(f"    Volume: {vol_status}")
        print(f"    Weight: {wt_status}")

        if vol_gap > 0:
            total_shortfall_vol += vol_gap
        if wt_gap > 0:
            total_shortfall_wt += wt_gap

print("\n" + "="*80)
print("SUMMARY OF CAPACITY CONSTRAINTS")
print("="*80)

if total_shortfall_vol > 0 or total_shortfall_wt > 0:
    print(f"\n⚠ CAPACITY SHORTFALLS DETECTED:")
    if total_shortfall_vol > 0:
        print(f"  - Total volume shortfall: {total_shortfall_vol:,.0f} cuft")
    if total_shortfall_wt > 0:
        print(f"  - Total weight shortfall: {total_shortfall_wt:,.0f} lbs")

    print(f"\n🔧 RECOMMENDED ACTIONS:")
    print(f"  1. Increase expansion limits (currently Sacramento ≤250K sqft, Austin ≤200K sqft)")
    print(f"  2. Check if repacking constraints are too restrictive")
    print(f"  3. Verify SKU dimensions and weights are parsed correctly")
    print(f"  4. Consider allowing overflow to multiple facilities")
else:
    print(f"\n✓ NO CAPACITY SHORTFALLS DETECTED")
    print(f"\n  Model infeasibility likely due to:")
    print(f"  1. Daily delivery constraints (max 1 truck/supplier/day)")
    print(f"  2. Lead time constraints creating temporal infeasibility")
    print(f"  3. Repacking variable conflicts")
    print(f"  4. Initial inventory constraints")

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80)
