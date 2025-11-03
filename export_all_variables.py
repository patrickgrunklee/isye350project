"""
Export All Decision Variables from Warehouse Optimization Model

This script runs the warehouse optimization model and exports ALL decision variables
to CSV files for detailed analysis.

Variables exported:
1. expansion - Square footage added at each facility
2. sac_tier1, sac_tier2 - Sacramento tiered expansion breakdown
3. add_shelves - Additional shelves by facility and storage type
4. monthly_inventory - Inventory levels for each month/SKU/facility
5. monthly_deliveries - Delivery quantities for each month/SKU/facility
6. monthly_shipments - Shipment quantities for each month/SKU/facility
7. packages_on_shelf - Package allocation by month/SKU/facility/storage type
8. total_cost - Total expansion cost objective value

All files saved to: results/ directory
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from pathlib import Path
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sense, Sum, Ord

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
RESULTS_DIR.mkdir(exist_ok=True)

# Model configuration
MONTHS = 120
DAYS_PER_MONTH = 21
WORKING_DAYS_PER_MONTH = 21
SAFETY_STOCK_MULTIPLIER = 1.0

print("="*80)
print("EXPORTING ALL VARIABLES - WAREHOUSE OPTIMIZATION MODEL")
print("="*80)
print(f"\nConfiguration:")
print(f"  Time horizon: {MONTHS} months ({MONTHS * DAYS_PER_MONTH} business days)")
print(f"  Working days per month: {WORKING_DAYS_PER_MONTH}")
print(f"  Safety stock multiplier: {SAFETY_STOCK_MULTIPLIER}")
print("="*80 + "\n")

# ============================================================================
# LOAD DATA FILES
# ============================================================================

print("[1/8] Loading data files...")
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
print("   ✓ All data files loaded\n")

# ============================================================================
# EXTRACT SETS
# ============================================================================

print("[2/8] Defining sets and extracting data...")
skus = sku_details_df['SKU Number'].tolist()
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable_facilities = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
months = list(range(1, MONTHS + 1))

# Supplier mapping
domestic_skus = []
international_skus = []
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    supplier = str(row['Supplier Type']).strip()
    if supplier == 'Domestic':
        domestic_skus.append(sku)
    else:
        international_skus.append(sku)

print(f"   ✓ {len(skus)} SKUs, {len(facilities)} facilities, {MONTHS} months, {DAYS_PER_MONTH} days/month")
print(f"   ✓ {len(domestic_skus)} domestic SKUs, {len(international_skus)} international SKUs\n")

# ============================================================================
# PARSE SKU DIMENSIONS
# ============================================================================

print("[3/8] Parsing SKU dimensions and package data...")

def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple (L, W, H) in feet"""
    parts = dim_str.strip().replace('x', ' x ').split(' x ')
    dims = [float(p.strip()) / 12 for p in parts]
    return dims[0] * dims[1] * dims[2]

def parse_weight(wt_str):
    """Parse weight string like '15 lbs' to float"""
    return float(str(wt_str).replace('lbs', '').replace('lb', '').strip())

def parse_inbound_qty(qty_str):
    """Parse inbound quantity like '144 (12 packs)' to int"""
    return int(str(qty_str).split()[0])

sell_vol_data = []
sell_wt_data = []
inbound_vol_data = []
inbound_wt_data = []
inbound_qty_data = []
can_consolidate_data = []
sku_storage_type = {}

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack
    sell_vol = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_wt = parse_weight(row['Sell Pack Weight'])
    sell_vol_data.append((sku, sell_vol))
    sell_wt_data.append((sku, sell_wt))

    # Inbound pack
    inbound_vol = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_wt = parse_weight(row['Inbound Pack Weight'])
    inbound_qty = parse_inbound_qty(row['Inbound Pack Quantity'])
    inbound_vol_data.append((sku, inbound_vol))
    inbound_wt_data.append((sku, inbound_wt))
    inbound_qty_data.append((sku, inbound_qty))

    # Consolidation
    can_consol = 1 if row['Can be packed out in a box with other materials (consolidation)?'] == 'Yes' else 0
    can_consolidate_data.append((sku, can_consol))

    # Storage type
    storage_method = str(row['Storage Method']).strip().lower()
    if 'bin' in storage_method:
        st = 'Bins'
    elif 'hazmat' in storage_method:
        st = 'Hazmat'
    elif 'rack' in storage_method:
        st = 'Racking'
    elif 'pallet' in storage_method:
        st = 'Pallet'
    else:
        st = 'Bins'
    sku_storage_type[sku] = st

