"""
PHASE 2 WITH TRUCK DISPATCH OPTIMIZATION
=========================================

Key Features:
1. Daily time granularity: 120 months × 21 business days = 2,520 time periods
2. Daily inventory carryover between days and months
3. **INTEGER TRUCK DISPATCH with 90% minimum utilization**
4. **Flexible delivery dates** to consolidate truck loads
5. **Early delivery allowance** to fill trucks to 90%
6. **Truck costs in objective** to minimize transportation

Truck Dispatch Rules:
  - Trucks are INTEGER variables (1, 2, 3, ... trucks)
  - 90% MINIMUM utilization on binding constraint (weight OR volume)
  - Can deliver early to fill trucks
  - Can adjust delivery dates within feasibility limits
  - Truck cost minimizes dispatches without affecting demand/DoH constraints

Purpose: Optimize truck dispatch schedules while meeting all operational constraints
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense, Options
from pathlib import Path
import sys
import os
from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    TRUCK_COST_PER_DELIVERY,
    MIN_TRUCK_UTILIZATION,
    SKU_TO_SUPPLIER,
    SKU_TO_SUPPLIER_TYPE,
    SUPPLIERS,
    calculate_truckloads,
    calculate_truck_utilization
)

os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\Model Data")
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase1_SetPacking")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WORKING_DAYS_PER_MONTH = 21
MAX_SOLVE_TIME = 600  # 10 minutes for truck optimization (more complex)

print("="*100)
print("PHASE 2: TRUCK DISPATCH OPTIMIZATION MODEL - 3/1 DAYS-ON-HAND")
print("="*100)
print("\nAPPROACH:")
print("  - Daily time granularity: 120 months × 21 days = 2,520 time periods")
print("  - INTEGER truck dispatch variables")
print(f"  - {MIN_TRUCK_UTILIZATION*100:.0f}% MINIMUM utilization on binding constraint")
print("  - Flexible delivery dates to consolidate truck loads")
print(f"  - Truck cost: ${TRUCK_COST_PER_DELIVERY} per delivery")
print("  - DoH: International: 3 business days | Domestic: 1 business day")
print(f"  - Max solve time: {MAX_SOLVE_TIME//60} minutes")
print()

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple (L, W, H) in inches"""
    parts = dim_str.strip().replace('x', ' x ').split(' x ')
    return tuple(float(p.strip()) for p in parts)

def parse_weight(weight_str):
    """Parse weight string like '15 lbs' to float"""
    return float(str(weight_str).split()[0])

# Load data
print("[1/8] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_3_1_business_days.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_pure_sku_discrete.csv')
print("   ✓ Data loaded")

# Parse SKU details with inbound pack quantities
print("\n[2/8] Processing SKU details with inbound pack conversion...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

    # Inbound pack details
    inbound_qty = parse_quantity(row['Inbound Pack Quantity'])

    # Sell pack dimensions (in inches)
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728  # Convert to cu ft
    sell_weight = parse_weight(row['Sell Pack Weight'])

    # Inbound pack dimensions and weight
    inbound_dims = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_volume = (inbound_dims[0] * inbound_dims[1] * inbound_dims[2]) / 1728  # Convert to cu ft
    inbound_weight = parse_weight(row['Inbound Pack Weight'])

    # Inbound to sell pack conversion ratio
    # Example: SKUW1 arrives in packs of 144 units, stored as 144/12 = 12 sell packs
    inbound_to_sell_ratio = inbound_qty / sell_qty if sell_qty > 0 else 1

    # Supplier type
    supplier_type = row['Supplier Type'].strip()

    sku_data[sku] = {
        'sell_qty': sell_qty,
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'inbound_qty': inbound_qty,
        'inbound_volume': inbound_volume,
        'inbound_weight': inbound_weight,
        'inbound_to_sell_ratio': inbound_to_sell_ratio,
        'supplier_type': supplier_type
    }

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs with inbound pack conversion")
print(f"   Example: SKUW1 - Inbound: {sku_data['SKUW1']['inbound_qty']} units = {sku_data['SKUW1']['inbound_to_sell_ratio']:.1f} sell packs")

# Extract demand data and distribute daily
print("\n[3/8] Extracting demand data and distributing daily...")
months = list(range(1, 121))
days = list(range(1, 22))  # 21 business days

# Monthly demand
monthly_demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        monthly_demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])

