"""
PHASE 2: TEST 14/3 DAYS-ON-HAND POLICY
========================================

Test reduced days-on-hand requirements:
- International SKUs: 14 calendar days (instead of 35-46)
- Domestic SKUs: 3 calendar days (instead of 3-15)

Goal: See if lower safety stock reduces shelf requirements
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
print("PHASE 2: TESTING 14/3 DAYS-ON-HAND POLICY")
print("="*100)
print("\nNEW POLICY:")
print("  International SKUs (SKUW, SKUE): 14 calendar days")
print("  Domestic SKUs (all others):       3 calendar days")
print()

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

# Load data
print("[1/6] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_14_3_business_days.csv")  # Corrected CSV
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')
print("   ✓ Data loaded (using Lead TIme_14_3_business_days.csv - 10/3 business days)")

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

# Parse days-on-hand (per facility)
print("\n[4/6] Processing days-on-hand (14/3 policy)...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_col = f"{fac} - Days on Hand" if fac != "Austin" else "Austin Days on Hand"
        if doh_col in row:
            doh_data[(sku, fac)] = float(row[doh_col])

print("\n   Days-on-hand by SKU type:")
intl_skus = ['SKUW1', 'SKUW2', 'SKUW3', 'SKUE1', 'SKUE2', 'SKUE3']
print(f"   International (SKUW, SKUE): {doh_data.get(('SKUW1', 'Columbus'), 0)} business days (14 calendar days)")
print(f"   Domestic (all others):      {doh_data.get(('SKUA1', 'Columbus'), 0)} business days (3 calendar days)")

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

print("\n[7/6] Building GAMSPy model...")

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

# Days-on-hand per facility
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
slack_doh = Variable(m, name="slack_doh", domain=[t, s, f], type="positive")
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")
slack_shelf_columbus = Variable(m, name="slack_shelf_columbus", domain=st, type="positive")

total_slack = Variable(m, name="total_slack", type="free")

print("   ✓ Variables created")

# Equations
print("\n   Creating constraints...")

obj = Equation(m, name="obj")
obj[...] = (
    total_slack ==
    Sum([t, s], slack_demand[t, s] * 1000) +
    Sum([t, s, f], slack_doh[t, s, f] * 10) +
    Sum(st, slack_shelf_sac[st] * 100) +
    Sum(st, slack_shelf_austin[st] * 100) +
    Sum(st, slack_shelf_columbus[st] * 100)
)

demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) + slack_demand[t, s] >= demand[t, s]

inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] >= shipments[t, s, f]

doh_constraint = Equation(m, name="doh_constraint", domain=[t, s, f])
doh_constraint[t, s, f] = (
    inventory[t, s, f] + slack_doh[t, s, f] >=
    (demand[t, s] / WORKING_DAYS_PER_MONTH) * days_on_hand[s, f]
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
print("SOLVING MODEL WITH 14/3 DAYS-ON-HAND POLICY")
print("="*100)

test_model = Model(
    m,
    name="phase2_14_3_doh",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_slack
)

test_model.solve()

print("\n" + "="*100)
print("RESULTS: 14/3 DAYS-ON-HAND POLICY")
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

print("\n" + "="*100)
print("COMPARISON: ORIGINAL vs 14/3 POLICY")
print("="*100)

print("\nOriginal days-on-hand (from previous run):")
print("  International: 35-46 days")
print("  Domestic: 3-15 days")
print("  Columbus Pallet slack: 30,594 shelves")
print()
print("New 14/3 policy:")
print("  International: 14 days")
print("  Domestic: 3 days")

if len(columbus_slack_df) > 0:
    columbus_pallet = columbus_slack_df[columbus_slack_df['Storage_Type'] == 'Pallet']
    if len(columbus_pallet) > 0:
        new_slack = columbus_pallet.iloc[0]['Excess_Shelves']
        print(f"  Columbus Pallet slack: {new_slack:,.0f} shelves")
        improvement = ((30594 - new_slack) / 30594 * 100) if new_slack < 30594 else 0
        if improvement > 0:
            print(f"  Improvement: {improvement:.1f}% reduction")
        else:
            print(f"  Change: {((new_slack - 30594) / 30594 * 100):.1f}% increase")
else:
    print("  Columbus Pallet slack: 0 shelves")
    print("  Improvement: 100% reduction!")

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