print(f"   ✓ Parsed dimensions and weights for {len(skus)} SKUs\n")

# ============================================================================
# PROCESS DEMAND AND LEAD TIME
# ============================================================================

print("[4/8] Processing demand and lead time data...")

# Demand data - each row is a month, each SKU column has demand for that month
demand_records = []
for month_idx in range(min(MONTHS, len(demand_df))):
    for sku in skus:
        if sku in demand_df.columns:
            demand_val = demand_df.iloc[month_idx][sku]
            demand_records.append((str(month_idx + 1), sku, float(demand_val)))

# Lead time and days on hand
lead_time_records = []
doh_records = []
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        # Lead time columns: 'Lead Time - Columbus', 'Lead Time - Sacramento', 'Lead Time - Austin'
        lt_col = f'Lead Time - {fac}'
        if lt_col in lead_time_df.columns:
            lt = float(row[lt_col]) if pd.notna(row[lt_col]) else 7.0
            lead_time_records.append((sku, fac, lt))

        # Days on hand columns: 'Columbus - Days on Hand', 'Sacramento - Days on Hand', 'Austin Days on Hand'
        doh_col = f'{fac} - Days on Hand' if fac != 'Austin' else 'Austin Days on Hand'
        if doh_col in lead_time_df.columns:
            doh = float(row[doh_col]) if pd.notna(row[doh_col]) else 3.0
            doh_records.append((sku, fac, doh))

print(f"   ✓ Loaded demand data for {MONTHS} months")
print(f"   ✓ Loaded lead times and days-on-hand for {len(skus)} SKUs × {len(facilities)} facilities\n")

# ============================================================================
# PROCESS SHELVING CAPACITY
# ============================================================================

print("[5/8] Processing shelving capacity data...")

# Map storage type names between files
storage_type_map = {
    'Pallets': 'Pallet',
    'Bins': 'Bins',
    'Racking': 'Racking',
    'Hazmat': 'Hazmat'
}

curr_shelves_records = []
shelf_wt_records = []
avg_sqft_records = []

for _, row in shelving_count_df.iterrows():
    fac = row['Facility']
    st_raw = row['Shelving Type']
    st = storage_type_map.get(st_raw, st_raw)
    num_shelves = float(row['Number of Shelves'])
    curr_shelves_records.append((fac, st, num_shelves))

    # Weight capacity from Shelving Count
    wt_cap = float(row['Weight Max / Shelf']) if pd.notna(row['Weight Max / Shelf']) else 5000.0
    shelf_wt_records.append((fac, st, wt_cap))

    # Average sqft per shelf
    area = float(row['Area'])
    num = float(row['Number of Shelves'])
    avg = area / num if num > 0 else 50.0
    avg_sqft_records.append((fac, st, avg))

# Volume and package capacity from Shelving Dimensions
shelf_vol_records = []
shelf_pkg_records = []

for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']

    dims_str = str(row['Dimensions (l,w,h)(ft)'])
    if dims_str != 'Auto':
        dims = [float(d.strip()) for d in dims_str.split(' x ')]
        vol = dims[0] * dims[1] * dims[2]
        shelf_vol_records.append((fac, st, vol))
    else:
        shelf_vol_records.append((fac, st, 1000.0))

    pkg_cap = int(row['Package Capacity']) if str(row['Package Capacity']) != 'Auto' else 10
    shelf_pkg_records.append((fac, st, pkg_cap))

print(f"   ✓ Loaded shelving data for {len(facilities)} facilities × {len(storage_types)} storage types\n")

# ============================================================================
# BUILD GAMSPY MODEL
# ============================================================================

print("[6/8] Building GAMSPy optimization model...")
print("   (This may take a few minutes for large models...)")

m = Container()

# Sets
s_set = Set(m, name="s", records=skus)
f_set = Set(m, name="f", records=facilities)
f_exp_set = Set(m, name="f_exp", records=expandable_facilities)
st_set = Set(m, name="st", records=storage_types)
t_month_set = Set(m, name="t_month", records=[str(i) for i in months])

print(f"   ✓ Sets defined ({MONTHS} months × {DAYS_PER_MONTH} days = {MONTHS * DAYS_PER_MONTH} daily periods)")