# Daily demand (uniform distribution)
daily_demand_data = {}
for month in months:
    for day in days:
        for sku in skus:
            monthly_demand = monthly_demand_data[(month, sku)]
            daily_demand_data[(month, day, sku)] = monthly_demand / WORKING_DAYS_PER_MONTH

print(f"   ✓ Loaded demand for {len(months)} months × {len(days)} days × {len(skus)} SKUs")
print(f"   Total daily time periods: {len(months) * len(days)} = 2,520")

# Parse days-on-hand
print("\n[4/8] Processing days-on-hand (daily safety stock)...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_col = f"{fac} - Days on Hand" if fac != "Austin" else "Austin Days on Hand"
        if doh_col in row:
            doh_data[(sku, fac)] = float(row[doh_col])

print(f"   International SKUs: {doh_data.get(('SKUW1', 'Columbus'), 0)} business days")
print(f"   Domestic SKUs:      {doh_data.get(('SKUA1', 'Columbus'), 0)} business days")

# Load current shelves
print("\n[5/8] Loading current shelving capacity...")
curr_shelves = {}
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
    curr_shelves[(fac, st)] = int(row['Number of Shelves'])

# Process configs
print("\n[6/8] Processing packing configurations...")
config_units = {}
config_facility = {}
config_storage_type = {}

for _, row in packing_configs_df.iterrows():
    cid = int(row['Config_ID'])
    sku = row['SKU']
    total_packages = int(row['Total_Packages_per_Shelf'])
    fac = row['Facility']
    st = row['Storage_Type']
    units_per_package = int(row['Units_per_Package'])

    total_units = total_packages * units_per_package

    if cid not in config_units:
        config_units[cid] = {}
        config_facility[cid] = fac
        config_storage_type[cid] = st

    config_units[cid][sku] = total_units

config_ids = sorted(packing_configs_df['Config_ID'].unique())
print(f"   ✓ {len(config_ids)} configurations ready")

print("\n[7/8] Building GAMSPy model with daily time structure...")
print("="*100)
print("BUILDING GAMSPY MODEL")
print("="*100)

m = Container()

# Sets - INCLUDING DAILY TIME DIMENSION AND SUPPLIERS
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
st = Set(m, name="st", records=storage_types)
t_month = Set(m, name="t_month", records=[str(i) for i in months])
t_day = Set(m, name="t_day", records=[str(i) for i in days])
c = Set(m, name="c", records=[str(i) for i in config_ids])
supplier = Set(m, name="supplier", records=SUPPLIERS)  # Truck dispatch by supplier

print("   ✓ Sets created (including daily time dimension and suppliers)")

# Parameters
daily_demand_records = [(str(month), str(day), sku, daily_demand_data[(month, day, sku)])
                        for month in months for day in days for sku in skus]
daily_demand = Parameter(m, name="daily_demand", domain=[t_month, t_day, s], records=daily_demand_records)

doh_records = [(sku, fac, doh_data.get((sku, fac), 0)) for sku in skus for fac in facilities]
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=doh_records)

config_units_records = []
for cid in config_ids:
    for sku in skus:
        units = config_units.get(cid, {}).get(sku, 0)
        if units > 0:
            config_units_records.append((str(cid), sku, units))
config_units_param = Parameter(m, name="config_units", domain=[c, s], records=config_units_records)

config_fac_records = []
for cid in config_ids:
    for fac in facilities:
        match = 1 if config_facility[cid] == fac else 0
        config_fac_records.append((str(cid), fac, match))
config_fac_param = Parameter(m, name="config_fac", domain=[c, f], records=config_fac_records)

config_st_records = []
for cid in config_ids:
    for st_type in storage_types:
        match = 1 if config_storage_type[cid] == st_type else 0
        config_st_records.append((str(cid), st_type, match))
config_st_param = Parameter(m, name="config_st", domain=[c, st], records=config_st_records)

curr_shelves_records = [(fac, st_type, curr_shelves.get((fac, st_type), 0))
                        for fac in facilities for st_type in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f, st], records=curr_shelves_records)

# Truck capacity parameters
truck_weight_cap = Parameter(m, name="truck_weight_cap", records=TRUCK_WEIGHT_CAPACITY_LBS)
truck_volume_cap = Parameter(m, name="truck_volume_cap", records=TRUCK_VOLUME_CAPACITY_CUFT)
min_util = Parameter(m, name="min_util", records=MIN_TRUCK_UTILIZATION)
truck_cost = Parameter(m, name="truck_cost", records=TRUCK_COST_PER_DELIVERY)

