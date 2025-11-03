"""
InkCredible Supplies - Integrated Warehouse Expansion & Storage Optimization
Option 2: Expand Sacramento and/or Austin Facilities

COMBINED MODEL:
1. MULTIPERIOD PLANNING: Procurement scheduling with lead times and days-on-hand
2. SET PACKING: Optimal shelf space allocation considering weight and volume constraints

Objective: Minimize total expansion cost while meeting all demand over 10 years (120 months)
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense, Ord
from pathlib import Path
import warnings
import sys
warnings.filterwarnings('ignore')

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
RESULTS_DIR.mkdir(exist_ok=True)

WORKING_DAYS_PER_MONTH = 21  # From assumptions

print("="*80)
print("INKREDIBLE SUPPLIES - WAREHOUSE OPTIMIZATION MODEL")
print("="*80)

# ============================================================================
# STEP 1: LOAD AND PROCESS DATA
# ============================================================================

print("\n[1/6] Loading data files...")

# Load CSV files
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
lead_time_df = pd.read_csv(DATA_DIR / "Lead TIme.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
floorplan_df = pd.read_csv(DATA_DIR / "Floorplan Layout.csv")

print("   ✓ All data files loaded successfully")

# ============================================================================
# STEP 2: EXTRACT AND ORGANIZE DATA
# ============================================================================

print("\n[2/6] Processing and organizing data...")

# Define sets
skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
facilities = ['Columbus', 'Sacramento', 'Austin']
expandable_facilities = ['Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
months = list(range(1, 121))  # 120 months

print(f"   ✓ {len(skus)} SKUs identified")
print(f"   ✓ {len(facilities)} facilities")
print(f"   ✓ {len(months)} time periods (months)")

# Parse SKU details
def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple of floats in feet"""
    parts = dim_str.strip().split(' x ')
    return tuple(float(p) / 12 for p in parts)  # Convert inches to feet

def parse_quantity(qty_str):
    """Parse quantity string like '12 (1 pack)' to int"""
    return int(str(qty_str).split()[0])

def parse_weight(weight_str):
    """Parse weight string like '1 lbs' to float"""
    return float(str(weight_str).split()[0])

sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Parse sell pack dimensions
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]  # cubic feet

    # Determine storage type
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
        storage_type = 'Bins'  # Default

    sku_data[sku] = {
        'sell_pack_qty': parse_quantity(row['Sell Pack Quantity']),
        'sell_volume': sell_volume,
        'sell_weight': parse_weight(row['Sell Pack Weight']),
        'storage_type': storage_type,
        'supplier_type': row['Supplier Type']
    }

# Extract demand data
demand_data = {}
for idx, row in demand_df.iterrows():
    month = idx + 1
    for sku in skus:
        demand_data[(month, sku)] = float(row[sku])

# Extract lead times and days on hand
lead_times = {}
days_on_hand = {}
for _, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for fac in facilities:
        lt_col = f'Lead Time - {fac}'
        doh_col_options = [f'{fac} - Days on Hand', f'{fac} Days on Hand']

        if lt_col in row.index:
            lead_times[(sku, fac)] = int(row[lt_col])

        for doh_col in doh_col_options:
            if doh_col in row.index:
                days_on_hand[(sku, fac)] = int(row[doh_col])
                break

# Process shelving capacity
current_shelves = {}
shelf_weight_cap = {}
shelf_area = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st = row['Shelving Type'].strip()

    # Normalize storage type name
    if st == 'Pallets':
        st = 'Pallet'

    current_shelves[(fac, st)] = int(row['Number of Shelves'])
    shelf_weight_cap[(fac, st)] = float(row['Weight Max / Shelf'])
    shelf_area[(fac, st)] = float(row['Area'])

# Process shelf dimensions
shelf_volumes = {}
shelf_dims_data = {}
for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']

    dims_str = str(row['Dimensions (l,w,h)(ft)'])
    if dims_str != 'Auto':
        dims = tuple(float(d) for d in dims_str.split(' x '))
        volume = dims[0] * dims[1] * dims[2]
        shelf_volumes[(fac, st)] = volume
        shelf_dims_data[(fac, st)] = {
            'length': dims[0],
            'width': dims[1],
            'height': dims[2],
            'capacity': int(row['Package Capacity'])
        }
    else:
        # Auto for Columbus Bins
        shelf_volumes[(fac, st)] = 1.728  # 12x12x12 inches = 1 cubic foot
        shelf_dims_data[(fac, st)] = {
            'length': 1.0,
            'width': 1.0,
            'height': 1.728,
            'capacity': 1
        }

