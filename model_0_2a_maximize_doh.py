"""
InkCredible Supplies - Model 0.2a-MaxDoH: Maximize Days-on-Hand Achievement
============================================================================

This model MAXIMIZES days-on-hand (DoH) as the objective function rather than
enforcing it as a constraint. This shows the maximum achievable DoH given:
- Capacity constraints (volume, weight, packages)
- Demand fulfillment requirements
- Lead times
- No truck delivery limits

OBJECTIVE: Maximize total system-wide days-on-hand across all SKUs

DoH Calculation:
- DoH[sku] = Average_inventory[sku] / Daily_demand[sku]
- Total_DoH = Sum across all SKUs

This approach identifies what DoH is naturally achievable rather than forcing
infeasible constraints.

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

# Import calendar utilities
from calendar_utils import (
    calendar_days_to_business_days,
    BUSINESS_DAYS_PER_MONTH
)

# Set license
os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Model0.2\MaxDoH")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Time parameters
MONTHS = 120  # 10 years
DAYS_PER_MONTH = 21  # Business days per month
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH  # 2,520 days

USE_FULL_HORIZON = True
TEST_MONTHS = 3
TEST_DAYS = TEST_MONTHS * DAYS_PER_MONTH if not USE_FULL_HORIZON else TOTAL_DAYS

WORKING_DAYS_PER_MONTH = 21

print("="*80)
print("MODEL 0.2a-MaxDoH: MAXIMIZE DAYS-ON-HAND ACHIEVEMENT")
print("="*80)
print(f"\nConfiguration:")
print(f"  Time horizon: {TEST_MONTHS if not USE_FULL_HORIZON else MONTHS} months ({TEST_DAYS} business days)")
print(f"  Working days per month: {WORKING_DAYS_PER_MONTH}")
print(f"  Objective: MAXIMIZE total system-wide DoH across all SKUs")
print(f"  Constraints: Capacity limits, demand fulfillment")
print(f"  NO truck delivery limits")
print("="*80)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' inches to tuple in feet"""
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        return tuple(float(p.strip()) / 12 for p in parts)  # inches to feet
    except:
        return (1.0, 1.0, 1.0)

def parse_weight(wt_str):
    """Parse weight string like '15 lbs' to float"""
    try:
        return float(str(wt_str).replace('lbs', '').replace('lb', '').strip())
    except:
        return 1.0

def parse_quantity(qty_str):
    """Parse quantity string like '144 (12 packs)' to integer"""
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

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

print("\n[2/7] Defining sets...")

# Time sets
months = list(range(1, (TEST_MONTHS if not USE_FULL_HORIZON else MONTHS) + 1))
days = list(range(1, DAYS_PER_MONTH + 1))

# SKU sets
skus = list(sku_details_df['SKU Number'].unique())
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable_facilities = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
supplier_types = ['Domestic', 'International']

# Classify SKUs by supplier type
domestic_skus = []
international_skus = []

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    supplier = row['Supplier Type'].strip()
    if supplier == 'Domestic':
        domestic_skus.append(sku)
    else:
        international_skus.append(sku)

print(f"   ✓ Sets defined:")
print(f"      - Time: {len(months)} months × {len(days)} days = {len(months)*len(days)} daily periods")
print(f"      - SKUs: {len(skus)} ({len(domestic_skus)} domestic, {len(international_skus)} international)")
print(f"      - Facilities: {len(facilities)} ({len(expandable_facilities)} expandable)")

# ============================================================================
# STEP 3: PARSE SKU DETAILS
# ============================================================================

print("\n[3/7] Processing SKU details...")

sku_data = {}

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Parse sell pack
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])

    # Parse inbound pack
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

    # Consolidation
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

print(f"   ✓ Processed {len(sku_data)} SKUs with dimensions, weights, and storage types")

# ============================================================================
# STEP 4: LOAD DEMAND AND LEAD TIME DATA
# ============================================================================

print("\n[4/7] Processing demand and lead time data...")

# Extract demand data
demand_data = {}
for idx, row in demand_df.iterrows():
    month = idx + 1
    if month > len(months):
        break
    for sku in skus:
        demand_data[(month, sku)] = float(row[sku])

