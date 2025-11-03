"""
PHASE 2: MULTIPERIOD INVENTORY OPTIMIZATION
===========================================

Uses discrete packing configurations from Phase 1 to optimize:
- Warehouse expansion decisions (Sacramento, Austin)
- Shelf deployment by configuration over time
- Inventory levels and order placement
- Demand fulfillment across 120 months

Key decision: How many shelves of each Config_ID to deploy at each facility
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
print("PHASE 2: MULTIPERIOD INVENTORY OPTIMIZATION WITH SET PACKING CONFIGURATIONS")
print("="*100)
print("\nObjective: Minimize total cost (expansion + inventory holding) over 120 months")
print("Approach: Use discrete packing configurations from Phase 1 as shelf deployment options")
print("Decision: Select which Config_IDs to use and how many shelves per config\n")

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
print("[1/8] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / "packing_configurations.csv")
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/8] Processing SKU details...")
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

    supplier_type = str(row['Supplier Type']).strip()

    sku_data[sku] = {
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'sell_qty': sell_qty,
        'storage_type': storage_type,
        'supplier': supplier_type
    }

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs")

# Extract demand data (120 months)
print("\n[3/8] Extracting demand data...")
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])

print(f"   ✓ Loaded demand for {len(months)} months × {len(skus)} SKUs")

# Parse lead times and days-on-hand
print("\n[4/8] Processing lead times and days-on-hand...")
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

print(f"   ✓ Loaded lead times and DoH for {len(skus)} SKUs × {len(facilities)} facilities")

# Load current shelf counts
print("\n[5/8] Loading current shelving capacity...")
curr_shelves = {}
shelf_weight_cap = {}

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
    shelf_weight_cap[(fac, st)] = float(row['Weight Max / Shelf'])

print(f"   ✓ Loaded capacity for {len(curr_shelves)} (facility, storage_type) combinations")

# Process Phase 1 packing configurations
print("\n[6/8] Processing Phase 1 packing configurations...")
print(f"   Total configurations from Phase 1: {packing_configs_df['Config_ID'].nunique()}")

# Create mapping: (Config_ID, SKU) -> Packages_per_Shelf
config_packages = {}
config_facility = {}
config_storage_type = {}

for _, row in packing_configs_df.iterrows():
    config_id = int(row['Config_ID'])
    sku = row['SKU']
    packages = int(row['Packages_per_Shelf'])
    fac = row['Facility']
    st = row['Storage_Type']

    config_packages[(config_id, sku)] = packages
    config_facility[config_id] = fac
    config_storage_type[config_id] = st

config_ids = sorted(packing_configs_df['Config_ID'].unique())
print(f"   ✓ Processed {len(config_ids)} configurations")

# Calculate inventory per config per shelf
# inventory_per_config[(config_id, sku)] = packages × units_per_package
inventory_per_config = {}
for (config_id, sku), packages in config_packages.items():
    units_per_package = sku_data[sku]['sell_qty']
    inventory_per_config[(config_id, sku)] = packages * units_per_package

# Display sample configurations
print("\n   Sample configurations:")
for config_id in config_ids[:5]:
    fac = config_facility[config_id]
    st = config_storage_type[config_id]
    skus_in_config = [sku for (cid, sku) in config_packages.keys() if cid == config_id]
    print(f"     Config {config_id}: {fac} {st:<10} - {len(skus_in_config)} SKUs ({', '.join(skus_in_config)})")

# Expansion parameters
print("\n[7/8] Setting up expansion parameters...")
MAX_EXPANSION_SAC = 200000  # sq ft
MAX_EXPANSION_AUSTIN = 200000  # sq ft
EXPANSION_COST_SAC_TIER1 = 2.0  # $/sq ft (first 100K)
EXPANSION_COST_SAC_TIER2 = 4.0  # $/sq ft (next 150K)
EXPANSION_COST_AUSTIN = 1.5  # $/sq ft
HOLDING_COST_PER_UNIT_PER_MONTH = 0.1  # $0.10 per unit per month

# Average sq ft per shelf by facility and storage type
avg_sqft_per_shelf = {}
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

    if 'Area per Storage Type (sqft)' in row:
        total_area = float(row['Area per Storage Type (sqft)'])
        num_shelves = int(row['Number of Shelves'])
        avg_sqft_per_shelf[(fac, st)] = total_area / num_shelves if num_shelves > 0 else 50.0

print("   ✓ Expansion parameters configured")

print("\n[8/8] Building GAMSPy optimization model...")

# Create GAMSPy container
m = Container()

# Sets
s = Set(m, name="s", records=skus, description="SKUs")
f = Set(m, name="f", records=facilities, description="Facilities")
f_exp = Set(m, name="f_exp", records=['Sacramento', 'Austin'], description="Expandable facilities")
st = Set(m, name="st", records=storage_types, description="Storage types")
t = Set(m, name="t", records=[str(i) for i in months], description="Time periods (months)")
c = Set(m, name="c", records=[str(i) for i in config_ids], description="Configuration IDs")

# Parameters
demand_records = [(str(month), sku, demand_data[(month, sku)]) for month, sku in demand_data.keys()]
demand = Parameter(m, name="demand", domain=[t, s], records=demand_records)

lead_time_records = [(sku, fac, lead_time_data.get((sku, fac), 0)) for sku in skus for fac in facilities]
lead_time = Parameter(m, name="lead_time", domain=[s, f], records=lead_time_records)

doh_records = [(sku, fac, doh_data.get((sku, fac), 0)) for sku in skus for fac in facilities]
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=doh_records)

# Phase 1 configuration data
# config_packages_param[(config_id, sku)] = packages per shelf for this config
config_packages_records = [(str(config_id), sku, config_packages[(config_id, sku)])
                           for (config_id, sku) in config_packages.keys()]
config_packages_param = Parameter(m, name="config_packages", domain=[c, s], records=config_packages_records)

# config_facility_param[config_id] = facility (1 if matches, 0 otherwise)
# We'll use this to constrain configs to their assigned facilities
config_fac_records = []
for config_id in config_ids:
    for fac in facilities:
        match = 1 if config_facility[config_id] == fac else 0
        config_fac_records.append((str(config_id), fac, match))
config_fac_param = Parameter(m, name="config_fac", domain=[c, f], records=config_fac_records)

# config_storage_param[config_id] = storage type (1 if matches, 0 otherwise)
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

# SKU storage type assignment
sku_st_records = [(sku, sku_data[sku]['storage_type'], 1) for sku in skus]
sku_st_param = Parameter(m, name="sku_st", domain=[s, st], records=sku_st_records)

print("   ✓ GAMSPy sets and parameters created")
print(f"     - {len(skus)} SKUs")
print(f"     - {len(facilities)} facilities")
print(f"     - {len(storage_types)} storage types")
print(f"     - {len(months)} time periods")
print(f"     - {len(config_ids)} packing configurations")

# Decision Variables
print("\n   Creating decision variables...")

# Expansion decisions (one-time, not time-indexed)
expansion_sac_tier1 = Variable(m, name="expansion_sac_tier1", type="positive")
expansion_sac_tier2 = Variable(m, name="expansion_sac_tier2", type="positive")
expansion_austin = Variable(m, name="expansion_austin", type="positive")

# Number of shelves using each configuration (one-time decision)
shelves_per_config = Variable(m, name="shelves_per_config", domain=[f, st, c], type="integer")

# Inventory, orders, shipments (time-indexed)
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
orders = Variable(m, name="orders", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

# Total cost
total_cost = Variable(m, name="total_cost", type="free")

print("   ✓ Decision variables created")

# Equations
print("\n   Creating constraints...")

# Objective function
obj = Equation(m, name="obj", description="Minimize total cost")
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

# Demand fulfillment (each month)
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) >= demand[t, s]

# Inventory balance (simplified: inventory = previous + orders - shipments)
# Note: Lead time handling would require more complex indexing
inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
# For first period
inv_balance[t, s, f].where[t.ord == 1] = (
    inventory[t, s, f] == orders[t, s, f] - shipments[t, s, f]
)
# For subsequent periods
inv_balance[t, s, f].where[t.ord > 1] = (
    inventory[t, s, f] == inventory[t.lag(1), s, f] + orders[t, s, f] - shipments[t, s, f]
)

# Days-on-hand constraint
doh_constraint = Equation(m, name="doh_constraint", domain=[t, s, f])
doh_constraint[t, s, f] = (
    inventory[t, s, f] >= (demand[t, s] / WORKING_DAYS_PER_MONTH) * days_on_hand[s, f]
)

# Capacity constraint: Link inventory to shelf configurations
# Total units on shelves >= inventory
capacity_link = Equation(m, name="capacity_link", domain=[t, s, f])
capacity_link[t, s, f] = (
    inventory[t, s, f] <=
    Sum([st, c],
        shelves_per_config[f, st, c] *
        config_packages_param[c, s] *
        config_fac_param[c, f] *
        config_st_param[c, st] *
        sku_st_param[s, st]
    )
)

# Shelf count constraint: total shelves (current + added) by storage type
# Sum of shelves across all configs for (f, st) must match current + expansion
# This requires converting expansion sq ft to shelf count

# For now, we'll use a simpler approach:
# Just ensure we don't exceed a reasonable shelf expansion
max_shelves_expansion = Equation(m, name="max_shelves_expansion", domain=[f, st])
max_shelves_expansion[f, st].where[Sum(c.where[config_fac_param[c, f] == 1], 1) > 0] = (
    Sum(c, shelves_per_config[f, st, c]) <=
    curr_shelves_param[f, st] * 5  # Allow up to 5× current capacity
)

# Configs can only be used at their assigned facility
config_facility_constraint = Equation(m, name="config_facility_constraint", domain=[f, st, c])
config_facility_constraint[f, st, c] = (
    shelves_per_config[f, st, c] <=
    config_fac_param[c, f] * 99999  # Big M constraint
)

print("   ✓ Constraints created")
print(f"     - Objective function")
print(f"     - Expansion limits (Sacramento 2-tier, Austin)")
print(f"     - Demand fulfillment (120 months)")
print(f"     - Inventory balance (120 months)")
print(f"     - Days-on-hand requirements")
print(f"     - Capacity linking (inventory ≤ shelf configs)")
print(f"     - Configuration assignment constraints")

# Create and solve model
print("\n" + "="*100)
print("SOLVING PHASE 2 OPTIMIZATION MODEL")
print("="*100)
print(f"\nModel statistics:")
print(f"  Decision variables: ~{len(months) * len(skus) * len(facilities) * 3 + len(config_ids) * len(facilities) * len(storage_types):,}")
print(f"  Constraints: ~{len(months) * len(skus) * (len(facilities) + 1):,}")
print(f"\nSolving... (this may take several minutes)")

warehouse_model = Model(
    m,
    name="phase2_multiperiod",
    equations=m.getEquations(),
    problem="MINLP",
    sense=Sense.MIN,
    objective=total_cost
)

warehouse_model.solve()

print("\n" + "="*100)
print("OPTIMIZATION COMPLETE")
print("="*100)

# Extract results
print("\n[RESULTS] Extracting solution...")

if warehouse_model.status != 1:
    print(f"\n⚠️  WARNING: Model status = {warehouse_model.status}")
    print("   Model may not have found optimal solution")
else:
    print("   ✓ Optimal solution found")

# Expansion decisions
print("\n" + "="*100)
print("EXPANSION DECISIONS")
print("="*100)

sac_tier1_val = expansion_sac_tier1.toValue()
sac_tier2_val = expansion_sac_tier2.toValue()
austin_val = expansion_austin.toValue()

print(f"\nSacramento:")
print(f"  Tier 1 (first 100K @ $2/sqft): {sac_tier1_val:>15,.0f} sq ft")
print(f"  Tier 2 (next 150K @ $4/sqft):  {sac_tier2_val:>15,.0f} sq ft")
print(f"  Total expansion:                {sac_tier1_val + sac_tier2_val:>15,.0f} sq ft")
print(f"  Cost: ${sac_tier1_val * EXPANSION_COST_SAC_TIER1 + sac_tier2_val * EXPANSION_COST_SAC_TIER2:>15,.0f}")

print(f"\nAustin:")
print(f"  Expansion @ $1.5/sqft:          {austin_val:>15,.0f} sq ft")
print(f"  Cost: ${austin_val * EXPANSION_COST_AUSTIN:>15,.0f}")

total_expansion_cost = (sac_tier1_val * EXPANSION_COST_SAC_TIER1 +
                        sac_tier2_val * EXPANSION_COST_SAC_TIER2 +
                        austin_val * EXPANSION_COST_AUSTIN)

print(f"\n{'='*100}")
print(f"Total expansion cost: ${total_expansion_cost:,.0f}")

# Shelf deployment by configuration
print("\n" + "="*100)
print("SHELF DEPLOYMENT BY CONFIGURATION")
print("="*100)

shelves_config_df = shelves_per_config.records
shelves_config_df.columns = ['Facility', 'Storage_Type', 'Config_ID', 'Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
shelves_config_df = shelves_config_df[shelves_config_df['Shelves'] > 0.01].sort_values('Shelves', ascending=False)

if len(shelves_config_df) > 0:
    print(f"\nDeployed configurations (showing configs with shelves > 0):")
    print(f"  {'Facility':<15} {'Storage':<10} {'Config_ID':<10} {'Shelves':<10}")
    print(f"  {'-'*50}")
    for _, row in shelves_config_df.head(20).iterrows():
        print(f"  {row['Facility']:<15} {row['Storage_Type']:<10} {row['Config_ID']:<10} {row['Shelves']:>8,.0f}")

    if len(shelves_config_df) > 20:
        print(f"  ... and {len(shelves_config_df) - 20} more configurations")
else:
    print("  ⚠️  No configurations deployed (model may be infeasible)")

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

# 1. Expansion summary
expansion_summary = pd.DataFrame([{
    'Facility': 'Sacramento',
    'Tier': 'Tier 1',
    'Expansion_sqft': sac_tier1_val,
    'Cost_per_sqft': EXPANSION_COST_SAC_TIER1,
    'Total_Cost': sac_tier1_val * EXPANSION_COST_SAC_TIER1
}, {
    'Facility': 'Sacramento',
    'Tier': 'Tier 2',
    'Expansion_sqft': sac_tier2_val,
    'Cost_per_sqft': EXPANSION_COST_SAC_TIER2,
    'Total_Cost': sac_tier2_val * EXPANSION_COST_SAC_TIER2
}, {
    'Facility': 'Austin',
    'Tier': 'Flat',
    'Expansion_sqft': austin_val,
    'Cost_per_sqft': EXPANSION_COST_AUSTIN,
    'Total_Cost': austin_val * EXPANSION_COST_AUSTIN
}])
expansion_summary.to_csv(RESULTS_DIR / 'expansion_summary.csv', index=False)
print(f"  ✓ Saved: expansion_summary.csv")

# 2. Shelf deployment
shelves_config_df.to_csv(RESULTS_DIR / 'shelf_deployment_by_config.csv', index=False)
print(f"  ✓ Saved: shelf_deployment_by_config.csv")

# 3. Inventory trajectories (sample - first 12 months)
inv_df = inventory.records
inv_df.columns = ['Month', 'SKU', 'Facility', 'Inventory', 'Marginal', 'Lower', 'Upper', 'Scale']
inv_df = inv_df[inv_df['Month'].astype(int) <= 12]  # First year only
inv_df.to_csv(RESULTS_DIR / 'inventory_first_year.csv', index=False)
print(f"  ✓ Saved: inventory_first_year.csv (first 12 months)")

print("\n" + "="*100)
print("PHASE 2 COMPLETE")
print("="*100)
print(f"\nResults saved to: {RESULTS_DIR}")
print(f"\nNext step: Review configurations and inventory trajectories")
print(f"           Adjust DoH requirements or expansion limits if needed")