# Calculate avg sqft per shelf for expansion calculations
avg_sqft_per_shelf = {}
for (fac, st), num_shelves in current_shelves.items():
    if num_shelves > 0 and (fac, st) in shelf_area:
        avg_sqft_per_shelf[(fac, st)] = shelf_area[(fac, st)] / num_shelves

print("   ✓ Data processing complete")

# ============================================================================
# STEP 3: CREATE GAMSPY MODEL
# ============================================================================

print("\n[3/6] Building GAMSPy optimization model...")

m = Container()

# Define sets
s_set = Set(m, name="s", records=skus, description="SKUs")
f_set = Set(m, name="f", records=facilities, description="Facilities")
t_set = Set(m, name="t", records=[str(i) for i in months], description="Time periods")
st_set = Set(m, name="st", records=storage_types, description="Storage types")
f_exp_set = Set(m, name="f_exp", domain=f_set, records=expandable_facilities,
                description="Expandable facilities")

print("   ✓ Sets defined")

# ============================================================================
# PARAMETERS
# ============================================================================

# Demand
demand_records = [(str(mo), sku, demand_data.get((mo, sku), 0))
                  for mo in months for sku in skus]
demand_param = Parameter(m, name="demand", domain=[t_set, s_set],
                        records=demand_records, description="Monthly demand")

# Lead time (in months - convert from days)
lead_time_records = [(sku, fac, lead_times.get((sku, fac), 0) / 30.0)  # Convert days to months
                     for sku in skus for fac in facilities]
lead_time_param = Parameter(m, name="lead_time", domain=[s_set, f_set],
                           records=lead_time_records, description="Lead time (months)")

# Days on hand
doh_records = [(sku, fac, days_on_hand.get((sku, fac), 0))
               for sku in skus for fac in facilities]
doh_param = Parameter(m, name="days_on_hand", domain=[s_set, f_set],
                     records=doh_records, description="Required days on hand")

# SKU properties
sku_vol_records = [(sku, sku_data[sku]['sell_volume']) for sku in skus]
sku_vol_param = Parameter(m, name="sku_volume", domain=s_set,
                         records=sku_vol_records, description="SKU volume (cu ft)")

sku_wt_records = [(sku, sku_data[sku]['sell_weight']) for sku in skus]
sku_wt_param = Parameter(m, name="sku_weight", domain=s_set,
                        records=sku_wt_records, description="SKU weight (lbs)")

# SKU-storage type mapping (binary: 1 if SKU uses this storage type)
sku_st_map_records = [(sku, sku_data[sku]['storage_type'], 1.0) for sku in skus]
sku_st_map = Parameter(m, name="sku_storage_map", domain=[s_set, st_set],
                      records=sku_st_map_records, description="SKU storage type assignment")

# Current shelving capacity
curr_shelves_records = [(fac, st, current_shelves.get((fac, st), 0))
                        for fac in facilities for st in storage_types]
curr_shelves_param = Parameter(m, name="current_shelves", domain=[f_set, st_set],
                              records=curr_shelves_records, description="Current shelves")

# Shelf capacities
shelf_vol_records = [(fac, st, shelf_volumes.get((fac, st), 0))
                     for fac in facilities for st in storage_types]
shelf_vol_param = Parameter(m, name="shelf_volume", domain=[f_set, st_set],
                           records=shelf_vol_records, description="Shelf volume capacity")

shelf_wt_records = [(fac, st, shelf_weight_cap.get((fac, st), 0))
                    for fac in facilities for st in storage_types]
shelf_wt_param = Parameter(m, name="shelf_weight", domain=[f_set, st_set],
                          records=shelf_wt_records, description="Shelf weight capacity")

# Average sqft per shelf
avg_sqft_records = [(fac, st, avg_sqft_per_shelf.get((fac, st), 0))
                    for fac in facilities for st in storage_types]
avg_sqft_param = Parameter(m, name="avg_sqft_shelf", domain=[f_set, st_set],
                          records=avg_sqft_records, description="Avg sqft per shelf")

# Expansion limits
max_exp_records = [('Sacramento', 250000), ('Austin', 200000)]
max_exp_param = Parameter(m, name="max_expansion", domain=f_exp_set,
                         records=max_exp_records, description="Max expansion (sqft)")

