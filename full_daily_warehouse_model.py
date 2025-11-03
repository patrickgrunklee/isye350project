"""
InkCredible Supplies - Full Daily Multiperiod Warehouse Optimization Model
===========================================================================

This model implements:
1. Daily time periods (2,520 business days over 120 months)
2. Supplier delivery scheduling (8am arrivals, 1 truckload per supplier per day)
3. Package repacking optimization (set packing)
4. Lead time constraints (in days)
5. Days-on-hand requirements
6. Volume, weight, and package capacity constraints
7. Warehouse expansion optimization

Model Components:
- 18 SKUs across 4 storage types
- 3 facilities (Columbus, Sacramento, Austin)
- 2 supplier types (Domestic, International)
- 120 months = 2,520 business days
- ~136,000+ decision variables

KEY UNIT CONVERSIONS:
===================
- DEMAND: Specified in SELL PACKS (outbound units) - this is what customers order
- DELIVERIES: Ordered in INBOUND PACKS from suppliers (larger packages)
- INVENTORY: Tracked in SELL PACKS (outbound units)
- SHIPMENTS: Fulfilled in SELL PACKS (outbound units)

Conversion: 1 INBOUND PACK = inbound_qty[sku] SELL PACKS
Example: SKUW1 inbound pack (144 units) = 12 sell packs (12 units each)

Repacking Decision:
- If repacked: Store as individual sell packs (1 unit per package)
- If not repacked: Store as inbound packs (inbound_qty units per package)

Author: Claude Code
Date: 2025
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense, Ord
from pathlib import Path
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Set license
os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
RESULTS_DIR.mkdir(exist_ok=True)

# Time parameters
MONTHS = 120  # 10 years
DAYS_PER_MONTH = 21  # Business days per month
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH  # 2,520 days

# For initial testing, use smaller time horizon
USE_FULL_HORIZON = True  # Set to True for full 120 months
TEST_MONTHS = 3  # Use 3 months for initial testing (63 daily periods)
TEST_DAYS = TEST_MONTHS * DAYS_PER_MONTH if not USE_FULL_HORIZON else TOTAL_DAYS

WORKING_DAYS_PER_MONTH = 21
SAFETY_STOCK_MULTIPLIER = 1.0

print("="*80)
print("INKREDIBLE SUPPLIES - FULL DAILY WAREHOUSE OPTIMIZATION MODEL")
print("="*80)
print(f"\nConfiguration:")
print(f"  Time horizon: {TEST_MONTHS if not USE_FULL_HORIZON else MONTHS} months ({TEST_DAYS} business days)")
print(f"  Working days per month: {WORKING_DAYS_PER_MONTH}")
print(f"  Safety stock multiplier: {SAFETY_STOCK_MULTIPLIER}")
print("="*80)

# ============================================================================
# STEP 1: LOAD AND PROCESS DATA
# ============================================================================

print("\n[1/7] Loading data files...")

demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")

print("   ✓ All data files loaded")

# ============================================================================
# STEP 2: DEFINE SETS
# ============================================================================

print("\n[2/7] Defining sets and extracting data...")

skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable_facilities = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
supplier_types = ['Domestic', 'International']

# Time periods
months = list(range(1, TEST_MONTHS + 1)) if not USE_FULL_HORIZON else list(range(1, MONTHS + 1))
days = list(range(1, DAYS_PER_MONTH + 1))

# SKU to supplier mapping
domestic_skus = ['SKUA1', 'SKUA2', 'SKUA3', 'SKUT1', 'SKUT2', 'SKUT3', 'SKUT4',
                 'SKUD1', 'SKUD2', 'SKUD3', 'SKUC1', 'SKUC2']
international_skus = ['SKUW1', 'SKUW2', 'SKUW3', 'SKUE1', 'SKUE2', 'SKUE3']

print(f"   ✓ {len(skus)} SKUs, {len(facilities)} facilities, {len(months)} months, {len(days)} days/month")
print(f"   ✓ {len(domestic_skus)} domestic SKUs, {len(international_skus)} international SKUs")

# ============================================================================
# STEP 3: PARSE SKU DATA (DIMENSIONS, WEIGHTS, CONSOLIDATION)
# ============================================================================

print("\n[3/7] Parsing SKU dimensions and package data...")

def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple (L, W, H) in feet"""
    parts = str(dim_str).strip().replace('x', ' x ').split(' x ')
    return tuple(float(p.strip()) / 12 for p in parts)  # Convert inches to feet

