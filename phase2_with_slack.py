"""
PHASE 2 WITH SLACK/SURPLUS VARIABLES
=====================================

This version adds slack and surplus variables to ALL constraints to:
1. Identify which constraints are infeasible
2. Determine capacity bottlenecks
3. Show how much capacity is needed beyond current limits

Objective: Minimize total slack (constraint violations)
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
print("PHASE 2 WITH SLACK/SURPLUS VARIABLES - CONSTRAINT ANALYSIS")
print("="*100)
print("\nObjective: Identify binding constraints and capacity bottlenecks")
print("Approach: Add slack variables to all constraints, minimize total slack\n")

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
print("[1/7] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / "packing_configurations.csv")
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/7] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_qty = parse_quantity(row['Sell Pack Quantity'])
    sku_data[sku] = {'sell_qty': sell_qty}

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs")

# Extract demand data
print("\n[3/7] Extracting demand data...")
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])
print(f"   ✓ Loaded demand for {len(months)} months × {len(skus)} SKUs")

# Parse days-on-hand
print("\n[4/7] Processing days-on-hand...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_col = f"{fac} Days on Hand"
        if doh_col in row:
            doh_data[(sku, fac)] = float(row[doh_col])

# Load current shelves
print("\n[5/7] Loading current shelving capacity...")
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

# Process Phase 1 configs
print("\n[6/7] Processing Phase 1 packing configurations...")
config_units = {}
config_facility = {}
config_storage_type = {}

for _, row in packing_configs_df.iterrows():
    config_id = int(row['Config_ID'])
    sku = row['SKU']
    units = int(row['Packages_per_Shelf']) * int(row['Units_per_Package'])

    if config_id not in config_units:
        config_units[config_id] = {}
        config_facility[config_id] = row['Facility']
        config_storage_type[config_id] = row['Storage_Type']

    config_units[config_id][sku] = units

config_ids = sorted(packing_configs_df['Config_ID'].unique())
print(f"   ✓ Processed {len(config_ids)} configurations")

print("\n[7/7] Building GAMSPy model with slack variables...")

# Create GAMSPy container
m = Container()

# Sets
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
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

# Config facility/storage matching
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

print("   ✓ Sets and parameters created")

# Decision Variables
print("\n   Creating decision variables with slack...")

# Core variables
shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="positive")
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

# Slack variables for each constraint type
slack_demand = Variable(m, name="slack_demand", domain=[t, s], type="positive")  # Unmet demand
slack_doh = Variable(m, name="slack_doh", domain=[t, s, f], type="positive")  # DoH shortfall
slack_capacity = Variable(m, name="slack_capacity", domain=[t, s, f], type="positive")  # Over-capacity
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")  # Sacramento shelf limit
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")  # Austin shelf limit
slack_shelf_columbus = Variable(m, name="slack_shelf_columbus", domain=st, type="positive")  # Columbus shelf limit

# Total slack
total_slack = Variable(m, name="total_slack", type="free")

print("   ✓ Variables created")

# Equations with slack
print("\n   Creating constraints with slack variables...")

# Objective: minimize total slack
obj = Equation(m, name="obj")
obj[...] = (
    total_slack ==
    Sum([t, s], slack_demand[t, s] * 1000) +  # High penalty for unmet demand
    Sum([t, s, f], slack_doh[t, s, f] * 10) +  # Medium penalty for DoH violations
    Sum([t, s, f], slack_capacity[t, s, f] * 1) +  # Low penalty for capacity violations
    Sum(st, slack_shelf_sac[st] * 100) +  # Penalty for shelf limit violations
    Sum(st, slack_shelf_austin[st] * 100) +
    Sum(st, slack_shelf_columbus[st] * 100)
)

# Demand fulfillment with slack
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) + slack_demand[t, s] >= demand[t, s]

# Inventory balance
inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] >= shipments[t, s, f]

# Days-on-hand with slack (25% of original)
doh_constraint = Equation(m, name="doh_constraint", domain=[t, s, f])
doh_constraint[t, s, f] = (
    inventory[t, s, f] + slack_doh[t, s, f] >=
    (demand[t, s] / WORKING_DAYS_PER_MONTH) * days_on_hand[s, f] * 0.25
)

# Capacity with slack
capacity_link = Equation(m, name="capacity_link", domain=[t, s, f])
capacity_link[t, s, f] = (
    inventory[t, s, f] <=
    Sum(c, shelves_per_config[c] * config_units_param[c, s] * config_fac_param[c, f]) +
    slack_capacity[t, s, f]
)

# Shelf limits with slack
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
    curr_shelves_param["Columbus", st] + slack_shelf_columbus[st]
)

print("   ✓ Constraints created")

# Solve
print("\n" + "="*100)
print("SOLVING MODEL WITH SLACK VARIABLES")
print("="*100)
print("\nSolving... (minimizing total constraint violations)")

slack_model = Model(
    m,
    name="phase2_slack",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_slack
)

slack_model.solve()

print("\n" + "="*100)
print("SLACK VARIABLE ANALYSIS - CONSTRAINT VIOLATIONS")
print("="*100)

total_slack_val = total_slack.toValue()
print(f"\nTotal slack value: {total_slack_val:,.2f}")

# Analyze demand slack
print("\n" + "="*100)
print("[1] DEMAND FULFILLMENT VIOLATIONS")
print("="*100)

demand_slack_df = slack_demand.records
demand_slack_df.columns = ['Month', 'SKU', 'Unmet_Demand', 'Marginal', 'Lower', 'Upper', 'Scale']
demand_slack_df = demand_slack_df[demand_slack_df['Unmet_Demand'] > 0.1].sort_values('Unmet_Demand', ascending=False)

if len(demand_slack_df) > 0:
    print(f"\nSKUs with unmet demand (top 10):")
    print(f"  {'SKU':<10} {'Month':<8} {'Unmet Demand':<15}")
    print(f"  {'-'*40}")
    for _, row in demand_slack_df.head(10).iterrows():
        print(f"  {row['SKU']:<10} {row['Month']:<8} {row['Unmet_Demand']:>12,.0f}")

    total_unmet = demand_slack_df['Unmet_Demand'].sum()
    print(f"\n  Total unmet demand: {total_unmet:,.0f} units")
else:
    print("\n✓ All demand can be met!")

# Analyze DoH slack
print("\n" + "="*100)
print("[2] DAYS-ON-HAND VIOLATIONS (25% requirement)")
print("="*100)

doh_slack_df = slack_doh.records
doh_slack_df.columns = ['Month', 'SKU', 'Facility', 'DoH_Shortfall', 'Marginal', 'Lower', 'Upper', 'Scale']
doh_slack_df = doh_slack_df[doh_slack_df['DoH_Shortfall'] > 0.1].sort_values('DoH_Shortfall', ascending=False)

if len(doh_slack_df) > 0:
    print(f"\nDoH violations (top 10):")
    print(f"  {'SKU':<10} {'Facility':<12} {'Month':<8} {'Shortfall':<15}")
    print(f"  {'-'*50}")
    for _, row in doh_slack_df.head(10).iterrows():
        print(f"  {row['SKU']:<10} {row['Facility']:<12} {row['Month']:<8} {row['DoH_Shortfall']:>12,.0f}")

    total_doh_slack = doh_slack_df['DoH_Shortfall'].sum()
    print(f"\n  Total DoH shortfall: {total_doh_slack:,.0f} units")
else:
    print("\n✓ All DoH requirements can be met!")

# Analyze capacity slack
print("\n" + "="*100)
print("[3] CAPACITY VIOLATIONS (inventory > shelf capacity)")
print("="*100)

capacity_slack_df = slack_capacity.records
capacity_slack_df.columns = ['Month', 'SKU', 'Facility', 'Excess_Inventory', 'Marginal', 'Lower', 'Upper', 'Scale']
capacity_slack_df = capacity_slack_df[capacity_slack_df['Excess_Inventory'] > 0.1].sort_values('Excess_Inventory', ascending=False)

if len(capacity_slack_df) > 0:
    print(f"\nCapacity violations (top 10):")
    print(f"  {'SKU':<10} {'Facility':<12} {'Month':<8} {'Excess Inv':<15}")
    print(f"  {'-'*50}")
    for _, row in capacity_slack_df.head(10).iterrows():
        print(f"  {row['SKU']:<10} {row['Facility']:<12} {row['Month']:<8} {row['Excess_Inventory']:>12,.0f}")

    total_capacity_slack = capacity_slack_df['Excess_Inventory'].sum()
    print(f"\n  Total excess inventory: {total_capacity_slack:,.0f} units")
else:
    print("\n✓ All inventory fits within shelf capacity!")

# Analyze shelf limit violations
print("\n" + "="*100)
print("[4] SHELF LIMIT VIOLATIONS")
print("="*100)

print("\nSacramento:")
sac_slack_df = slack_shelf_sac.records
sac_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
sac_slack_df = sac_slack_df[sac_slack_df['Excess_Shelves'] > 0.1]
if len(sac_slack_df) > 0:
    for _, row in sac_slack_df.iterrows():
        st_type = row['Storage_Type']
        excess = row['Excess_Shelves']
        current = curr_shelves.get(('Sacramento', st_type), 0)
        print(f"  {st_type:<12}: Need {excess:>8,.0f} more shelves (current: {current:>8,})")
else:
    print("  ✓ Within current capacity")

print("\nAustin:")
austin_slack_df = slack_shelf_austin.records
austin_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
austin_slack_df = austin_slack_df[austin_slack_df['Excess_Shelves'] > 0.1]
if len(austin_slack_df) > 0:
    for _, row in austin_slack_df.iterrows():
        st_type = row['Storage_Type']
        excess = row['Excess_Shelves']
        current = curr_shelves.get(('Austin', st_type), 0)
        print(f"  {st_type:<12}: Need {excess:>8,.0f} more shelves (current: {current:>8,})")
else:
    print("  ✓ Within current capacity")

print("\nColumbus:")
columbus_slack_df = slack_shelf_columbus.records
columbus_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
columbus_slack_df = columbus_slack_df[columbus_slack_df['Excess_Shelves'] > 0.1]
if len(columbus_slack_df) > 0:
    for _, row in columbus_slack_df.iterrows():
        st_type = row['Storage_Type']
        excess = row['Excess_Shelves']
        current = curr_shelves.get(('Columbus', st_type), 0)
        print(f"  {st_type:<12}: Need {excess:>8,.0f} more shelves (current: {current:>8,}) ⚠️  CANNOT EXPAND")
else:
    print("  ✓ Within current capacity")

# Save results
print("\n[SAVING RESULTS]")

demand_slack_df.to_csv(RESULTS_DIR / 'slack_demand_violations.csv', index=False)
doh_slack_df.to_csv(RESULTS_DIR / 'slack_doh_violations.csv', index=False)
capacity_slack_df.to_csv(RESULTS_DIR / 'slack_capacity_violations.csv', index=False)
sac_slack_df.to_csv(RESULTS_DIR / 'slack_shelf_sacramento.csv', index=False)
austin_slack_df.to_csv(RESULTS_DIR / 'slack_shelf_austin.csv', index=False)
columbus_slack_df.to_csv(RESULTS_DIR / 'slack_shelf_columbus.csv', index=False)

print(f"  ✓ Saved all slack analysis results")

print("\n" + "="*100)
print("SLACK ANALYSIS COMPLETE")
print("="*100)
print("\nRecommendations:")
print("  1. Review shelf limit violations to determine expansion needs")
print("  2. Check capacity violations to identify storage type bottlenecks")
print("  3. Analyze demand violations to find SKUs that need redistribution")