# Expansion costs (base rates)
exp_cost_records = [('Sacramento', 2.0), ('Austin', 1.5)]
exp_cost_param = Parameter(m, name="expansion_cost", domain=f_exp_set,
                          records=exp_cost_records, description="Expansion cost ($/sqft)")

print("   ✓ Parameters defined")

# ============================================================================
# DECISION VARIABLES
# ============================================================================

# Expansion decisions
expansion = Variable(m, name="expansion", domain=f_exp_set, type="positive",
                    description="Square feet expanded at each facility")

# Sacramento tiered pricing
sac_tier1 = Variable(m, name="sac_tier1", type="positive",
                    description="Sacramento expansion tier 1 (0-100k)")
sac_tier2 = Variable(m, name="sac_tier2", type="positive",
                    description="Sacramento expansion tier 2 (100k-250k)")

# Additional shelves per facility per storage type
add_shelves = Variable(m, name="add_shelves", domain=[f_exp_set, st_set], type="positive",
                      description="Additional shelves added")

# Inventory at end of each month (in sell packs)
inventory = Variable(m, name="inventory", domain=[t_set, s_set, f_set], type="positive",
                    description="Inventory level at end of month")

# Orders placed (in sell packs)
orders = Variable(m, name="orders", domain=[t_set, s_set, f_set], type="positive",
                 description="Orders placed in month")

# Shipments out (in sell packs)
shipments = Variable(m, name="shipments", domain=[t_set, s_set, f_set], type="positive",
                    description="Shipments from facility in month")

# Peak inventory per SKU per facility (for capacity planning)
peak_inventory = Variable(m, name="peak_inventory", domain=[s_set, f_set], type="positive",
                         description="Peak inventory for capacity planning")

# Total expansion cost
total_cost = Variable(m, name="total_cost", type="free",
                     description="Total expansion cost objective")

print("   ✓ Variables defined")

# ============================================================================
# STEP 4: DEFINE CONSTRAINTS
# ============================================================================

print("\n[4/6] Defining constraints...")

# OBJECTIVE: Minimize total expansion cost
obj_def = Equation(m, name="obj_def", description="Total cost objective")
obj_def[...] = total_cost == (
    sac_tier1 * 2.0 +  # $2/sqft for first 100k
    sac_tier2 * 4.0 +  # $4/sqft for above 100k
    expansion['Austin'] * 1.5  # $1.5/sqft
)

# Sacramento tier constraints
sac_t1_max = Equation(m, name="sac_t1_max", description="Sac tier 1 max")
sac_t1_max[...] = sac_tier1 <= 100000

sac_t2_max = Equation(m, name="sac_t2_max", description="Sac tier 2 max")
sac_t2_max[...] = sac_tier2 <= 150000

sac_total = Equation(m, name="sac_total", description="Sac total expansion")
sac_total[...] = expansion['Sacramento'] == sac_tier1 + sac_tier2

# Maximum expansion limits
max_exp_con = Equation(m, name="max_exp_con", domain=f_exp_set,
                      description="Max expansion constraint")
max_exp_con[f_exp_set] = expansion[f_exp_set] <= max_exp_param[f_exp_set]

# Link expansion to shelves
exp_to_shelves = Equation(m, name="exp_to_shelves", domain=f_exp_set,
                         description="Convert expansion sqft to shelves")
exp_to_shelves[f_exp_set] = (
    expansion[f_exp_set] == Sum(st_set, add_shelves[f_exp_set, st_set] * avg_sqft_param[f_exp_set, st_set])
)

# INVENTORY BALANCE
# For month 1
inv_balance_init = Equation(m, name="inv_balance_init", domain=[s_set, f_set],
                           description="Initial inventory balance")
inv_balance_init[s_set, f_set] = (
    inventory['1', s_set, f_set] == orders['1', s_set, f_set] - shipments['1', s_set, f_set]
)

# For subsequent months
inv_balance = Equation(m, name="inv_balance", domain=[t_set, s_set, f_set],
                      description="Inventory balance")
inv_balance[t_set, s_set, f_set].where[Ord(t_set) > 1] = (
    inventory[t_set, s_set, f_set] ==
    inventory[t_set.lag(1), s_set, f_set] +
    orders[t_set, s_set, f_set] -
    shipments[t_set, s_set, f_set]
)

