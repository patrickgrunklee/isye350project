"""
InkCredible Supplies - Model 0.2a-MaxMin: Maximize MINIMUM Days-on-Hand
========================================================================

This model MAXIMIZES the MINIMUM DoH across all SKUs (max-min objective).
This ensures all SKUs get some inventory and reveals which storage types
are the true capacity bottlenecks.

OBJECTIVE: Maximize the minimum DoH across all 18 SKUs

This approach ensures balanced inventory across all SKUs rather than
gaming the system by holding massive amounts of low-demand items.

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
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Model0.2\MaxMinDoH")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MONTHS = 120
DAYS_PER_MONTH = 21
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH

USE_FULL_HORIZON = True
TEST_MONTHS = 3
TEST_DAYS = TEST_MONTHS * DAYS_PER_MONTH if not USE_FULL_HORIZON else TOTAL_DAYS

WORKING_DAYS_PER_MONTH = 21

print("="*80)
print("MODEL 0.2a-MaxMin: MAXIMIZE MINIMUM DAYS-ON-HAND")
print("="*80)
print(f"\nConfiguration:")
print(f"  Time horizon: {TEST_MONTHS if not USE_FULL_HORIZON else MONTHS} months ({TEST_DAYS} business days)")
print(f"  Objective: MAXIMIZE the MINIMUM DoH across all 18 SKUs")
print(f"  This ensures all SKUs get inventory and reveals capacity bottlenecks")
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

# Parse SKU details
print("\n[3/7] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])
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

print(f"   ✓ Processed {len(sku_data)} SKUs")

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

# Load lead times
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

print(f"   ✓ Loaded lead times")

# Parse shelving data
print("\n[5/7] Processing shelving data...")
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
        shelf_volume_cap[(fac, st)] = 1.728
        shelf_package_cap[(fac, st)] = 100

avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves
    else:
        avg_sqft_per_shelf[(fac, st)] = 50.0

print(f"   ✓ Loaded shelving data")

# Create GAMSPy model
print("\n[6/7] Building GAMSPy model...")
m = Container()

s_set = Set(m, name="s", records=skus)
f_set = Set(m, name="f", records=facilities)
f_exp_set = Set(m, name="f_exp", domain=f_set, records=expandable_facilities)
st_set = Set(m, name="st", records=storage_types)
sup_set = Set(m, name="sup", records=supplier_types)
t_month_set = Set(m, name="t_month", records=[str(m) for m in months])
t_day_set = Set(m, name="t_day", records=[str(d) for d in days])

# Parameters
demand_records = [(str(month), sku, demand_data.get((month, sku), 0)) for month in months for sku in skus]
demand_param = Parameter(m, name="demand", domain=[t_month_set, s_set], records=demand_records)

daily_demand_records = [(str(month), sku, demand_data.get((month, sku), 0) / DAYS_PER_MONTH) for month in months for sku in skus]
daily_demand_param = Parameter(m, name="daily_demand", domain=[t_month_set, s_set], records=daily_demand_records)

sell_vol_records = [(sku, sku_data[sku]['sell_volume']) for sku in skus]
sell_vol = Parameter(m, name="sell_volume", domain=s_set, records=sell_vol_records)

sell_wt_records = [(sku, sku_data[sku]['sell_weight']) for sku in skus]
sell_wt = Parameter(m, name="sell_weight", domain=s_set, records=sell_wt_records)

inbound_vol_records = [(sku, sku_data[sku]['inbound_volume']) for sku in skus]
inbound_vol = Parameter(m, name="inbound_volume", domain=s_set, records=inbound_vol_records)

inbound_wt_records = [(sku, sku_data[sku]['inbound_weight']) for sku in skus]
inbound_wt = Parameter(m, name="inbound_weight", domain=s_set, records=inbound_wt_records)

inbound_qty_records = [(sku, sku_data[sku]['inbound_qty']) for sku in skus]
inbound_qty = Parameter(m, name="inbound_qty", domain=s_set, records=inbound_qty_records)

can_consolidate_records = [(sku, sku_data[sku]['can_consolidate']) for sku in skus]
can_consolidate = Parameter(m, name="can_consolidate", domain=s_set, records=can_consolidate_records)

# SKU to storage type mapping
# SPECIAL: Allow SKUD1 and SKUC1 to use BOTH Racking and Pallet
sku_st_records = []
for sku in skus:
    primary_st = sku_data[sku]['storage_type']
    sku_st_records.append((sku, primary_st, 1))

    # Allow SKUD1 and SKUC1 to ALSO use the alternative storage type
    if sku == 'SKUD1' and primary_st == 'Racking':
        sku_st_records.append((sku, 'Pallet', 1))  # Can also use Pallet
    elif sku == 'SKUD1' and primary_st == 'Pallet':
        sku_st_records.append((sku, 'Racking', 1))  # Can also use Racking

    if sku == 'SKUC1' and primary_st == 'Racking':
        sku_st_records.append((sku, 'Pallet', 1))  # Can also use Pallet
    elif sku == 'SKUC1' and primary_st == 'Pallet':
        sku_st_records.append((sku, 'Racking', 1))  # Can also use Racking

sku_st_map = Parameter(m, name="sku_st_map", domain=[s_set, st_set], records=sku_st_records)

sku_sup_records = []
for sku in domestic_skus:
    sku_sup_records.append((sku, 'Domestic', 1))
for sku in international_skus:
    sku_sup_records.append((sku, 'International', 1))
sku_sup_map = Parameter(m, name="sku_sup_map", domain=[s_set, sup_set], records=sku_sup_records)

lead_time_records = [(sku, fac, lead_times_business.get((sku, fac), 5)) for sku in skus for fac in facilities]
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set], records=lead_time_records)

curr_shelves_records = [(fac, st, current_shelves.get((fac, st), 0)) for fac in facilities for st in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f_set, st_set], records=curr_shelves_records)

shelf_vol_records = [(fac, st, shelf_volume_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_vol_param = Parameter(m, name="shelf_volume", domain=[f_set, st_set], records=shelf_vol_records)

shelf_wt_records = [(fac, st, shelf_weight_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_wt_param = Parameter(m, name="shelf_weight", domain=[f_set, st_set], records=shelf_wt_records)

shelf_pkg_records = [(fac, st, shelf_package_cap.get((fac, st), 1)) for fac in facilities for st in storage_types]
shelf_pkg_param = Parameter(m, name="shelf_packages", domain=[f_set, st_set], records=shelf_pkg_records)

expansion_cost_records = [('Sacramento', 2.0), ('Austin', 1.5)]
expansion_cost_param = Parameter(m, name="expansion_cost", domain=f_exp_set, records=expansion_cost_records)

sac_tier2_cost = Parameter(m, name="sac_tier2_cost", records=2.0)

sqft_records = [(fac, st, avg_sqft_per_shelf.get((fac, st), 50)) for fac in expandable_facilities for st in storage_types]
sqft_param = Parameter(m, name="sqft_per_shelf", domain=[f_exp_set, st_set], records=sqft_records)

print("   ✓ Parameters created")

# Variables
expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive")
sac_tier1 = Variable(m, name="sac_tier1", type="positive")
sac_tier2 = Variable(m, name="sac_tier2", type="positive")

daily_inventory = Variable(m, name="daily_inventory", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
daily_deliveries = Variable(m, name="daily_deliveries", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
daily_shipments = Variable(m, name="daily_shipments", domain=[t_month_set, t_day_set, s_set, f_set], type="positive")
packages_on_shelf = Variable(m, name="packages_on_shelf", domain=[t_month_set, t_day_set, s_set, f_set, st_set], type="positive")

# DoH variables
avg_inventory = Variable(m, name="avg_inventory", domain=s_set, type="positive")
avg_inventory_by_st = Variable(m, name="avg_inventory_by_st", domain=[s_set, st_set], type="positive",
                               description="Average inventory per SKU per storage type")
doh_per_sku = Variable(m, name="doh_per_sku", domain=s_set, type="positive")
min_doh = Variable(m, name="min_doh", type="free", description="Minimum DoH across all SKUs")

print("   ✓ Variables created")

# Constraints
print("   ✓ Creating constraints...")

# Calculate average inventory per SKU per storage type
calc_avg_inv_by_st = Equation(m, name="calc_avg_inv_by_st", domain=[s_set, st_set])
calc_avg_inv_by_st[s_set, st_set] = (
    avg_inventory_by_st[s_set, st_set] ==
    Sum([t_month_set, t_day_set, f_set],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_qty[s_set]
    ) / (len(months) * DAYS_PER_MONTH)
)

# Calculate total average inventory per SKU (sum across all storage types)
calc_avg_inv = Equation(m, name="calc_avg_inv", domain=s_set)
calc_avg_inv[s_set] = (
    avg_inventory[s_set] == Sum([t_month_set, t_day_set, f_set],
                                 daily_inventory[t_month_set, t_day_set, s_set, f_set]) / (len(months) * DAYS_PER_MONTH)
)

# Calculate DoH per SKU
calc_doh = Equation(m, name="calc_doh", domain=s_set)
calc_doh[s_set] = (
    doh_per_sku[s_set] * Sum(t_month_set, daily_demand_param[t_month_set, s_set]) ==
    avg_inventory[s_set] * (len(months) * DAYS_PER_MONTH)
)

# Min DoH constraint: min_doh <= doh_per_sku for all SKUs
min_doh_constraint = Equation(m, name="min_doh_constraint", domain=s_set)
min_doh_constraint[s_set] = min_doh <= doh_per_sku[s_set]

# Expansion limits
sac_tier_split = Equation(m, name="sac_tier_split")
sac_tier_split[...] = expansion['Sacramento'] == sac_tier1 + sac_tier2

sac_tier1_limit = Equation(m, name="sac_tier1_limit")
sac_tier1_limit[...] = sac_tier1 <= 100000

sac_tier2_limit = Equation(m, name="sac_tier2_limit")
sac_tier2_limit[...] = sac_tier2 <= 150000

austin_limit = Equation(m, name="austin_limit")
austin_limit[...] = expansion['Austin'] <= 200000

expansion_calc = Equation(m, name="expansion_calc", domain=f_exp_set)
expansion_calc[f_exp_set] = expansion[f_exp_set] == Sum(st_set, add_shelves[f_exp_set, st_set] * sqft_param[f_exp_set, st_set])

# Inventory balance
inv_balance_first = Equation(m, name="inv_balance_first", domain=[s_set, f_set])
inv_balance_first[s_set, f_set] = (
    daily_inventory['1', '1', s_set, f_set] ==
    daily_deliveries['1', '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', '1', s_set, f_set]
)

inv_balance_month1 = Equation(m, name="inv_balance_month1", domain=[t_day_set, s_set, f_set])
inv_balance_month1[t_day_set, s_set, f_set].where[Ord(t_day_set) > 1] = (
    daily_inventory['1', t_day_set, s_set, f_set] ==
    daily_inventory['1', t_day_set.lag(1, 'linear'), s_set, f_set] +
    daily_deliveries['1', t_day_set, s_set, f_set] * inbound_qty[s_set] -
    daily_shipments['1', t_day_set, s_set, f_set]
)

inv_balance_month_boundary = Equation(m, name="inv_balance_month_boundary", domain=[t_month_set, s_set, f_set])
inv_balance_month_boundary[t_month_set, s_set, f_set].where[Ord(t_month_set) > 1] = (
    daily_inventory[t_month_set, '1', s_set, f_set] ==
    daily_inventory[t_month_set.lag(1, 'linear'), '21', s_set, f_set] +
    daily_deliveries[t_month_set, '1', s_set, f_set] * inbound_qty[s_set] -
    daily_shipments[t_month_set, '1', s_set, f_set]
)

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

# Link packages to inventory
pkg_inv_link = Equation(m, name="pkg_inv_link", domain=[t_month_set, t_day_set, s_set, f_set])
pkg_inv_link[t_month_set, t_day_set, s_set, f_set] = (
    daily_inventory[t_month_set, t_day_set, s_set, f_set] ==
    Sum(st_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_set, st_set] * inbound_qty[s_set]
    )
)

# Capacity constraints
pkg_capacity_exp = Equation(m, name="pkg_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
pkg_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_pkg_param[f_exp_set, st_set]
)

pkg_capacity_fixed = Equation(m, name="pkg_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
pkg_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_pkg_param['Columbus', st_set]
)

vol_capacity_exp = Equation(m, name="vol_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
vol_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_vol[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_vol_param[f_exp_set, st_set]
)

vol_capacity_fixed = Equation(m, name="vol_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
vol_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_vol[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_vol_param['Columbus', st_set]
)

wt_capacity_exp = Equation(m, name="wt_capacity_exp", domain=[t_month_set, t_day_set, f_exp_set, st_set])
wt_capacity_exp[t_month_set, t_day_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, f_exp_set, st_set] * inbound_wt[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_wt_param[f_exp_set, st_set]
)

wt_capacity_fixed = Equation(m, name="wt_capacity_fixed", domain=[t_month_set, t_day_set, st_set])
wt_capacity_fixed[t_month_set, t_day_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, t_day_set, s_set, 'Columbus', st_set] * inbound_wt[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_wt_param['Columbus', st_set]
)

print("   ✓ Constraints created")

# Solve
print("\n[7/7] Solving model...")
print("="*80)

warehouse_model = Model(
    m,
    name="warehouse_maxmin_doh",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MAX,
    objective=min_doh
)

print("\nSolving...")
warehouse_model.solve()

print("="*80)
print(f"\nModel Status: {warehouse_model.status}")
print(f"Objective Value (Minimum DoH): {warehouse_model.objective_value:,.2f} days")
print("="*80)

# Extract results
print("\n[8/8] Extracting results...")

model_status_str = str(warehouse_model.status)
is_optimal = 'Optimal' in model_status_str

if is_optimal:
    expansion_df = expansion.records
    expansion_df.to_csv(RESULTS_DIR / "var_expansion.csv", index=False)

    add_shelves_df = add_shelves.records
    add_shelves_df.to_csv(RESULTS_DIR / "var_add_shelves.csv", index=False)

    doh_df = doh_per_sku.records
    doh_df.to_csv(RESULTS_DIR / "var_doh_per_sku.csv", index=False)

    # Average inventory by storage type
    avg_inv_by_st_df = avg_inventory_by_st.records
    avg_inv_by_st_df.to_csv(RESULTS_DIR / "var_avg_inventory_by_storage_type.csv", index=False)

    daily_inventory_df = daily_inventory.records
    daily_inventory_df.to_csv(RESULTS_DIR / "var_daily_inventory.csv", index=False)

    # Packages on shelf
    packages_df = packages_on_shelf.records
    packages_df.to_csv(RESULTS_DIR / "var_packages_on_shelf.csv", index=False)

    print("   ✓ Results saved")

    # Create detailed DoH breakdown report
    print("\nDoH BREAKDOWN BY SKU AND STORAGE TYPE:")
    print("="*100)

    # Get demand data for calculations
    total_demand_by_sku = {}
    for month in months:
        for sku in skus:
            if sku not in total_demand_by_sku:
                total_demand_by_sku[sku] = 0
            total_demand_by_sku[sku] += demand_data.get((month, sku), 0)

    avg_daily_demand_by_sku = {sku: total_demand_by_sku[sku] / (len(months) * DAYS_PER_MONTH) for sku in skus}

    # Print breakdown
    for _, row in doh_df.iterrows():
        sku = row['s']
        total_doh = row['level']
        avg_demand = avg_daily_demand_by_sku[sku]

        print(f"\n{sku} (Total DoH: {total_doh:.2f} days, Avg Demand: {avg_demand:.1f} units/day)")
        print("-"*100)

        # Get storage type breakdown
        inv_by_st = avg_inv_by_st_df[avg_inv_by_st_df['s'] == sku]
        for _, inv_row in inv_by_st.iterrows():
            st = inv_row['st']
            avg_inv = inv_row['level']
            if avg_inv > 0.01:  # Only show non-zero inventory
                doh_for_st = avg_inv / avg_demand if avg_demand > 0 else 0
                pct = (avg_inv / (total_doh * avg_demand)) * 100 if total_doh * avg_demand > 0 else 0
                print(f"  {st:<12}: {avg_inv:>10.1f} units avg inventory, {doh_for_st:>8.2f} days DoH ({pct:>5.1f}% of total)")

    print("\n" + "="*100)

    print("\nEXPANSION BY STORAGE TYPE:")
    print("-"*80)
    for _, row in add_shelves_df[add_shelves_df['level'] > 0].iterrows():
        print(f"  {row['f_exp']:<15} {row['st']:<12}: {row['level']:>8.0f} shelves")

else:
    print(f"\n   ⚠ Model unsolved - Status: {warehouse_model.status}")

print("\n" + "="*80)
print("MODEL 0.2a-MaxMin COMPLETE")
print("="*80)
print(f"\nResults: {RESULTS_DIR}")
if is_optimal:
    print(f"Minimum DoH: {warehouse_model.objective_value:,.2f} days")
    print("\nThis shows the balanced DoH achievable across ALL SKUs")
    print("Capacity bottlenecks revealed by which storage types need expansion")
print("="*80)