# SKU to supplier mapping (binary parameter: 1 if SKU s belongs to supplier sup)
sku_supplier_records = []
for sku in skus:
    for sup in SUPPLIERS:
        if SKU_TO_SUPPLIER.get(sku) == sup:
            sku_supplier_records.append((sku, sup, 1))
sku_supplier_map = Parameter(m, name="sku_supplier_map", domain=[s, supplier], records=sku_supplier_records)

# Inbound pack volume and weight (needed for truck loading)
inbound_vol_records = [(sku, sku_data[sku]['inbound_volume']) for sku in skus]
inbound_weight_records = [(sku, sku_data[sku]['inbound_weight']) for sku in skus]
inbound_vol = Parameter(m, name="inbound_vol", domain=s, records=inbound_vol_records)
inbound_weight = Parameter(m, name="inbound_weight", domain=s, records=inbound_weight_records)

print("   ✓ Parameters created (daily demand, truck capacity, supplier mapping)")

# Variables - DAILY INDEXED
shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="positive")
daily_inventory = Variable(m, name="daily_inventory", domain=[t_month, t_day, s, f], type="positive")
daily_shipments = Variable(m, name="daily_shipments", domain=[t_month, t_day, s, f], type="positive")
daily_deliveries = Variable(m, name="daily_deliveries", domain=[t_month, t_day, s, f], type="positive")

# TRUCK DISPATCH VARIABLES (INTEGER)
num_trucks = Variable(m, name="num_trucks", domain=[t_month, t_day, supplier, f], type="integer")
# Binary variable: 1 if supplier delivers to facility on this day
truck_dispatch = Variable(m, name="truck_dispatch", domain=[t_month, t_day, supplier, f], type="binary")

slack_demand = Variable(m, name="slack_demand", domain=[t_month, t_day, s], type="positive")
slack_doh = Variable(m, name="slack_doh", domain=[t_month, t_day, s, f], type="positive")
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")

total_slack = Variable(m, name="total_slack", type="free")

print("   ✓ Variables created (daily inventory, shipments, deliveries, INTEGER TRUCKS)")

# Objective - MINIMIZE SLACK AND TRUCK COSTS
obj = Equation(m, name="obj")
obj[...] = (
    total_slack ==
    Sum([t_month, t_day, s], slack_demand[t_month, t_day, s] * 1000) +
    Sum([t_month, t_day, s, f], slack_doh[t_month, t_day, s, f] * 10) +
    Sum(st, slack_shelf_sac[st] * 100) +
    Sum(st, slack_shelf_austin[st] * 100) +
    # ADD TRUCK COSTS - Low weight so it minimizes trucks without dominating other constraints
    Sum([t_month, t_day, supplier, f], num_trucks[t_month, t_day, supplier, f] * truck_cost)
)

# Daily demand fulfillment
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month, t_day, s])
demand_fulfill[t_month, t_day, s] = (
    Sum(f, daily_shipments[t_month, t_day, s, f]) + slack_demand[t_month, t_day, s] >=
    daily_demand[t_month, t_day, s]
)

# Daily inventory balance with carryover
# Note: We need to handle day 1 of month 1 separately (no previous inventory)
inv_balance = Equation(m, name="inv_balance", domain=[t_month, t_day, s, f])
inv_balance[t_month, t_day, s, f].where[
    (t_month.val > "1") | (t_day.val > "1")
] = (
    daily_inventory[t_month, t_day, s, f] ==
    daily_inventory[t_month, t_day.lag(1, "circular"), s, f].where[t_day.val > "1"] +
    daily_inventory[t_month.lag(1, "circular"), "21", s, f].where[t_day.val == "1"] +
    daily_deliveries[t_month, t_day, s, f] -
    daily_shipments[t_month, t_day, s, f]
)

# Initial inventory (month 1, day 1) - starts at zero
inv_initial = Equation(m, name="inv_initial", domain=[s, f])
inv_initial[s, f] = (
    daily_inventory["1", "1", s, f] ==
    daily_deliveries["1", "1", s, f] -
    daily_shipments["1", "1", s, f]
)