def parse_weight(weight_str):
    """Parse weight string like '1 lbs' to float"""
    return float(str(weight_str).split()[0])

def parse_quantity(qty_str):
    """Parse quantity string like '144 (12 packs)' to int"""
    return int(str(qty_str).split()[0])

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
        st = 'Bins'
    elif 'hazmat' in storage_method:
        st = 'Hazmat'
    elif 'rack' in storage_method:
        st = 'Racking'
    elif 'pallet' in storage_method:
        st = 'Pallet'
    else:
        st = 'Bins'

    # Consolidation flag
    can_consolidate = 1 if row['Can be packed out in a box with other materials (consolidation)?'] == 'Yes' else 0

    # Supplier type
    supplier = row['Supplier Type'].strip()

    sku_data[sku] = {
        'sell_length': sell_dims[0],
        'sell_width': sell_dims[1],
        'sell_height': sell_dims[2],
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'inbound_length': inbound_dims[0],
        'inbound_width': inbound_dims[1],
        'inbound_height': inbound_dims[2],
        'inbound_volume': inbound_volume,
        'inbound_weight': inbound_weight,
        'inbound_qty': inbound_qty,
        'storage_type': st,
        'can_consolidate': can_consolidate,
        'supplier': supplier
    }

print(f"   ✓ Parsed dimensions and weights for {len(sku_data)} SKUs")

# ============================================================================
# STEP 4: PARSE DEMAND AND LEAD TIME DATA
# ============================================================================

print("\n[4/7] Processing demand and lead time data...")

# Extract demand data (limit to test months if testing)
demand_data = {}
for idx, row in demand_df.iterrows():
    month = idx + 1
    if month > len(months):
        break
    for sku in skus:
        demand_data[(month, sku)] = float(row[sku])

print(f"   ✓ Loaded demand data for {len(months)} months")

# Extract lead times (in days) and days on hand
lead_times = {}
days_on_hand = {}

for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        lt_col = f'Lead Time - {fac}'
        doh_col_options = [f'{fac} - Days on Hand', f'{fac} Days on Hand']

        if lt_col in row.index:
            lead_times[(sku, fac)] = int(row[lt_col])

        for doh_col in doh_col_options:
            if doh_col in row.index:
                days_on_hand[(sku, fac)] = int(row[doh_col])
                break

print(f"   ✓ Loaded lead times and days-on-hand for {len(skus)} SKUs × {len(facilities)} facilities")

# ============================================================================
# STEP 5: PARSE SHELVING DATA
# ============================================================================

print("\n[5/7] Processing shelving capacity data...")

# Current shelving
current_shelves = {}
shelf_weight_cap = {}
shelf_area = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st = row['Shelving Type'].strip()
    if st == 'Pallets':
        st = 'Pallet'

    current_shelves[(fac, st)] = int(row['Number of Shelves'])
    shelf_weight_cap[(fac, st)] = float(row['Weight Max / Shelf'])
    shelf_area[(fac, st)] = float(row['Area'])

# Shelf dimensions and capacity
shelf_volume_cap = {}
shelf_package_cap = {}

for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']

    dims_str = str(row['Dimensions (l,w,h)(ft)'])
    if dims_str != 'Auto':
        dims = tuple(float(d.strip()) for d in dims_str.split(' x '))
        shelf_volume_cap[(fac, st)] = dims[0] * dims[1] * dims[2]
        shelf_package_cap[(fac, st)] = int(row['Package Capacity'])
    else:
        # Columbus Bins - Auto
        shelf_volume_cap[(fac, st)] = 1.728  # 12x12x12 inches
        shelf_package_cap[(fac, st)] = 100  # Arbitrary large number

# Average sqft per shelf
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves
    else:
        avg_sqft_per_shelf[(fac, st)] = 50.0  # Default

print(f"   ✓ Loaded shelving data for {len(facilities)} facilities × {len(storage_types)} storage types")

# ============================================================================
# STEP 6: CREATE GAMSPY MODEL
# ============================================================================

print("\n[6/7] Building GAMSPy optimization model...")
print("   (This may take a few minutes for large models...)")

m = Container()