# Parameters
print("   ✓ Creating parameters...")
demand_param = Parameter(m, name="demand", domain=[t_month_set, s_set], records=demand_records)
sell_vol = Parameter(m, name="sell_vol", domain=s_set, records=sell_vol_data)
sell_wt = Parameter(m, name="sell_wt", domain=s_set, records=sell_wt_data)
inbound_vol = Parameter(m, name="inbound_vol", domain=s_set, records=inbound_vol_data)
inbound_wt = Parameter(m, name="inbound_wt", domain=s_set, records=inbound_wt_data)
inbound_qty = Parameter(m, name="inbound_qty", domain=s_set, records=inbound_qty_data)
can_consolidate = Parameter(m, name="can_consolidate", domain=s_set, records=can_consolidate_data)
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set], records=lead_time_records)
doh_param = Parameter(m, name="doh", domain=[s_set, f_set], records=doh_records)

# SKU-storage type mapping
sku_st_map_records = [(sku, sku_storage_type[sku], 1) for sku in skus]
sku_st_map = Parameter(m, name="sku_st_map", domain=[s_set, st_set], records=sku_st_map_records)

# Supplier mapping
sku_sup_map_records = [(sku, 'Domestic', 1) for sku in domestic_skus] + \
                      [(sku, 'International', 1) for sku in international_skus]
sku_sup_map = Parameter(m, name="sku_sup_map", domain=[s_set, Set(m, name="sup", records=['Domestic', 'International'])],
                        records=sku_sup_map_records)

# Shelving parameters
curr_shelves_param = Parameter(m, name="curr_shelves", domain=[f_set, st_set], records=curr_shelves_records)
shelf_vol_param = Parameter(m, name="shelf_vol", domain=[f_set, st_set], records=shelf_vol_records)
shelf_wt_param = Parameter(m, name="shelf_wt", domain=[f_set, st_set], records=shelf_wt_records)
shelf_pkg_param = Parameter(m, name="shelf_pkg", domain=[f_set, st_set], records=shelf_pkg_records)
avg_sqft_param = Parameter(m, name="avg_sqft", domain=[f_set, st_set], records=avg_sqft_records)

print(f"   ✓ {len(m.getParameters())} parameters created")

# Variables
print("   ✓ Defining decision variables...")
expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive")
sac_t1 = Variable(m, name="sac_tier1", type="positive")
sac_t2 = Variable(m, name="sac_tier2", type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive")
monthly_inventory = Variable(m, name="monthly_inventory", domain=[t_month_set, s_set, f_set], type="positive")
monthly_deliveries = Variable(m, name="monthly_deliveries", domain=[t_month_set, s_set, f_set], type="positive")
monthly_shipments = Variable(m, name="monthly_shipments", domain=[t_month_set, s_set, f_set], type="positive")
packages_on_shelf = Variable(m, name="packages_on_shelf", domain=[t_month_set, s_set, f_set, st_set], type="positive")
total_cost = Variable(m, name="total_cost", type="free")

print(f"   ✓ Decision variables defined")
print(f"   ✓ Estimated model size: ~{len(months) * len(skus) * len(facilities) * 3} variables")

# Constraints
print("   ✓ Defining constraints...")

obj_eq = Equation(m, name="obj")
obj_eq[...] = total_cost == sac_t1 * 2.0 + sac_t2 * 4.0 + expansion['Austin'] * 1.5

sac_t1_max = Equation(m, name="sac_t1_max")
sac_t1_max[...] = sac_t1 <= 100000

sac_t2_max = Equation(m, name="sac_t2_max")
sac_t2_max[...] = sac_t2 <= 150000

sac_total = Equation(m, name="sac_total")
sac_total[...] = expansion['Sacramento'] == sac_t1 + sac_t2

max_exp_sac = Equation(m, name="max_exp_sac")
max_exp_sac[...] = expansion['Sacramento'] <= 250000

max_exp_aus = Equation(m, name="max_exp_aus")
max_exp_aus[...] = expansion['Austin'] <= 200000

# Link expansion sqft to shelves added - separate equation for each expandable facility
exp_shelves_sac = Equation(m, name="exp_shelves_sac")
exp_shelves_sac[...] = expansion['Sacramento'] == Sum(st_set, add_shelves['Sacramento', st_set] * avg_sqft_param['Sacramento', st_set])

exp_shelves_aus = Equation(m, name="exp_shelves_aus")
exp_shelves_aus[...] = expansion['Austin'] == Sum(st_set, add_shelves['Austin', st_set] * avg_sqft_param['Austin', st_set])

demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month_set, s_set])
demand_fulfill[t_month_set, s_set] = Sum(f_set, monthly_shipments[t_month_set, s_set, f_set]) >= demand_param[t_month_set, s_set]