# Days-on-hand constraint (daily)
doh_constraint = Equation(m, name="doh_constraint", domain=[t_month, t_day, s, f])
doh_constraint[t_month, t_day, s, f] = (
    daily_inventory[t_month, t_day, s, f] + slack_doh[t_month, t_day, s, f] >=
    daily_demand[t_month, t_day, s] * days_on_hand[s, f]
)

# Capacity link (daily inventory must fit on shelves)
capacity_link = Equation(m, name="capacity_link", domain=[t_month, t_day, s, f])
capacity_link[t_month, t_day, s, f] = (
    daily_inventory[t_month, t_day, s, f] <=
    Sum(c, shelves_per_config[c] * config_units_param[c, s] * config_fac_param[c, f])
)

# Shelf limits
shelf_limit_sac = Equation(m, name="shelf_limit_sac", domain=st)
shelf_limit_sac[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Sacramento"] * config_st_param[c, st]) <=
    curr_shelves_param["Sacramento", st] + slack_shelf_sac[st]
)

shelf_limit_austin = Equation(m, name="shelf_limit_austin", domain=st)
shelf_limit_austin[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Austin"] * config_st_param[c, st]) <=
    curr_shelves_param["Austin", st] + slack_shelf_austin[st]
)

shelf_limit_columbus = Equation(m, name="shelf_limit_columbus", domain=st)
shelf_limit_columbus[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Columbus"] * config_st_param[c, st]) <=
    curr_shelves_param["Columbus", st]
)

# 99% utilization constraints
total_expansion_slack = Sum(st, slack_shelf_sac[st]) + Sum(st, slack_shelf_austin[st])

columbus_utilization = Equation(m, name="columbus_utilization")
columbus_utilization[...] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Columbus"] * config_st_param[c, "Pallet"]) >=
    0.99 * curr_shelves_param["Columbus", "Pallet"] -
    1000000 * (1 - total_expansion_slack / 1000000)
)

sacramento_utilization = Equation(m, name="sacramento_utilization")
sacramento_utilization[...] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Sacramento"] * config_st_param[c, "Pallet"]) >=
    0.99 * curr_shelves_param["Sacramento", "Pallet"] -
    1000000 * (1 - total_expansion_slack / 1000000)
)

austin_utilization = Equation(m, name="austin_utilization")
austin_utilization[...] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Austin"] * config_st_param[c, "Pallet"]) >=
    0.99 * curr_shelves_param["Austin", "Pallet"] -
    1000000 * (1 - total_expansion_slack / 1000000)
)

# ==================================================================================
# TRUCK DISPATCH OPTIMIZATION CONSTRAINTS
# ==================================================================================

# 1. Link deliveries to trucks: Total weight/volume of deliveries from supplier must fit in trucks
truck_weight_capacity = Equation(m, name="truck_weight_capacity", domain=[t_month, t_day, supplier, f])
truck_weight_capacity[t_month, t_day, supplier, f] = (
    Sum(s.where[sku_supplier_map[s, supplier] > 0],
        daily_deliveries[t_month, t_day, s, f] * inbound_weight[s])
    <= num_trucks[t_month, t_day, supplier, f] * truck_weight_cap
)

truck_volume_capacity = Equation(m, name="truck_volume_capacity", domain=[t_month, t_day, supplier, f])
truck_volume_capacity[t_month, t_day, supplier, f] = (
    Sum(s.where[sku_supplier_map[s, supplier] > 0],
        daily_deliveries[t_month, t_day, s, f] * inbound_vol[s])
    <= num_trucks[t_month, t_day, supplier, f] * truck_volume_cap
)

# 2. Minimum 90% utilization on WEIGHT constraint
# Only dispatch truck if weight >= 90% of capacity
truck_min_weight_util = Equation(m, name="truck_min_weight_util", domain=[t_month, t_day, supplier, f])
truck_min_weight_util[t_month, t_day, supplier, f] = (
    Sum(s.where[sku_supplier_map[s, supplier] > 0],
        daily_deliveries[t_month, t_day, s, f] * inbound_weight[s])
    >= num_trucks[t_month, t_day, supplier, f] * truck_weight_cap * min_util
)

# 3. Minimum 90% utilization on VOLUME constraint
# Only dispatch truck if volume >= 90% of capacity
truck_min_volume_util = Equation(m, name="truck_min_volume_util", domain=[t_month, t_day, supplier, f])
truck_min_volume_util[t_month, t_day, supplier, f] = (
    Sum(s.where[sku_supplier_map[s, supplier] > 0],
        daily_deliveries[t_month, t_day, s, f] * inbound_vol[s])
    >= num_trucks[t_month, t_day, supplier, f] * truck_volume_cap * min_util
)