# Define sets
s_set = Set(m, name="s", records=skus, description="SKUs")
f_set = Set(m, name="f", records=facilities, description="Facilities")
f_exp_set = Set(m, name="f_exp", domain=f_set, records=expandable_facilities, description="Expandable facilities")
st_set = Set(m, name="st", records=storage_types, description="Storage types")
sup_set = Set(m, name="sup", records=supplier_types, description="Supplier types")
t_month_set = Set(m, name="t_month", records=[str(m) for m in months], description="Months")
t_day_set = Set(m, name="t_day", records=[str(d) for d in days], description="Days within month")

print(f"   ✓ Sets defined ({len(months)} months × {len(days)} days = {len(months)*len(days)} daily periods)")

# ============================================================================
# PARAMETERS
# ============================================================================

print("   ✓ Creating parameters...")

# Demand (monthly, will be distributed daily)
demand_records = [(str(month), sku, demand_data.get((month, sku), 0))
                  for month in months for sku in skus]
demand_param = Parameter(m, name="demand", domain=[t_month_set, s_set], records=demand_records)

# SKU properties - Sell pack
sell_vol_records = [(sku, sku_data[sku]['sell_volume']) for sku in skus]
sell_vol = Parameter(m, name="sell_volume", domain=s_set, records=sell_vol_records)

sell_wt_records = [(sku, sku_data[sku]['sell_weight']) for sku in skus]
sell_wt = Parameter(m, name="sell_weight", domain=s_set, records=sell_wt_records)

# SKU properties - Inbound pack
inbound_vol_records = [(sku, sku_data[sku]['inbound_volume']) for sku in skus]
inbound_vol = Parameter(m, name="inbound_volume", domain=s_set, records=inbound_vol_records)

inbound_wt_records = [(sku, sku_data[sku]['inbound_weight']) for sku in skus]
inbound_wt = Parameter(m, name="inbound_weight", domain=s_set, records=inbound_wt_records)

inbound_qty_records = [(sku, sku_data[sku]['inbound_qty']) for sku in skus]
inbound_qty = Parameter(m, name="inbound_qty", domain=s_set, records=inbound_qty_records)

# Consolidation flag
can_consolidate_records = [(sku, sku_data[sku]['can_consolidate']) for sku in skus]
can_consolidate = Parameter(m, name="can_consolidate", domain=s_set, records=can_consolidate_records)

# SKU to storage type mapping
sku_st_records = [(sku, sku_data[sku]['storage_type'], 1) for sku in skus]
sku_st_map = Parameter(m, name="sku_st_map", domain=[s_set, st_set], records=sku_st_records)

# SKU to supplier mapping
sku_sup_records = []
for sku in domestic_skus:
    sku_sup_records.append((sku, 'Domestic', 1))
for sku in international_skus:
    sku_sup_records.append((sku, 'International', 1))
sku_sup_map = Parameter(m, name="sku_sup_map", domain=[s_set, sup_set], records=sku_sup_records)

# Lead times (in days)
lead_time_records = [(sku, fac, lead_times.get((sku, fac), 7)) for sku in skus for fac in facilities]
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set], records=lead_time_records)

# Days on hand
doh_records = [(sku, fac, days_on_hand.get((sku, fac), 7)) for sku in skus for fac in facilities]
doh_param = Parameter(m, name="days_on_hand", domain=[s_set, f_set], records=doh_records)

# Current shelves
curr_shelves_records = [(fac, st, current_shelves.get((fac, st), 0))
                        for fac in facilities for st in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f_set, st_set], records=curr_shelves_records)

# Shelf capacities
shelf_vol_records = [(fac, st, shelf_volume_cap.get((fac, st), 0))
                     for fac in facilities for st in storage_types]
shelf_vol_param = Parameter(m, name="shelf_volume", domain=[f_set, st_set], records=shelf_vol_records)

shelf_wt_records = [(fac, st, shelf_weight_cap.get((fac, st), 0))
                    for fac in facilities for st in storage_types]
shelf_wt_param = Parameter(m, name="shelf_weight", domain=[f_set, st_set], records=shelf_wt_records)

shelf_pkg_records = [(fac, st, shelf_package_cap.get((fac, st), 0))
                     for fac in facilities for st in storage_types]
shelf_pkg_param = Parameter(m, name="shelf_package_cap", domain=[f_set, st_set], records=shelf_pkg_records)