# DEMAND FULFILLMENT
# Total shipments across all facilities must meet demand each month
demand_met = Equation(m, name="demand_met", domain=[t_set, s_set],
                     description="Demand must be met")
demand_met[t_set, s_set] = Sum(f_set, shipments[t_set, s_set, f_set]) >= demand_param[t_set, s_set]

# DAYS ON HAND REQUIREMENT
# Inventory must be >= (demand / working_days) * days_on_hand
# This ensures sufficient pipeline inventory
min_inventory = Equation(m, name="min_inventory", domain=[t_set, s_set, f_set],
                        description="Minimum inventory for days on hand")
min_inventory[t_set, s_set, f_set] = (
    inventory[t_set, s_set, f_set] >=
    (demand_param[t_set, s_set] / WORKING_DAYS_PER_MONTH) * doh_param[s_set, f_set]
)

# PEAK INVENTORY TRACKING
# Track peak inventory for capacity planning
peak_inv_track = Equation(m, name="peak_inv_track", domain=[t_set, s_set, f_set],
                         description="Track peak inventory")
peak_inv_track[t_set, s_set, f_set] = (
    peak_inventory[s_set, f_set] >= inventory[t_set, s_set, f_set]
)

# STORAGE CAPACITY CONSTRAINTS
# Volume constraint: total volume of peak inventory <= shelf volume capacity
# For expandable facilities (Sacramento and Austin)
storage_volume_exp = Equation(m, name="storage_volume_exp", domain=[f_exp_set, st_set],
                             description="Storage volume constraint (expandable)")
storage_volume_exp[f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        peak_inventory[s_set, f_exp_set] * sku_vol_param[s_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) *
    shelf_vol_param[f_exp_set, st_set]
)

# For Columbus (fixed capacity)
storage_volume_columbus = Equation(m, name="storage_volume_columbus", domain=st_set,
                                   description="Storage volume constraint (Columbus)")
storage_volume_columbus[st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        peak_inventory[s_set, 'Columbus'] * sku_vol_param[s_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_vol_param['Columbus', st_set]
)

# Weight constraint: total weight of peak inventory <= shelf weight capacity
# For expandable facilities (Sacramento and Austin)
storage_weight_exp = Equation(m, name="storage_weight_exp", domain=[f_exp_set, st_set],
                             description="Storage weight constraint (expandable)")
storage_weight_exp[f_exp_set, st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        peak_inventory[s_set, f_exp_set] * sku_wt_param[s_set]) <=
    (curr_shelves_param[f_exp_set, st_set] + add_shelves[f_exp_set, st_set]) *
    shelf_wt_param[f_exp_set, st_set]
)

# For Columbus (fixed capacity)
storage_weight_columbus = Equation(m, name="storage_weight_columbus", domain=st_set,
                                   description="Storage weight constraint (Columbus)")
storage_weight_columbus[st_set] = (
    Sum(s_set.where[sku_st_map[s_set, st_set] > 0],
        peak_inventory[s_set, 'Columbus'] * sku_wt_param[s_set]) <=
    curr_shelves_param['Columbus', st_set] * shelf_wt_param['Columbus', st_set]
)

print("   ✓ All constraints defined")
print(f"   ✓ Total equations: {len(m.getEquations())}")

# ============================================================================
# STEP 5: CREATE AND SOLVE MODEL
# ============================================================================

print("\n[5/6] Creating and solving optimization model...")
print("   (This may take several minutes...)")

warehouse_model = Model(
    m,
    name="warehouse_expansion_optimization",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

# Solve
print("\n   Solving...")
warehouse_model.solve()

# ============================================================================
# STEP 6: EXTRACT AND DISPLAY RESULTS
# ============================================================================

print("\n[6/6] Processing results...")
print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)

# Model status
print(f"\nModel Status: {warehouse_model.status}")
print(f"Solve Status: {warehouse_model.solve_status}")

# Objective value
obj_value = total_cost.toValue()
print(f"\n{'TOTAL EXPANSION COST:':<40} ${obj_value:,.2f}")

# Expansion details
print("\n" + "-"*80)
print("EXPANSION DECISIONS")
print("-"*80)

sac_exp = expansion.records[expansion.records['f_exp'] == 'Sacramento']['level'].values[0]
aus_exp = expansion.records[expansion.records['f_exp'] == 'Austin']['level'].values[0]
sac_t1_val = sac_tier1.toValue()
sac_t2_val = sac_tier2.toValue()