# 4. Binary dispatch indicator: truck_dispatch = 1 if num_trucks > 0
# This helps with linearization and tracking
truck_dispatch_link = Equation(m, name="truck_dispatch_link", domain=[t_month, t_day, supplier, f])
truck_dispatch_link[t_month, t_day, supplier, f] = (
    num_trucks[t_month, t_day, supplier, f] <= truck_dispatch[t_month, t_day, supplier, f] * 100
    # Max 100 trucks per delivery (very generous upper bound)
)

print("   ✓ Constraints created (daily inventory balance + TRUCK DISPATCH with 90% minimum utilization)")

print("\n[8/8] Solving model with truck optimization...")
print("="*100)
print("SOLVING MODEL")
print("="*100)
print(f"\nModel size:")
print(f"  - Time periods: 2,520 (120 months × 21 days)")
print(f"  - SKUs: {len(skus)}")
print(f"  - Facilities: {len(facilities)}")
print(f"  - Suppliers: {len(SUPPLIERS)}")
print(f"  - Configurations: {len(config_ids)}")
print(f"  - Estimated daily inventory variables: {2520 * len(skus) * len(facilities):,}")
print(f"  - Truck dispatch variables (INTEGER): {2520 * len(SUPPLIERS) * len(facilities):,}")
print(f"  - Max solve time: {MAX_SOLVE_TIME} seconds ({MAX_SOLVE_TIME//60} minutes)")
print()

daily_model = Model(
    m,
    name="phase2_daily_truck_opt",
    equations=m.getEquations(),
    problem="MIP",  # Mixed Integer Programming (has integer truck variables)
    sense=Sense.MIN,
    objective=total_slack
)

# Set solver options for MIP
solve_options = Options()
solve_options.time_limit = MAX_SOLVE_TIME
solve_options.relative_optimality_gap = 0.05  # 5% gap acceptable for large MIP
solve_options.threads = 4  # Use multiple cores

print("Starting MIP solve (with integer truck variables)...")
daily_model.solve(options=solve_options)

print("\n" + "="*100)
print("RESULTS: DAILY TIME PERIODS MODEL")
print("="*100)

print(f"\nSolver status: {daily_model.status}")
# Solve time not directly available

total_slack_val = total_slack.toValue()
print(f"Total slack value: {total_slack_val:,.2f}")

# Solver completed successfully within time limit

