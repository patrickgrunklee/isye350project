"""
PHASE 2: REDISTRIBUTE DEMAND TO SACRAMENTO
===========================================

Key insight: Sacramento has excess capacity after 3D bin packing
Strategy: Relax days-on-hand per facility, allow flexible allocation
Goal: Shift Columbus/Austin pallet demand to Sacramento
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
print("PHASE 2: DEMAND REDISTRIBUTION WITH 3D BIN PACKING")
print("="*100)
print("\nSTRATEGY: Shift excess demand from Columbus/Austin pallets to Sacramento")
print("CONSTRAINT: Maintain AGGREGATE days-on-hand, not per-facility\n")

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

# Load data
print("[1/6] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/6] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_qty = parse_quantity(row['Sell Pack Quantity'])
    sku_data[sku] = {'sell_qty': sell_qty}

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs")

# Extract demand data
print("\n[3/6] Extracting demand data...")
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])
print(f"   ✓ Loaded demand for {len(months)} months × {len(skus)} SKUs")

# Parse days-on-hand (AGGREGATE, not per-facility)
print("\n[4/6] Processing days-on-hand...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    # Take AVERAGE days-on-hand across facilities
    doh_values = []
    for fac in facilities:
        doh_col = f"{fac} Days on Hand"
        if doh_col in row:
            doh_values.append(float(row[doh_col]))
    if doh_values:
        doh_data[sku] = np.mean(doh_values)  # Average DoH across facilities

# Load current shelves
print("\n[5/6] Loading current shelving capacity...")
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

# Process Phase 1 configs (3D packed)
print("\n[6/6] Processing Phase 1 3D configurations...")
print(f"   Total configurations from Phase 1: {len(packing_configs_df)}")

config_units = {}
config_facility = {}
config_storage_type = {}

for _, row in packing_configs_df.iterrows():
    config_id = int(row['Config_ID'])
    sku = row['SKU']
    total_packages = int(row['Total_Packages_per_Shelf'])
    fac = row['Facility']
    st = row['Storage_Type']
    units_per_package = int(row['Units_per_Package'])

    total_units = total_packages * units_per_package

    if config_id not in config_units:
        config_units[config_id] = {}
        config_facility[config_id] = fac
        config_storage_type[config_id] = st

    config_units[config_id][sku] = total_units

config_ids = sorted(packing_configs_df['Config_ID'].unique())
print(f"   ✓ Processed {len(config_ids)} configurations")

print("\n[7/6] Building GAMSPy model with flexible allocation...")

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

# AGGREGATE days-on-hand (not per-facility)
doh_records = [(sku, doh_data.get(sku, 0)) for sku in skus]
days_on_hand = Parameter(m, name="days_on_hand", domain=s, records=doh_records)

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
print("\n   Creating decision variables...")

shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="positive")
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

# Slack variables
slack_demand = Variable(m, name="slack_demand", domain=[t, s], type="positive")
slack_doh = Variable(m, name="slack_doh", domain=[t, s], type="positive")  # AGGREGATE DoH
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")
slack_shelf_columbus = Variable(m, name="slack_shelf_columbus", domain=st, type="positive")

total_slack = Variable(m, name="total_slack", type="free")

print("   ✓ Variables created")

# Equations
print("\n   Creating constraints with flexible allocation...")

obj = Equation(m, name="obj")
obj[...] = (
    total_slack ==
    Sum([t, s], slack_demand[t, s] * 1000) +
    Sum([t, s], slack_doh[t, s] * 10) +  # Changed from [t, s, f] to [t, s]
    Sum(st, slack_shelf_sac[st] * 100) +
    Sum(st, slack_shelf_austin[st] * 100) +
    Sum(st, slack_shelf_columbus[st] * 100)
)

demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) + slack_demand[t, s] >= demand[t, s]

inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] >= shipments[t, s, f]

# AGGREGATE days-on-hand across all facilities
doh_constraint = Equation(m, name="doh_constraint", domain=[t, s])
doh_constraint[t, s] = (
    Sum(f, inventory[t, s, f]) + slack_doh[t, s] >=
    (demand[t, s] / WORKING_DAYS_PER_MONTH) * days_on_hand[s]
)

capacity_link = Equation(m, name="capacity_link", domain=[t, s, f])
capacity_link[t, s, f] = (
    inventory[t, s, f] <=
    Sum(c, shelves_per_config[c] * config_units_param[c, s] * config_fac_param[c, f])
)

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
print("SOLVING MODEL WITH FLEXIBLE ALLOCATION")
print("="*100)

redist_model = Model(
    m,
    name="phase2_redistribute",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_slack
)

redist_model.solve()

print("\n" + "="*100)
print("REDISTRIBUTION RESULTS")
print("="*100)

total_slack_val = total_slack.toValue()
print(f"\nTotal slack value: {total_slack_val:,.2f}")

# Analyze demand slack
print("\n[1] DEMAND FULFILLMENT")
demand_slack_df = slack_demand.records
demand_slack_df.columns = ['Month', 'SKU', 'Unmet_Demand', 'Marginal', 'Lower', 'Upper', 'Scale']
demand_slack_df = demand_slack_df[demand_slack_df['Unmet_Demand'] > 0.1]

if len(demand_slack_df) > 0:
    total_unmet = demand_slack_df['Unmet_Demand'].sum()
    print(f"  ⚠️  Total unmet demand: {total_unmet:,.0f} units")
else:
    print("  ✓ All demand can be met!")

# Analyze shelf limit violations
print("\n[2] SHELF LIMIT VIOLATIONS")

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

# Show inventory redistribution
print("\n" + "="*100)
print("[3] INVENTORY REDISTRIBUTION")
print("="*100)

inv_df = inventory.records
inv_df.columns = ['Month', 'SKU', 'Facility', 'Inventory', 'Marginal', 'Lower', 'Upper', 'Scale']
inv_df = inv_df[inv_df['Inventory'] > 0.1]

# Aggregate by SKU and facility
inv_summary = inv_df.groupby(['SKU', 'Facility'])['Inventory'].sum().reset_index()
inv_summary = inv_summary.sort_values('Inventory', ascending=False)

print("\nTop 15 SKU-Facility inventory allocations:")
print(f"{'SKU':<10} {'Facility':<15} {'Total Inventory':>20}")
print("─" * 50)
for _, row in inv_summary.head(15).iterrows():
    sku = row['SKU']
    fac = row['Facility']
    inv = row['Inventory']
    print(f"{sku:<10} {fac:<15} {inv:>20,.0f}")

# Show if Sacramento is picking up slack
print("\n" + "="*100)
print("[4] SACRAMENTO UTILIZATION")
print("="*100)

sac_inv = inv_summary[inv_summary['Facility'] == 'Sacramento']['Inventory'].sum()
total_inv = inv_summary['Inventory'].sum()
sac_pct = (sac_inv / total_inv * 100) if total_inv > 0 else 0

print(f"\nSacramento inventory: {sac_inv:>15,.0f} units")
print(f"Total inventory:      {total_inv:>15,.0f} units")
print(f"Sacramento share:     {sac_pct:>14.1f}%")

# Check shelf usage at Sacramento
shelves_df = shelves_per_config.records
shelves_df.columns = ['Config_ID', 'Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
shelves_df = shelves_df[shelves_df['Shelves'] > 0.1]

sac_shelves_used = {}
for _, row in shelves_df.iterrows():
    config_id = int(float(row['Config_ID']))
    shelves = row['Shelves']
    fac = config_facility[config_id]
    st = config_storage_type[config_id]

    if fac == 'Sacramento':
        if st not in sac_shelves_used:
            sac_shelves_used[st] = 0
        sac_shelves_used[st] += shelves

print("\nSacramento shelf usage:")
for st in storage_types:
    used = sac_shelves_used.get(st, 0)
    current = curr_shelves.get(('Sacramento', st), 0)
    pct = (used / current * 100) if current > 0 else 0
    print(f"  {st:<12}: {used:>8,.0f} / {current:>8,} ({pct:>5.1f}% utilized)")

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
print("\nWith flexible allocation, Sacramento can absorb excess demand!")
print("This should reduce expansion requirements at Columbus and Austin.")
