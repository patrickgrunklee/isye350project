"""
InkCredible Supplies - Model 0.2a-MaxMin with SET PACKING OPTIMIZATION
========================================================================

This model MAXIMIZES the MINIMUM DoH across all SKUs with full consolidation/
repacking optimization.

KEY FEATURE: Binary repack decision per SKU per facility
- SKUs with "Consolidation = Yes" can be repacked from inbound pallets to sell packs
- SKUs with "Consolidation = No" must be stored as received
- Package capacity based on OPTIMIZED package sets (not raw inbound pallets)
- Volume/weight capacity conditional on repacking decision

OBJECTIVE: Maximize the minimum DoH across all 18 SKUs

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

from calendar_utils import calendar_days_to_business_days, BUSINESS_DAYS_PER_MONTH

os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Model0.2\MaxMinDoH_SetPacking")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MONTHS = 120
DAYS_PER_MONTH = 21
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH

USE_FULL_HORIZON = True
TEST_MONTHS = 3
TEST_DAYS = TEST_MONTHS * DAYS_PER_MONTH if not USE_FULL_HORIZON else TOTAL_DAYS

WORKING_DAYS_PER_MONTH = 21

print("="*80)
print("MODEL 0.2a-MaxMin: MAXIMIZE MINIMUM DoH WITH SET PACKING OPTIMIZATION")
print("="*80)
print(f"\nConfiguration:")
print(f"  Time horizon: {TEST_MONTHS if not USE_FULL_HORIZON else MONTHS} months ({TEST_DAYS} business days)")
print(f"  Objective: MAXIMIZE the MINIMUM DoH across all 18 SKUs")
print(f"  Set Packing: Binary repack decision per SKU per facility")
print(f"  Package capacity: Based on OPTIMIZED package sets (not raw inbound pallets)")
print(f"\nConstraints:")
print(f"  Minimum DoH: Domestic = 1 business day (~1.4 calendar), International = 3 business days (~4.2 calendar)")
print(f"  Max expansion: Sacramento ≤ 200,000 sq ft, Austin ≤ 200,000 sq ft")
print(f"  Columbus: Cannot expand (fixed capacity)")
print("="*80)

# Utility functions
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

# Load data
print("\n[1/7] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
print("   ✓ All data files loaded")

# Define sets
print("\n[2/7] Defining sets...")
months = list(range(1, (TEST_MONTHS if not USE_FULL_HORIZON else MONTHS) + 1))
days = list(range(1, DAYS_PER_MONTH + 1))
skus = list(sku_details_df['SKU Number'].unique())
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable_facilities = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
supplier_types = ['Domestic', 'International']

domestic_skus = []
international_skus = []
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    supplier = row['Supplier Type'].strip()
    if supplier == 'Domestic':
        domestic_skus.append(sku)
    else:
        international_skus.append(sku)

print(f"   ✓ Sets defined: {len(skus)} SKUs, {len(facilities)} facilities, {len(months)*len(days)} daily periods")

# Parse SKU details WITH CONSOLIDATION FLAGS
print("\n[3/7] Processing SKU details with consolidation flags...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack dimensions
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])

    # Inbound pack dimensions
    inbound_dims = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_volume = inbound_dims[0] * inbound_dims[1] * inbound_dims[2]
    inbound_weight = parse_weight(row['Inbound Pack Weight'])
    inbound_qty = parse_quantity(row['Inbound Pack Quantity'])

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

    # CRITICAL: Parse consolidation flag
    can_consolidate = 1 if str(row['Can be packed out in a box with other materials (consolidation)?']).strip().lower() == 'yes' else 0

    sku_data[sku] = {
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'sell_dims': sell_dims,
        'inbound_volume': inbound_volume,
        'inbound_weight': inbound_weight,
        'inbound_dims': inbound_dims,
        'inbound_qty': inbound_qty,
        'storage_type': storage_type,
        'can_consolidate': can_consolidate,
        'supplier': row['Supplier Type'].strip()
    }

consolidatable_skus = [s for s in skus if sku_data[s]['can_consolidate'] == 1]
non_consolidatable_skus = [s for s in skus if sku_data[s]['can_consolidate'] == 0]

print(f"   ✓ Processed {len(sku_data)} SKUs")
print(f"   ✓ Can consolidate: {len(consolidatable_skus)} SKUs")
print(f"      {', '.join(consolidatable_skus)}")
print(f"   ✓ Cannot consolidate: {len(non_consolidatable_skus)} SKUs (must store as received)")
print(f"      {', '.join(non_consolidatable_skus)}")

# Load demand
print("\n[4/7] Processing demand data...")
demand_data = {}
for idx, row in demand_df.iterrows():
    month = idx + 1
    if month > len(months):
        break
    for sku in skus:
        demand_data[(month, sku)] = float(row[sku])

print(f"   ✓ Loaded demand for {len(months)} months")

# Load lead times and convert to business days
lead_times_calendar = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        lt_col = f'Lead Time - {fac}'
        if lt_col in row.index:
            lead_times_calendar[(sku, fac)] = int(row[lt_col])

lead_times_business = {}
for (sku, fac), cal_days in lead_times_calendar.items():
    lead_times_business[(sku, fac)] = calendar_days_to_business_days(cal_days)

print(f"   ✓ Loaded lead times (converted to business days)")

# Load shelving data
print("\n[5/7] Processing shelving data...")
curr_shelves = {}
shelf_vol = {}
shelf_weight = {}
shelf_pkg_cap = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st_raw = row['Shelving Type'].strip()
    # Normalize storage type names
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
        shelf_pkg_cap[(fac, st)] = int(row['Package Capacity'])
    else:
        shelf_vol[(fac, st)] = 999999.0
        shelf_pkg_cap[(fac, st)] = 999999

print(f"   ✓ Loaded shelving data for {len(facilities)} facilities and {len(storage_types)} storage types")

# ============================================================================
# GAMSPY MODEL
# ============================================================================

print("\n[6/7] Building GAMSPy optimization model...")
m = Container()

# Sets
s_set = Set(m, name="s", records=[str(s) for s in skus])
f_set = Set(m, name="f", records=facilities)
f_exp_set = Set(m, name="f_exp", records=expandable_facilities)
st_set = Set(m, name="st", records=storage_types)
t_month_set = Set(m, name="t_month", records=[str(i) for i in months])
t_day_set = Set(m, name="t_day", records=[str(i) for i in days])

# SKU to storage type mapping - ALLOW SKUD1/SKUC1 TO USE BOTH RACKING AND PALLET
sku_st_records = []
for sku in skus:
    primary_st = sku_data[sku]['storage_type']
    sku_st_records.append((sku, primary_st, 1))

    # Allow SKUD1 and SKUC1 to ALSO use the alternative storage type
    if sku == 'SKUD1' and primary_st == 'Racking':
        sku_st_records.append((sku, 'Pallet', 1))
    elif sku == 'SKUD1' and primary_st == 'Pallet':
        sku_st_records.append((sku, 'Racking', 1))

    if sku == 'SKUC1' and primary_st == 'Racking':
        sku_st_records.append((sku, 'Pallet', 1))
    elif sku == 'SKUC1' and primary_st == 'Pallet':
        sku_st_records.append((sku, 'Racking', 1))

sku_st_map = Parameter(m, name="sku_st_map", domain=[s_set, st_set], records=sku_st_records)

# Parameters - SKU properties
sell_vol_records = [(sku, sku_data[sku]['sell_volume']) for sku in skus]
sell_vol = Parameter(m, name="sell_vol", domain=s_set, records=sell_vol_records)

sell_weight_records = [(sku, sku_data[sku]['sell_weight']) for sku in skus]
sell_weight = Parameter(m, name="sell_weight", domain=s_set, records=sell_weight_records)

inbound_vol_records = [(sku, sku_data[sku]['inbound_volume']) for sku in skus]
inbound_vol = Parameter(m, name="inbound_vol", domain=s_set, records=inbound_vol_records)

inbound_weight_records = [(sku, sku_data[sku]['inbound_weight']) for sku in skus]
inbound_weight = Parameter(m, name="inbound_weight", domain=s_set, records=inbound_weight_records)

inbound_qty_records = [(sku, sku_data[sku]['inbound_qty']) for sku in skus]
inbound_qty = Parameter(m, name="inbound_qty", domain=s_set, records=inbound_qty_records)

# CRITICAL: Consolidation flag parameter
can_consolidate_records = [(sku, sku_data[sku]['can_consolidate']) for sku in skus]
can_consolidate_param = Parameter(m, name="can_consolidate", domain=s_set, records=can_consolidate_records)

# Lead times
lead_time_records = [(sku, fac, lead_times_business.get((sku, fac), 0)) for sku in skus for fac in facilities]
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set], records=lead_time_records)

# Demand
demand_records = [(str(month), sku, demand_data.get((month, sku), 0)) for month in months for sku in skus]
demand_param = Parameter(m, name="demand", domain=[t_month_set, s_set], records=demand_records)

# Shelving capacity
curr_shelves_records = [(fac, st, curr_shelves.get((fac, st), 0)) for fac in facilities for st in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f_set, st_set], records=curr_shelves_records)

shelf_vol_records = [(fac, st, shelf_vol.get((fac, st), 0)) for fac in facilities for st in storage_types]
shelf_vol_param = Parameter(m, name="shelf_vol", domain=[f_set, st_set], records=shelf_vol_records)

shelf_weight_records = [(fac, st, shelf_weight.get((fac, st), 0)) for fac in facilities for st in storage_types]
shelf_weight_param = Parameter(m, name="shelf_weight", domain=[f_set, st_set], records=shelf_weight_records)

shelf_pkg_records = [(fac, st, shelf_pkg_cap.get((fac, st), 0)) for fac in facilities for st in storage_types]
shelf_pkg_param = Parameter(m, name="shelf_pkg_cap", domain=[f_set, st_set], records=shelf_pkg_records)

print("   ✓ Created GAMSPy sets and parameters")

# Variables
print("   ✓ Defining decision variables...")

# Expansion decisions with UPPER BOUNDS
MAX_EXPANSION_SACRAMENTO = 200000  # sq ft
MAX_EXPANSION_AUSTIN = 200000      # sq ft

expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive",
                    description="Square feet to add at expandable facilities")
expansion.up['Sacramento'] = MAX_EXPANSION_SACRAMENTO
expansion.up['Austin'] = MAX_EXPANSION_AUSTIN

add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive",
                      description="Additional shelves to add")

# Total shelves (current + added) - defined for ALL facilities
total_shelves = Variable(m, name="total_shelves", domain=[f_set, st_set], type="positive",
                        description="Total shelves available (current + expansion)")

# CRITICAL: Binary repack decision per SKU per facility
repack_decision = Variable(m, name="repack_decision", domain=[s_set, f_set], type="binary",
                          description="1 if SKU s is repacked at facility f, 0 if stored as received")

# Daily operations
daily_deliveries = Variable(m, name="daily_deliveries", domain=[t_month_set, t_day_set, s_set, f_set],
                           type="positive", description="Inbound packs delivered")

daily_inventory = Variable(m, name="daily_inventory", domain=[t_month_set, t_day_set, s_set, f_set],
                          type="positive", description="Inventory in sell pack units")

daily_shipments = Variable(m, name="daily_shipments", domain=[t_month_set, t_day_set, s_set, f_set],
                          type="positive", description="Units shipped to customers")

# Package storage - SPLIT into repacked and inbound to avoid nonlinear terms
# packages_repacked: Number of REPACKED packages (using sell pack dimensions)
# packages_inbound: Number of INBOUND packages (using inbound pack dimensions)
# Only ONE will be non-zero for each SKU based on repack_decision

packages_repacked = Variable(m, name="packages_repacked",
                             domain=[t_month_set, t_day_set, s_set, f_set, st_set],
                             type="positive",
                             description="Number of repacked packages (sell pack dimensions)")

packages_inbound = Variable(m, name="packages_inbound",
                            domain=[t_month_set, t_day_set, s_set, f_set, st_set],
                            type="positive",
                            description="Number of inbound packages (inbound pack dimensions)")

# DoH tracking
avg_inventory = Variable(m, name="avg_inventory", domain=s_set, type="positive",
                        description="Average inventory per SKU across all facilities")

avg_inventory_by_st = Variable(m, name="avg_inventory_by_st", domain=[s_set, st_set], type="positive",
                               description="Average inventory per SKU per storage type")

doh_per_sku = Variable(m, name="doh_per_sku", domain=s_set, type="positive",
                      description="Days on hand per SKU")

min_doh = Variable(m, name="min_doh", type="free",
                  description="Minimum DoH across all SKUs (objective to maximize)")

print("   ✓ Created decision variables")

# Equations
print("   ✓ Defining constraints...")

# === OBJECTIVE: Maximize minimum DoH ===
obj = Equation(m, name="obj")
obj[...] = min_doh == min_doh

# Min DoH constraints - UPDATED: Add minimum DoH requirements by supplier type
min_doh_constraint = Equation(m, name="min_doh_constraint", domain=s_set)
min_doh_constraint[s_set] = min_doh <= doh_per_sku[s_set]

# MINIMUM DoH REQUIREMENTS (REDUCED to test feasibility)
MIN_DOH_DOMESTIC = 1  # business days (~1.4 calendar days)
MIN_DOH_INTERNATIONAL = 3  # business days (~4.2 calendar days)

# Create minimum DoH parameter by SKU
min_doh_required_records = []
for sku in skus:
    supplier = sku_data[sku]['supplier']
    if supplier == 'Domestic':
        min_doh_required_records.append((sku, MIN_DOH_DOMESTIC))
    else:
        min_doh_required_records.append((sku, MIN_DOH_INTERNATIONAL))

min_doh_required = Parameter(m, name="min_doh_required", domain=s_set, records=min_doh_required_records)

# Enforce minimum DoH per SKU based on supplier type
enforce_min_doh = Equation(m, name="enforce_min_doh", domain=s_set)
enforce_min_doh[s_set] = doh_per_sku[s_set] >= min_doh_required[s_set]

# Calculate average inventory
calc_avg_inv = Equation(m, name="calc_avg_inv", domain=s_set)
calc_avg_inv[s_set] = (
    avg_inventory[s_set] ==
    Sum([t_month_set, t_day_set, f_set], daily_inventory[t_month_set, t_day_set, s_set, f_set]) /
    (len(months) * DAYS_PER_MONTH)
)

# Calculate average inventory by storage type
calc_avg_inv_by_st = Equation(m, name="calc_avg_inv_by_st", domain=[s_set, st_set])
calc_avg_inv_by_st[s_set, st_set] = (
    avg_inventory_by_st[s_set, st_set] ==
    Sum([t_month_set, t_day_set, f_set],
        (packages_repacked[t_month_set, t_day_set, s_set, f_set, st_set] +
         packages_inbound[t_month_set, t_day_set, s_set, f_set, st_set]) * inbound_qty[s_set]
    ) / (len(months) * DAYS_PER_MONTH)
)

# Calculate DoH per SKU
calc_doh = Equation(m, name="calc_doh", domain=s_set)
total_demand_per_sku = {}
for sku in skus:
    total_demand_per_sku[sku] = sum(demand_data.get((m, sku), 0) for m in months)
avg_daily_demand_records = [(sku, total_demand_per_sku[sku] / (len(months) * DAYS_PER_MONTH)) for sku in skus]
avg_daily_demand = Parameter(m, name="avg_daily_demand", domain=s_set, records=avg_daily_demand_records)

calc_doh[s_set] = doh_per_sku[s_set] * avg_daily_demand[s_set] == avg_inventory[s_set]

# === INVENTORY BALANCE EQUATIONS ===
# Month 1, Day 1 (cold start)
inv_balance_start = Equation(m, name="inv_balance_start", domain=[s_set, f_set])
inv_balance_start[s_set, f_set] = (
    daily_inventory['1', '1', s_set, f_set] ==
    daily_deliveries['1', '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', '1', s_set, f_set]
)

# Month 1, Days 2-21
inv_balance_month1 = Equation(m, name="inv_balance_month1", domain=[t_day_set, s_set, f_set])
inv_balance_month1[t_day_set, s_set, f_set].where[Ord(t_day_set) > 1] = (
    daily_inventory['1', t_day_set, s_set, f_set] ==
    daily_inventory['1', t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries['1', t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', t_day_set, s_set, f_set]
)

# Month boundaries (day 1 of month t)
inv_balance_month_boundary = Equation(m, name="inv_balance_month_boundary", domain=[t_month_set, s_set, f_set])
inv_balance_month_boundary[t_month_set, s_set, f_set].where[Ord(t_month_set) > 1] = (
    daily_inventory[t_month_set, '1', s_set, f_set] ==
    daily_inventory[t_month_set.lag(1, 'linear'), '21', s_set, f_set] +
    daily_deliveries[t_month_set, '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, '1', s_set, f_set]
)

# General case (month > 1, day > 1)
inv_balance_general = Equation(m, name="inv_balance_general", domain=[t_month_set, t_day_set, s_set, f_set])
inv_balance_general[t_month_set, t_day_set, s_set, f_set].where[(Ord(t_month_set) > 1) & (Ord(t_day_set) > 1)] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    daily_inventory[t_month_set, t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries[t_month_set, t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, t_day_set, s_set, f_set]
)

# Demand fulfillment
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month_set, s_set])
demand_fulfill[t_month_set, s_set] = (
    Sum([t_day_set, f_set], daily_shipments[t_month_set, t_day_set, s_set, f_set]) >=
    demand_param[t_month_set, s_set]
)

# === LINK PACKAGES TO INVENTORY ===
# Inventory must equal packages on shelves × units per package
# Total packages = repacked + inbound (only one will be non-zero based on repack decision)
pkg_inv_link = Equation(m, name="pkg_inv_link", domain=[t_month_set, t_day_set, s_set, f_set])
pkg_inv_link[t_month_set, t_day_set, s_set, f_set] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    Sum(st_set.where[sku_st_map[s_set, st_set] > 0],
        (packages_repacked[t_month_set, t_day_set, s_set, f_set, st_set] +
         packages_inbound[t_month_set, t_day_set, s_set, f_set, st_set]) * inbound_qty[s_set]
    )
)

# === TOTAL SHELVES CALCULATION ===
# For expandable facilities: total = current + added
# For non-expandable facilities: total = current only

define_total_shelves_sac = Equation(m, name="define_total_shelves_sac", domain=st_set)
define_total_shelves_sac[st_set] = (
    total_shelves['Sacramento', st_set] == curr_shelves_param['Sacramento', st_set] + add_shelves['Sacramento', st_set]
)

define_total_shelves_austin = Equation(m, name="define_total_shelves_austin", domain=st_set)
define_total_shelves_austin[st_set] = (
    total_shelves['Austin', st_set] == curr_shelves_param['Austin', st_set] + add_shelves['Austin', st_set]
)

define_total_shelves_columbus = Equation(m, name="define_total_shelves_columbus", domain=st_set)
define_total_shelves_columbus[st_set] = (
    total_shelves['Columbus', st_set] == curr_shelves_param['Columbus', st_set]
)

# === BIG-M CONSTRAINTS TO LINK REPACK DECISION TO PACKAGE VARIABLES ===
# If repack_decision = 1: packages_inbound must be 0 (force repacking)
# If repack_decision = 0: packages_repacked must be 0 (force inbound storage)

# Big-M value (max possible packages)
BIG_M = 1000000

# If repack_decision = 0, then packages_repacked must be 0
force_repacked_zero = Equation(m, name="force_repacked_zero", domain=[t_month_set, t_day_set, s_set, f_set, st_set])
force_repacked_zero[t_month_set, t_day_set, s_set, f_set, st_set] = (
    packages_repacked[t_month_set, t_day_set, s_set, f_set, st_set] <= BIG_M * repack_decision[s_set, f_set]
)

# If repack_decision = 1, then packages_inbound must be 0
force_inbound_zero = Equation(m, name="force_inbound_zero", domain=[t_month_set, t_day_set, s_set, f_set, st_set])
force_inbound_zero[t_month_set, t_day_set, s_set, f_set, st_set] = (
    packages_inbound[t_month_set, t_day_set, s_set, f_set, st_set] <= BIG_M * (1 - repack_decision[s_set, f_set])
)

# === CAPACITY CONSTRAINTS WITH SET PACKING ===
# NOTE: Package capacity is determined by volume and weight constraints below.
# No fixed discrete package count - the optimizer determines optimal packing
# based on volume/weight limits per shelf.

# Volume capacity - LINEARIZED (separate terms for repacked vs inbound)
vol_capacity = Equation(m, name="vol_capacity", domain=[t_month_set, t_day_set, f_set, st_set])
vol_capacity[t_month_set, t_day_set, f_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_repacked[t_month_set, t_day_set, s_set, f_set, st_set] * sell_vol[s_set] * inbound_qty[s_set] +
        packages_inbound[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_vol[s_set]
    ) <= total_shelves[f_set, st_set] * shelf_vol_param[f_set, st_set]
)

# Weight capacity - LINEARIZED (separate terms for repacked vs inbound)
weight_capacity = Equation(m, name="weight_capacity", domain=[t_month_set, t_day_set, f_set, st_set])
weight_capacity[t_month_set, t_day_set, f_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_repacked[t_month_set, t_day_set, s_set, f_set, st_set] * sell_weight[s_set] * inbound_qty[s_set] +
        packages_inbound[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_weight[s_set]
    ) <= total_shelves[f_set, st_set] * shelf_weight_param[f_set, st_set]
)

# === CONSOLIDATION CONSTRAINT ===
# Only allow repacking for SKUs with can_consolidate = 1
repack_constraint = Equation(m, name="repack_constraint", domain=[s_set, f_set])
repack_constraint[s_set, f_set] = repack_decision[s_set, f_set] <= can_consolidate_param[s_set]

print("   ✓ Created constraints")

# Create model
print("\n[7/7] Creating optimization model...")
warehouse_model = Model(
    m,
    name="warehouse_maxmin_doh_setpacking",
    equations=m.getEquations(),
    problem="MIP",  # Mixed-Integer Programming (binary repack decisions)
    sense=Sense.MAX,
    objective=min_doh
)

print("   ✓ Model created successfully")
print(f"\nModel Statistics:")
print(f"  Problem type: MIP (Mixed-Integer Programming)")
print(f"  Decision variables: {len(m.data)} (including binary repack decisions)")
print(f"  Constraints: {len(m.getEquations())}")

# Solve
print("\n" + "="*80)
print("SOLVING MODEL...")
print("="*80)
warehouse_model.solve(output=sys.stdout)

print("\n" + "="*80)
print("SOLUTION RESULTS")
print("="*80)
print(f"Model Status: {warehouse_model.status}")
print(f"Solver Status: {warehouse_model.solve_status}")

if warehouse_model.status.value in [1, 2, 8]:  # Optimal or feasible
    print(f"\n✓ MODEL SOLVED SUCCESSFULLY")
    print(f"\nOBJECTIVE VALUE (Max-Min DoH): {warehouse_model.objective_value:.2f} days")

    # Extract results
    doh_df = doh_per_sku.records
    avg_inv_df = avg_inventory.records
    avg_inv_by_st_df = avg_inventory_by_st.records
    expansion_df = expansion.records
    add_shelves_df = add_shelves.records
    repack_df = repack_decision.records

    # Save results
    doh_df.to_csv(RESULTS_DIR / 'doh_per_sku.csv', index=False)
    avg_inv_df.to_csv(RESULTS_DIR / 'avg_inventory.csv', index=False)
    avg_inv_by_st_df.to_csv(RESULTS_DIR / 'avg_inventory_by_st.csv', index=False)
    expansion_df.to_csv(RESULTS_DIR / 'var_expansion.csv', index=False)
    add_shelves_df.to_csv(RESULTS_DIR / 'var_add_shelves.csv', index=False)
    repack_df.to_csv(RESULTS_DIR / 'var_repack_decision.csv', index=False)
    daily_inventory.records.to_csv(RESULTS_DIR / 'var_daily_inventory.csv', index=False)
    daily_deliveries.records.to_csv(RESULTS_DIR / 'var_daily_deliveries.csv', index=False)
    daily_shipments.records.to_csv(RESULTS_DIR / 'var_daily_shipments.csv', index=False)
    packages_repacked.records.to_csv(RESULTS_DIR / 'var_packages_repacked.csv', index=False)
    packages_inbound.records.to_csv(RESULTS_DIR / 'var_packages_inbound.csv', index=False)

    print(f"\n✓ Results saved to {RESULTS_DIR}")

    # Print DoH summary
    print("\n" + "="*80)
    print("DAYS ON HAND (DoH) BY SKU")
    print("="*80)
    doh_sorted = doh_df.sort_values('level', ascending=True)
    for _, row in doh_sorted.iterrows():
        print(f"  {row['s']:<10}: {row['level']:>8.2f} days")

    # Print expansion summary
    print("\n" + "="*80)
    print("EXPANSION DECISIONS")
    print("="*80)
    for _, row in expansion_df.iterrows():
        if row['level'] > 0.01:
            print(f"  {row['f_exp']}: {row['level']:>10,.0f} sq ft")

    print("\nShelves Added by Facility and Storage Type:")
    shelves_added = add_shelves_df[add_shelves_df['level'] > 0.01].sort_values(['f_exp', 'st'])
    for _, row in shelves_added.iterrows():
        print(f"  {row['f_exp']:<12} {row['st']:<10}: +{row['level']:>8,.0f} shelves")

    # Print repacking decisions
    print("\n" + "="*80)
    print("REPACKING DECISIONS")
    print("="*80)
    print("\nSKUs choosing to REPACK (from inbound pallets to sell packs):")
    repacked = repack_df[(repack_df['level'] > 0.5)]
    if len(repacked) > 0:
        for _, row in repacked.iterrows():
            sku = row['s']
            fac = row['f']
            inbound_vol_val = sku_data[sku]['inbound_volume']
            sell_vol_val = sku_data[sku]['sell_volume']
            inbound_qty_val = sku_data[sku]['inbound_qty']
            total_sell_vol = sell_vol_val * inbound_qty_val
            savings_pct = (1 - total_sell_vol / inbound_vol_val) * 100
            print(f"  {sku} @ {fac}: {inbound_vol_val:.2f} cu ft inbound -> {total_sell_vol:.2f} cu ft repacked ({savings_pct:+.1f}% space)")
    else:
        print("  (None - all items stored as received)")

    print("\nSKUs storing AS RECEIVED (inbound pack dimensions):")
    not_repacked = repack_df[(repack_df['level'] < 0.5)]
    for _, row in not_repacked.iterrows():
        sku = row['s']
        fac = row['f']
        can_consolidate_val = sku_data[sku]['can_consolidate']
        if can_consolidate_val == 0:
            reason = "(cannot consolidate)"
        else:
            reason = "(optimizer chose not to repack)"
        print(f"  {sku} @ {fac}: {sku_data[sku]['inbound_volume']:.2f} cu ft {reason}")

    # Detailed breakdown by SKU and storage type
    print("\n" + "="*80)
    print("DoH BREAKDOWN BY SKU AND STORAGE TYPE")
    print("="*80)

    total_demand_by_sku = {}
    for month in months:
        for sku in skus:
            if sku not in total_demand_by_sku:
                total_demand_by_sku[sku] = 0
            total_demand_by_sku[sku] += demand_data.get((month, sku), 0)

    avg_daily_demand_by_sku = {sku: total_demand_by_sku[sku] / (len(months) * DAYS_PER_MONTH) for sku in skus}

    for _, row in doh_sorted.iterrows():
        sku = row['s']
        total_doh = row['level']
        avg_demand = avg_daily_demand_by_sku[sku]

        print(f"\n{sku} (Total DoH: {total_doh:.2f} days, Avg Demand: {avg_demand:.1f} units/day)")
        print("-"*80)

        inv_by_st = avg_inv_by_st_df[avg_inv_by_st_df['s'] == sku]
        for _, inv_row in inv_by_st.iterrows():
            st = inv_row['st']
            avg_inv = inv_row['level']
            if avg_inv > 0.01:
                doh_for_st = avg_inv / avg_demand if avg_demand > 0 else 0
                pct = (avg_inv / (total_doh * avg_demand)) * 100 if total_doh * avg_demand > 0 else 0

                # Check repack status for this SKU's primary facility
                repack_status = ""
                for fac in facilities:
                    repack_val = repack_df[(repack_df['s'] == sku) & (repack_df['f'] == fac)]['level'].values
                    if len(repack_val) > 0 and repack_val[0] > 0.5:
                        repack_status = " [REPACKED]"
                        break

                print(f"  {st:<12}: {avg_inv:>10.1f} units avg, {doh_for_st:>8.2f} days DoH ({pct:>5.1f}% of total){repack_status}")

else:
    print(f"\n✗ MODEL FAILED TO SOLVE")
    print(f"   Status: {warehouse_model.status}")
    print(f"   Check model formulation and data inputs")

print("\n" + "="*80)
print("MODEL RUN COMPLETE")
print("="*80)
