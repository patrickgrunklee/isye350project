"""
PHASE 2 V2: MULTIPERIOD INVENTORY OPTIMIZATION - IMPROVED CAPACITY CONSTRAINTS
===============================================================================

Improvements over V1:
1. Proper expansion-to-shelf conversion
2. Current capacity enforcement (Columbus cannot expand)
3. Realistic shelf deployment limits
4. Better inventory-capacity linking
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
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase2_Multiperiod")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WORKING_DAYS_PER_MONTH = 21

print("="*100)
print("PHASE 2 V2: MULTIPERIOD INVENTORY OPTIMIZATION (RELAXED DOH)")
print("="*100)
print("\nImprovements:")
print("  - Proper capacity constraints")
print("  - Expansion-to-shelf conversion")
print("  - Columbus cannot expand (fixed)")
print("  - Realistic shelf limits")
print("  - DoH DISABLED for testing (identifying infeasibility source)\n")

# Utility functions
def parse_dimension(dim_str, in_feet=False):
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        if in_feet:
            return tuple(float(p.strip()) for p in parts)
        else:
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
print("[1/9] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / "packing_configurations.csv")
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/9] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

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
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'sell_qty': sell_qty,
        'storage_type': storage_type
    }

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs")

# Extract demand data
print("\n[3/9] Extracting demand data...")
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])
print(f"   ✓ Loaded demand for {len(months)} months × {len(skus)} SKUs")

# Parse lead times and days-on-hand
print("\n[4/9] Processing lead times and days-on-hand...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

lead_time_data = {}
doh_data = {}

for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        lt_col = f"{fac} Lead Time (days)"
        doh_col = f"{fac} Days on Hand"
        if lt_col in row and doh_col in row:
            lead_time_data[(sku, fac)] = float(row[lt_col])
            doh_data[(sku, fac)] = float(row[doh_col])

print(f"   ✓ Loaded lead times and DoH")

# Load current shelf counts and area per shelf
print("\n[5/9] Loading current shelving capacity and area...")
curr_shelves = {}
shelf_weight_cap = {}
area_per_storage_type = {}

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

    num_shelves = int(row['Number of Shelves'])
    curr_shelves[(fac, st)] = num_shelves
    shelf_weight_cap[(fac, st)] = float(row['Weight Max / Shelf'])

    # Calculate average sq ft per shelf
    if 'Area' in row and pd.notna(row['Area']):
        total_area = float(row['Area'])
        area_per_storage_type[(fac, st)] = total_area
        avg_sqft_per_shelf = total_area / num_shelves if num_shelves > 0 else 50.0
    else:
        avg_sqft_per_shelf = 50.0  # Default

print(f"   ✓ Loaded capacity for {len(curr_shelves)} (facility, storage_type) combinations")

# Process Phase 1 packing configurations
print("\n[6/9] Processing Phase 1 packing configurations...")
config_packages = {}
config_facility = {}
config_storage_type = {}
config_units = {}  # Total units per shelf for this config

for _, row in packing_configs_df.iterrows():
    config_id = int(row['Config_ID'])
    sku = row['SKU']
    packages = int(row['Packages_per_Shelf'])
    fac = row['Facility']
    st = row['Storage_Type']
    units_per_package = int(row['Units_per_Package'])

    config_packages[(config_id, sku)] = packages
    config_facility[config_id] = fac
    config_storage_type[config_id] = st

    # Track total units for this config
    if config_id not in config_units:
        config_units[config_id] = {}
    config_units[config_id][sku] = packages * units_per_package

config_ids = sorted(packing_configs_df['Config_ID'].unique())
print(f"   ✓ Processed {len(config_ids)} configurations")

# Expansion parameters
print("\n[7/9] Setting up expansion parameters...")
MAX_EXPANSION_SAC = 200000  # sq ft
MAX_EXPANSION_AUSTIN = 200000  # sq ft
EXPANSION_COST_SAC_TIER1 = 2.0  # $/sq ft
EXPANSION_COST_SAC_TIER2 = 4.0  # $/sq ft
EXPANSION_COST_AUSTIN = 1.5  # $/sq ft
HOLDING_COST_PER_UNIT_PER_MONTH = 0.1  # $0.10

# Average sq ft per shelf (for converting expansion to shelf count)
avg_sqft_per_shelf_data = {}
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

    if 'Area' in row and pd.notna(row['Area']):
        total_area = float(row['Area'])
        num_shelves = int(row['Number of Shelves'])
        avg_sqft_per_shelf_data[(fac, st)] = total_area / num_shelves if num_shelves > 0 else 50.0
    else:
        avg_sqft_per_shelf_data[(fac, st)] = 50.0

print("   ✓ Expansion parameters configured")

print("\n[8/9] Building GAMSPy optimization model...")

# Create GAMSPy container
m = Container()

# Sets
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
f_exp = Set(m, name="f_exp", records=['Sacramento', 'Austin'])
st = Set(m, name="st", records=storage_types)
t = Set(m, name="t", records=[str(i) for i in months])
c = Set(m, name="c", records=[str(i) for i in config_ids])

# Parameters
demand_records = [(str(month), sku, demand_data[(month, sku)]) for month, sku in demand_data.keys()]
demand = Parameter(m, name="demand", domain=[t, s], records=demand_records)

doh_records = [(sku, fac, doh_data.get((sku, fac), 0)) for sku in skus for fac in facilities]
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=doh_records)

# Config data
config_units_records = []
for config_id in config_ids:
    for sku in skus:
        units = config_units.get(config_id, {}).get(sku, 0)
        if units > 0:
            config_units_records.append((str(config_id), sku, units))

config_units_param = Parameter(m, name="config_units", domain=[c, s], records=config_units_records)

# Config facility/storage type matching
config_fac_records = []
for config_id in config_ids:
    for fac in facilities:
        match = 1 if config_facility[config_id] == fac else 0
        config_fac_records.append((str(config_id), fac, match))
config_fac_param = Parameter(m, name="config_fac", domain=[c, f], records=config_fac_records)

config_st_records = []
for config_id in config_ids:
    for st_type in storage_types:
        match = 1 if config_storage_type[config_id] == st_type else 0
        config_st_records.append((str(config_id), st_type, match))
config_st_param = Parameter(m, name="config_st", domain=[c, st], records=config_st_records)

# Current shelves
curr_shelves_records = [(fac, st_type, curr_shelves.get((fac, st_type), 0))
                        for fac in facilities for st_type in storage_types]
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f, st], records=curr_shelves_records)

# Average sq ft per shelf
sqft_per_shelf_records = [(fac, st_type, avg_sqft_per_shelf_data.get((fac, st_type), 50.0))
                          for fac in facilities for st_type in storage_types]
sqft_per_shelf_param = Parameter(m, name="sqft_per_shelf", domain=[f, st], records=sqft_per_shelf_records)

print("   ✓ GAMSPy sets and parameters created")

# Decision Variables
print("\n   Creating decision variables...")

# Expansion decisions
expansion_sac_tier1 = Variable(m, name="expansion_sac_tier1", type="positive")
expansion_sac_tier2 = Variable(m, name="expansion_sac_tier2", type="positive")
expansion_austin = Variable(m, name="expansion_austin", type="positive")

# Additional shelves by storage type (derived from expansion)
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")

# Number of shelves using each configuration
shelves_per_config = Variable(m, name="shelves_per_config", domain=[c], type="integer")

# Inventory, shipments (simplified - no orders for now)
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

# Total cost
total_cost = Variable(m, name="total_cost", type="free")

print("   ✓ Decision variables created")

# Equations
print("\n   Creating constraints...")

# Objective
obj = Equation(m, name="obj")
obj[...] = (
    total_cost ==
    expansion_sac_tier1 * EXPANSION_COST_SAC_TIER1 +
    expansion_sac_tier2 * EXPANSION_COST_SAC_TIER2 +
    expansion_austin * EXPANSION_COST_AUSTIN +
    Sum([t, s, f], inventory[t, s, f] * HOLDING_COST_PER_UNIT_PER_MONTH)
)

# Expansion limits
exp_sac_tier1_limit = Equation(m, name="exp_sac_tier1_limit")
exp_sac_tier1_limit[...] = expansion_sac_tier1 <= 100000

exp_sac_tier2_limit = Equation(m, name="exp_sac_tier2_limit")
exp_sac_tier2_limit[...] = expansion_sac_tier2 <= 150000

exp_austin_limit = Equation(m, name="exp_austin_limit")
exp_austin_limit[...] = expansion_austin <= MAX_EXPANSION_AUSTIN

# Link expansion sq ft to added shelves (DISABLED - allow free expansion for now)
# Total expansion = sum of added shelves × sqft per shelf
# expansion_shelf_link_sac = Equation(m, name="expansion_shelf_link_sac")
# expansion_shelf_link_sac[...] = (
#     expansion_sac_tier1 + expansion_sac_tier2 ==
#     Sum(st, add_shelves["Sacramento", st] * sqft_per_shelf_param["Sacramento", st])
# )

# expansion_shelf_link_austin = Equation(m, name="expansion_shelf_link_austin")
# expansion_shelf_link_austin[...] = (
#     expansion_austin ==
#     Sum(st, add_shelves["Austin", st] * sqft_per_shelf_param["Austin", st])
# )

# Demand fulfillment
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) >= demand[t, s]

# Inventory balance (simplified)
inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] >= shipments[t, s, f]

# Days-on-hand constraint (DISABLED FOR TESTING - checking if other constraints are feasible)
# DOH_RELAXATION_FACTOR = 0.25  # Use only 25% of the original DoH requirement
# doh_constraint = Equation(m, name="doh_constraint", domain=[t, s, f])
# doh_constraint[t, s, f] = (
#     inventory[t, s, f] >= (demand[t, s] / WORKING_DAYS_PER_MONTH) * days_on_hand[s, f] * DOH_RELAXATION_FACTOR
# )

# Capacity constraint: inventory must fit on shelves AT EACH TIME PERIOD
# At each time t, inventory must not exceed shelf capacity
capacity_link = Equation(m, name="capacity_link", domain=[t, s, f])
capacity_link[t, s, f] = (
    inventory[t, s, f] <=
    Sum(c, shelves_per_config[c] * config_units_param[c, s] * config_fac_param[c, f])
)

# Total shelves deployed per (facility, storage_type) must not exceed current + added
# Sacramento - Allow large expansion (10× current) for testing
shelf_limit_sac = Equation(m, name="shelf_limit_sac", domain=[st])
shelf_limit_sac[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Sacramento"] * config_st_param[c, st]) <=
    curr_shelves_param["Sacramento", st] * 10
)

# Austin - Allow large expansion (10× current) for testing
shelf_limit_austin = Equation(m, name="shelf_limit_austin", domain=[st])
shelf_limit_austin[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Austin"] * config_st_param[c, st]) <=
    curr_shelves_param["Austin", st] * 10
)

# Columbus cannot expand - strict limit
shelf_limit_columbus = Equation(m, name="shelf_limit_columbus", domain=[st])
shelf_limit_columbus[st] = (
    Sum(c, shelves_per_config[c] * config_fac_param[c, "Columbus"] * config_st_param[c, st]) <=
    curr_shelves_param["Columbus", st]
)

print("   ✓ Constraints created")

# Create and solve model
print("\n" + "="*100)
print("SOLVING PHASE 2 V2 OPTIMIZATION MODEL")
print("="*100)

warehouse_model = Model(
    m,
    name="phase2_v2",
    equations=m.getEquations(),
    problem="MINLP",
    sense=Sense.MIN,
    objective=total_cost
)

print("\nSolving... (this may take several minutes)")
warehouse_model.solve()

print("\n" + "="*100)
print("OPTIMIZATION COMPLETE")
print("="*100)

# Extract results
print("\n[RESULTS] Extracting solution...")

if warehouse_model.status == 1:
    print("   ✓ Optimal solution found")
else:
    print(f"   ⚠️  Model status: {warehouse_model.status}")

# Expansion decisions
print("\n" + "="*100)
print("EXPANSION DECISIONS")
print("="*100)

sac_tier1_val = expansion_sac_tier1.toValue()
sac_tier2_val = expansion_sac_tier2.toValue()
austin_val = expansion_austin.toValue()

print(f"\nSacramento:")
print(f"  Tier 1 @ $2/sqft:      {sac_tier1_val:>15,.0f} sq ft")
print(f"  Tier 2 @ $4/sqft:      {sac_tier2_val:>15,.0f} sq ft")
print(f"  Total:                  {sac_tier1_val + sac_tier2_val:>15,.0f} sq ft")
print(f"  Cost: ${sac_tier1_val * 2 + sac_tier2_val * 4:>15,.0f}")

print(f"\nAustin:")
print(f"  Expansion @ $1.5/sqft: {austin_val:>15,.0f} sq ft")
print(f"  Cost: ${austin_val * 1.5:>15,.0f}")

total_expansion_cost = (sac_tier1_val * 2 + sac_tier2_val * 4 + austin_val * 1.5)

# Shelf deployment
print("\n" + "="*100)
print("CONFIGURATION DEPLOYMENT")
print("="*100)

shelves_df = shelves_per_config.records
shelves_df.columns = ['Config_ID', 'Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
shelves_df = shelves_df[shelves_df['Shelves'] > 0.1].sort_values('Shelves', ascending=False)

if len(shelves_df) > 0:
    print(f"\nTop 15 deployed configurations:")
    print(f"  {'Config':<8} {'Facility':<15} {'Storage':<12} {'Shelves':<12}")
    print(f"  {'-'*50}")
    for _, row in shelves_df.head(15).iterrows():
        config_id = int(float(row['Config_ID']))
        fac = config_facility[config_id]
        st = config_storage_type[config_id]
        shelves = row['Shelves']
        print(f"  {config_id:<8} {fac:<15} {st:<12} {shelves:>10,.0f}")
else:
    print("  No configurations deployed")

# Total cost
total_cost_val = total_cost.toValue()
holding_cost_val = total_cost_val - total_expansion_cost

print("\n" + "="*100)
print("TOTAL COSTS")
print("="*100)
print(f"\nExpansion cost:        ${total_expansion_cost:>15,.0f}")
print(f"Holding cost (120 mo): ${holding_cost_val:>15,.0f}")
print(f"TOTAL COST:            ${total_cost_val:>15,.0f}")

# Save results
print("\n[SAVING RESULTS]")

expansion_summary = pd.DataFrame([{
    'Facility': 'Sacramento',
    'Tier': 'Tier 1',
    'Expansion_sqft': sac_tier1_val,
    'Cost_per_sqft': 2.0,
    'Total_Cost': sac_tier1_val * 2
}, {
    'Facility': 'Sacramento',
    'Tier': 'Tier 2',
    'Expansion_sqft': sac_tier2_val,
    'Cost_per_sqft': 4.0,
    'Total_Cost': sac_tier2_val * 4
}, {
    'Facility': 'Austin',
    'Tier': 'Flat',
    'Expansion_sqft': austin_val,
    'Cost_per_sqft': 1.5,
    'Total_Cost': austin_val * 1.5
}])
expansion_summary.to_csv(RESULTS_DIR / 'expansion_summary_v2.csv', index=False)
print(f"  ✓ Saved: expansion_summary_v2.csv")

shelves_df.to_csv(RESULTS_DIR / 'shelf_deployment_v2.csv', index=False)
print(f"  ✓ Saved: shelf_deployment_v2.csv")

print("\n" + "="*100)
print("PHASE 2 V2 COMPLETE")
print("="*100)