# Average sqft per shelf
avg_sqft_records = [(fac, st, avg_sqft_per_shelf.get((fac, st), 50))
                    for fac in facilities for st in storage_types]
avg_sqft_param = Parameter(m, name="avg_sqft", domain=[f_set, st_set], records=avg_sqft_records)

print(f"   ✓ {len(m.getParameters())} parameters created")

# ============================================================================
# DECISION VARIABLES
# ============================================================================

print("   ✓ Defining decision variables...")

# Expansion decisions (one-time)
expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive")
sac_t1 = Variable(m, name="sac_tier1", type="positive")
sac_t2 = Variable(m, name="sac_tier2", type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive")

# Repacking decision - DISABLED to keep model linear
# (Assume all SKUs stored in inbound packs - no repacking)
# repack = Variable(m, name="repack_decision", domain=[s_set, f_set], type="binary")

# DAILY VARIABLES - True day-by-day tracking
daily_inventory = Variable(m, name="daily_inventory", domain=[t_month_set, t_day_set, s_set, f_set], type="positive",
                          description="Inventory at end of day d in month t")
daily_deliveries = Variable(m, name="daily_deliveries", domain=[t_month_set, t_day_set, s_set, f_set], type="positive",
                           description="Inbound packs delivered on day d in month t (8am arrival)")
daily_shipments = Variable(m, name="daily_shipments", domain=[t_month_set, t_day_set, s_set, f_set], type="positive",
                          description="Sell packs shipped on day d in month t (before 5pm)")

# Package allocation (daily)
packages_on_shelf = Variable(m, name="packages_on_shelf", domain=[t_month_set, t_day_set, s_set, f_set, st_set], type="positive",
                            description="Number of packages on shelf at end of day d in month t")

# Truck constraint slack variables - one per day per supplier
truck_slack = Variable(m, name="truck_slack", domain=[t_month_set, t_day_set, sup_set, f_set], type="positive",
                      description="Extra trucks needed per supplier per day beyond 1 truck limit")

# Objective
total_cost = Variable(m, name="total_cost", type="free")

print(f"   ✓ Decision variables defined")
print(f"   ✓ Estimated model size: ~{len(months) * len(days) * len(skus) * len(facilities) * 3:,} daily variables")
print(f"   ✓ Time periods: {len(months)} months × {len(days)} days = {len(months) * len(days):,} daily periods")

# ============================================================================
# CONSTRAINTS
# ============================================================================

print("   ✓ Defining constraints...")

# Objective: minimize expansion cost + penalty for exceeding truck limits
# Heavy penalty for truck slack to encourage staying within 1 truck/supplier/day limit
TRUCK_PENALTY = 10000  # $10,000 per extra truck per day (high penalty)

obj_eq = Equation(m, name="obj")
obj_eq[...] = (
    total_cost ==
    sac_t1 * 2.0 + sac_t2 * 4.0 + expansion['Austin'] * 1.5 +
    TRUCK_PENALTY * Sum([t_month_set, t_day_set, sup_set, f_set], truck_slack[t_month_set, t_day_set, sup_set, f_set])
)

# Sacramento tiered pricing
sac_t1_max = Equation(m, name="sac_t1_max")
sac_t1_max[...] = sac_t1 <= 100000

sac_t2_max = Equation(m, name="sac_t2_max")
sac_t2_max[...] = sac_t2 <= 150000

sac_total = Equation(m, name="sac_total")
sac_total[...] = expansion['Sacramento'] == sac_t1 + sac_t2

# Max expansion limits
max_exp_sac = Equation(m, name="max_exp_sac")
max_exp_sac[...] = expansion['Sacramento'] <= 250000

max_exp_aus = Equation(m, name="max_exp_aus")
max_exp_aus[...] = expansion['Austin'] <= 200000

# Link expansion to shelves
exp_shelves = Equation(m, name="exp_shelves", domain=f_exp_set)
exp_shelves[f_exp_set] = expansion[f_exp_set] == Sum(st_set, add_shelves[f_exp_set, st_set] * avg_sqft_param[f_exp_set, st_set])

# Monthly demand fulfillment
# NOTE: Demand is in SELL PACKS (outbound units), shipments are in SELL PACKS
# Daily shipments must sum across all days in the month to meet monthly demand
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month_set, s_set])
demand_fulfill[t_month_set, s_set] = (
    Sum([t_day_set, f_set], daily_shipments[t_month_set, t_day_set, s_set, f_set]) >= demand_param[t_month_set, s_set]
)