print(f"\nSacramento:")
print(f"  Total Expansion: {sac_exp:,.0f} sq ft")
print(f"  - Tier 1 (0-100k @ $2/sqft): {sac_t1_val:,.0f} sq ft = ${sac_t1_val * 2:,.2f}")
print(f"  - Tier 2 (100k+ @ $4/sqft): {sac_t2_val:,.0f} sq ft = ${sac_t2_val * 4:,.2f}")
print(f"  - Total Cost: ${(sac_t1_val * 2 + sac_t2_val * 4):,.2f}")

print(f"\nAustin:")
print(f"  Total Expansion: {aus_exp:,.0f} sq ft")
print(f"  - Cost @ $1.5/sqft: ${aus_exp * 1.5:,.2f}")

# Additional shelves
print("\n" + "-"*80)
print("ADDITIONAL SHELVING REQUIRED")
print("-"*80)

shelves_df = add_shelves.records[add_shelves.records['level'] > 0.5].copy()
if len(shelves_df) > 0:
    shelves_df['level'] = shelves_df['level'].round(0).astype(int)
    shelves_df = shelves_df.rename(columns={'f_exp': 'Facility', 'st': 'Storage Type', 'level': 'Additional Shelves'})
    print("\n" + shelves_df.to_string(index=False))
else:
    print("\nNo additional shelves required")

# Peak inventory summary
print("\n" + "-"*80)
print("PEAK INVENTORY SUMMARY (Top 10 SKUs by Volume)")
print("-"*80)

peak_df = peak_inventory.records[peak_inventory.records['level'] > 0.1].copy()
if len(peak_df) > 0:
    peak_df['volume'] = peak_df.apply(lambda row: row['level'] * sku_data[row['s']]['sell_volume'], axis=1)
    peak_df = peak_df.sort_values('volume', ascending=False).head(10)
    peak_df['level'] = peak_df['level'].round(0).astype(int)
    peak_df['volume'] = peak_df['volume'].round(2)
    peak_df = peak_df.rename(columns={'s': 'SKU', 'f': 'Facility', 'level': 'Peak Units', 'volume': 'Volume (cu ft)'})
    print("\n" + peak_df[['SKU', 'Facility', 'Peak Units', 'Volume (cu ft)']].to_string(index=False))

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n" + "-"*80)
print("SAVING RESULTS TO CSV")
print("-"*80)

# Expansion summary
exp_summary = pd.DataFrame({
    'Facility': ['Sacramento', 'Austin', 'TOTAL'],
    'Expansion_sqft': [sac_exp, aus_exp, sac_exp + aus_exp],
    'Cost_USD': [
        sac_t1_val * 2 + sac_t2_val * 4,
        aus_exp * 1.5,
        obj_value
    ]
})
exp_summary.to_csv(RESULTS_DIR / 'expansion_summary.csv', index=False)
print(f"✓ Saved: expansion_summary.csv")

# Additional shelves
if len(shelves_df) > 0:
    shelves_df.to_csv(RESULTS_DIR / 'additional_shelves.csv', index=False)
    print(f"✓ Saved: additional_shelves.csv")

# Peak inventory
if len(peak_df) > 0:
    peak_inventory.records.to_csv(RESULTS_DIR / 'peak_inventory_full.csv', index=False)
    print(f"✓ Saved: peak_inventory_full.csv")

# Inventory levels (sample)
inv_df = inventory.records[inventory.records['level'] > 0.1]
if len(inv_df) > 0:
    inv_sample = inv_df[inv_df['t'].astype(int) <= 12]  # First year
    inv_sample.to_csv(RESULTS_DIR / 'inventory_sample_year1.csv', index=False)
    print(f"✓ Saved: inventory_sample_year1.csv")

# Orders (sample)
ord_df = orders.records[orders.records['level'] > 0.1]
if len(ord_df) > 0:
    ord_sample = ord_df[ord_df['t'].astype(int) <= 12]  # First year
    ord_sample.to_csv(RESULTS_DIR / 'orders_sample_year1.csv', index=False)
    print(f"✓ Saved: orders_sample_year1.csv")

print(f"\nAll results saved to: {RESULTS_DIR}")

print("\n" + "="*80)
print("OPTIMIZATION COMPLETE!")
print("="*80 + "\n")
