"""
InkCredible Supplies - Simplified Warehouse Expansion Optimization
Option 2: Expand Sacramento and/or Austin Facilities

SIMPLIFIED APPROACH:
1. Calculate peak storage requirements based on demand forecasts + days on hand
2. Optimize shelf allocation (set packing) to minimize expansion cost
3. Consider both volume and weight constraints for each storage type

This model avoids month-by-month inventory tracking to reduce complexity
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense
from pathlib import Path
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
RESULTS_DIR.mkdir(exist_ok=True)

WORKING_DAYS_PER_MONTH = 21
SAFETY_STOCK_MULTIPLIER = 1.2  # 20% safety stock

print("="*80)
print("INKREDIBLE SUPPLIES - WAREHOUSE EXPANSION OPTIMIZATION")
print("Simplified Model - Peak Storage Requirements")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1/5] Loading data...")

demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

print("   ✓ Data loaded")

# ============================================================================
# PROCESS DATA
# ============================================================================

print("\n[2/5] Processing data...")

# Extract SKUs
skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

print(f"   ✓ {len(skus)} SKUs, {len(facilities)} facilities")

# Parse SKU details
def parse_dimension(dim_str):
    parts = dim_str.strip().split(' x ')
    return tuple(float(p) / 12 for p in parts)

def parse_quantity(qty_str):
    return int(str(qty_str).split()[0])

def parse_weight(weight_str):
    return float(str(weight_str).split()[0])

sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]

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
        'volume': sell_volume,
        'weight': parse_weight(row['Sell Pack Weight']),
        'storage_type': storage_type
    }

# Calculate peak monthly demand for each SKU (max across all 120 months)
peak_demand = {}
for sku in skus:
    peak_demand[sku] = demand_df[sku].max()

print(f"   ✓ Peak demand calculated")

# Extract days on hand requirements
days_on_hand = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_cols = [f'{fac} - Days on Hand', f'{fac} Days on Hand']
        for col in doh_cols:
            if col in row.index:
                days_on_hand[(sku, fac)] = int(row[col])
                break

# Calculate required storage: peak_demand * (days_on_hand / working_days) * safety_factor
required_storage = {}
for sku in skus:
    for fac in facilities:
        doh = days_on_hand.get((sku, fac), 7)  # Default 7 days
        # Storage needed = peak monthly demand * (days on hand / days per month) * safety factor
        required_storage[(sku, fac)] = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH) * SAFETY_STOCK_MULTIPLIER

print(f"   ✓ Storage requirements calculated")

# Current shelving
current_shelves = {}
shelf_weight_cap = {}
shelf_volume_cap = {}
shelf_area = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st = row['Shelving Type'].strip()
    if st == 'Pallets':
        st = 'Pallet'

    current_shelves[(fac, st)] = int(row['Number of Shelves'])
    shelf_weight_cap[(fac, st)] = float(row['Weight Max / Shelf'])
    shelf_area[(fac, st)] = float(row['Area'])

# Shelf dimensions
for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']
    dims_str = str(row['Dimensions (l,w,h)(ft)'])

    if dims_str != 'Auto':
        dims = tuple(float(d) for d in dims_str.split(' x '))
        shelf_volume_cap[(fac, st)] = dims[0] * dims[1] * dims[2]
    else:
        shelf_volume_cap[(fac, st)] = 1.728  # 12x12x12 inches

# Average sqft per shelf
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves

print("   ✓ Current capacity processed")

# ============================================================================
# CREATE MODEL
# ============================================================================

print("\n[3/5] Building optimization model...")

m = Container()

# Sets
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
f_exp = Set(m, name="f_exp", domain=f, records=expandable)
st = Set(m, name="st", records=storage_types)

# Parameters
req_storage_records = [(sku, fac, required_storage.get((sku, fac), 0))
                       for sku in skus for fac in facilities]
req_storage_param = Parameter(m, name="req_storage", domain=[s, f],
                              records=req_storage_records)

sku_vol_records = [(sku, sku_data[sku]['volume']) for sku in skus]
sku_vol_param = Parameter(m, name="sku_volume", domain=s, records=sku_vol_records)

sku_wt_records = [(sku, sku_data[sku]['weight']) for sku in skus]
sku_wt_param = Parameter(m, name="sku_weight", domain=s, records=sku_wt_records)

sku_st_records = [(sku, sku_data[sku]['storage_type'], 1) for sku in skus]
sku_st_param = Parameter(m, name="sku_storage_type", domain=[s, st], records=sku_st_records)

curr_shelves_records = [(fac, stor, current_shelves.get((fac, stor), 0))
                        for fac in facilities for stor in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f, st], records=curr_shelves_records)

shelf_vol_records = [(fac, stor, shelf_volume_cap.get((fac, stor), 0))
                     for fac in facilities for stor in storage_types]
shelf_vol_param = Parameter(m, name="shelf_volume_cap", domain=[f, st], records=shelf_vol_records)

shelf_wt_records = [(fac, stor, shelf_weight_cap.get((fac, stor), 0))
                    for fac in facilities for stor in storage_types]
shelf_wt_param = Parameter(m, name="shelf_weight_cap", domain=[f, st], records=shelf_wt_records)

avg_sqft_records = [(fac, stor, avg_sqft_per_shelf.get((fac, stor), 50))
                    for fac in facilities for stor in storage_types]
avg_sqft_param = Parameter(m, name="avg_sqft", domain=[f, st], records=avg_sqft_records)

# Variables
expansion = Variable(m, name="expansion", domain=f_exp, type="positive")
sac_tier1 = Variable(m, name="sac_tier1", type="positive")
sac_tier2 = Variable(m, name="sac_tier2", type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")
storage_allocation = Variable(m, name="storage_alloc", domain=[s, f], type="positive")
total_cost = Variable(m, name="total_cost", type="free")

print("   ✓ Sets, parameters, and variables defined")

# ============================================================================
# CONSTRAINTS
# ============================================================================

print("\n[4/5] Defining constraints...")

# Objective
obj_eq = Equation(m, name="obj_eq")
obj_eq[...] = total_cost == sac_tier1 * 2.0 + sac_tier2 * 4.0 + expansion['Austin'] * 1.5

# Sacramento tiers
sac_t1 = Equation(m, name="sac_t1")
sac_t1[...] = sac_tier1 <= 100000

sac_t2 = Equation(m, name="sac_t2")
sac_t2[...] = sac_tier2 <= 150000

sac_tot = Equation(m, name="sac_tot")
sac_tot[...] = expansion['Sacramento'] == sac_tier1 + sac_tier2

# Max expansion
max_exp_sac = Equation(m, name="max_exp_sac")
max_exp_sac[...] = expansion['Sacramento'] <= 250000

max_exp_aus = Equation(m, name="max_exp_aus")
max_exp_aus[...] = expansion['Austin'] <= 200000

# Link expansion to shelves
exp_to_shelves = Equation(m, name="exp_to_shelves", domain=f_exp)
exp_to_shelves[f_exp] = expansion[f_exp] == Sum(st, add_shelves[f_exp, st] * avg_sqft_param[f_exp, st])

# Storage allocation must meet requirements
storage_req = Equation(m, name="storage_req", domain=[s, f])
storage_req[s, f] = storage_allocation[s, f] >= req_storage_param[s, f]

# Total demand must be allocated somewhere
total_allocation = Equation(m, name="total_allocation", domain=s)
total_allocation[s] = Sum(f, storage_allocation[s, f]) >= Sum(f, req_storage_param[s, f])

# Volume capacity constraints (expandable facilities)
vol_cap_exp = Equation(m, name="vol_cap_exp", domain=[f_exp, st])
vol_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st_param[s, st] > 0], storage_allocation[s, f_exp] * sku_vol_param[s]) <=
    (curr_shelves_param[f_exp, st] + add_shelves[f_exp, st]) * shelf_vol_param[f_exp, st]
)

# Weight capacity constraints (expandable facilities)
wt_cap_exp = Equation(m, name="wt_cap_exp", domain=[f_exp, st])
wt_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st_param[s, st] > 0], storage_allocation[s, f_exp] * sku_wt_param[s]) <=
    (curr_shelves_param[f_exp, st] + add_shelves[f_exp, st]) * shelf_wt_param[f_exp, st]
)

# Columbus fixed capacity (volume)
vol_cap_col = Equation(m, name="vol_cap_col", domain=st)
vol_cap_col[st] = (
    Sum(s.where[sku_st_param[s, st] > 0], storage_allocation[s, 'Columbus'] * sku_vol_param[s]) <=
    curr_shelves_param['Columbus', st] * shelf_vol_param['Columbus', st]
)

# Columbus fixed capacity (weight)
wt_cap_col = Equation(m, name="wt_cap_col", domain=st)
wt_cap_col[st] = (
    Sum(s.where[sku_st_param[s, st] > 0], storage_allocation[s, 'Columbus'] * sku_wt_param[s]) <=
    curr_shelves_param['Columbus', st] * shelf_wt_param['Columbus', st]
)

print("   ✓ Constraints defined")
print(f"   ✓ Total equations: {len(m.getEquations())}")

# ============================================================================
# SOLVE
# ============================================================================

print("\n[5/5] Solving model...")

warehouse_model = Model(
    m,
    name="warehouse_expansion",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

warehouse_model.solve()

# ============================================================================
# RESULTS
# ============================================================================

print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)

print(f"\nModel Status: {warehouse_model.status}")
print(f"Solve Status: {warehouse_model.solve_status}")

if warehouse_model.status.value in [1, 2, 7, 8]:  # Optimal or feasible solution
    obj_value = total_cost.toValue()
    print(f"\n{'TOTAL EXPANSION COST:':<40} ${obj_value:,.2f}")

    # Expansion
    print("\n" + "-"*80)
    print("EXPANSION DECISIONS")
    print("-"*80)

    sac_exp = expansion.records[expansion.records['f_exp'] == 'Sacramento']['level'].values[0]
    aus_exp = expansion.records[expansion.records['f_exp'] == 'Austin']['level'].values[0]

    print(f"\nSacramento: {sac_exp:,.0f} sq ft (Cost: ${sac_tier1.toValue() * 2 + sac_tier2.toValue() * 4:,.2f})")
    print(f"  - Tier 1: {sac_tier1.toValue():,.0f} sq ft @ $2/sqft")
    print(f"  - Tier 2: {sac_tier2.toValue():,.0f} sq ft @ $4/sqft")

    print(f"\nAustin: {aus_exp:,.0f} sq ft (Cost: ${aus_exp * 1.5:,.2f})")

    # Shelves
    print("\n" + "-"*80)
    print("ADDITIONAL SHELVING")
    print("-"*80)

    shelves_df = add_shelves.records[add_shelves.records['level'] > 0.5]
    if len(shelves_df) > 0:
        print("\n" + shelves_df.to_string(index=False))
    else:
        print("\nNo additional shelves needed")

    # Save results
    print("\n" + "-"*80)
    print("SAVING RESULTS")
    print("-"*80)

    exp_summary = pd.DataFrame({
        'Facility': ['Sacramento', 'Austin', 'TOTAL'],
        'Expansion_sqft': [sac_exp, aus_exp, sac_exp + aus_exp],
        'Cost_USD': [
            sac_tier1.toValue() * 2 + sac_tier2.toValue() * 4,
            aus_exp * 1.5,
            obj_value
        ]
    })
    exp_summary.to_csv(RESULTS_DIR / 'expansion_summary.csv', index=False)
    print("✓ Saved: expansion_summary.csv")

    if len(shelves_df) > 0:
        shelves_df.to_csv(RESULTS_DIR / 'additional_shelves.csv', index=False)
        print("✓ Saved: additional_shelves.csv")

    storage_allocation.records.to_csv(RESULTS_DIR / 'storage_allocation.csv', index=False)
    print("✓ Saved: storage_allocation.csv")

else:
    print("\n*** MODEL IS INFEASIBLE OR NO SOLUTION FOUND ***")
    print("This may indicate:")
    print("  - Current facilities cannot handle peak demand even with expansion")
    print("  - Constraints are too restrictive")
    print("  - Data inconsistencies")

print("\n" + "="*80)
print("COMPLETE!")
print("="*80 + "\n")