inv_balance_first = Equation(m, name="inv_balance_first", domain=[s_set, f_set])
inv_balance_first[s_set, f_set] = (
    monthly_inventory['1', s_set, f_set] ==
    monthly_deliveries['1', s_set, f_set] * inbound_qty[s_set] -
    monthly_shipments['1', s_set, f_set]
)

inv_balance = Equation(m, name="inv_balance", domain=[t_month_set, s_set, f_set])
inv_balance[t_month_set, s_set, f_set].where[Ord(t_month_set) > 1] = (
    monthly_inventory[t_month_set, s_set, f_set] ==
    monthly_inventory[t_month_set.lag(1, 'linear'), s_set, f_set] +
    monthly_deliveries[t_month_set, s_set, f_set] * inbound_qty[s_set] -
    monthly_shipments[t_month_set, s_set, f_set]
)

pkg_inv_link = Equation(m, name="pkg_inv_link", domain=[t_month_set, s_set, f_set])
pkg_inv_link[t_month_set, s_set, f_set] = (
    monthly_inventory[t_month_set, s_set, f_set] ==
    Sum(st_set, packages_on_shelf[t_month_set, s_set, f_set, st_set])
)

pkg_capacity_exp = Equation(m, name="pkg_capacity_exp", domain=[t_month_set, f_exp_set, st_set])
pkg_capacity_exp[t_month_set, f_exp_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, s_set, f_exp_set, st_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_pkg_param[f_exp_set, st_set]
)

pkg_capacity_fixed = Equation(m, name="pkg_capacity_fixed", domain=[t_month_set, st_set])
pkg_capacity_fixed[t_month_set, st_set] = (
    Sum(s_set, packages_on_shelf[t_month_set, s_set, 'Columbus', st_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_pkg_param['Columbus', st_set]
)

vol_capacity_exp = Equation(m, name="vol_capacity_exp", domain=[t_month_set, f_exp_set, st_set])
vol_capacity_exp[t_month_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, s_set, f_exp_set, st_set] * inbound_vol[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_vol_param[f_exp_set, st_set]
)

vol_capacity_fixed = Equation(m, name="vol_capacity_fixed", domain=[t_month_set, st_set])
vol_capacity_fixed[t_month_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, s_set, 'Columbus', st_set] * inbound_vol[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_vol_param['Columbus', st_set]
)

wt_capacity_exp = Equation(m, name="wt_capacity_exp", domain=[t_month_set, f_exp_set, st_set])
wt_capacity_exp[t_month_set, f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, s_set, f_exp_set, st_set] * inbound_wt[s_set]
    ) <= (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) * shelf_wt_param[f_exp_set, st_set]
)

wt_capacity_fixed = Equation(m, name="wt_capacity_fixed", domain=[t_month_set, st_set])
wt_capacity_fixed[t_month_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        packages_on_shelf[t_month_set, s_set, 'Columbus', st_set] * inbound_wt[s_set]
    ) <= curr_shelves_param['Columbus', st_set] * shelf_wt_param['Columbus', st_set]
)

print(f"   ✓ {len(m.getEquations())} constraint equations defined\n")

# ============================================================================
# SOLVE MODEL
# ============================================================================

print("[7/8] Solving optimization model...")
print("   (This may take several minutes for large models...)\n")

