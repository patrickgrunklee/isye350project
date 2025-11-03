"""
Feasibility Check Model - Identify exact capacity shortfalls

This model includes slack variables to identify WHERE and BY HOW MUCH
we are short on capacity. This will guide us on what storage types need expansion.
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
SAFETY_STOCK_MULTIPLIER = 1.0  # Start without safety stock

print("="*80)
print("FEASIBILITY CHECK - Identifying Capacity Shortfalls")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1/4] Loading data...")

demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

print(f"   ✓ Data loaded: {len(skus)} SKUs, {len(facilities)} facilities")

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

# Peak demand
peak_demand = {sku: demand_df[sku].max() for sku in skus}

# Average days on hand
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

# Total required storage
total_required_storage = {}
for sku in skus:
    doh = avg_days_on_hand[sku]
    total_required_storage[sku] = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH) * SAFETY_STOCK_MULTIPLIER

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

# Fix Hazmat volume
for fac in facilities:
    if shelf_volume_cap.get((fac, 'Hazmat'), 0) == 0:
        shelf_volume_cap[(fac, 'Hazmat')] = 27.0  # Use Racking size

# Average sqft per shelf
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves
    else:
        avg_sqft_per_shelf[(fac, st)] = 50.0

print("   ✓ Data processed")

# ============================================================================
# CREATE MODEL WITH SLACK VARIABLES
# ============================================================================

print("\n[2/4] Building feasibility check model...")

m = Container()

# Sets
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
f_exp = Set(m, name="f_exp", domain=f, records=expandable)
st = Set(m, name="st", records=storage_types)

# Parameters
total_req_param = Parameter(m, name="total_req", domain=s,
                            records=[(sku, total_required_storage[sku]) for sku in skus])

sku_vol = Parameter(m, name="sku_vol", domain=s,
                    records=[(sku, sku_data[sku]['volume']) for sku in skus])

sku_wt = Parameter(m, name="sku_wt", domain=s,
                   records=[(sku, sku_data[sku]['weight']) for sku in skus])

sku_st = Parameter(m, name="sku_st", domain=[s, st],
                   records=[(sku, sku_data[sku]['storage_type'], 1) for sku in skus])

curr_shelves = Parameter(m, name="curr_shelves", domain=[f, st],
                        records=[(fac, stor, current_shelves.get((fac, stor), 0))
                                for fac in facilities for stor in storage_types])

shelf_vol = Parameter(m, name="shelf_vol", domain=[f, st],
                      records=[(fac, stor, shelf_volume_cap.get((fac, stor), 0))
                              for fac in facilities for stor in storage_types])

shelf_wt = Parameter(m, name="shelf_wt", domain=[f, st],
                     records=[(fac, stor, shelf_weight_cap.get((fac, stor), 0))
                             for fac in facilities for stor in storage_types])

avg_sqft = Parameter(m, name="avg_sqft", domain=[f, st],
                     records=[(fac, stor, avg_sqft_per_shelf.get((fac, stor), 50))
                             for fac in facilities for stor in storage_types])

# Penalty for slack (high value to minimize slack)
BIG_PENALTY = 1000000

# Variables
expansion = Variable(m, name="expansion", domain=f_exp, type="positive")
sac_t1 = Variable(m, name="sac_t1", type="positive")
sac_t2 = Variable(m, name="sac_t2", type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")
storage_alloc = Variable(m, name="storage_alloc", domain=[s, f], type="positive")

# SLACK VARIABLES - to identify shortfalls
vol_slack = Variable(m, name="vol_slack", domain=[f, st], type="positive",
                    description="Volume capacity slack (shortfall)")
wt_slack = Variable(m, name="wt_slack", domain=[f, st], type="positive",
                   description="Weight capacity slack (shortfall)")

total_cost = Variable(m, name="total_cost", type="free")

print("   ✓ Model structure defined")

# ============================================================================
# CONSTRAINTS
# ============================================================================

print("\n[3/4] Defining constraints...")

# Objective: minimize expansion cost + heavily penalize slack
obj = Equation(m, name="obj")
obj[...] = total_cost == (
    sac_t1 * 2.0 + sac_t2 * 4.0 + expansion['Austin'] * 1.5 +
    BIG_PENALTY * (Sum([f, st], vol_slack[f, st] + wt_slack[f, st]))
)

# Sacramento tiers
sac_t1_max = Equation(m, name="sac_t1_max")
sac_t1_max[...] = sac_t1 <= 100000

sac_t2_max = Equation(m, name="sac_t2_max")
sac_t2_max[...] = sac_t2 <= 150000

sac_tot = Equation(m, name="sac_tot")
sac_tot[...] = expansion['Sacramento'] == sac_t1 + sac_t2

# Max expansion (allow generous limits)
max_exp_sac = Equation(m, name="max_exp_sac")
max_exp_sac[...] = expansion['Sacramento'] <= 500000  # Generous limit

max_exp_aus = Equation(m, name="max_exp_aus")
max_exp_aus[...] = expansion['Austin'] <= 500000  # Generous limit

# Link expansion to shelves
exp_shelves = Equation(m, name="exp_shelves", domain=f_exp)
exp_shelves[f_exp] = expansion[f_exp] == Sum(st, add_shelves[f_exp, st] * avg_sqft[f_exp, st])

# Total storage must meet requirements
total_req_eq = Equation(m, name="total_req_eq", domain=s)
total_req_eq[s] = Sum(f, storage_alloc[s, f]) >= total_req_param[s]

# Volume capacity with slack - expandable
vol_cap_exp = Equation(m, name="vol_cap_exp", domain=[f_exp, st])
vol_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, f_exp] * sku_vol[s]) <=
    (curr_shelves[f_exp, st] + add_shelves[f_exp, st]) * shelf_vol[f_exp, st] + vol_slack[f_exp, st]
)

# Weight capacity with slack - expandable
wt_cap_exp = Equation(m, name="wt_cap_exp", domain=[f_exp, st])
wt_cap_exp[f_exp, st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, f_exp] * sku_wt[s]) <=
    (curr_shelves[f_exp, st] + add_shelves[f_exp, st]) * shelf_wt[f_exp, st] + wt_slack[f_exp, st]
)

# Volume capacity with slack - Columbus
vol_cap_col = Equation(m, name="vol_cap_col", domain=st)
vol_cap_col[st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, 'Columbus'] * sku_vol[s]) <=
    curr_shelves['Columbus', st] * shelf_vol['Columbus', st] + vol_slack['Columbus', st]
)

# Weight capacity with slack - Columbus
wt_cap_col = Equation(m, name="wt_cap_col", domain=st)
wt_cap_col[st] = (
    Sum(s.where[sku_st[s, st] > 0], storage_alloc[s, 'Columbus'] * sku_wt[s]) <=
    curr_shelves['Columbus', st] * shelf_wt['Columbus', st] + wt_slack['Columbus', st]
)

print("   ✓ Constraints defined")

# ============================================================================
# SOLVE
# ============================================================================

print("\n[4/4] Solving model...")

warehouse_model = Model(
    m,
    name="feasibility_check",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

warehouse_model.solve()

# ============================================================================
# ANALYZE RESULTS
# ============================================================================

print("\n" + "="*80)
print("FEASIBILITY CHECK RESULTS")
print("="*80)

print(f"\nModel Status: {warehouse_model.status}")

if warehouse_model.status.value in [1, 2, 7, 8]:
    print("\n" + "-"*80)
    print("CAPACITY SHORTFALLS IDENTIFIED")
    print("-"*80)

    # Volume slack
    vol_slack_df = vol_slack.records[vol_slack.records['level'] > 0.1].copy()
    if len(vol_slack_df) > 0:
        print("\nVOLUME SHORTFALLS:")
        vol_slack_df['level'] = vol_slack_df['level'].round(1)
        vol_slack_df = vol_slack_df.rename(columns={'f': 'Facility', 'st': 'Storage Type', 'level': 'Shortfall (cu ft)'})
        print("\n" + vol_slack_df[['Facility', 'Storage Type', 'Shortfall (cu ft)']].to_string(index=False))

        # Calculate additional shelves needed
        print("\nADDITIONAL SHELVES NEEDED TO COVER VOLUME SHORTFALL:")
        for _, row in vol_slack_df.iterrows():
            fac = row['Facility']
            st = row['Storage Type']
            shortfall = row['Shortfall (cu ft)']
            shelf_vol_cap = shelf_volume_cap.get((fac, st), 0)
            if shelf_vol_cap > 0:
                shelves_needed = np.ceil(shortfall / shelf_vol_cap)
                sqft_needed = shelves_needed * avg_sqft_per_shelf.get((fac, st), 50)
                print(f"  {fac} - {st}: {int(shelves_needed)} shelves ({sqft_needed:,.0f} sq ft)")
    else:
        print("\n✓ NO VOLUME SHORTFALLS")

    # Weight slack
    wt_slack_df = wt_slack.records[wt_slack.records['level'] > 0.1].copy()
    if len(wt_slack_df) > 0:
        print("\n\nWEIGHT SHORTFALLS:")
        wt_slack_df['level'] = wt_slack_df['level'].round(1)
        wt_slack_df = wt_slack_df.rename(columns={'f': 'Facility', 'st': 'Storage Type', 'level': 'Shortfall (lbs)'})
        print("\n" + wt_slack_df[['Facility', 'Storage Type', 'Shortfall (lbs)']].to_string(index=False))

        # Calculate additional shelves needed
        print("\nADDITIONAL SHELVES NEEDED TO COVER WEIGHT SHORTFALL:")
        for _, row in wt_slack_df.iterrows():
            fac = row['Facility']
            st = row['Storage Type']
            shortfall = row['Shortfall (lbs)']
            shelf_wt_cap = shelf_weight_cap.get((fac, st), 0)
            if shelf_wt_cap > 0:
                shelves_needed = np.ceil(shortfall / shelf_wt_cap)
                sqft_needed = shelves_needed * avg_sqft_per_shelf.get((fac, st), 50)
                print(f"  {fac} - {st}: {int(shelves_needed)} shelves ({sqft_needed:,.0f} sq ft)")
    else:
        print("\n✓ NO WEIGHT SHORTFALLS")

    # Expansion solution
    print("\n" + "-"*80)
    print("PROPOSED EXPANSION (within model limits)")
    print("-"*80)

    sac_exp = expansion.records[expansion.records['f_exp'] == 'Sacramento']['level'].values[0]
    aus_exp = expansion.records[expansion.records['f_exp'] == 'Austin']['level'].values[0]

    print(f"\nSacramento: {sac_exp:,.0f} sq ft")
    print(f"Austin: {aus_exp:,.0f} sq ft")
    print(f"Total: {sac_exp + aus_exp:,.0f} sq ft")

    # Save results
    print("\n" + "-"*80)
    print("SAVING RESULTS")
    print("-"*80)

    if len(vol_slack_df) > 0:
        vol_slack_df.to_csv(RESULTS_DIR / 'volume_shortfalls.csv', index=False)
        print("\n✓ Saved: volume_shortfalls.csv")

    if len(wt_slack_df) > 0:
        wt_slack_df.to_csv(RESULTS_DIR / 'weight_shortfalls.csv', index=False)
        print("✓ Saved: weight_shortfalls.csv")

else:
    print("\n*** MODEL COULD NOT FIND SOLUTION ***")

print("\n" + "="*80)
print("FEASIBILITY CHECK COMPLETE!")
print("="*80 + "\n")
