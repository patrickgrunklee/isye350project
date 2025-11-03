"""
Diagnostic Analysis - Determine why the model is infeasible
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
WORKING_DAYS_PER_MONTH = 21
SAFETY_STOCK_MULTIPLIER = 1.2

print("="*80)
print("DIAGNOSTIC ANALYSIS - Capacity vs. Demand")
print("="*80)

# Load data
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']

print(f"\nAnalyzing {len(skus)} SKUs across {len(facilities)} facilities")

# Parse SKU data
def parse_dimension(dim_str):
    parts = dim_str.strip().split(' x ')
    return tuple(float(p) / 12 for p in parts)

def parse_weight(weight_str):
    return float(str(weight_str).split()[0])

sku_info = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    volume = sell_dims[0] * sell_dims[1] * sell_dims[2]

    storage_method = str(row['Storage Method']).strip().lower()
    if 'bin' in storage_method:
        st = 'Bins'
    elif 'hazmat' in storage_method:
        st = 'Hazmat'
    elif 'rack' in storage_method:
        st = 'Racking'
    elif 'pallet' in storage_method:
        st = 'Pallet'
    else:
        st = 'Bins'

    sku_info[sku] = {
        'volume': volume,
        'weight': parse_weight(row['Sell Pack Weight']),
        'storage_type': st
    }

# Peak demand
peak_demand = {sku: demand_df[sku].max() for sku in skus}

# Days on hand
days_on_hand = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        cols = [f'{fac} - Days on Hand', f'{fac} Days on Hand']
        for col in cols:
            if col in row.index:
                days_on_hand[(sku, fac)] = int(row[col])
                break

# Current capacity
current_capacity = {}
for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st = row['Shelving Type'].strip()
    if st == 'Pallets':
        st = 'Pallet'

    current_capacity[(fac, st)] = {
        'num_shelves': int(row['Number of Shelves']),
        'weight_cap_per_shelf': float(row['Weight Max / Shelf']),
        'total_weight_cap': float(row['Total Weight Capacity'])
    }

# Shelf volumes
shelf_volumes = {}
for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']
    dims_str = str(row['Dimensions (l,w,h)(ft)'])

    if dims_str != 'Auto':
        dims = tuple(float(d) for d in dims_str.split(' x '))
        shelf_volumes[(fac, st)] = dims[0] * dims[1] * dims[2]
    else:
        shelf_volumes[(fac, st)] = 1.728

# ============================================================================
# ANALYSIS BY STORAGE TYPE
# ============================================================================

print("\n" + "="*80)
print("CAPACITY ANALYSIS BY STORAGE TYPE")
print("="*80)

storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

for fac in facilities:
    print(f"\n{fac}:")
    print("-" * 60)

    for st in storage_types:
        # Get SKUs that use this storage type
        skus_for_st = [sku for sku in skus if sku_info[sku]['storage_type'] == st]

        if len(skus_for_st) == 0:
            continue

        # Calculate required storage
        total_req_volume = 0
        total_req_weight = 0

        for sku in skus_for_st:
            doh = days_on_hand.get((sku, fac), 7)
            req_units = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH) * SAFETY_STOCK_MULTIPLIER
            total_req_volume += req_units * sku_info[sku]['volume']
            total_req_weight += req_units * sku_info[sku]['weight']

        # Current capacity
        if (fac, st) in current_capacity:
            cap = current_capacity[(fac, st)]
            shelf_vol = shelf_volumes.get((fac, st), 0)

            available_volume = cap['num_shelves'] * shelf_vol
            available_weight = cap['total_weight_cap']

            vol_util = (total_req_volume / available_volume * 100) if available_volume > 0 else 999
            wt_util = (total_req_weight / available_weight * 100) if available_weight > 0 else 999

            print(f"\n  {st}:")
            print(f"    SKUs: {len(skus_for_st)}")
            print(f"    Required Volume: {total_req_volume:,.1f} cu ft")
            print(f"    Available Volume: {available_volume:,.1f} cu ft")
            print(f"    Volume Utilization: {vol_util:.1f}%")
            print(f"    Required Weight: {total_req_weight:,.1f} lbs")
            print(f"    Available Weight: {available_weight:,.1f} lbs")
            print(f"    Weight Utilization: {wt_util:.1f}%")

            if vol_util > 100:
                print(f"    ⚠️ VOLUME SHORTAGE: {total_req_volume - available_volume:,.1f} cu ft")
            if wt_util > 100:
                print(f"    ⚠️ WEIGHT SHORTAGE: {total_req_weight - available_weight:,.1f} lbs")

# ============================================================================
# OVERALL CAPACITY CHECK
# ============================================================================

print("\n\n" + "="*80)
print("OVERALL CAPACITY SUMMARY")
print("="*80)

for fac in facilities:
    print(f"\n{fac}:")

    total_req_vol = 0
    total_avail_vol = 0
    total_req_wt = 0
    total_avail_wt = 0

    for st in storage_types:
        skus_for_st = [sku for sku in skus if sku_info[sku]['storage_type'] == st]

        for sku in skus_for_st:
            doh = days_on_hand.get((sku, fac), 7)
            req_units = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH) * SAFETY_STOCK_MULTIPLIER
            total_req_vol += req_units * sku_info[sku]['volume']
            total_req_wt += req_units * sku_info[sku]['weight']

        if (fac, st) in current_capacity:
            cap = current_capacity[(fac, st)]
            shelf_vol = shelf_volumes.get((fac, st), 0)
            total_avail_vol += cap['num_shelves'] * shelf_vol
            total_avail_wt += cap['total_weight_cap']

    print(f"  Total Required Volume: {total_req_vol:,.1f} cu ft")
    print(f"  Total Available Volume: {total_avail_vol:,.1f} cu ft")
    print(f"  Volume Utilization: {(total_req_vol/total_avail_vol*100):.1f}%")
    print(f"  Total Required Weight: {total_req_wt:,.1f} lbs")
    print(f"  Total Available Weight: {total_avail_wt:,.1f} lbs")
    print(f"  Weight Utilization: {(total_req_wt/total_avail_wt*100):.1f}%")

    if total_req_vol > total_avail_vol:
        shortfall = total_req_vol - total_avail_vol
        print(f"  ⚠️ VOLUME SHORTFALL: {shortfall:,.1f} cu ft ({shortfall/total_avail_vol*100:.1f}% over capacity)")

    if total_req_wt > total_avail_wt:
        shortfall = total_req_wt - total_avail_wt
        print(f"  ⚠️ WEIGHT SHORTFALL: {shortfall:,.1f} lbs ({shortfall/total_avail_wt*100:.1f}% over capacity)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
