"""
CHECK ALL STORAGE TYPES FOR SLACK

Show violations across ALL storage types (Bins, Racking, Pallet, Hazmat)
to verify if the 22,580 shelves are ONLY pallets or include other types
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

WORKING_DAYS_PER_MONTH = 21

print("="*100)
print("DETAILED STORAGE TYPE ANALYSIS")
print("="*100)

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

# Load data (abbreviated version)
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_14_3_business_days.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')

sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_qty = parse_quantity(row['Sell Pack Quantity'])
    sku_data[sku] = {'sell_qty': sell_qty}

skus = list(sku_data.keys())
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])

facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_col = f"{fac} - Days on Hand" if fac != "Austin" else "Austin Days on Hand"
        if doh_col in row:
            doh_data[(sku, fac)] = float(row[doh_col])

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

print("Building GAMSPy model...")

m = Container()
s = Set(m, name="s", records=skus)
f = Set(m, name="f", records=facilities)
st = Set(m, name="st", records=storage_types)
t = Set(m, name="t", records=[str(i) for i in months])
c = Set(m, name="c", records=[str(i) for i in config_ids])

demand_records = [(str(month), sku, demand_data[(month, sku)]) for month, sku in demand_data.keys()]
demand = Parameter(m, name="demand", domain=[t, s], records=demand_records)

doh_records = [(sku, fac, doh_data.get((sku, fac), 0)) for sku in skus for fac in facilities]
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=doh_records)

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

shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="positive")
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

slack_demand = Variable(m, name="slack_demand", domain=[t, s], type="positive")
slack_doh = Variable(m, name="slack_doh", domain=[t, s, f], type="positive")
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")
slack_shelf_columbus = Variable(m, name="slack_shelf_columbus", domain=st, type="positive")

total_slack = Variable(m, name="total_slack", type="free")

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

print("Solving...")

test_model = Model(
    m,
    name="storage_type_check",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_slack
)

test_model.solve()

print("\n" + "="*100)
print("DETAILED STORAGE TYPE SLACK ANALYSIS")
print("="*100)

# Show ALL storage types for each facility
for fac_name, slack_var in [('Sacramento', slack_shelf_sac),
                             ('Austin', slack_shelf_austin),
                             ('Columbus', slack_shelf_columbus)]:
    print(f"\n{fac_name}:")
    print("-" * 80)
    print(f"{'Storage Type':<15} {'Current Shelves':<20} {'Slack Shelves':<20} {'Total Needed':<20}")
    print("-" * 80)

    slack_df = slack_var.records
    slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']

    for st_type in storage_types:
        current = curr_shelves.get((fac_name, st_type), 0)
        slack_row = slack_df[slack_df['Storage_Type'] == st_type]

        if len(slack_row) > 0:
            excess = slack_row['Excess_Shelves'].values[0]
        else:
            excess = 0.0

        total_needed = current + excess

        if excess > 0.1:
            print(f"{st_type:<15} {current:<20,} {excess:<20,.0f} {total_needed:<20,.0f} ⚠️")
        else:
            print(f"{st_type:<15} {current:<20,} {excess:<20,.0f} {total_needed:<20,.0f} ✓")

print("\n" + "="*100)
print("ANSWER TO YOUR QUESTION")
print("="*100)
print("\nAre these shelves all pallets?")
print("Check the table above - it shows slack for ALL storage types:")
print("  - Bins")
print("  - Racking")
print("  - Pallet")
print("  - Hazmat")
print()
print("If only Pallet shows slack > 0, then YES, all violations are pallets.")
print("If other types also show slack > 0, then NO, violations include other storage types.")
print("="*100)
