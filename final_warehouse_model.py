"""
InkCredible Supplies - Final Warehouse Expansion Optimization
Option 2: Expand Sacramento and/or Austin Facilities

KEY INSIGHTS FROM DIAGNOSTIC:
- Columbus has sufficient capacity (96% utilization)
- Sacramento and Austin are massively over capacity
- Pallet storage is the main bottleneck
- Model allows flexible allocation across facilities to meet TOTAL demand

APPROACH:
1. Each facility doesn't need to meet its own demand - they can share
2. Total storage across all facilities must meet peak requirements
3. Expansion only at Sacramento and Austin
4. Minimize total expansion cost
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
RESULTS_DIR.mkdir(exist_ok=True)

WORKING_DAYS_PER_MONTH = 21
SAFETY_STOCK_MULTIPLIER = 1.0  # No safety stock for now to test feasibility
MAX_EXPANSION_MULTIPLIER = 2.0  # Allow more expansion if needed

print("="*80)
print("INKREDIBLE SUPPLIES - WAREHOUSE EXPANSION OPTIMIZATION")
print("Final Model - Flexible Allocation Across Facilities")
print("="*80)

# ============================================================================
# LOAD & PROCESS DATA
# ============================================================================

print("\n[1/5] Loading and processing data...")

demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

print(f"   ✓ {len(skus)} SKUs, {len(facilities)} facilities")

# Parse SKU details
def parse_dimension(dim_str):
    parts = dim_str.strip().split(' x ')
    return tuple(float(p) / 12 for p in parts)

def parse_weight(weight_str):
    return float(str(weight_str).split()[0])

sku_data = {}
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

    sku_data[sku] = {
        'volume': volume,
        'weight': parse_weight(row['Sell Pack Weight']),
        'storage_type': st
    }

# Peak demand (max monthly demand across all 120 months)
peak_demand = {sku: demand_df[sku].max() for sku in skus}

# Days on hand - use AVERAGE across facilities to calculate minimum storage needed
avg_days_on_hand = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    doh_values = []
    for fac in facilities:
        cols = [f'{fac} - Days on Hand', f'{fac} Days on Hand']
        for col in cols:
            if col in row.index:
                doh_values.append(int(row[col]))
                break
    avg_days_on_hand[sku] = np.mean(doh_values) if doh_values else 10

# Calculate TOTAL required storage across all facilities
total_required_storage = {}
for sku in skus:
    doh = avg_days_on_hand[sku]
    # Total storage = peak monthly demand * (days on hand / days per month) * safety factor
    total_required_storage[sku] = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH) * SAFETY_STOCK_MULTIPLIER

print(f"   ✓ Storage requirements calculated")

# Current capacity
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

# Shelf volumes
for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']
    dims_str = str(row['Dimensions (l,w,h)(ft)'])

    if dims_str != 'Auto':
        dims = tuple(float(d) for d in dims_str.split(' x '))
        shelf_volume_cap[(fac, st)] = dims[0] * dims[1] * dims[2]
    else:
        shelf_volume_cap[(fac, st)] = 1.728

# Fix Hazmat volume (currently shows 0, use Racking dimensions as proxy)
for fac in facilities:
    if shelf_volume_cap.get((fac, 'Hazmat'), 0) == 0:
        shelf_volume_cap[(fac, 'Hazmat')] = shelf_volume_cap.get((fac, 'Racking'), 27.0)

# Average sqft per shelf
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves
    else:
        avg_sqft_per_shelf[(fac, st)] = 50.0  # Default 50 sqft per shelf

print("   ✓ Current capacity data processed")

# ============================================================================
# CREATE GAMSPY MODEL
# ============================================================================

print("\n[2/5] Building optimization model...")

m = Container()

# Sets
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
f_exp = Set(m, name="f_exp", domain=f, records=expandable)
st = Set(m, name="st", records=storage_types)

# Parameters
total_req_storage_records = [(sku, total_required_storage[sku]) for sku in skus]
total_req_param = Parameter(m, name="total_req_storage", domain=s, records=total_req_storage_records)

sku_vol_records = [(sku, sku_data[sku]['volume']) for sku in skus]
sku_vol = Parameter(m, name="sku_volume", domain=s, records=sku_vol_records)

sku_wt_records = [(sku, sku_data[sku]['weight']) for sku in skus]
sku_wt = Parameter(m, name="sku_weight", domain=s, records=sku_wt_records)

sku_st_records = [(sku, sku_data[sku]['storage_type'], 1) for sku in skus]
sku_st = Parameter(m, name="sku_storage_type", domain=[s, st], records=sku_st_records)

curr_shelves_records = [(fac, stor, current_shelves.get((fac, stor), 0))
                        for fac in facilities for stor in storage_types]
curr_shelves = Parameter(m, name="curr_shelves", domain=[f, st], records=curr_shelves_records)

shelf_vol_records = [(fac, stor, shelf_volume_cap.get((fac, stor), 0))
                     for fac in facilities for stor in storage_types]
shelf_vol = Parameter(m, name="shelf_volume", domain=[f, st], records=shelf_vol_records)

shelf_wt_records = [(fac, stor, shelf_weight_cap.get((fac, stor), 0))
                    for fac in facilities for stor in storage_types]
shelf_wt = Parameter(m, name="shelf_weight", domain=[f, st], records=shelf_wt_records)

avg_sqft_records = [(fac, stor, avg_sqft_per_shelf.get((fac, stor), 50))
                    for fac in facilities for stor in storage_types]
avg_sqft = Parameter(m, name="avg_sqft", domain=[f, st], records=avg_sqft_records)

# Variables
expansion = Variable(m, name="expansion", domain=f_exp, type="positive")
sac_t1 = Variable(m, name="sac_tier1", type="positive")
sac_t2 = Variable(m, name="sac_tier2", type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")

# Storage allocation: how many units of each SKU stored at each facility
storage_alloc = Variable(m, name="storage_alloc", domain=[s, f], type="positive")

total_cost = Variable(m, name="total_cost", type="free")

print("   ✓ Sets, parameters, and variables defined")

# ============================================================================
# CONSTRAINTS
# ============================================================================

print("\n[3/5] Defining constraints...")

# Objective: minimize expansion cost
obj = Equation(m, name="obj")
obj[...] = total_cost == sac_t1 * 2.0 + sac_t2 * 4.0 + expansion['Austin'] * 1.5

# Sacramento expansion tiers
sac_tier1_max = Equation(m, name="sac_tier1_max")
sac_tier1_max[...] = sac_t1 <= 100000

sac_tier2_max = Equation(m, name="sac_tier2_max")
sac_tier2_max[...] = sac_t2 <= 150000

sac_total = Equation(m, name="sac_total")
sac_total[...] = expansion['Sacramento'] == sac_t1 + sac_t2

# Max expansion limits (allow more if needed)
max_exp_sac = Equation(m, name="max_exp_sac")
max_exp_sac[...] = expansion['Sacramento'] <= 250000 * MAX_EXPANSION_MULTIPLIER

max_exp_aus = Equation(m, name="max_exp_aus")
max_exp_aus[...] = expansion['Austin'] <= 200000 * MAX_EXPANSION_MULTIPLIER

# Link expansion to shelves
exp_shelves = Equation(m, name="exp_shelves", domain=f_exp)
exp_shelves[f_exp] = expansion[f_exp] == Sum(st, add_shelves[f_exp, st] * avg_sqft[f_exp, st])

# TOTAL storage allocation across ALL facilities must meet total requirements
total_storage_req = Equation(m, name="total_storage_req", domain=s)
total_storage_req[s] = Sum(f, storage_alloc[s, f]) >= total_req_param[s]

# Volume capacity - expandable facilities
vol_cap_exp = Equation(m, name="vol_cap_exp", domain=[f_exp, st])
vol_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, f_exp] * sku_vol[s]) <=
    (curr_shelves[f_exp, st] + add_shelves[f_exp, st]) * shelf_vol[f_exp, st]
)

# Weight capacity - expandable facilities
wt_cap_exp = Equation(m, name="wt_cap_exp", domain=[f_exp, st])
wt_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, f_exp] * sku_wt[s]) <=
    (curr_shelves[f_exp, st] + add_shelves[f_exp, st]) * shelf_wt[f_exp, st]
)

# Volume capacity - Columbus (fixed)
vol_cap_col = Equation(m, name="vol_cap_col", domain=st)
vol_cap_col[st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, 'Columbus'] * sku_vol[s]) <=
    curr_shelves['Columbus', st] * shelf_vol['Columbus', st]
)

# Weight capacity - Columbus (fixed)
wt_cap_col = Equation(m, name="wt_cap_col", domain=st)
wt_cap_col[st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, 'Columbus'] * sku_wt[s]) <=
    curr_shelves['Columbus', st] * shelf_wt['Columbus', st]
)

print("   ✓ Constraints defined")
print(f"   ✓ Total equations: {len(m.getEquations())}")

# ============================================================================
# SOLVE MODEL
# ============================================================================

print("\n[4/5] Solving optimization model...")
print("   (This may take a minute...)")

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
# DISPLAY RESULTS
# ============================================================================

print("\n[5/5] Processing results...")
print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)

print(f"\nModel Status: {warehouse_model.status}")
print(f"Solve Status: {warehouse_model.solve_status}")

if warehouse_model.status.value in [1, 2, 7, 8]:  # Optimal or feasible
    obj_value = total_cost.toValue()

    print(f"\n{'='*80}")
    print(f"TOTAL EXPANSION COST: ${obj_value:,.2f}")
    print(f"{'='*80}")

    # Expansion details
    print("\n" + "-"*80)
    print("EXPANSION DECISIONS")
    print("-"*80)

    sac_exp = expansion.records[expansion.records['f_exp'] == 'Sacramento']['level'].values[0]
    aus_exp = expansion.records[expansion.records['f_exp'] == 'Austin']['level'].values[0]
    sac_t1_val = sac_t1.toValue()
    sac_t2_val = sac_t2.toValue()

    print(f"\n✓ Sacramento Expansion: {sac_exp:,.0f} sq ft")
    print(f"  - Tier 1 (0-100K @ $2/sqft): {sac_t1_val:,.0f} sq ft → ${sac_t1_val * 2:,.2f}")
    print(f"  - Tier 2 (100K-250K @ $4/sqft): {sac_t2_val:,.0f} sq ft → ${sac_t2_val * 4:,.2f}")
    print(f"  - Subtotal: ${(sac_t1_val * 2 + sac_t2_val * 4):,.2f}")

    print(f"\n✓ Austin Expansion: {aus_exp:,.0f} sq ft")
    print(f"  - Cost @ $1.5/sqft: ${aus_exp * 1.5:,.2f}")

    # Additional shelves
    print("\n" + "-"*80)
    print("ADDITIONAL SHELVING REQUIRED")
    print("-"*80 + "\n")

    shelves_df = add_shelves.records[add_shelves.records['level'] > 0.5].copy()
    if len(shelves_df) > 0:
        shelves_df['level'] = shelves_df['level'].round(0).astype(int)
        shelves_df = shelves_df.rename(columns={'f_exp': 'Facility', 'st': 'Type', 'level': 'Additional Shelves'})
        print(shelves_df[['Facility', 'Type', 'Additional Shelves']].to_string(index=False))
    else:
        print("No additional shelves needed")

    # Storage allocation summary
    print("\n" + "-"*80)
    print("STORAGE ALLOCATION BY FACILITY")
    print("-"*80)

    for fac in facilities:
        fac_alloc = storage_alloc.records[storage_alloc.records['f'] == fac]
        total_units = fac_alloc['level'].sum()
        total_vol = sum(fac_alloc.apply(lambda row: row['level'] * sku_data[row['s']]['volume'], axis=1))
        total_wt = sum(fac_alloc.apply(lambda row: row['level'] * sku_data[row['s']]['weight'], axis=1))

        print(f"\n{fac}:")
        print(f"  Total Units Stored: {total_units:,.0f}")
        print(f"  Total Volume: {total_vol:,.1f} cu ft")
        print(f"  Total Weight: {total_wt:,.1f} lbs")

    # Save results
    print("\n" + "-"*80)
    print("SAVING RESULTS")
    print("-"*80 + "\n")

    # Expansion summary
    exp_summary = pd.DataFrame({
        'Facility': ['Sacramento', 'Austin', 'TOTAL'],
        'Expansion_sqft': [sac_exp, aus_exp, sac_exp + aus_exp],
        'Cost_USD': [
            sac_t1_val * 2 + sac_t2_val * 4,
            aus_exp * 1.5,
            obj_value
        ]
    })
    exp_summary.to_csv(RESULTS_DIR / 'expansion_summary.csv', index=False)
    print("✓ Saved: expansion_summary.csv")

    # Shelving details
    if len(shelves_df) > 0:
        shelves_df.to_csv(RESULTS_DIR / 'additional_shelves.csv', index=False)
        print("✓ Saved: additional_shelves.csv")

    # Storage allocation
    storage_alloc.records.to_csv(RESULTS_DIR / 'storage_allocation_full.csv', index=False)
    print("✓ Saved: storage_allocation_full.csv")

    print(f"\nAll results saved to: {RESULTS_DIR}")

else:
    print("\n*** MODEL IS INFEASIBLE OR NO SOLUTION FOUND ***")
    print("\nPossible reasons:")
    print("  - Expansion limits are insufficient for demand growth")
    print("  - Weight/volume constraints are too restrictive")
    print("  - Consider increasing max expansion or reducing safety stock")

print("\n" + "="*80)
print("OPTIMIZATION COMPLETE!")
print("="*80 + "\n")