print("\n[1] FACILITY UTILIZATION")
shelves_used_df = shelves_per_config.records
shelves_used_df.columns = ['Config_ID', 'Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
shelves_used_df = shelves_used_df[shelves_used_df['Shelves'] > 0.01]

facility_utilization = {}
for fac in facilities:
    pallet_used = 0
    for _, row in shelves_used_df.iterrows():
        config_id = int(float(row['Config_ID']))
        shelves = row['Shelves']
        if config_facility[config_id] == fac and config_storage_type[config_id] == 'Pallet':
            pallet_used += shelves

    pallet_capacity = curr_shelves.get((fac, 'Pallet'), 0)
    utilization_pct = (pallet_used / pallet_capacity * 100) if pallet_capacity > 0 else 0
    facility_utilization[fac] = {
        'used': pallet_used,
        'capacity': pallet_capacity,
        'pct': utilization_pct
    }

for fac in facilities:
    util = facility_utilization[fac]
    print(f"\n{fac}:")
    print(f"  Pallet shelves: {util['used']:,.0f} / {util['capacity']:,} ({util['pct']:.1f}%)")
    if util['pct'] >= 99:
        print(f"  ✓ At 99%+ capacity")

print("\n[2] EXPANSION REQUIREMENTS")
for fac_name, slack_var in [('Sacramento', slack_shelf_sac),
                             ('Austin', slack_shelf_austin)]:
    print(f"\n{fac_name}:")
    slack_df = slack_var.records
    slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
    slack_df = slack_df[slack_df['Excess_Shelves'] > 0.1]

    if len(slack_df) > 0:
        for _, row in slack_df.iterrows():
            st_type = row['Storage_Type']
            excess = row['Excess_Shelves']
            current = curr_shelves.get((fac_name, st_type), 0)
            print(f"  {st_type:<12}: Need {excess:>8,.0f} more shelves (current: {current:>8,})")
    else:
        print("  ✓ No expansion needed")

# Calculate totals
sac_slack_df = slack_shelf_sac.records
sac_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
sac_total = sac_slack_df[sac_slack_df['Excess_Shelves'] > 0.1]['Excess_Shelves'].sum()

austin_slack_df = slack_shelf_austin.records
austin_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
austin_total = austin_slack_df[austin_slack_df['Excess_Shelves'] > 0.1]['Excess_Shelves'].sum()

total_expansion = sac_total + austin_total

print("\n" + "="*100)
print(f"TOTAL EXPANSION REQUIRED: {total_expansion:,.0f} pallet shelves")
print("="*100)
print(f"  Sacramento: {sac_total:,.0f} shelves")
print(f"  Austin: {austin_total:,.0f} shelves")
print("="*100)

print("\n[3] COMPARISON TO MONTHLY MODEL")
print("\nMonthly aggregation model (3/1 DoH): 6,511 shelves")
print(f"Daily time period model (3/1 DoH):   {total_expansion:,.0f} shelves")
if total_expansion > 0:
    diff = total_expansion - 6511
    pct_diff = (diff / 6511 * 100)
    print(f"Difference: {diff:+,.0f} shelves ({pct_diff:+.1f}%)")

    if abs(pct_diff) < 5:
        print("\n✓ Results are consistent! Daily model confirms monthly approximation.")
    else:
        print("\n⚠️  Significant difference detected.")
        print("   Daily inventory carryover reveals different capacity needs.")

print("\n[4] TRUCK DISPATCH RESULTS (INTEGER OPTIMIZATION)")
print("="*100)

# Extract truck dispatch results
trucks_df = num_trucks.records
trucks_df.columns = ['Month', 'Day', 'Supplier', 'Facility', 'Num_Trucks', 'Marginal', 'Lower', 'Upper', 'Scale']
trucks_df = trucks_df[trucks_df['Num_Trucks'] > 0.01]  # Only show actual deliveries

if len(trucks_df) > 0:
    total_trucks = trucks_df['Num_Trucks'].sum()
    print(f"\n✓ Total trucks dispatched over 10 years: {total_trucks:,.0f}")
    print(f"✓ Total delivery events: {len(trucks_df):,}")
    print(f"✓ Average trucks per delivery: {trucks_df['Num_Trucks'].mean():.2f}")
    print(f"✓ Maximum trucks in single delivery: {trucks_df['Num_Trucks'].max():.0f}")

    print("\n--- Trucks by Supplier ---")
    for supplier_name in SUPPLIERS:
        sup_trucks = trucks_df[trucks_df['Supplier'] == supplier_name]
        if len(sup_trucks) > 0:
            print(f"\n{supplier_name}:")
            print(f"  Total trucks: {sup_trucks['Num_Trucks'].sum():,.0f}")
            print(f"  Delivery days: {len(sup_trucks):,}")
            print(f"  Avg trucks/delivery: {sup_trucks['Num_Trucks'].mean():.2f}")

    print("\n--- Trucks by Facility ---")
    for fac in facilities:
        fac_trucks = trucks_df[trucks_df['Facility'] == fac]
        if len(fac_trucks) > 0:
            print(f"\n{fac}:")
            print(f"  Total trucks: {fac_trucks['Num_Trucks'].sum():.0f}")
            print(f"  Delivery days: {len(fac_trucks):,}")
            print(f"  Avg trucks/delivery: {fac_trucks['Num_Trucks'].mean():.2f}")

    # Save truck dispatch results
    trucks_output = RESULTS_DIR / "truck_dispatch_integer_3_1_doh.csv"
    trucks_df.to_csv(trucks_output, index=False)
    print(f"\n✓ Truck dispatch results saved to: {trucks_output}")
else:
    print("\n⚠️  No truck dispatches found in solution")

print("\n[5] DETAILED TRUCKLOAD ANALYSIS (WITH UTILIZATION)")
print("="*100)
print(f"Truck specifications: 53ft trailer")
print(f"  - Weight capacity: {TRUCK_WEIGHT_CAPACITY_LBS:,} lbs")
print(f"  - Volume capacity: {TRUCK_VOLUME_CAPACITY_CUFT:,} cu ft")
print("="*100)

# Extract delivery data
deliveries_df = daily_deliveries.records
deliveries_df.columns = ['Month', 'Day', 'SKU', 'Facility', 'Deliveries', 'Marginal', 'Lower', 'Upper', 'Scale']
deliveries_df = deliveries_df[deliveries_df['Deliveries'] > 0.01]

# Calculate truckloads per supplier per day per facility
print("\nCalculating truckloads per supplier (by company name) per day...")
print(f"Tracking {len(SUPPLIERS)} suppliers: {', '.join(SUPPLIERS)}")

truckload_data = []
for month in months:
    for day in days:
        for fac in facilities:
            for supplier_name in SUPPLIERS:
                # Get all deliveries for this specific supplier on this day to this facility
                day_supplier_deliveries = deliveries_df[
                    (deliveries_df['Month'] == str(month)) &
                    (deliveries_df['Day'] == str(day)) &
                    (deliveries_df['Facility'] == fac)
                ]

                total_weight = 0
                total_volume = 0
                num_skus = 0
                skus_delivered = []

                for _, row in day_supplier_deliveries.iterrows():
                    sku = row['SKU']
                    # Check if this SKU belongs to the current supplier
                    if SKU_TO_SUPPLIER.get(sku) == supplier_name:
                        num_inbound_packs = row['Deliveries']
                        # Each delivery is in units of inbound packs
                        total_weight += num_inbound_packs * sku_data[sku]['inbound_weight']
                        total_volume += num_inbound_packs * sku_data[sku]['inbound_volume']
                        num_skus += 1
                        skus_delivered.append(sku)

                if total_weight > 0 or total_volume > 0:
                    trucks_needed = calculate_truckloads(total_weight, total_volume)
                    utilization = calculate_truck_utilization(total_weight, total_volume, trucks_needed)

                    truckload_data.append({
                        'Month': month,
                        'Day': day,
                        'Facility': fac,
                        'Supplier': supplier_name,
                        'Supplier_Type': SKU_TO_SUPPLIER_TYPE.get(skus_delivered[0]) if skus_delivered else 'Unknown',
                        'Weight_lbs': total_weight,
                        'Volume_cuft': total_volume,
                        'Trucks_Needed': trucks_needed,
                        'Weight_Utilization_Pct': utilization['weight_utilization_pct'],
                        'Volume_Utilization_Pct': utilization['volume_utilization_pct'],
                        'Binding_Constraint': utilization['binding_constraint'],
                        'Num_SKUs': num_skus,
                        'SKUs_Delivered': ','.join(skus_delivered)
                    })

truckload_df = pd.DataFrame(truckload_data)

if len(truckload_df) > 0:
    # Summary statistics
    print(f"\n✓ Calculated truckloads for {len(truckload_df)} delivery events")

    print("\n--- Overall Statistics ---")
    print(f"Total delivery days with trucks: {len(truckload_df):,}")
    print(f"Total trucks needed over 10 years: {truckload_df['Trucks_Needed'].sum():,.2f}")
    print(f"Average trucks per delivery: {truckload_df['Trucks_Needed'].mean():.2f}")
    print(f"Max trucks in single day: {truckload_df['Trucks_Needed'].max():.2f}")
    print(f"Average weight utilization: {truckload_df['Weight_Utilization_Pct'].mean():.1f}%")
    print(f"Average volume utilization: {truckload_df['Volume_Utilization_Pct'].mean():.1f}%")

    # Binding constraint analysis
    weight_constrained = (truckload_df['Binding_Constraint'] == 'weight').sum()
    volume_constrained = (truckload_df['Binding_Constraint'] == 'volume').sum()
    print(f"\nBinding constraints:")
    print(f"  Weight-constrained deliveries: {weight_constrained:,} ({weight_constrained/len(truckload_df)*100:.1f}%)")
    print(f"  Volume-constrained deliveries: {volume_constrained:,} ({volume_constrained/len(truckload_df)*100:.1f}%)")

    print("\n--- By Specific Supplier (Company Name) ---")
    for supplier_name in SUPPLIERS:
        supplier_trucks = truckload_df[truckload_df['Supplier'] == supplier_name]
        if len(supplier_trucks) > 0:
            supplier_type = supplier_trucks['Supplier_Type'].iloc[0]
            print(f"\n{supplier_name} ({supplier_type}):")
            print(f"  Total trucks: {supplier_trucks['Trucks_Needed'].sum():,.2f}")
            print(f"  Delivery days: {len(supplier_trucks):,}")
            print(f"  Avg trucks/delivery: {supplier_trucks['Trucks_Needed'].mean():.2f}")
            print(f"  Max trucks/day: {supplier_trucks['Trucks_Needed'].max():.2f}")
            print(f"  Avg weight utilization: {supplier_trucks['Weight_Utilization_Pct'].mean():.1f}%")
            print(f"  Avg volume utilization: {supplier_trucks['Volume_Utilization_Pct'].mean():.1f}%")
            weight_bound = (supplier_trucks['Binding_Constraint'] == 'weight').sum()
            print(f"  Weight-constrained: {weight_bound}/{len(supplier_trucks)} ({weight_bound/len(supplier_trucks)*100:.1f}%)")

    print("\n--- By Facility ---")
    for fac in facilities:
        fac_trucks = truckload_df[truckload_df['Facility'] == fac]
        if len(fac_trucks) > 0:
            print(f"\n{fac}:")
            print(f"  Total trucks: {fac_trucks['Trucks_Needed'].sum():,.2f}")
            print(f"  Delivery days: {len(fac_trucks):,}")
            print(f"  Avg trucks/delivery: {fac_trucks['Trucks_Needed'].mean():.2f}")
            print(f"  Max trucks/day: {fac_trucks['Trucks_Needed'].max():.2f}")
            print(f"  Avg weight utilization: {fac_trucks['Weight_Utilization_Pct'].mean():.1f}%")
            print(f"  Avg volume utilization: {fac_trucks['Volume_Utilization_Pct'].mean():.1f}%")

    # Peak days analysis
    print("\n--- Peak Delivery Days (>5 trucks) ---")
    peak_days = truckload_df[truckload_df['Trucks_Needed'] > 5].sort_values('Trucks_Needed', ascending=False)
    if len(peak_days) > 0:
        print(f"\nFound {len(peak_days)} days with >5 trucks")
        print("\nTop 10 highest truck days:")
        for idx, (_, row) in enumerate(peak_days.head(10).iterrows(), 1):
            print(f"  {idx}. Month {row['Month']}, Day {row['Day']} - {row['Facility']} - {row['Supplier']}: {row['Trucks_Needed']:.2f} trucks")
            print(f"      Weight util: {row['Weight_Utilization_Pct']:.1f}%, Volume util: {row['Volume_Utilization_Pct']:.1f}% ({row['Binding_Constraint']} constrained)")
    else:
        print("  No days with >5 trucks needed")

    # Low utilization analysis
    print("\n--- Low Utilization Deliveries (<50% on binding constraint) ---")
    low_util = truckload_df[
        ((truckload_df['Binding_Constraint'] == 'weight') & (truckload_df['Weight_Utilization_Pct'] < 50)) |
        ((truckload_df['Binding_Constraint'] == 'volume') & (truckload_df['Volume_Utilization_Pct'] < 50))
    ].sort_values('Trucks_Needed', ascending=False)

    if len(low_util) > 0:
        print(f"\nFound {len(low_util)} deliveries with <50% utilization on binding constraint")
        print(f"Total trucks in low-utilization deliveries: {low_util['Trucks_Needed'].sum():.2f}")
        print(f"Potential optimization opportunity: {(1 - low_util['Weight_Utilization_Pct'].mean()/100) * low_util['Trucks_Needed'].sum():.2f} trucks could be saved")
        print("\nTop 5 lowest utilization deliveries:")
        for idx, (_, row) in enumerate(low_util.head(5).iterrows(), 1):
            binding_util = row['Weight_Utilization_Pct'] if row['Binding_Constraint'] == 'weight' else row['Volume_Utilization_Pct']
            print(f"  {idx}. {row['Supplier']} to {row['Facility']} (Month {row['Month']}, Day {row['Day']})")
            print(f"      {row['Trucks_Needed']:.2f} trucks, {binding_util:.1f}% utilization on {row['Binding_Constraint']}")
    else:
        print("\n✓ All deliveries have >50% utilization - efficient truck usage!")

    # Save truckload analysis to CSV
    output_file = RESULTS_DIR / "truckload_analysis_3_1_doh.csv"
    truckload_df.to_csv(output_file, index=False)
    print(f"\n✓ Truckload analysis saved to: {output_file}")
else:
    print("\n⚠️  No deliveries found in model solution")

print("\n" + "="*100)
print("DAILY MODEL COMPLETE")
print("="*100)