warehouse_model = Model(
    m,
    name="full_daily_warehouse",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

warehouse_model.solve()

# ============================================================================
# EXPORT ALL VARIABLES
# ============================================================================

print("[8/8] Exporting all decision variables to CSV files...")
print()

if warehouse_model.status == 1:  # Optimal solution

    # 1. Expansion decisions
    print("   ✓ Exporting expansion decisions...")
    expansion_df = expansion.records.copy()
    expansion_df.to_csv(RESULTS_DIR / 'var_expansion.csv', index=False)

    # 2. Sacramento tier breakdown
    print("   ✓ Exporting Sacramento tier breakdown...")
    sac_tier_df = pd.DataFrame({
        'Tier': ['Tier 1 (0-100K @ $2/sqft)', 'Tier 2 (100K-250K @ $4/sqft)'],
        'sqft': [sac_t1.records['level'].iloc[0], sac_t2.records['level'].iloc[0]],
        'cost_usd': [sac_t1.records['level'].iloc[0] * 2.0, sac_t2.records['level'].iloc[0] * 4.0]
    })
    sac_tier_df.to_csv(RESULTS_DIR / 'var_sacramento_tiers.csv', index=False)

    # 3. Additional shelves
    print("   ✓ Exporting additional shelves...")
    shelves_df = add_shelves.records.copy()
    shelves_df.to_csv(RESULTS_DIR / 'var_add_shelves.csv', index=False)

    # 4. Monthly inventory (full time series)
    print("   ✓ Exporting monthly inventory (120 months × 18 SKUs × 3 facilities)...")
    inventory_df = monthly_inventory.records.copy()
    inventory_df.to_csv(RESULTS_DIR / 'var_monthly_inventory.csv', index=False)

    # 5. Monthly deliveries (order quantities)
    print("   ✓ Exporting monthly deliveries (order schedule)...")
    deliveries_df = monthly_deliveries.records.copy()
    deliveries_df.to_csv(RESULTS_DIR / 'var_monthly_deliveries.csv', index=False)

    # 6. Monthly shipments (customer fulfillment)
    print("   ✓ Exporting monthly shipments (customer fulfillment)...")
    shipments_df = monthly_shipments.records.copy()
    shipments_df.to_csv(RESULTS_DIR / 'var_monthly_shipments.csv', index=False)

    # 7. Packages on shelf (storage allocation)
    print("   ✓ Exporting packages on shelf (storage allocation)...")
    packages_df = packages_on_shelf.records.copy()
    packages_df.to_csv(RESULTS_DIR / 'var_packages_on_shelf.csv', index=False)

    # 8. Total cost (objective value)
    print("   ✓ Exporting total cost (objective value)...")
    cost_df = pd.DataFrame({
        'Variable': ['total_cost'],
        'Value_USD': [total_cost.records['level'].iloc[0]]
    })
    cost_df.to_csv(RESULTS_DIR / 'var_total_cost.csv', index=False)

    # Summary report
    print("\n   ✓ Creating summary report...")
    summary_lines = []
    summary_lines.append("="*80)
    summary_lines.append("WAREHOUSE OPTIMIZATION - ALL VARIABLES EXPORTED")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append(f"Total Cost: ${total_cost.records['level'].iloc[0]:,.2f}")
    summary_lines.append("")
    summary_lines.append("Expansion Decisions:")
    for _, row in expansion_df.iterrows():
        summary_lines.append(f"  {row['f_exp']}: {row['level']:,.0f} sqft")
    summary_lines.append("")
    summary_lines.append("Files Exported:")
    summary_lines.append("  1. var_expansion.csv - Expansion square footage by facility")
    summary_lines.append("  2. var_sacramento_tiers.csv - Sacramento tiered pricing breakdown")
    summary_lines.append("  3. var_add_shelves.csv - Additional shelves by facility/storage type")
    summary_lines.append("  4. var_monthly_inventory.csv - Inventory levels (120 months × 18 SKUs × 3 facilities)")
    summary_lines.append("  5. var_monthly_deliveries.csv - Delivery quantities (order schedule)")
    summary_lines.append("  6. var_monthly_shipments.csv - Shipment quantities (customer fulfillment)")
    summary_lines.append("  7. var_packages_on_shelf.csv - Package allocation by storage type")
    summary_lines.append("  8. var_total_cost.csv - Total expansion cost objective value")
    summary_lines.append("")
    summary_lines.append(f"All files saved to: {RESULTS_DIR}")
    summary_lines.append("="*80)

    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)

    with open(RESULTS_DIR / 'VARIABLES_SUMMARY.txt', 'w') as f:
        f.write(summary_text)

    print("\n✓ EXPORT COMPLETE - All variables saved to results/ directory")

else:
    print("\n*** MODEL DID NOT SOLVE TO OPTIMALITY ***")
    print(f"Model Status: {warehouse_model.status}")
    print("\nNo variables exported.")

print("\n" + "="*80)
print("DONE!")
print("="*80 + "\n")
