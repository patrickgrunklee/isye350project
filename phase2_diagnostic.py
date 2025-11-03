"""
PHASE 2 DIAGNOSTIC: Identify Infeasibility
===========================================

Simplified model to identify what's causing infeasibility:
- Remove DoH constraints temporarily
- Simplify inventory balance
- Check if basic demand can be met
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

print("="*100)
print("PHASE 2 DIAGNOSTIC: INFEASIBILITY ANALYSIS")
print("="*100)
print("\nSimplified model:")
print("  - NO days-on-hand constraints")
print("  - NO time-indexed inventory balance")
print("  - ONLY: Can we meet total demand with available capacity?\n")

# Load data
print("[1] Loading data...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / "packing_configurations.csv")

# SKUs
skus = list(sku_details_df['SKU Number'])
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

# Total demand over 120 months
total_demand = {}
for sku in skus:
    total_demand[sku] = demand_df[sku].sum()

print(f"   ✓ Total demand over 120 months:")
for sku in skus[:5]:
    print(f"     {sku}: {total_demand[sku]:>10,.0f} units")
print(f"     ... and {len(skus) - 5} more SKUs\n")

# Current shelves
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

# Phase 1 configs
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

print(f"[2] Current capacity:")
for (fac, st), shelves in sorted(curr_shelves.items()):
    print(f"     {fac:<15} {st:<10}: {shelves:>8,} shelves")

# Build model
print(f"\n[3] Building diagnostic model...")
m = Container()

# Sets
s = Set(m, name="s", records=skus)
c = Set(m, name="c", records=[str(i) for i in config_ids])

# Parameters
total_demand_records = [(sku, total_demand[sku]) for sku in skus]
total_demand_param = Parameter(m, name="total_demand", domain=s, records=total_demand_records)

config_units_records = []
for config_id in config_ids:
    for sku in skus:
        units = config_units.get(config_id, {}).get(sku, 0)
        if units > 0:
            config_units_records.append((str(config_id), sku, units))
config_units_param = Parameter(m, name="config_units", domain=[c, s], records=config_units_records)

# Variables
shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="integer")
slack = Variable(m, name="slack", domain=s, type="positive")  # Unmet demand

# Objective: minimize unmet demand
total_slack = Variable(m, name="total_slack", type="free")

obj = Equation(m, name="obj")
obj[...] = total_slack == Sum(s, slack[s])

# Demand constraint with slack
demand_with_slack = Equation(m, name="demand_with_slack", domain=s)
demand_with_slack[s] = (
    Sum(c, shelves_per_config[c] * config_units_param[c, s]) + slack[s] >= total_demand_param[s]
)

# Capacity limits (assume 2× expansion for diagnostic)
max_shelves_per_config = {}
for config_id in config_ids:
    fac = config_facility[config_id]
    st = config_storage_type[config_id]
    max_shelves_per_config[config_id] = curr_shelves.get((fac, st), 0) * 3  # 3× current

max_shelves_records = [(str(cid), max_shelves_per_config[cid]) for cid in config_ids]
max_shelves_param = Parameter(m, name="max_shelves", domain=c, records=max_shelves_records)

shelf_limit = Equation(m, name="shelf_limit", domain=c)
shelf_limit[c] = shelves_per_config[c] <= max_shelves_param[c]

# Solve
print(f"\n[4] Solving...")
diag_model = Model(m, name="diagnostic", equations=m.getEquations(), problem="MIP", sense=Sense.MIN, objective=total_slack)
diag_model.solve()

print("\n" + "="*100)
print("DIAGNOSTIC RESULTS")
print("="*100)

if diag_model.status == 1:
    print("\n✓ Model is FEASIBLE (can meet demand with 3× capacity expansion)")
else:
    print(f"\n⚠️  Model status: {diag_model.status}")

total_slack_val = total_slack.toValue()
print(f"\nTotal unmet demand (slack): {total_slack_val:,.0f} units")

if total_slack_val > 0:
    print("\nSKUs with unmet demand:")
    slack_df = slack.records
    slack_df.columns = ['SKU', 'Unmet_Demand', 'Marginal', 'Lower', 'Upper', 'Scale']
    slack_df = slack_df[slack_df['Unmet_Demand'] > 1].sort_values('Unmet_Demand', ascending=False)

    for _, row in slack_df.head(10).iterrows():
        sku = row['SKU']
        unmet = row['Unmet_Demand']
        total_dem = total_demand[sku]
        pct = (unmet / total_dem * 100) if total_dem > 0 else 0
        print(f"  {sku}: {unmet:>12,.0f} / {total_dem:>12,.0f} ({pct:>5.1f}% unmet)")

# Deployed configs
shelves_df = shelves_per_config.records
shelves_df.columns = ['Config_ID', 'Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
shelves_df = shelves_df[shelves_df['Shelves'] > 0.1].sort_values('Shelves', ascending=False)

print(f"\n" + "="*100)
print("CONFIGURATION DEPLOYMENT (Top 15)")
print("="*100)

for _, row in shelves_df.head(15).iterrows():
    config_id = int(float(row['Config_ID']))
    fac = config_facility[config_id]
    st = config_storage_type[config_id]
    shelves = row['Shelves']
    max_allowed = max_shelves_per_config[config_id]
    print(f"Config {config_id:>3}: {fac:<15} {st:<10} - {shelves:>8,.0f} shelves (max: {max_allowed:>8,})")

print("\n" + "="*100)
print("CONCLUSION")
print("="*100)

if total_slack_val == 0:
    print("\n✓ The model CAN meet all demand with realistic expansion")
    print("  Issue is likely in the DoH or inventory balance constraints")
else:
    print(f"\n⚠️  The model CANNOT meet demand even with 3× expansion")
    print(f"  Total unmet: {total_slack_val:,.0f} units")
    print("  Recommendation: Check SKU-to-storage-type assignments or increase capacity")
