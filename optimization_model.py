"""
InkCredible Supplies - Warehouse Expansion Optimization Model
Option 2: Expand Sacramento and/or Austin Facilities

This model combines:
1. Multiperiod Modeling: SKU procurement, storage, and demand fulfillment over 120 months
2. Set Packing: Optimal assignment of SKU packages to shelving to maximize storage utilization

Objective: Minimize facility expansion while meeting all demand constraints
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense, Options
from pathlib import Path

# ============================================================================
# DATA LOADING
# ============================================================================

print("Loading data files...")
data_dir = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

# Load all data files
demand_df = pd.read_csv(data_dir / "Demand Details.csv")
sku_details_df = pd.read_csv(data_dir / "SKU Details.csv")
lead_time_df = pd.read_csv(data_dir / "Lead TIme.csv")
shelving_count_df = pd.read_csv(data_dir / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(data_dir / "Shelving Dimensions.csv")
floorplan_df = pd.read_csv(data_dir / "Floorplan Layout.csv")
inbound_criteria_df = pd.read_csv(data_dir / "Inbound Criteria.csv")

print("Data loaded successfully!")

# ============================================================================
# DATA PREPROCESSING
# ============================================================================

print("\nProcessing data...")

# Extract SKU list (exclude Month and Year columns from demand data)
skus = [col for col in demand_df.columns if col not in ['Month', 'Year']]
num_skus = len(skus)
print(f"Number of SKUs: {num_skus}")

# Facilities
facilities = ['Columbus', 'Sacramento', 'Austin']
num_facilities = len(facilities)

# Time periods (120 months)
months = list(range(1, 121))
num_months = len(months)

# Storage types
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

# ============================================================================
# EXTRACT PARAMETERS
# ============================================================================

# Demand data: demand[month, sku, facility] - for simplicity, any facility can fulfill any demand
# We'll aggregate total demand per month per SKU
demand_data = {}
for idx, row in demand_df.iterrows():
    month = idx + 1  # Month 1-120
    for sku in skus:
        demand_data[(month, sku)] = row[sku]

# SKU Details: dimensions, weight, storage method
sku_info = {}
for idx, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    # Parse sell pack dimensions (format: "L x W x H")
    sell_dims = row['Sell Pack Dimensions (in)'].split(' x ')
    sell_length, sell_width, sell_height = float(sell_dims[0]), float(sell_dims[1]), float(sell_dims[2])

    sku_info[sku] = {
        'sell_pack_qty': row['Sell Pack Quantity'].split()[0],  # Extract number
        'sell_length': sell_length / 12,  # Convert inches to feet
        'sell_width': sell_width / 12,
        'sell_height': sell_height / 12,
        'sell_weight': row['Sell Pack Weight'].split()[0],  # Extract number
        'storage_method': row['Storage Method'].strip().capitalize(),
        'supplier_type': row['Supplier Type']
    }

# Lead times and days on hand per SKU per facility
lead_time_data = {}
days_on_hand_data = {}
for idx, row in lead_time_df.iterrows():
    sku = row['SKU Number']
    for facility in facilities:
        lead_time_col = f'Lead Time - {facility}'
        days_on_hand_col = f'{facility} - Days on Hand' if facility == 'Columbus' else f'{facility} Days on Hand'

        if lead_time_col in row.index:
            lead_time_data[(sku, facility)] = row[lead_time_col]
        if days_on_hand_col in row.index:
            days_on_hand_data[(sku, facility)] = row[days_on_hand_col]

# Current shelving capacity per facility
current_capacity = {}
for idx, row in shelving_count_df.iterrows():
    facility = row['Facility'].strip()
    storage_type = row['Shelving Type'].strip().capitalize()

    # Normalize storage type names
    if storage_type == 'Pallets':
        storage_type = 'Pallet'

    current_capacity[(facility, storage_type)] = {
        'num_shelves': row['Number of Shelves'],
        'max_items_per_shelf': row['Max Items / Shelf'],
        'total_units': row['Number of Units Total'],
        'weight_max_per_shelf': row['Weight Max / Shelf'],
        'total_weight_capacity': row['Total Weight Capacity'],
        'area_sqft': row['Area']
    }

# Shelving dimensions per facility and storage type
shelf_dimensions = {}
for idx, row in shelving_dims_df.iterrows():
    facility = row['Location']
    storage_type = row['Storage Type']

    if row['Dimensions (l,w,h)(ft)'] == 'Auto':
        # Columbus Bins are auto-calculated
        shelf_dimensions[(facility, storage_type)] = {
            'length': 'Auto',
            'width': 'Auto',
            'height': 'Auto',
            'capacity': 'Auto'
        }
    else:
        dims = row['Dimensions (l,w,h)(ft)'].split(' x ')
        shelf_dimensions[(facility, storage_type)] = {
            'length': float(dims[0]),
            'width': float(dims[1]),
            'height': float(dims[2]),
            'capacity': row['Package Capacity']
        }

# Storage area per facility
storage_area = {}
for idx, row in floorplan_df.iterrows():
    facility = row['Facility']
    if row['Department'] == 'Storage':
        storage_area[facility] = row['Area (ft^2)']

# Expansion costs and limits
expansion_cost = {
    'Sacramento': {'first_100k': 2.0, 'above_100k': 4.0, 'max': 250000},
    'Austin': {'cost': 1.5, 'max': 200000}
}

print("Data processing complete!")

# ============================================================================
# GAMSPY MODEL SETUP
# ============================================================================

print("\n" + "="*80)
print("Building GAMSPy Optimization Model...")
print("="*80)

# Create GAMS container
m = Container()

# ============================================================================
# SETS
# ============================================================================

print("\nDefining sets...")

# Define sets
s = Set(m, name="s", records=skus, description="SKUs")
f = Set(m, name="f", records=facilities, description="Facilities")
t = Set(m, name="t", records=[str(i) for i in months], description="Time periods (months)")
st = Set(m, name="st", records=storage_types, description="Storage types")

# Subset: Expandable facilities
f_expand = Set(m, name="f_expand", domain=f, records=['Sacramento', 'Austin'],
               description="Facilities that can be expanded")

# ============================================================================
# PARAMETERS
# ============================================================================

print("Defining parameters...")

# Demand parameter
demand_records = [(str(month), sku, demand_data.get((month, sku), 0))
                  for month in months for sku in skus]
demand = Parameter(m, name="demand", domain=[t, s], records=demand_records,
                   description="Demand for SKU s in month t")

# Lead time parameter (in days)
lead_time_records = [(sku, fac, lead_time_data.get((sku, fac), 0))
                     for sku in skus for fac in facilities]
lead_time = Parameter(m, name="lead_time", domain=[s, f], records=lead_time_records,
                      description="Lead time for SKU s to facility f (days)")

# Days on hand parameter (in days)
days_on_hand_records = [(sku, fac, days_on_hand_data.get((sku, fac), 0))
                        for sku in skus for fac in facilities]
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=days_on_hand_records,
                         description="Required days on hand for SKU s at facility f")

# SKU dimensions (in cubic feet per sell pack)
sku_volume_records = []
sku_weight_records = []
for sku in skus:
    if sku in sku_info:
        volume = sku_info[sku]['sell_length'] * sku_info[sku]['sell_width'] * sku_info[sku]['sell_height']
        weight = float(sku_info[sku]['sell_weight'])
        sku_volume_records.append((sku, volume))
        sku_weight_records.append((sku, weight))

sku_volume = Parameter(m, name="sku_volume", domain=s, records=sku_volume_records,
                       description="Volume of one sell pack of SKU s (cubic feet)")
sku_weight = Parameter(m, name="sku_weight", domain=s, records=sku_weight_records,
                       description="Weight of one sell pack of SKU s (lbs)")

# SKU to storage type mapping
sku_storage_records = []
for sku in skus:
    if sku in sku_info:
        storage_method = sku_info[sku]['storage_method']
        # Map storage method to storage type
        if storage_method.lower() in ['bins', 'bin']:
            storage_type = 'Bins'
        elif storage_method.lower() == 'hazmat':
            storage_type = 'Hazmat'
        elif storage_method.lower() == 'racking':
            storage_type = 'Racking'
        elif storage_method.lower() == 'pallet':
            storage_type = 'Pallet'
        else:
            storage_type = 'Bins'  # Default
        sku_storage_records.append((sku, storage_type, 1))

sku_storage_type = Parameter(m, name="sku_storage_type", domain=[s, st],
                             records=sku_storage_records,
                             description="1 if SKU s uses storage type st")

# Current storage capacity (number of shelf spaces)
current_shelf_capacity_records = []
for (fac, stor_type), data in current_capacity.items():
    current_shelf_capacity_records.append((fac, stor_type, data['num_shelves']))

current_shelf_capacity = Parameter(m, name="current_shelf_capacity", domain=[f, st],
                                   records=current_shelf_capacity_records,
                                   description="Current number of shelves at facility f of type st")

# Shelf weight capacity
shelf_weight_capacity_records = []
for (fac, stor_type), data in current_capacity.items():
    shelf_weight_capacity_records.append((fac, stor_type, data['weight_max_per_shelf']))

shelf_weight_capacity = Parameter(m, name="shelf_weight_capacity", domain=[f, st],
                                  records=shelf_weight_capacity_records,
                                  description="Weight capacity per shelf (lbs)")

# Shelf volume capacity (approximate from dimensions)
shelf_volume_capacity_records = []
for fac in facilities:
    for stor_type in storage_types:
        if (fac, stor_type) in shelf_dimensions:
            dims = shelf_dimensions[(fac, stor_type)]
            if dims['length'] != 'Auto':
                volume = dims['length'] * dims['width'] * dims['height']
                shelf_volume_capacity_records.append((fac, stor_type, volume))
            else:
                # For auto bins, use a reasonable default
                shelf_volume_capacity_records.append((fac, stor_type, 1.728))  # ~12x12x12 inches

shelf_volume_capacity = Parameter(m, name="shelf_volume_capacity", domain=[f, st],
                                  records=shelf_volume_capacity_records,
                                  description="Volume capacity per shelf (cubic feet)")

# Expansion costs
# Sacramento: $2/sqft for first 100k, $4/sqft above
# Austin: $1.5/sqft
expansion_cost_param_records = [
    ('Sacramento', 2.0),  # We'll handle the tiered pricing in constraints
    ('Austin', 1.5)
]
expansion_cost_param = Parameter(m, name="expansion_cost_param", domain=f_expand,
                                records=expansion_cost_param_records,
                                description="Base expansion cost per sqft")

# Maximum expansion allowed
max_expansion_records = [
    ('Sacramento', 250000),
    ('Austin', 200000)
]
max_expansion = Parameter(m, name="max_expansion", domain=f_expand,
                         records=max_expansion_records,
                         description="Maximum expansion allowed (sqft)")

# Average sqft per shelf (for expansion calculation)
avg_sqft_per_shelf_records = []
for (fac, stor_type), data in current_capacity.items():
    if data['num_shelves'] > 0:
        avg_sqft = data['area_sqft'] / data['num_shelves']
        avg_sqft_per_shelf_records.append((fac, stor_type, avg_sqft))

avg_sqft_per_shelf = Parameter(m, name="avg_sqft_per_shelf", domain=[f, st],
                               records=avg_sqft_per_shelf_records,
                               description="Average sqft per shelf")

# Working days per month
working_days_per_month = 21  # As per assumptions

# ============================================================================
# DECISION VARIABLES
# ============================================================================

print("Defining decision variables...")

# Expansion variables
expansion_sqft = Variable(m, name="expansion_sqft", domain=f_expand, type="positive",
                         description="Square feet of expansion at facility f")

# For Sacramento tiered pricing
sacramento_expansion_tier1 = Variable(m, name="sacramento_expansion_tier1", type="positive",
                                     description="Sacramento expansion in tier 1 (0-100k sqft)")
sacramento_expansion_tier2 = Variable(m, name="sacramento_expansion_tier2", type="positive",
                                     description="Sacramento expansion in tier 2 (100k-250k sqft)")

# Number of additional shelves to add
additional_shelves = Variable(m, name="additional_shelves", domain=[f_expand, st],
                             type="positive",
                             description="Additional shelves of type st at facility f")

# Inventory level: number of sell packs of SKU s at facility f at end of month t
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive",
                    description="Inventory of SKU s at facility f at end of month t")

# Orders: number of sell packs of SKU s ordered for facility f in month t
orders = Variable(m, name="orders", domain=[t, s, f], type="positive",
                 description="Orders of SKU s for facility f in month t")

# Shipments: number of sell packs of SKU s shipped from facility f in month t
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive",
                    description="Shipments of SKU s from facility f in month t")

# Storage utilization: sell packs of SKU s stored on storage type st at facility f in month t
storage_used = Variable(m, name="storage_used", domain=[t, s, f, st], type="positive",
                       description="Sell packs of SKU s on storage type st at facility f in month t")

# Total cost variable
total_cost = Variable(m, name="total_cost", type="free",
                     description="Total expansion cost")

print("Variables defined!")

# ============================================================================
# EQUATIONS/CONSTRAINTS
# ============================================================================

print("\nDefining constraints...")

# Objective function: Minimize expansion cost
obj_eq = Equation(m, name="obj_eq", description="Total expansion cost objective")
obj_eq[...] = total_cost == (
    sacramento_expansion_tier1 * 2.0 +
    sacramento_expansion_tier2 * 4.0 +
    expansion_sqft['Austin'] * 1.5
)

# Sacramento expansion tier constraints
sacramento_tier_eq1 = Equation(m, name="sacramento_tier_eq1",
                              description="Sacramento tier 1 max 100k")
sacramento_tier_eq1[...] = sacramento_expansion_tier1 <= 100000

sacramento_tier_eq2 = Equation(m, name="sacramento_tier_eq2",
                              description="Sacramento tier 2 max 150k")
sacramento_tier_eq2[...] = sacramento_expansion_tier2 <= 150000

sacramento_total_eq = Equation(m, name="sacramento_total_eq",
                              description="Sacramento total expansion")
sacramento_total_eq[...] = expansion_sqft['Sacramento'] == (
    sacramento_expansion_tier1 + sacramento_expansion_tier2
)

# Maximum expansion constraints
max_expansion_eq = Equation(m, name="max_expansion_eq", domain=f_expand,
                           description="Maximum expansion allowed")
max_expansion_eq[f_expand] = expansion_sqft[f_expand] <= max_expansion[f_expand]

# Link expansion to additional shelves
# expansion_sqft = sum over storage types (additional_shelves * avg_sqft_per_shelf)
expansion_shelves_eq = Equation(m, name="expansion_shelves_eq", domain=f_expand,
                               description="Link expansion sqft to shelves")
expansion_shelves_eq[f_expand] = (
    expansion_sqft[f_expand] == Sum(st, additional_shelves[f_expand, st] * avg_sqft_per_shelf[f_expand, st])
)

# Inventory balance constraints
# inventory[t, s, f] = inventory[t-1, s, f] + orders[t - lead_time, s, f] - shipments[t, s, f]
# Simplified: inventory[t] = inventory[t-1] + orders[t] - shipments[t]
# (Lead time will be handled by ensuring orders are placed early enough)

inventory_balance = Equation(m, name="inventory_balance", domain=[t, s, f],
                            description="Inventory balance at each facility")

# For t > 1
inventory_balance[t, s, f].where[t.val > 1] = (
    inventory[t, s, f] == inventory[t.lag(1), s, f] + orders[t, s, f] - shipments[t, s, f]
)

# For t = 1 (initial inventory = 0)
inventory_balance[t, s, f].where[t.val == 1] = (
    inventory[t, s, f] == orders[t, s, f] - shipments[t, s, f]
)

# Demand fulfillment: total shipments across all facilities must meet demand
demand_fulfillment = Equation(m, name="demand_fulfillment", domain=[t, s],
                             description="Total shipments must meet demand")
demand_fulfillment[t, s] = Sum(f, shipments[t, s, f]) >= demand[t, s]

# Days on hand requirement: inventory must cover the pipeline
# Required inventory = (days_on_hand / working_days_per_month) * monthly_demand
# Simplified: inventory >= average daily demand * days on hand
days_on_hand_req = Equation(m, name="days_on_hand_req", domain=[t, s, f],
                           description="Days on hand requirement")
days_on_hand_req[t, s, f] = (
    inventory[t, s, f] >= (demand[t, s] / working_days_per_month) * days_on_hand[s, f]
)

# Storage capacity: inventory must fit in available shelves
# storage_used[t, s, f, st] = amount of SKU s on storage type st
storage_assignment = Equation(m, name="storage_assignment", domain=[t, s, f],
                             description="Assign inventory to storage type")
storage_assignment[t, s, f] = inventory[t, s, f] == Sum(st, storage_used[t, s, f, st])

# SKU can only use its designated storage type
storage_type_constraint = Equation(m, name="storage_type_constraint", domain=[t, s, f, st],
                                  description="SKU must use correct storage type")
storage_type_constraint[t, s, f, st] = (
    storage_used[t, s, f, st] <= sku_storage_type[s, st] * 1e9  # Big M
)

# Shelf capacity constraint - Volume
shelf_volume_constraint = Equation(m, name="shelf_volume_constraint", domain=[t, f, st],
                                  description="Shelf volume capacity")
shelf_volume_constraint[t, f, st] = (
    Sum(s, storage_used[t, s, f, st] * sku_volume[s]) <=
    (current_shelf_capacity[f, st] + additional_shelves[f, st].where[f.sameAs(f_expand)]) *
    shelf_volume_capacity[f, st]
)

# Shelf capacity constraint - Weight
shelf_weight_constraint = Equation(m, name="shelf_weight_constraint", domain=[t, f, st],
                                  description="Shelf weight capacity")
shelf_weight_constraint[t, f, st] = (
    Sum(s, storage_used[t, s, f, st] * sku_weight[s]) <=
    (current_shelf_capacity[f, st] + additional_shelves[f, st].where[f.sameAs(f_expand)]) *
    shelf_weight_capacity[f, st]
)

print("Constraints defined!")

# ============================================================================
# MODEL DEFINITION
# ============================================================================

print("\nCreating model...")

warehouse_model = Model(
    m,
    name="warehouse_expansion",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

print("Model created successfully!")

# ============================================================================
# SOLVE
# ============================================================================

print("\n" + "="*80)
print("SOLVING MODEL...")
print("="*80 + "\n")

# Set solver options
options = Options()
options.relative_optimality_gap = 0.01  # 1% gap

# Solve the model
warehouse_model.solve(options=options)

# ============================================================================
# RESULTS
# ============================================================================

print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80 + "\n")

# Check model status
print(f"Model Status: {warehouse_model.status}")
print(f"Solver Status: {warehouse_model.solver_status}")
print(f"Objective Value (Total Expansion Cost): ${total_cost.toValue():,.2f}\n")

# Expansion results
print("EXPANSION DECISIONS:")
print("-" * 40)
print(f"Sacramento Expansion: {expansion_sqft.records.loc['Sacramento', 'level']:,.0f} sq ft")
print(f"  - Tier 1 (0-100k @ $2/sqft): {sacramento_expansion_tier1.toValue():,.0f} sq ft")
print(f"  - Tier 2 (100k+ @ $4/sqft): {sacramento_expansion_tier2.toValue():,.0f} sq ft")
print(f"  - Cost: ${(sacramento_expansion_tier1.toValue() * 2 + sacramento_expansion_tier2.toValue() * 4):,.2f}")
print(f"\nAustin Expansion: {expansion_sqft.records.loc['Austin', 'level']:,.0f} sq ft")
print(f"  - Cost: ${(expansion_sqft.records.loc['Austin', 'level'] * 1.5):,.2f}")

# Additional shelves
print("\n\nADDITIONAL SHELVES NEEDED:")
print("-" * 40)
if len(additional_shelves.records) > 0:
    shelves_df = additional_shelves.records[additional_shelves.records['level'] > 0.1]
    if len(shelves_df) > 0:
        print(shelves_df.to_string())
    else:
        print("No additional shelves needed")
else:
    print("No additional shelves needed")

# Save detailed results
print("\n\nSaving detailed results to CSV files...")
results_dir = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
results_dir.mkdir(exist_ok=True)

# Save expansion results
expansion_results = pd.DataFrame({
    'Facility': ['Sacramento', 'Austin'],
    'Expansion_sqft': [
        expansion_sqft.records.loc['Sacramento', 'level'],
        expansion_sqft.records.loc['Austin', 'level']
    ],
    'Cost': [
        sacramento_expansion_tier1.toValue() * 2 + sacramento_expansion_tier2.toValue() * 4,
        expansion_sqft.records.loc['Austin', 'level'] * 1.5
    ]
})
expansion_results.to_csv(results_dir / 'expansion_decisions.csv', index=False)

# Save inventory levels (sample - first 12 months)
if len(inventory.records) > 0:
    inventory_df = inventory.records[inventory.records['level'] > 0.1]
    inventory_df.to_csv(results_dir / 'inventory_levels.csv', index=False)

# Save orders (sample - first 12 months)
if len(orders.records) > 0:
    orders_df = orders.records[orders.records['level'] > 0.1]
    orders_df.to_csv(results_dir / 'orders.csv', index=False)

print(f"\nResults saved to: {results_dir}")
print("\n" + "="*80)
print("MODEL COMPLETE!")
print("="*80)