print(f"   ✓ Loaded demand data for {len(months)} months")

# Extract lead times (in CALENDAR days)
lead_times_calendar = {}

for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        lt_col = f'Lead Time - {fac}'
        if lt_col in row.index:
            lead_times_calendar[(sku, fac)] = int(row[lt_col])

# Convert calendar days to business days using 5/7 ratio
lead_times_business = {}
for (sku, fac), cal_days in lead_times_calendar.items():
    lead_times_business[(sku, fac)] = calendar_days_to_business_days(cal_days)

print(f"   ✓ Loaded lead times for {len(skus)} SKUs × {len(facilities)} facilities")
print(f"   ✓ Converted calendar days to business days (5/7 ratio)")

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
        shelf_package_cap[(fac, st)] = 100

# Average sqft per shelf
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves
    else:
        avg_sqft_per_shelf[(fac, st)] = 50.0

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

# Demand (monthly, distributed evenly across days)
demand_records = [(str(month), sku, demand_data.get((month, sku), 0))
                  for month in months for sku in skus]
demand_param = Parameter(m, name="demand", domain=[t_month_set, s_set], records=demand_records)

# Daily demand (monthly demand / 21 days)
daily_demand_records = [(str(month), sku, demand_data.get((month, sku), 0) / DAYS_PER_MONTH)
                        for month in months for sku in skus]
daily_demand_param = Parameter(m, name="daily_demand", domain=[t_month_set, s_set], records=daily_demand_records)

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

# Lead times (in business days, converted from calendar days)
lead_time_records = [(sku, fac, lead_times_business.get((sku, fac), 5)) for sku in skus for fac in facilities]
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set], records=lead_time_records)

# Shelving parameters
curr_shelves_records = [(fac, st, current_shelves.get((fac, st), 0)) for fac in facilities for st in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f_set, st_set], records=curr_shelves_records)

