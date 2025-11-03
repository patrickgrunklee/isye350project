"""
PHASE 2 WITH PURE-SKU CONTINUOUS PACKING
=========================================

Key Changes:
1. Pure-SKU shelves: Continuous volume-based packing (no discrete item limits)
2. Mixed-SKU shelves: Follow 7-item discrete structure
3. Verify DoH is traditional safety stock calculation

Pure-SKU Capacity Calculation:
  - For Columbus Pallet: 448 cu ft total shelf volume
  - Capacity = floor(448 / package_volume)
  - Only limited by volume and weight (no item slot constraint)
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
print("PHASE 2: PURE-SKU CONTINUOUS PACKING MODEL - 5/2 DAYS-ON-HAND")
print("="*100)
print("\nAPPROACH:")
print("  - Pure-SKU shelves: Continuous packing (volume/weight only)")
print("  - Mixed-SKU shelves: Discrete 7-item structure")
print("  - DoH = Traditional safety stock (days of demand coverage)")
print("  - International: 5 business days | Domestic: 2 business days")
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
print("[1/7] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme_5_2_business_days.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')
print("   ✓ Data loaded")

# Parse SKU details with dimensions
print("\n[2/7] Processing SKU details and dimensions...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

    # Parse sell pack dimensions (in inches)
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728  # Convert to cu ft
    sell_weight = parse_weight(row['Sell Pack Weight'])

    sku_data[sku] = {
        'sell_qty': sell_qty,
        'sell_volume': sell_volume,
        'sell_weight': sell_weight
    }

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs with volume/weight data")

# Extract demand data
print("\n[3/7] Extracting demand data...")
months = list(range(1, 121))
demand_data = {}
for month_idx, month in enumerate(months):
    for sku in skus:
        demand_data[(month, sku)] = float(demand_df.iloc[month_idx][sku])
print(f"   ✓ Loaded demand for {len(months)} months × {len(skus)} SKUs")

# Parse days-on-hand (per facility)
print("\n[4/7] Processing days-on-hand (traditional safety stock)...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

doh_data = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        doh_col = f"{fac} - Days on Hand" if fac != "Austin" else "Austin Days on Hand"
        if doh_col in row:
            doh_data[(sku, fac)] = float(row[doh_col])

print("\n   Days-on-Hand Calculation:")
print("   Formula: Safety Stock = (Monthly Demand / 21 working days) × DoH")
print("   This is TRADITIONAL safety stock (days of demand coverage)")
print()
print(f"   International SKUs: {doh_data.get(('SKUW1', 'Columbus'), 0)} business days")
print(f"   Domestic SKUs:      {doh_data.get(('SKUA1', 'Columbus'), 0)} business days")

# Get shelf specifications
print("\n[5/7] Loading shelf specifications for pure-SKU continuous packing...")
shelf_specs = {}
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

    max_items = int(row['Max Items / Shelf'])
    weight_per_shelf = float(row['Weight Max / Shelf'])

    # Get dimensions
    dims_row = shelving_dims_df[
        (shelving_dims_df['Location'].str.strip() == fac) &
        (shelving_dims_df['Storage Type'].str.contains(st.replace('s', '')))  # Handle plural
    ]

    if len(dims_row) > 0:
        dims_str = str(dims_row['Dimensions (l,w,h)(ft)'].values[0])
        if dims_str != 'Auto':
            dims = tuple(float(d.strip()) for d in dims_str.split(' x '))
            shelf_volume = dims[0] * dims[1] * dims[2]
        else:
            shelf_volume = None
    else:
        shelf_volume = None

    shelf_specs[(fac, st)] = {
        'max_items': max_items,
        'weight_limit': weight_per_shelf,
        'volume': shelf_volume
    }

print("   ✓ Shelf specifications loaded")

# Generate PURE-SKU continuous packing configurations
print("\n[6/7] Generating pure-SKU continuous packing configurations...")
print("   Pure-SKU = entire shelf dedicated to one SKU (no discrete item limits)")

pure_sku_configs = []
config_id = packing_configs_df['Config_ID'].max() + 1

for fac in facilities:
    for st in storage_types:
        specs = shelf_specs.get((fac, st))
        if specs is None or specs['volume'] is None:
            continue

        shelf_vol = specs['volume']
        shelf_weight = specs['weight_limit']

        # For each SKU, calculate pure-SKU continuous capacity
        for sku in skus:
            pkg_vol = sku_data[sku]['sell_volume']
            pkg_weight = sku_data[sku]['sell_weight']

            # Continuous packing: limited only by volume and weight
            by_volume = int(shelf_vol / pkg_vol)
            by_weight = int(shelf_weight / pkg_weight)

            max_packages = min(by_volume, by_weight)

            if max_packages > 0:
                pure_sku_configs.append({
                    'Config_ID': config_id,
                    'Facility': fac,
                    'Storage_Type': st,
                    'SKU': sku,
                    'Packages_per_Item': max_packages,  # All in "one continuous slot"
                    'Items_per_Shelf': 1,
                    'Total_Packages_per_Shelf': max_packages,
                    'Weight_per_Package': pkg_weight,
                    'Total_Weight': max_packages * pkg_weight,
                    'Units_per_Package': 1,
                    'Config_Type': 'Pure_SKU_Continuous'
                })
                config_id += 1

# Combine with existing 3D bin packing configs (for mixed-SKU shelves)
print(f"   ✓ Generated {len(pure_sku_configs)} pure-SKU continuous configurations")

# Add config type to existing configs
packing_configs_df['Config_Type'] = 'Mixed_SKU_Discrete'

# Mark existing pure configs
for idx, row in packing_configs_df.iterrows():
    if row['Items_per_Shelf'] == 1 and row['Total_Packages_per_Shelf'] > 15:
        packing_configs_df.at[idx, 'Config_Type'] = 'Pure_SKU_Special'

# Combine
all_configs_df = pd.concat([
    packing_configs_df,
    pd.DataFrame(pure_sku_configs)
], ignore_index=True)

print(f"   Total configurations: {len(all_configs_df)}")
print(f"     - Mixed-SKU discrete: {len(packing_configs_df)}")
print(f"     - Pure-SKU continuous: {len(pure_sku_configs)}")

# Save combined configs
all_configs_df.to_csv(PHASE1_DIR / 'packing_configurations_pure_sku.csv', index=False)
print(f"   ✓ Saved to packing_configurations_pure_sku.csv")

# Load current shelves
print("\n[7/7] Loading current shelving capacity...")
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

# Process configs for optimization
config_units = {}
config_facility = {}
config_storage_type = {}

for _, row in all_configs_df.iterrows():
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

config_ids = sorted(all_configs_df['Config_ID'].unique())

print("\n" + "="*100)
print("BUILDING GAMSPY MODEL WITH PURE-SKU CONTINUOUS PACKING")
print("="*100)

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

print("   ✓ Sets and parameters created")

shelves_per_config = Variable(m, name="shelves_per_config", domain=c, type="positive")
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")

slack_demand = Variable(m, name="slack_demand", domain=[t, s], type="positive")
slack_doh = Variable(m, name="slack_doh", domain=[t, s, f], type="positive")
slack_shelf_sac = Variable(m, name="slack_shelf_sac", domain=st, type="positive")
slack_shelf_austin = Variable(m, name="slack_shelf_austin", domain=st, type="positive")
# NO slack for Columbus - must work within current capacity

total_slack = Variable(m, name="total_slack", type="free")

print("   ✓ Variables created (Columbus has no slack - must fit in current capacity)")

obj = Equation(m, name="obj")
obj[...] = (
    total_slack ==
    Sum([t, s], slack_demand[t, s] * 1000) +
    Sum([t, s, f], slack_doh[t, s, f] * 10) +
    Sum(st, slack_shelf_sac[st] * 100) +
    Sum(st, slack_shelf_austin[st] * 100)
    # No Columbus slack in objective
)

demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) + slack_demand[t, s] >= demand[t, s]

inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] >= shipments[t, s, f]

# DAYS-ON-HAND: Traditional safety stock calculation
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
    curr_shelves_param["Columbus", st]
    # NO slack - Columbus MUST fit within current capacity
)

print("   ✓ Constraints created")

print("\n" + "="*100)
print("SOLVING MODEL")
print("="*100)

pure_sku_model = Model(
    m,
    name="phase2_pure_sku",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_slack
)

pure_sku_model.solve()

print("\n" + "="*100)
print("RESULTS: PURE-SKU CONTINUOUS PACKING")
print("="*100)

total_slack_val = total_slack.toValue()
print(f"\nTotal slack value: {total_slack_val:,.2f}")

print("\n[1] DEMAND FULFILLMENT")
demand_slack_df = slack_demand.records
demand_slack_df.columns = ['Month', 'SKU', 'Unmet_Demand', 'Marginal', 'Lower', 'Upper', 'Scale']
demand_slack_df = demand_slack_df[demand_slack_df['Unmet_Demand'] > 0.1]

if len(demand_slack_df) > 0:
    total_unmet = demand_slack_df['Unmet_Demand'].sum()
    print(f"  ⚠️  Total unmet demand: {total_unmet:,.0f} units")
else:
    print("  ✓ All demand can be met!")

print("\n[2] SHELF LIMIT VIOLATIONS")

# Columbus first - show it's within capacity
print(f"\nColumbus: (HARD CONSTRAINT - no expansion allowed)")
print("  ✓ All storage within current capacity (no slack variables)")

# Sacramento and Austin - can expand
for fac_name, slack_var in [('Sacramento', slack_shelf_sac),
                             ('Austin', slack_shelf_austin)]:
    print(f"\n{fac_name}: (Can expand)")
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
        print("  ✓ Within current capacity")

print("\n" + "="*100)
print("REDISTRIBUTION ANALYSIS")
print("="*100)

print("\nPrevious model (with Columbus slack allowed):")
print("  Columbus Pallet: 4,104 more shelves needed")
print("  Sacramento Pallet: 1,514 more shelves needed")
print("  Austin Pallet: 251 more shelves needed")
print()
print("Current model (Columbus HARD CONSTRAINT - no expansion):")
print("  Columbus: MUST fit within 3,080 pallet shelves")
print("  Demand shifted to Sacramento and Austin (can expand)")
print()

# Calculate total expansion at Sacramento and Austin
sac_total = 0
austin_total = 0

sac_slack_df = slack_shelf_sac.records
sac_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
for _, row in sac_slack_df.iterrows():
    if row['Excess_Shelves'] > 0.1:
        sac_total += row['Excess_Shelves']

austin_slack_df = slack_shelf_austin.records
austin_slack_df.columns = ['Storage_Type', 'Excess_Shelves', 'Marginal', 'Lower', 'Upper', 'Scale']
for _, row in austin_slack_df.iterrows():
    if row['Excess_Shelves'] > 0.1:
        austin_total += row['Excess_Shelves']

print(f"Total new shelves needed:")
print(f"  Sacramento: {sac_total:,.0f} shelves")
print(f"  Austin: {austin_total:,.0f} shelves")
print(f"  TOTAL EXPANSION: {sac_total + austin_total:,.0f} shelves")
print()
print(f"Previous total (with Columbus expansion): {4104 + 1514 + 251:,.0f} shelves")
print(f"Difference: {(sac_total + austin_total) - (4104 + 1514 + 251):+,.0f} shelves")

print("\n" + "="*100)