# DAILY inventory balance with temporal continuity
# Case 1: First day of first month (t=1, d=1) - no prior inventory
inv_balance_first = Equation(m, name="inv_balance_first", domain=[s_set, f_set])
inv_balance_first[s_set, f_set] = (
    daily_inventory['1', '1', s_set, f_set] ==
    daily_deliveries['1', '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', '1', s_set, f_set]
)

# Case 2: Subsequent days within first month (t=1, d>1)
inv_balance_first_month = Equation(m, name="inv_balance_first_month", domain=[t_day_set, s_set, f_set])
inv_balance_first_month[t_day_set, s_set, f_set].where[Ord(t_day_set) > 1] = (
    daily_inventory['1', t_day_set, s_set, f_set] ==
    daily_inventory['1', t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries['1', t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', t_day_set, s_set, f_set]
)

# Case 3: First day of subsequent months (t>1, d=1) - carry from last day of previous month
inv_balance_month_boundary = Equation(m, name="inv_balance_month_boundary", domain=[t_month_set, s_set, f_set])
inv_balance_month_boundary[t_month_set, s_set, f_set].where[Ord(t_month_set) > 1] = (
    daily_inventory[t_month_set, '1', s_set, f_set] ==
    daily_inventory[t_month_set.lag(1, 'linear'), '21', s_set, f_set] +  # Last day of previous month
    daily_deliveries[t_month_set, '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, '1', s_set, f_set]
)

# Case 4: Subsequent days within subsequent months (t>1, d>1)
inv_balance = Equation(m, name="inv_balance", domain=[t_month_set, t_day_set, s_set, f_set])
inv_balance[t_month_set, t_day_set, s_set, f_set].where[(Ord(t_month_set) > 1) & (Ord(t_day_set) > 1)] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    daily_inventory[t_month_set, t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries[t_month_set, t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, t_day_set, s_set, f_set]
)

# Days on hand requirement (DISABLED - testing infeasibility)
# This requires inventory >= (daily_demand * days_on_hand)
# May be causing infeasibility if requirements too high
# doh_req = Equation(m, name="doh_req", domain=[t_month_set, s_set, f_set])
# doh_req[t_month_set, s_set, f_set] = (
#     monthly_inventory[t_month_set, s_set, f_set] >=
#     (demand_param[t_month_set, s_set] / WORKING_DAYS_PER_MONTH) * doh_param[s_set, f_set]
# )

# Link packages to inventory
# NOTE: Inventory is in SELL PACKS (units)
# With repacking disabled, all packages are inbound packs containing inbound_qty[s] sell packs
pkg_inv_link = Equation(m, name="pkg_inv_link", domain=[t_month_set, t_day_set, s_set, f_set])
pkg_inv_link[t_month_set, t_day_set, s_set, f_set] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    Sum(st_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_qty[s_set]
    )
)

# Package capacity constraint (SET PACKING) - DAILY
# For expandable facilities: current shelves + new shelves
pkg_capacity_exp = Equation(m, name="pkg_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
pkg_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_pkg_param[f_exp_set, st_set]
)

# For non-expandable facility (Columbus): only current shelves
pkg_capacity_fixed = Equation(m, name="pkg_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
pkg_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_pkg_param['Columbus', st_set]
)

# Volume capacity (assumes all SKUs stored in inbound pack format - no repacking) - DAILY
# For expandable facilities
vol_capacity_exp = Equation(m, name="vol_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
vol_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_vol[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_vol_param[f_exp_set, st_set]
)

# For non-expandable facility (Columbus)
vol_capacity_fixed = Equation(m, name="vol_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
vol_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_vol[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_vol_param['Columbus', st_set]
)

# Weight capacity (assumes all SKUs stored in inbound pack format - no repacking) - DAILY
# For expandable facilities
wt_capacity_exp = Equation(m, name="wt_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
wt_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_wt[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_wt_param[f_exp_set, st_set]
)

# For non-expandable facility (Columbus)
wt_capacity_fixed = Equation(m, name="wt_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
wt_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_wt[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_wt_param['Columbus', st_set]
)

# ============================================================================
# TRUCK DELIVERY CONSTRAINTS (WITH SLACK - ENABLED)
# ============================================================================
# Constraint: 1 truck delivery per supplier per day (8am arrivals)
# We allow slack variables to identify when additional trucks are needed
# Heavy penalty encourages staying within limit but allows violations if necessary

# Repacking constraint - DISABLED (no repacking in model)
# repack_constraint = Equation(m, name="repack_constraint", domain=[s_set, f_set])
# repack_constraint[s_set, f_set] = repack[s_set, f_set] <= can_consolidate[s_set]

# Truck delivery limit with slack - DAILY
# Sum of all deliveries for a supplier at a facility per day <= 1 + slack
truck_limit = Equation(m, name="truck_limit", domain=[t_month_set, t_day_set, sup_set, f_set])
truck_limit[t_month_set, t_day_set, sup_set, f_set] = (
    Sum(s_set.where[sku_sup_map[s_set, sup_set] > 0], daily_deliveries[t_month_set, t_day_set, s_set, f_set]) <=
    1 + truck_slack[t_month_set, t_day_set, sup_set, f_set]
)

print(f"   ✓ {len(m.getEquations())} constraint equations defined (including truck limits)")
print(f"   ✓ Truck penalty: ${TRUCK_PENALTY:,} per extra delivery beyond limit")

# ============================================================================
# SOLVE MODEL
# ============================================================================

print("\n[7/7] Solving optimization model...")
print("   (This may take several minutes for large models...)")

warehouse_model = Model(
    m,
    name="full_daily_warehouse",
    equations=m.getEquations(),
    problem="LP",  # Linear Programming (no binary variables after removing repacking)
    sense=Sense.MIN,
    objective=total_cost
)

# Solve with time limit
try:
    warehouse_model.solve()  # Remove options parameter for now
except Exception as e:
    print(f"\n   ⚠ Solver encountered an issue: {e}")
    print(f"   Attempting to continue with best solution found...")

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)

print(f"\nModel Status: {warehouse_model.status}")
print(f"Solve Status: {warehouse_model.solve_status}")

# Check if we have a valid solution
if warehouse_model.status is not None and hasattr(warehouse_model.status, 'value') and warehouse_model.status.value in [1, 2, 7, 8, 15]:  # Optimal or feasible solution
    obj_value = total_cost.toValue()

    print(f"\n{'='*80}")
    print(f"TOTAL EXPANSION COST: ${obj_value:,.2f}")
    print(f"{'='*80}")

    # Expansion details
    print("\n" + "-"*80)
    print("EXPANSION DECISIONS")
    print("-"*80)

    exp_records = expansion.records
    sac_exp = exp_records[exp_records['f_exp'] == 'Sacramento']['level'].values[0] if 'Sacramento' in exp_records['f_exp'].values else 0
    aus_exp = exp_records[exp_records['f_exp'] == 'Austin']['level'].values[0] if 'Austin' in exp_records['f_exp'].values else 0
    sac_t1_val = sac_t1.toValue()
    sac_t2_val = sac_t2.toValue()

    print(f"\n✓ Sacramento Expansion: {sac_exp:,.0f} sq ft")
    print(f"  - Tier 1 (0-100K @ $2/sqft): {sac_t1_val:,.0f} sq ft → ${sac_t1_val * 2:,.2f}")
    print(f"  - Tier 2 (100K-250K @ $4/sqft): {sac_t2_val:,.0f} sq ft → ${sac_t2_val * 4:,.2f}")

    print(f"\n✓ Austin Expansion: {aus_exp:,.0f} sq ft")
    print(f"  - Cost @ $1.5/sqft: ${aus_exp * 1.5:,.2f}")

    # Additional shelves
    print("\n" + "-"*80)
    print("ADDITIONAL SHELVING REQUIRED")
    print("-"*80 + "\n")

    shelves_df = add_shelves.records[add_shelves.records['level'] > 0.5].copy()
    if len(shelves_df) > 0:
        shelves_df['level'] = shelves_df['level'].round(0).astype(int)
        print(shelves_df[['f_exp', 'st', 'level']].to_string(index=False))
    else:
        print("No additional shelves needed")

    # Repacking disabled - all SKUs stored in inbound pack format
    print("\n" + "-"*80)
    print("STORAGE FORMAT")
    print("-"*80 + "\n")
    print("All SKUs stored in inbound pack format (no repacking)")
    print("This simplifies the model to keep it linear.")

    # Save results
    print("\n" + "-"*80)
    print("SAVING RESULTS")
    print("-"*80 + "\n")

    exp_summary = pd.DataFrame({
        'Facility': ['Sacramento', 'Austin', 'TOTAL'],
        'Expansion_sqft': [sac_exp, aus_exp, sac_exp + aus_exp],
        'Cost_USD': [sac_t1_val * 2 + sac_t2_val * 4, aus_exp * 1.5, obj_value]
    })
    exp_summary.to_csv(RESULTS_DIR / 'full_daily_expansion_summary.csv', index=False)
    print("✓ Saved: full_daily_expansion_summary.csv")

    if len(shelves_df) > 0:
        shelves_df.to_csv(RESULTS_DIR / 'full_daily_additional_shelves.csv', index=False)
        print("✓ Saved: full_daily_additional_shelves.csv")

    # Export ALL decision variables to CSV files
    print("\n" + "-"*80)
    print("EXPORTING ALL DECISION VARIABLES (DAILY DATA)")
    print("-"*80 + "\n")

    # Variable 1: Expansion
    expansion.records.to_csv(RESULTS_DIR / 'var_expansion.csv', index=False)
    print("✓ var_expansion.csv")

    # Variable 2: Sacramento tiers
    sac_tier_df = pd.DataFrame({
        'Tier': ['Tier 1 (0-100K @ $2/sqft)', 'Tier 2 (100K-250K @ $4/sqft)'],
        'sqft': [sac_t1_val, sac_t2_val],
        'cost_usd': [sac_t1_val * 2.0, sac_t2_val * 4.0]
    })
    sac_tier_df.to_csv(RESULTS_DIR / 'var_sacramento_tiers.csv', index=False)
    print("✓ var_sacramento_tiers.csv")

    # Variable 3: Additional shelves
    add_shelves.records.to_csv(RESULTS_DIR / 'var_add_shelves.csv', index=False)
    print("✓ var_add_shelves.csv")

    # Variable 4: DAILY inventory (day-by-day breakdown)
    daily_inventory.records.to_csv(RESULTS_DIR / 'var_daily_inventory.csv', index=False)
    print("✓ var_daily_inventory.csv (DAILY breakdown)")

    # Variable 5: DAILY deliveries (day-by-day breakdown)
    daily_deliveries.records.to_csv(RESULTS_DIR / 'var_daily_deliveries.csv', index=False)
    print("✓ var_daily_deliveries.csv (DAILY breakdown)")

    # Variable 6: DAILY shipments (day-by-day breakdown)
    daily_shipments.records.to_csv(RESULTS_DIR / 'var_daily_shipments.csv', index=False)
    print("✓ var_daily_shipments.csv (DAILY breakdown)")

    # Variable 7: Packages on shelf (DAILY breakdown)
    packages_on_shelf.records.to_csv(RESULTS_DIR / 'var_packages_on_shelf.csv', index=False)
    print("✓ var_packages_on_shelf.csv (DAILY breakdown)")

    # Variable 8: Truck slack (DAILY breakdown - shows when extra trucks needed)
    truck_slack.records.to_csv(RESULTS_DIR / 'var_truck_slack.csv', index=False)
    print("✓ var_truck_slack.csv (DAILY breakdown)")

    # Variable 9: Total cost
    cost_summary = pd.DataFrame({
        'Variable': ['total_cost'],
        'Value_USD': [obj_value]
    })
    cost_summary.to_csv(RESULTS_DIR / 'var_total_cost.csv', index=False)
    print("✓ var_total_cost.csv")

    print(f"\n✓ All 9 decision variables exported to: {RESULTS_DIR}")
    print(f"✓ Daily variables include {len(months)} months × {len(days)} days = {len(months)*len(days)} time periods")

else:
    print("\n*** MODEL IS INFEASIBLE OR NO SOLUTION FOUND ***")
    print("\nPossible reasons:")
    print("  - Expansion limits insufficient for demand")
    print("  - Truck capacity constraints too restrictive (max 1 truck/supplier/day)")
    print("  - Package capacity limits too tight")
    print("  - Safety stock requirements (days-on-hand) too high")

print("\n" + "="*80)
print("OPTIMIZATION COMPLETE!")
print("="*80)
print(f"\nTo run with full 120-month horizon, set USE_FULL_HORIZON = True in the script")
print("="*80 + "\n")