shelf_vol_records = [(fac, st, shelf_volume_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_vol_param = Parameter(m, name="shelf_volume", domain=[f_set, st_set], records=shelf_vol_records)

shelf_wt_records = [(fac, st, shelf_weight_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_wt_param = Parameter(m, name="shelf_weight", domain=[f_set, st_set], records=shelf_wt_records)

shelf_pkg_records = [(fac, st, shelf_package_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_pkg_param = Parameter(m, name="shelf_packages", domain=[f_set, st_set], records=shelf_pkg_records)

# Expansion costs
expansion_cost_records = [
    ('Sacramento', 2.0),  # Tier 1: $2/sqft (first 100K)
    ('Austin', 1.5)
]
expansion_cost_param = Parameter(m, name="expansion_cost", domain=f_exp_set, records=expansion_cost_records)

# Sacramento tiered pricing
sac_tier2_cost = Parameter(m, name="sac_tier2_cost", records=2.0)

# Avg sqft per shelf
sqft_records = [(fac, st, avg_sqft_per_shelf.get((fac, st), 50)) for fac in expandable_facilities for st in storage_types]
sqft_param = Parameter(m, name="sqft_per_shelf", domain=[f_exp_set, st_set], records=sqft_records)

print("   ✓ Parameters created")

# ============================================================================
# DECISION VARIABLES
# ============================================================================

print("   ✓ Creating decision variables...")

# Expansion decisions (one-time, not time-indexed)
expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive", description="Square feet to add")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive", description="Additional shelves")

# Sacramento tiered expansion
sac_tier1 = Variable(m, name="sac_tier1", type="positive", description="Sacramento expansion 0-100K sqft")
sac_tier2 = Variable(m, name="sac_tier2", type="positive", description="Sacramento expansion 100K-250K sqft")

# Daily inventory and operations (TIME-INDEXED)
daily_inventory = Variable(m, name="daily_inventory", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
daily_deliveries = Variable(m, name="daily_deliveries", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
daily_shipments = Variable(m, name="daily_shipments", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
packages_on_shelf = Variable(m, name="packages_on_shelf", domain=[t_month_set, t_day_set, s_set, f_set, st_set], type="positive")

# DoH achievement variables (what we're maximizing)
# Calculate DoH per SKU: avg_inventory[s] / avg_daily_demand[s]
avg_inventory = Variable(m, name="avg_inventory", domain=s_set, type="positive", description="Average inventory per SKU")
doh_per_sku = Variable(m, name="doh_per_sku", domain=s_set, type="positive", description="Days-on-hand per SKU")
total_doh = Variable(m, name="total_doh", type="free", description="Sum of DoH across all SKUs")

print(f"   ✓ Variables created")
print(f"      Estimated size: ~{len(months)*len(days)*len(skus)*len(facilities)*5 + len(expandable_facilities)*len(storage_types)*2:,} decision variables")

# ============================================================================
# CONSTRAINTS
# ============================================================================

print("   ✓ Creating constraints...")

# ----------------------------------------------------------------------------
# 1. OBJECTIVE: MAXIMIZE Total Days-on-Hand (Per-SKU Calculation)
# ----------------------------------------------------------------------------

# Calculate average inventory per SKU across all time periods and facilities
calc_avg_inv = Equation(m, name="calc_avg_inv", domain=s_set)
calc_avg_inv[s_set] = (
    avg_inventory[s_set] == Sum([t_month_set, t_day_set, f_set],
                                 daily_inventory[t_month_set, t_day_set, s_set, f_set]) /
                            (len(months) * DAYS_PER_MONTH)
)

# Calculate DoH per SKU: avg_inventory / avg_daily_demand
# Using average daily demand across all months
calc_doh = Equation(m, name="calc_doh", domain=s_set)
calc_doh[s_set] = (
    doh_per_sku[s_set] * Sum(t_month_set, daily_demand_param[t_month_set, s_set]) ==
    avg_inventory[s_set] * (len(months) * DAYS_PER_MONTH)
)

# Total DoH = sum of DoH across all SKUs
calc_total_doh = Equation(m, name="calc_total_doh")
calc_total_doh[...] = total_doh == Sum(s_set, doh_per_sku[s_set])

# ----------------------------------------------------------------------------
# 2. EXPANSION LIMITS
# ----------------------------------------------------------------------------

# Sacramento split into tiers
sac_tier_split = Equation(m, name="sac_tier_split")
sac_tier_split[...] = expansion['Sacramento'] == sac_tier1 + sac_tier2

sac_tier1_limit = Equation(m, name="sac_tier1_limit")
sac_tier1_limit[...] = sac_tier1 <= 100000

sac_tier2_limit = Equation(m, name="sac_tier2_limit")
sac_tier2_limit[...] = sac_tier2 <= 150000

# Austin limit
austin_limit = Equation(m, name="austin_limit")
austin_limit[...] = expansion['Austin'] <= 200000

# Expansion = sum of shelf additions
expansion_calc = Equation(m, name="expansion_calc", domain=f_exp_set)
expansion_calc[f_exp_set] = expansion[f_exp_set] == Sum(st_set, add_shelves[f_exp_set, st_set] * sqft_param[f_exp_set, st_set])

# ----------------------------------------------------------------------------
# 3. INVENTORY BALANCE EQUATIONS
# ----------------------------------------------------------------------------

# Month 1 - Day 1
inv_balance_first = Equation(m, name="inv_balance_first", domain=[s_set, f_set])
inv_balance_first[s_set, f_set] = (
    daily_inventory['1', '1', s_set, f_set] ==
    daily_deliveries['1', '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', '1', s_set, f_set]
)

# Month 1 - Days 2-21
inv_balance_month1 = Equation(m, name="inv_balance_month1", domain=[t_day_set, s_set, f_set])
inv_balance_month1[t_day_set, s_set, f_set].where[Ord(t_day_set) > 1] = (
    daily_inventory['1', t_day_set, s_set, f_set] ==
    daily_inventory['1', t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries['1', t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', t_day_set, s_set, f_set]
)

# Month 2+ - Day 1 (carry from previous month)
inv_balance_month_boundary = Equation(m, name="inv_balance_month_boundary", domain=[t_month_set, s_set, f_set])
inv_balance_month_boundary[t_month_set, s_set, f_set].where[Ord(t_month_set) > 1] = (
    daily_inventory[t_month_set, '1', s_set, f_set] ==
    daily_inventory[t_month_set.lag(1, 'linear'), '21', s_set, f_set] +
    daily_deliveries[t_month_set, '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, '1', s_set, f_set]
)

# Month 2+ - Days 2-21
inv_balance_general = Equation(m, name="inv_balance_general", domain=[t_month_set, t_day_set, s_set, f_set])
inv_balance_general[t_month_set, t_day_set, s_set, f_set].where[(Ord(t_month_set) > 1) & (Ord(t_day_set) > 1)] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    daily_inventory[t_month_set, t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries[t_month_set, t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, t_day_set, s_set, f_set]
)

# ----------------------------------------------------------------------------
# 4. DEMAND FULFILLMENT
# ----------------------------------------------------------------------------

# Monthly demand must be met across all facilities
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month_set, s_set])
demand_fulfill[t_month_set, s_set] = (
    Sum([t_day_set, f_set], daily_shipments[t_month_set, t_day_set, s_set, f_set]) >=
    demand_param[t_month_set, s_set]
)

# ----------------------------------------------------------------------------
# 5. LINK PACKAGES TO INVENTORY
# ----------------------------------------------------------------------------

pkg_inv_link = Equation(m, name="pkg_inv_link", domain=[t_month_set, t_day_set, s_set, f_set])
pkg_inv_link[t_month_set, t_day_set, s_set, f_set] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    Sum(st_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_qty[s_set]
    )
)

# ----------------------------------------------------------------------------
# 6. CAPACITY CONSTRAINTS (Volume, Weight, Package count)
# ----------------------------------------------------------------------------

# Package capacity - expandable facilities
pkg_capacity_exp = Equation(m, name="pkg_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
pkg_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_pkg_param[f_exp_set, st_set]
)

# Package capacity - Columbus (non-expandable)
pkg_capacity_fixed = Equation(m, name="pkg_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
pkg_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_pkg_param['Columbus', st_set]
)

# Volume capacity - expandable facilities
vol_capacity_exp = Equation(m, name="vol_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
vol_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_vol[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_vol_param[f_exp_set, st_set]
)

# Volume capacity - Columbus
vol_capacity_fixed = Equation(m, name="vol_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
vol_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_vol[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_vol_param['Columbus', st_set]
)

# Weight capacity - expandable facilities
wt_capacity_exp = Equation(m, name="wt_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
wt_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_wt[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_wt_param[f_exp_set, st_set]
)

# Weight capacity - Columbus
wt_capacity_fixed = Equation(m, name="wt_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
wt_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_wt[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_wt_param['Columbus', st_set]
)

print(f"   ✓ Constraints created")

# ============================================================================
# STEP 7: SOLVE MODEL
# ============================================================================

print("\n[7/7] Solving optimization model...")
print("="*80)

warehouse_model = Model(
    m,
    name="warehouse_maximize_doh",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MAX,  # MAXIMIZE DoH
    objective=total_doh
)

print("\nSolving... (this may take several minutes for large models)")
warehouse_model.solve()

print("="*80)
print(f"\nModel Status: {warehouse_model.status}")
print(f"Objective Value (Total DoH): {warehouse_model.objective_value:,.2f} days")
print("="*80)

# ============================================================================
# STEP 8: EXTRACT AND SAVE RESULTS
# ============================================================================

print("\n[8/8] Extracting and saving results...")

# Check if model solved successfully
model_status_str = str(warehouse_model.status)
is_optimal = 'Optimal' in model_status_str or warehouse_model.status in [1, 2, 'OptimalGlobal', 'OptimalLocal']

if is_optimal:
    # Expansion decisions
    if hasattr(expansion, 'records') and expansion.records is not None:
        expansion_df = expansion.records
        expansion_df.to_csv(RESULTS_DIR / "var_expansion.csv", index=False)
        print(f"   ✓ Saved expansion decisions")

    if hasattr(add_shelves, 'records') and add_shelves.records is not None:
        add_shelves_df = add_shelves.records
        add_shelves_df.to_csv(RESULTS_DIR / "var_add_shelves.csv", index=False)
        print(f"   ✓ Saved shelf additions")

    # Daily inventory
    if hasattr(daily_inventory, 'records') and daily_inventory.records is not None:
        daily_inventory_df = daily_inventory.records
        daily_inventory_df.to_csv(RESULTS_DIR / "var_daily_inventory.csv", index=False)
        print(f"   ✓ Saved daily inventory")

    # Daily deliveries
    if hasattr(daily_deliveries, 'records') and daily_deliveries.records is not None:
        daily_deliveries_df = daily_deliveries.records
        daily_deliveries_df.to_csv(RESULTS_DIR / "var_daily_deliveries.csv", index=False)
        print(f"   ✓ Saved daily deliveries")

    # Daily shipments
    if hasattr(daily_shipments, 'records') and daily_shipments.records is not None:
        daily_shipments_df = daily_shipments.records
        daily_shipments_df.to_csv(RESULTS_DIR / "var_daily_shipments.csv", index=False)
        print(f"   ✓ Saved daily shipments")

    # Packages on shelf
    if hasattr(packages_on_shelf, 'records') and packages_on_shelf.records is not None:
        packages_df = packages_on_shelf.records
        packages_df.to_csv(RESULTS_DIR / "var_packages_on_shelf.csv", index=False)
        print(f"   ✓ Saved packages on shelf")

    # DoH per SKU (from model variables)
    if hasattr(doh_per_sku, 'records') and doh_per_sku.records is not None:
        doh_sku_df = doh_per_sku.records
        doh_sku_df.to_csv(RESULTS_DIR / "var_doh_per_sku.csv", index=False)
        print(f"   ✓ Saved DoH per SKU from model")

    # Calculate and report DoH by SKU
    print(f"\n   ✓ Calculating DoH metrics by SKU...")

    # Get total inventory and demand
    inv_df = daily_inventory_df[daily_inventory_df['level'] > 0].copy()

    # Calculate average inventory per SKU
    avg_inv_by_sku = inv_df.groupby('s')['level'].mean()

    # Calculate average daily demand per SKU
    total_demand_by_sku = {}
    for month in months:
        for sku in skus:
            if sku not in total_demand_by_sku:
                total_demand_by_sku[sku] = 0
            total_demand_by_sku[sku] += demand_data.get((month, sku), 0)

    avg_daily_demand_by_sku = {sku: total_demand_by_sku[sku] / (len(months) * DAYS_PER_MONTH) for sku in skus}

    # Calculate DoH per SKU
    doh_by_sku = {}
    for sku in skus:
        avg_inv = avg_inv_by_sku.get(sku, 0)
        avg_daily_demand = avg_daily_demand_by_sku.get(sku, 0.0001)  # Avoid div by zero
        doh_by_sku[sku] = avg_inv / avg_daily_demand if avg_daily_demand > 0 else 0

    # Create DoH report
    doh_report_df = pd.DataFrame([
        {
            'SKU': sku,
            'Supplier': sku_data[sku]['supplier'],
            'Avg_Inventory': avg_inv_by_sku.get(sku, 0),
            'Avg_Daily_Demand': avg_daily_demand_by_sku.get(sku, 0),
            'DoH_Achieved': doh_by_sku[sku]
        }
        for sku in skus
    ])
    doh_report_df.to_csv(RESULTS_DIR / "doh_by_sku.csv", index=False)
    print(f"   ✓ Saved DoH analysis by SKU")

else:
    print(f"\n   ⚠ Model is infeasible or unsolved - cannot extract results")
    print(f"   Status: {warehouse_model.status}")

print("\n" + "="*80)
print("MODEL 0.2a-MaxDoH COMPLETE: Maximize Days-on-Hand")
print("="*80)
print(f"\nResults saved to: {RESULTS_DIR}")
if is_optimal:
    print(f"\nTotal DoH Achieved: {warehouse_model.objective_value:,.2f} days")
    print("\nThis represents the MAXIMUM achievable DoH given capacity and demand constraints")
    print("See 'doh_by_sku.csv' for per-SKU breakdown")
print("="*80)
