# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.python optimization_model.p

## Project Overview

Full multiperiod warehouse expansion optimization model for InkCredible Supplies using Mixed-Integer Linear Programming (MILP). The project optimizes expansion decisions for Sacramento and Austin facilities with **daily supplier delivery scheduling** over 120 months (2026-2035) while minimizing total costs.

**Approach**: True multiperiod optimization with:
- **Daily time granularity** (2,520 business days over 10 years)
- Supplier delivery scheduling with inbound pack quantities
- Inventory balance equations with lead time considerations
- Dynamic demand fulfillment across facilities
- Operational constraints (1 truckload per supplier per day, 8am deliveries, 5pm shipment deadlines)

**Time Structure**:
- **Monthly level**: 120 months for demand aggregation and strategic planning
- **Daily level**: 21 business days per month for supplier delivery scheduling and inventory tracking
- **Total planning horizon**: 2,520 business days

**Model Components**:
1. **Primary optimization**: Warehouse expansion sizing (square footage, shelves by type)
2. **Secondary optimization (Set Packing)**: Package repacking decisions for optimal shelf utilization
   - 13 SKUs allow consolidation/repacking (writing utensils, textbooks, art supplies, electronics)
   - 5 SKUs cannot be repacked (desks, chairs - must store as received)
   - Binary decision per SKU per facility: store as inbound packs OR repack into sell packs
   - Constraint: Max packages per shelf varies by facility and storage type (3-8 packages)

**Context**: ISyE 350 course project analyzing Option 2 (expand Sacramento and/or Austin facilities).

## Key Commands

### Run Optimization Models

```bash
# Full multiperiod model - 120 months with inventory tracking (PRIMARY MODEL)
python optimization_model.py
# OR
python warehouse_optimization.py

# Legacy simplified models (NOT RECOMMENDED - use only for comparison):
python diagnostic_analysis.py        # Peak demand diagnostic only
python feasibility_check_model.py    # Peak demand with slack variables
python final_warehouse_model.py      # Peak demand optimization
```

### Data Preparation Utilities

```bash
# Convert Excel files to CSV (if updating source data)
python convert_excel_to_csv.py

# Clean up Excel files after conversion
python delete_excel_files.py
```

### Dependencies

```bash
# Core dependencies for optimization models
pip install pandas numpy gamspy openpyxl

# Optional: for convert_excel_to_csv.py colored output (not required for models)
# pip install colorama  # Alternative to rainbow-ansi
```

### License Installation

**Two academic licenses have been provided**:
- License 1: `d81a3160-ec06-4fb4-9543-bfff870b9ecb`
- License 2: `8c39a188-c68a-4295-9c9d-b65ac74bce78`

**Method 1: Install via Python script** (recommended):

```bash
python install_licenses.py
```

The `install_licenses.py` script will install both licenses automatically.

**Method 2: Install manually via Python**:

```python
from gamspy import GamspyWorkspace

# Install first license
ws1 = GamspyWorkspace(license="d81a3160-ec06-4fb4-9543-bfff870b9ecb")
print("License 1 installed successfully")

# Install second license
ws2 = GamspyWorkspace(license="8c39a188-c68a-4295-9c9d-b65ac74bce78")
print("License 2 installed successfully")
```

**Method 3: Set environment variable**:

```bash
# Windows PowerShell
$env:GAMSLICE_STRING="d81a3160-ec06-4fb4-9543-bfff870b9ecb"

# Windows CMD
set GAMSLICE_STRING=d81a3160-ec06-4fb4-9543-bfff870b9ecb

# Linux/Mac
export GAMSLICE_STRING="d81a3160-ec06-4fb4-9543-bfff870b9ecb"
```

**Verify installation**:

```bash
python -c "from gamspy import Container; m = Container(); print('GAMSPy license OK')"
```

**Troubleshooting**:
- `gamspy` CLI command doesn't exist - use Python methods above
- If license validation fails: Check internet connection (requires online verification)
- For large models: Ensure you have sufficient RAM (8GB+ recommended for 136K variables)

## Architecture & Design

### Model Hierarchy

**PRIMARY MODELS** (Full Multiperiod - USE THESE):

1. **optimization_model.py** - Complete multiperiod MILP model
   - 120 time periods with month-by-month inventory tracking
   - Inventory balance equations with lead times and days-on-hand
   - Time-indexed variables: `inventory[t, s, f]`, `orders[t, s, f]`, `shipments[t, s, f]`
   - Expansion decisions optimized against full demand trajectory
   - Most comprehensive and accurate representation

2. **warehouse_optimization.py** - Alternative multiperiod implementation
   - Similar to optimization_model.py but different constraint formulation
   - Also includes full 120-month time horizon

**NOTE**: Both primary models currently use **monthly** time granularity. To implement **daily** supplier delivery scheduling (as required), you must:
- Add daily time set `t_day` (1-21 days per month)
- Change variables to `[t_month, t_day, s, f]` domain
- Add supplier delivery constraints (1 truckload/supplier/day)
- Parse inbound pack quantities from `SKU Details.csv`
- Handle lead time calculations in days (not months)
- See "Supplier Delivery Scheduling (Daily Time Periods)" section below for implementation details

**LEGACY MODELS** (Simplified Peak Demand - For Reference Only):

3. **diagnostic_analysis.py** - Pure Python peak demand analysis
   - NO time dimension - uses `peak_demand[sku] = max(demand_df[sku])`
   - Quick diagnostic for capacity bottlenecks
   - Not an optimization model

4. **feasibility_check_model.py** - Peak demand with slack variables
   - NO time dimension - static capacity planning
   - Identifies capacity gaps using slack variables

5. **final_warehouse_model.py** - Peak demand optimization
   - NO time dimension - simplified approach
   - Flexible allocation across facilities but no temporal dynamics

### GAMSPy Model Structure - Full Multiperiod

The PRIMARY models (`optimization_model.py`, `warehouse_optimization.py`) follow this pattern:

```python
# 1. Data loading and preprocessing
demand_df = pd.read_csv(DATA_DIR / "Demand Details.csv")
# ... parse SKU dimensions, weights, storage types
months = list(range(1, 121))  # 120 time periods

# 2. GAMSPy container and sets
m = Container()
s = Set(m, name="s", records=skus)  # SKUs
f = Set(m, name="f", records=facilities)  # Facilities
t = Set(m, name="t", records=[str(i) for i in months])  # TIME PERIODS (120 months)
st = Set(m, name="st", records=storage_types)  # Storage types

# 3. Parameters (data inputs) - TIME-INDEXED
demand = Parameter(m, name="demand", domain=[t, s], records=...)  # demand[month, sku]
lead_time = Parameter(m, name="lead_time", domain=[s, f], records=...)
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f], records=...)
sku_vol = Parameter(m, name="sku_volume", domain=s, records=...)
shelf_weight = Parameter(m, name="shelf_weight", domain=[f, st], records=...)

# 4. Variables (decision variables) - TIME-INDEXED
expansion = Variable(m, name="expansion", domain=f_exp, type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")
inventory = Variable(m, name="inventory", domain=[t, s, f], type="positive")  # TIME-INDEXED
orders = Variable(m, name="orders", domain=[t, s, f], type="positive")  # TIME-INDEXED
shipments = Variable(m, name="shipments", domain=[t, s, f], type="positive")  # TIME-INDEXED

# 5. Equations (constraints + objective)
obj = Equation(m, name="obj")
obj[...] = total_cost == expansion_cost + Sum([t, s, f], inventory_holding_cost[s] * inventory[t, s, f])

# Inventory balance for each month t
inv_balance = Equation(m, name="inv_balance", domain=[t, s, f])
inv_balance[t, s, f] = inventory[t, s, f] == inventory[t-1, s, f] + orders[t-lead_time, s, f] - shipments[t, s, f]

# Demand fulfillment each month
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t, s])
demand_fulfill[t, s] = Sum(f, shipments[t, s, f]) >= demand[t, s]

# Capacity constraints (volume/weight) for each month
vol_cap = Equation(m, name="vol_cap", domain=[t, f, st])
vol_cap[t, f, st] = Sum(s, inventory[t, s, f] * sku_vol[s]) <= (shelves[f, st] + add_shelves[f, st]) * shelf_vol[f, st]

# 6. Model creation and solving
model = Model(m, equations=m.getEquations(), problem="LP", sense=Sense.MIN, objective=total_cost)
model.solve()

# 7. Results extraction - TIME-SERIES DATA
inventory_df = inventory.records  # Full 120-month inventory trajectory
expansion_df = expansion.records  # Expansion decisions
```

### Key Model Components

**Sets**:
- `s`: 18 SKUs (writing utensils, textbooks, office supplies, etc.)
- `f`: 3 facilities (Columbus, Sacramento, Austin)
- `f_exp`: 2 expandable facilities (Sacramento, Austin - Columbus cannot expand)
- `st`: 4 storage types (Bins, Racking, Pallet, Hazmat)
- **`t`: 120 time periods (months)** - CRITICAL for multiperiod modeling
- **`d`: Daily time periods within each month** - For supplier delivery scheduling (21 business days per month)
- `supplier`: 2 supplier types (Domestic, International) - delivery schedules differ by type

**Decision Variables** (time-indexed):
- `expansion[f]`: Square feet to add at facility f (one-time decision)
- `add_shelves[f, st]`: Additional shelves of type st at facility f (one-time decision)
- **`inventory[t, s, f]`**: Units of SKU s held at facility f at end of month t (in sell pack units)
- **`orders[t, s, f]`**: Units of SKU s ordered for facility f in month t
- **`shipments[t, s, f]`**: Units of SKU s shipped from facility f in month t
- **`packages_on_shelf[t, s, f, st]`**: Number of packages of SKU s on storage type st at facility f (SET PACKING)
- **`repack_decision[s, f]`**: Binary variable - 1 if SKU s is repacked at facility f, 0 if stored as inbound
- `sac_tier1`, `sac_tier2`: Sacramento expansion split into pricing tiers

**Key Constraints**:
- **Inventory balance (multiperiod)**: `inventory[t, s, f] = inventory[t-1, s, f] + orders[t-lead_time, s, f] - shipments[t, s, f]`
- **Demand fulfillment each month**: `Sum_f(shipments[t, s, f]) >= demand[t, s]` for all t
- **Days-on-hand requirements**: `inventory[t, s, f] >= (demand[t, s] / working_days) * days_on_hand[s, f]`
- **Package capacity (SET PACKING)**: `Sum_s(packages_on_shelf[t, s, f, st]) <= shelves[f, st] * shelf_package_capacity[f, st]`
- **Volume capacity with repacking**: `Sum_s(packages * (repack ? sell_volume : inbound_volume)) <= shelves * shelf_volume`
- **Weight capacity with repacking**: `Sum_s(packages * (repack ? sell_weight : inbound_weight)) <= shelves * shelf_weight`
- **Repacking constraint**: `repack_decision[s, f] <= can_consolidate[s]` (only if SKU allows consolidation)
- **Inventory-package link**: Inventory must equal packages on shelves (accounting for repacking)
- Expansion limits: Sacramento ≤250K sqft, Austin ≤200K sqft
- Conversion: `expansion[f] = Sum(add_shelves[f, st] * avg_sqft_per_shelf[f, st])`

**Critical Insights**:
1. **Full multiperiod optimization** - Models 120 months (or 2,520 days) explicitly with inventory balance equations
2. **Lead time integration** - Orders placed in period t arrive at facility after lead_time periods
3. **Dynamic demand fulfillment** - Any facility can fulfill demand each period (flexible allocation)
4. **Days-on-hand constraints** - Ensures sufficient safety stock at each facility each period
5. **Set packing optimization** - Secondary optimization: repack items for optimal shelf utilization
6. **Consolidation decisions** - Binary choice per SKU per facility: store as inbound packs OR repack into sell packs
7. **Package capacity limits** - Hard limit on number of packages per shelf (independent of volume/weight)

### Data Flow

```
Model Data/*.csv (120 rows of monthly demand per SKU)
    ↓
Data loading & parsing (parse_dimension, parse_weight functions)
    ↓
Extract demand_data[(month, sku)] for all 120 months
    ↓
Extract lead_time[(sku, facility)] and days_on_hand[(sku, facility)]
    ↓
Create time-indexed GAMSPy parameters: demand[t, s], inventory[t, s, f], etc.
    ↓
GAMSPy multiperiod optimization (120 time periods)
    ↓
Extract time-series results: inventory trajectories, order schedules, shipment plans
    ↓
results/*.csv (includes monthly inventory levels, orders, shipments)
```

### Set Packing Optimization: Package Repacking for Storage

The model includes a **secondary set packing optimization** where packages can be repacked for optimized storage in the warehouse after receiving inbound shipments.

**Key Concept**: Items arrive in **inbound packs** (supplier packaging) but can be **consolidated/repacked** into optimized storage packages based on shelf dimensions at each facility.

**Repacking Rules** (from `SKU Details.csv` - "Can be packed out in a box with other materials (consolidation)?"):

**Consolidation Allowed (Can Repack)**:
- SKUW1, SKUW2, SKUW3 (writing utensils) - International
- SKUA1, SKUA2, SKUA3 (art supplies/adhesives) - Domestic
- SKUT1-4 (textbooks) - Domestic
- SKUE1, SKUE2, SKUE3 (electronics) - International
- **Total: 13 SKUs can be repacked**

**No Consolidation (Cannot Repack)**:
- SKUD1, SKUD2, SKUD3 (desks) - Must store as received
- SKUC1, SKUC2 (chairs) - Must store as received
- **Total: 5 SKUs cannot be repacked**

**Package Dimensions by Type**:

| Package Type | Sell Pack Dimensions (in) | Sell Pack Volume (cu ft) | Inbound Pack Dimensions (in) | Inbound Pack Volume (cu ft) | Consolidation? |
|--------------|---------------------------|--------------------------|------------------------------|----------------------------|----------------|
| SKUW1 | 3×6×1 | 0.0104 | 10×10×6 | 0.347 | Yes |
| SKUW2 | 6×3×2 | 0.0208 | 10×10×8 | 0.463 | Yes |
| SKUW3 | 6×3×2 | 0.0208 | 10×10×8 | 0.463 | Yes |
| SKUA1 | 4×4×1 | 0.0093 | 5×5×5 | 0.0723 | Yes |
| SKUA2 | 7×5×2 | 0.0405 | 10×10×7 | 0.405 | Yes |
| SKUA3 | 9×12×4 | 0.250 | 9×12×4 | 0.250 | Yes |
| SKUT1 | 10×14×3 | 0.243 | 10×14×9 | 0.729 | Yes |
| SKUT2 | 10×14×3 | 0.243 | 48×48×20 | 26.67 | Yes |
| SKUT3 | 10×14×3 | 0.243 | 48×48×20 | 26.67 | Yes |
| SKUT4 | 10×14×3 | 0.243 | 10×14×9 | 0.729 | Yes |
| SKUD1 | 36×24×5 | 2.50 | 36×24×5 | 2.50 | **No** |
| SKUD2 | 48×36×20 | 20.0 | 48×48×48 | 64.0 | **No** |
| SKUD3 | 24×36×36 | 18.0 | 48×48×48 | 64.0 | **No** |
| SKUC1 | 48×40×20 | 22.2 | 48×40×20 | 22.2 | **No** |
| SKUC2 | 20×36×5 | 2.08 | 48×48×48 | 64.0 | **No** |
| SKUE1 | 2×2×2 | 0.0046 | 10×10×10 | 0.579 | Yes |
| SKUE2 | 14×10×3 | 0.243 | 48×48×48 | 64.0 | Yes |
| SKUE3 | 20×14×4 | 0.648 | 48×48×48 | 64.0 | Yes |

**Shelf Capacity by Facility and Storage Type** (from `Shelving Dimensions.csv`):

| Facility | Storage Type | Shelf Dimensions (ft) | Shelf Volume (cu ft) | Package Capacity |
|----------|--------------|----------------------|---------------------|------------------|
| Columbus | Pallet | 10 × 4.25 × 24 | 1,020 | 7 packages |
| Columbus | Racking | 3 × 1.5 × 6 | 27 | 8 packages |
| Columbus | Bins | Auto | Auto | Auto |
| Austin | Pallet | 10 × 4.25 × 18 | 765 | 6 packages |
| Austin | Racking | 3 × 1.5 × 6 | 27 | 8 packages |
| Austin | Bins | 1.25 × 1.25 × 4 | 6.25 | 3 packages |
| Sacramento | Pallet | 5 × 4.25 × 24 | 510 | 4 packages |
| Sacramento | Racking | 3 × 1.5 × 6 | 27 | 8 packages |
| Sacramento | Bins | 1.25 × 1.25 × 4 | 6.25 | 3 packages |

**Set Packing Model Structure**:

```python
# Sets
s = Set(m, name="s", records=skus)  # SKUs
f = Set(m, name="f", records=facilities)  # Facilities
st = Set(m, name="st", records=storage_types)  # Storage types
p = Set(m, name="p", records=package_configs)  # Package configurations (repacking options)

# Parameters - Package Dimensions
sell_pack_length = Parameter(m, name="sell_pack_length", domain=s, records=...)
sell_pack_width = Parameter(m, name="sell_pack_width", domain=s, records=...)
sell_pack_height = Parameter(m, name="sell_pack_height", domain=s, records=...)
sell_pack_volume = Parameter(m, name="sell_pack_volume", domain=s, records=...)
sell_pack_weight = Parameter(m, name="sell_pack_weight", domain=s, records=...)

inbound_pack_length = Parameter(m, name="inbound_pack_length", domain=s, records=...)
inbound_pack_width = Parameter(m, name="inbound_pack_width", domain=s, records=...)
inbound_pack_height = Parameter(m, name="inbound_pack_height", domain=s, records=...)
inbound_pack_volume = Parameter(m, name="inbound_pack_volume", domain=s, records=...)
inbound_pack_weight = Parameter(m, name="inbound_pack_weight", domain=s, records=...)

can_consolidate = Parameter(m, name="can_consolidate", domain=s, records=...)
# Binary: 1 if SKU can be repacked, 0 if must store as received

# Shelf capacity parameters
shelf_length = Parameter(m, name="shelf_length", domain=[f, st], records=...)
shelf_width = Parameter(m, name="shelf_width", domain=[f, st], records=...)
shelf_height = Parameter(m, name="shelf_height", domain=[f, st], records=...)
shelf_volume_capacity = Parameter(m, name="shelf_volume_capacity", domain=[f, st], records=...)
shelf_package_capacity = Parameter(m, name="shelf_package_capacity", domain=[f, st], records=...)
# Max number of packages per shelf

# Variables - Set Packing
packages_on_shelf = Variable(m, name="packages_on_shelf", domain=[t_month, t_day, s, f, st], type="integer")
# Number of packages of SKU s on storage type st at facility f

repack_decision = Variable(m, name="repack_decision", domain=[s, f], type="binary")
# 1 if SKU s is repacked at facility f, 0 if stored as received

# Constraints
# 1. Package capacity constraint per shelf
package_capacity = Equation(m, name="package_capacity", domain=[t_month, t_day, f, st])
package_capacity[t_month, t_day, f, st] = (
    Sum(s, packages_on_shelf[t_month, t_day, s, f, st]) <=
    (curr_shelves[f, st] + add_shelves[f, st]) * shelf_package_capacity[f, st]
)

# 2. Volume capacity (considering repacking)
volume_capacity = Equation(m, name="volume_capacity", domain=[t_month, t_day, f, st])
volume_capacity[t_month, t_day, f, st] = (
    Sum(s, packages_on_shelf[t_month, t_day, s, f, st] * (
        repack_decision[s, f] * sell_pack_volume[s] +
        (1 - repack_decision[s, f]) * inbound_pack_volume[s]
    )) <= (curr_shelves[f, st] + add_shelves[f, st]) * shelf_volume_capacity[f, st]
)

# 3. Weight capacity (considering repacking)
weight_capacity = Equation(m, name="weight_capacity", domain=[t_month, t_day, f, st])
weight_capacity[t_month, t_day, f, st] = (
    Sum(s, packages_on_shelf[t_month, t_day, s, f, st] * (
        repack_decision[s, f] * sell_pack_weight[s] +
        (1 - repack_decision[s, f]) * inbound_pack_weight[s]
    )) <= (curr_shelves[f, st] + add_shelves[f, st]) * shelf_weight_cap[f, st]
)

# 4. Repacking only allowed for consolidatable SKUs
repack_constraint = Equation(m, name="repack_constraint", domain=[s, f])
repack_constraint[s, f] = repack_decision[s, f] <= can_consolidate[s]

# 5. Inventory balance with repacking
# Inventory is tracked in SELL PACK units (after repacking if applicable)
inv_balance_repack = Equation(m, name="inv_balance_repack", domain=[t_month, t_day, s, f])
inv_balance_repack[t_month, t_day, s, f] = (
    daily_inventory[t_month, t_day, s, f] ==
    daily_inventory[t_month, t_day-1, s, f] +
    deliveries[t_month, t_day, s, f] * inbound_pack_qty[s] -  # Receive in inbound packs
    daily_shipments[t_month, t_day, s, f]  # Ship in sell packs
)

# 6. Link packages on shelf to inventory
packages_inventory_link = Equation(m, name="packages_inventory_link", domain=[t_month, t_day, s, f])
packages_inventory_link[t_month, t_day, s, f] = (
    daily_inventory[t_month, t_day, s, f] ==
    Sum(st, packages_on_shelf[t_month, t_day, s, f, st] * (
        repack_decision[s, f] * 1 +  # If repacked: 1 sell pack per package
        (1 - repack_decision[s, f]) * inbound_pack_qty[s]  # If not repacked: inbound_pack_qty per package
    ))
)
```

**Repacking Cost Considerations**:

```python
# Optional: Add repacking labor cost to objective
repack_cost_per_unit = Parameter(m, name="repack_cost_per_unit", domain=s, records=...)
# Cost to repack one inbound pack into sell packs

total_repack_cost = Sum([t_month, t_day, s, f],
    deliveries[t_month, t_day, s, f] * repack_decision[s, f] * repack_cost_per_unit[s])

# Updated objective
obj[...] = total_cost == expansion_cost + holding_cost + total_repack_cost
```

### Supplier Delivery Scheduling (Daily Time Periods)

The model should include **daily time granularity** for supplier deliveries within each month:

**Key Data from Supporting Materials**:

From `Problem Criteria.csv`:
- All supplier deliveries arrive at **8am local time**
- 1 truckload per supplier can be received **per day**
- 21 working business days per month
- All shipments to customers occur before 5pm local time

From `SKU Details.csv` - Supplier Information:
- **International suppliers**: SKUW1-3, SKUE1-3 (6 SKUs)
- **Domestic suppliers**: All others (12 SKUs)

From `Lead TIme.csv` - Lead times vary by supplier and facility:
- International: 28-37 days depending on facility
- Domestic: 3-15 days depending on SKU and facility

**Inbound Pack Details** (from `SKU Details.csv`):
Each SKU has different inbound pack quantities vs. sell pack quantities:
- SKUW1: Inbound pack = 144 units (12 sell packs), 15 lbs
- SKUT2: Inbound pack = 64 units, 550 lbs (pallet delivery)
- SKUE1: Inbound pack = 100 units, 30 lbs
- etc.

**Model Structure with Daily Periods**:

```python
# Sets
months = list(range(1, 121))  # 120 months
days_per_month = 21  # Business days
days = list(range(1, days_per_month + 1))  # Days 1-21 within each month

t_month = Set(m, name="t_month", records=[str(i) for i in months])
t_day = Set(m, name="t_day", records=[str(i) for i in days])
supplier_type = Set(m, name="supplier_type", records=['Domestic', 'International'])

# Composite time index: (month, day)
# Total time periods: 120 months × 21 days = 2,520 daily periods

# Parameters
delivery_time = Parameter(m, name="delivery_time", domain=[s, f],
                         records=...)  # 8am delivery time
inbound_pack_qty = Parameter(m, name="inbound_pack_qty", domain=s,
                            records=...)  # Units per inbound pack
inbound_pack_weight = Parameter(m, name="inbound_pack_weight", domain=s,
                               records=...)  # Weight per inbound pack
supplier_lead_time = Parameter(m, name="supplier_lead_time", domain=[s, f],
                              records=...)  # Lead time in DAYS (not months)

# Variables - DAILY INDEXED
deliveries = Variable(m, name="deliveries", domain=[t_month, t_day, s, f], type="positive")
# Number of inbound packs delivered on day d of month t for SKU s to facility f

daily_inventory = Variable(m, name="daily_inventory", domain=[t_month, t_day, s, f], type="positive")
# Inventory level at end of day d of month t

# Constraints
# Daily inventory balance
daily_inv_balance = Equation(m, name="daily_inv_balance", domain=[t_month, t_day, s, f])
daily_inv_balance[t_month, t_day, s, f] = (
    daily_inventory[t_month, t_day, s, f] ==
    daily_inventory[t_month, t_day-1, s, f] +
    deliveries[t_month, t_day, s, f] * inbound_pack_qty[s] -
    daily_shipments[t_month, t_day, s, f]
)

# Max 1 truckload per supplier per day per facility
max_deliveries_per_day = Equation(m, name="max_deliveries_per_day", domain=[t_month, t_day, supplier_type, f])
max_deliveries_per_day[t_month, t_day, supplier_type, f] = (
    Sum(s.where[sku_supplier[s, supplier_type] > 0], deliveries[t_month, t_day, s, f]) <= 1
)

# Deliveries arrive after lead time (in days)
delivery_timing = Equation(m, name="delivery_timing", domain=[t_month, t_day, s, f])
# Order placed on (month_t - lead_time_months, day_d - lead_time_days_remainder)
# arrives on (month_t, day_d)
```

**Inbound Pack Quantities by SKU** (for model parameters):

| SKU | Supplier | Inbound Pack Qty | Inbound Pack Weight | Sell Pack Qty |
|-----|----------|------------------|---------------------|---------------|
| SKUW1 | International | 144 units | 15 lbs | 12 units |
| SKUW2 | International | 120 units | 25 lbs | 12 units |
| SKUW3 | International | 120 units | 25 lbs | 12 units |
| SKUA1 | Domestic | 15 units | 8 lbs | 3 units |
| SKUA2 | Domestic | 35 units | 12 lbs | 7 units |
| SKUA3 | Domestic | 100 units | 10 lbs | 100 units |
| SKUT1 | Domestic | 3 units | 25 lbs | 1 unit |
| SKUT2 | Domestic | 64 units | 550 lbs | 1 unit |
| SKUT3 | Domestic | 64 units | 550 lbs | 1 unit |
| SKUT4 | Domestic | 3 units | 25 lbs | 1 unit |
| SKUD1 | Domestic | 1 unit | 30 lbs | 1 unit |
| SKUD2 | Domestic | 1 unit | 75 lbs | 1 unit |
| SKUD3 | Domestic | 1 unit | 35 lbs | 1 unit |
| SKUC1 | Domestic | 1 unit | 60 lbs | 1 unit |
| SKUC2 | Domestic | 24 units | 200 lbs | 3 units |
| SKUE1 | International | 100 units | 30 lbs | 1 unit |
| SKUE2 | International | 60 units | 520 lbs | 1 unit |
| SKUE3 | International | 24 units | 400 lbs | 1 unit |

**Model Complexity Impact**:
- Without daily periods: 120 months × 18 SKUs × 3 facilities ≈ 6,480 time-indexed variables
- With daily periods: 120 months × 21 days × 18 SKUs × 3 facilities ≈ 136,080 time-indexed variables
- **21× increase in problem size** - requires careful solver tuning

**Implementation Steps for Daily Model**:

1. **Parse inbound pack data from `SKU Details.csv`**:
```python
# Extract inbound pack details
inbound_pack_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    # Parse "144 (12 packs)" format
    inbound_qty_str = str(row['Inbound Pack Quantity'])
    inbound_qty = int(inbound_qty_str.split()[0])

    # Parse inbound pack weight
    inbound_weight = parse_weight(row['Inbound Pack Weight'])

    inbound_pack_data[sku] = {
        'quantity': inbound_qty,  # Units per inbound pack
        'weight': inbound_weight,
        'supplier': row['Supplier Type']
    }
```

2. **Create daily time index**:
```python
# Create composite time index (month, day)
daily_periods = []
for month in range(1, 121):
    for day in range(1, 22):
        daily_periods.append((month, day))

# Or create as multi-dimensional set in GAMSPy
t_month = Set(m, name="t_month", records=[str(i) for i in range(1, 121)])
t_day = Set(m, name="t_day", records=[str(i) for i in range(1, 22)])
```

3. **Map SKUs to supplier types**:
```python
domestic_skus = ['SKUA1', 'SKUA2', 'SKUA3', 'SKUT1', 'SKUT2', 'SKUT3', 'SKUT4',
                 'SKUD1', 'SKUD2', 'SKUD3', 'SKUC1', 'SKUC2']
international_skus = ['SKUW1', 'SKUW2', 'SKUW3', 'SKUE1', 'SKUE2', 'SKUE3']

sku_supplier_records = []
for sku in domestic_skus:
    sku_supplier_records.append((sku, 'Domestic', 1))
for sku in international_skus:
    sku_supplier_records.append((sku, 'International', 1))

sku_supplier = Parameter(m, name="sku_supplier", domain=[s, supplier_type],
                         records=sku_supplier_records)
```

4. **Handle lead time day/month boundary crossings**:
```python
def calculate_delivery_date(order_month, order_day, lead_time_days):
    """
    Given order placed on (order_month, order_day) with lead_time_days,
    return delivery (delivery_month, delivery_day)
    """
    total_days = (order_month - 1) * 21 + order_day + lead_time_days
    delivery_month = (total_days - 1) // 21 + 1
    delivery_day = (total_days - 1) % 21 + 1
    return delivery_month, delivery_day
```

5. **Solver settings for large daily model**:
```python
# Recommended solver options for 136K+ variable model
warehouse_model = Model(
    m,
    name="warehouse_daily",
    equations=m.getEquations(),
    problem="LP",
    sense=Sense.MIN,
    objective=total_cost
)

# Set solver options for large-scale problems
warehouse_model.solve(
    solver='CPLEX',  # or 'GUROBI' if available
    options={
        'threads': 8,  # Use multiple cores
        'mipgap': 0.01,  # 1% optimality gap acceptable
        'timelimit': 3600,  # 1 hour time limit
        'memoryemphasis': 1  # Memory optimization
    }
)
```

### Storage Type Assignment Logic

```python
# SKU storage type is determined from "Storage Method" column:
storage_method = str(row['Storage Method']).strip().lower()
if 'bin' in storage_method: st = 'Bins'
elif 'hazmat' in storage_method: st = 'Hazmat'
elif 'rack' in storage_method: st = 'Racking'
elif 'pallet' in storage_method: st = 'Pallet'
else: st = 'Bins'  # Default

# SKU supplier type is determined from "Supplier Type" column:
supplier_type = row['Supplier Type'].strip()  # 'Domestic' or 'International'
```

## Important Constants

```python
DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")
WORKING_DAYS_PER_MONTH = 21  # Business days per month (5 days/week × 50 weeks/year ÷ 12 months)
SAFETY_STOCK_MULTIPLIER = 1.0  # Set to 1.0 for base case, increase for safety stock

# Time granularity options:
MONTHS = 120  # Total planning horizon
DAYS_PER_MONTH = 21  # Business days per month
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH  # 2,520 business days over 10 years

# Operational constraints
DELIVERY_TIME = 8  # 8am local time (all suppliers)
SHIPMENT_DEADLINE = 17  # 5pm local time (all customer shipments)
MAX_TRUCKLOADS_PER_SUPPLIER_PER_DAY = 1  # One truckload per supplier per day per facility
```

## Common Development Patterns

### Parsing Package Dimensions from Data

```python
def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple (L, W, H) in feet"""
    parts = dim_str.strip().replace('x', ' x ').split(' x ')
    return tuple(float(p.strip()) / 12 for p in parts)  # Convert inches to feet

# Parse sell pack dimensions
sell_pack_dims = {}
inbound_pack_dims = {}
can_consolidate = {}

for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_pack_dims[sku] = {
        'length': sell_dims[0],
        'width': sell_dims[1],
        'height': sell_dims[2],
        'volume': sell_dims[0] * sell_dims[1] * sell_dims[2],
        'weight': parse_weight(row['Sell Pack Weight'])
    }

    # Inbound pack
    inbound_dims = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_pack_dims[sku] = {
        'length': inbound_dims[0],
        'width': inbound_dims[1],
        'height': inbound_dims[2],
        'volume': inbound_dims[0] * inbound_dims[1] * inbound_dims[2],
        'weight': parse_weight(row['Inbound Pack Weight'])
    }

    # Consolidation flag
    can_consolidate[sku] = 1 if row['Can be packed out in a box with other materials (consolidation)?'] == 'Yes' else 0

# Parse shelf dimensions and package capacity
shelf_dims = {}
shelf_package_cap = {}

for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']

    dims_str = str(row['Dimensions (l,w,h)(ft)'])
    if dims_str != 'Auto':
        dims = tuple(float(d.strip()) for d in dims_str.split(' x '))
        shelf_dims[(fac, st)] = {
            'length': dims[0],
            'width': dims[1],
            'height': dims[2],
            'volume': dims[0] * dims[1] * dims[2]
        }
        shelf_package_cap[(fac, st)] = int(row['Package Capacity'])
    else:
        # Columbus Bins - Auto calculated
        shelf_dims[(fac, st)] = 'Auto'
        shelf_package_cap[(fac, st)] = 'Auto'
```

### Adding a New Constraint

```python
# 1. Define equation with domain
new_constraint = Equation(m, name="new_constraint", domain=[f, st])

# 2. Specify constraint logic using GAMSPy syntax
new_constraint[f, st] = Sum(s, variable[s, f]) <= limit[f, st]

# 3. Constraint is automatically included via m.getEquations()
```

### Debugging Infeasibility

1. Run `diagnostic_analysis.py` to see which facilities/storage types are over capacity
2. Run `feasibility_check_model.py` to see exact shortfall amounts
3. Check slack variable values in results CSVs
4. Increase `MAX_EXPANSION_MULTIPLIER` or adjust expansion limits
5. Verify data loading (check parsed dimensions/weights match CSV)
6. For daily models: Check lead time calculations (days vs months conversion)
7. Verify supplier delivery constraints (max 1 truckload per supplier per day)
8. Check inbound pack quantities vs sell pack quantities conversion

### Windows UTF-8 Handling

All Python files include this boilerplate for proper console output:

```python
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
```

## File Organization

```
Model/
├── final_warehouse_model.py          # Main optimization model (run this)
├── feasibility_check_model.py        # Diagnostic with slack variables
├── diagnostic_analysis.py            # Capacity analysis (no optimization)
├── convert_excel_to_csv.py           # Utility: Excel → CSV conversion
├── delete_excel_files.py             # Utility: Clean up Excel files
├── warehouse_optimization.py         # Legacy/simplified version
├── optimization_model.py             # Legacy/initial version
├── simplified_warehouse_model.py     # Legacy/simplified version
├── Model Data/                       # Input CSV files (18 SKUs, demand, lead times, shelving)
└── results/                          # Output CSVs (expansion plan, storage allocation, shortfalls)
```

**PRIMARY files (use these)**: `optimization_model.py`, `warehouse_optimization.py`

**Legacy/diagnostic files**: `final_warehouse_model.py`, `feasibility_check_model.py`, `diagnostic_analysis.py`, `simplified_warehouse_model.py` (simplified peak demand approaches - for debugging only)

## Multiperiod vs. Simplified Approaches

### Primary Approach: Full Multiperiod Model

**USE THIS**: `optimization_model.py` or `warehouse_optimization.py`

These models include **time as a set** with 120 periods:
```python
months = list(range(1, 121))  # 120 months
t = Set(m, name="t", records=months)
inventory[t, s, f] = Variable(...)  # Time-indexed inventory tracking
orders[t, s, f] = Variable(...)     # Time-indexed order placement
shipments[t, s, f] = Variable(...)  # Time-indexed shipment decisions
```

**Why full multiperiod is necessary:**
- Captures **temporal dynamics**: demand fluctuations, seasonal patterns, growth trends
- **Lead time constraints**: Orders placed in month t arrive at month t + lead_time
- **Days-on-hand requirements**: Dynamic safety stock that varies with monthly demand
- **Inventory holding costs**: Penalizes excess inventory across time
- **Optimal order timing**: When and how much to order each month
- **Realistic representation**: Matches actual warehouse operations over 10 years

**Model size:**
- Variables: ~388,800 (120 months × 18 SKUs × 3 facilities × 60 decision types)
- Constraints: ~100,000+
- Solve time: Several minutes to hours depending on solver settings
- Accuracy: Highest - represents true operational reality

### Legacy Simplified Approach (NOT RECOMMENDED)

**AVOID UNLESS DEBUGGING**: `final_warehouse_model.py`, `feasibility_check_model.py`, `diagnostic_analysis.py`

These simplified models collapsed time using **peak demand**:
```python
# Collapse all 120 months into single peak requirement
peak_demand = {sku: demand_df[sku].max() for sku in skus}
total_required_storage[sku] = peak_demand[sku] * (doh / WORKING_DAYS_PER_MONTH)
# NO time-indexed variables
```

**Why this is inadequate:**
- ❌ Assumes peak demand occurs simultaneously for all SKUs (unrealistic)
- ❌ Cannot model lead times or order timing
- ❌ Ignores seasonal patterns and demand growth trajectory
- ❌ Over-sizes capacity (designs for impossible worst-case scenario)
- ❌ Cannot optimize inventory holding costs or order schedules
- ❌ Does not represent actual operational decisions managers need

**Only use simplified models for:**
- Quick diagnostic analysis of capacity bottlenecks
- Debugging data loading issues
- Initial exploration before running full model

## Data Files Reference

All data located in `Model Data/` folder:

| File | Description | Key Information |
|------|-------------|-----------------|
| `Demand Details.csv` | Monthly demand for 18 SKUs over 120 months | 120 rows (months) × 18 SKU columns |
| `SKU Details.csv` | Dimensions, weight, storage method, **supplier type**, **inbound pack quantities** | Includes both sell pack and inbound pack details |
| `Lead TIme.csv` | Lead times (in **days**) and days-on-hand by SKU and facility | Varies: Domestic 3-15 days, International 28-37 days |
| `Shelving Count.csv` | Current shelving capacity by facility and type | Number of shelves, weight capacity, area per storage type |
| `Shelving Dimensions.csv` | Physical dimensions and capacity of each shelf type | Volume capacity (l×w×h in feet) |
| `Floorplan Layout.csv` | Square footage allocation by department | Total facility sizes: Columbus 1M, Sacramento 250K, Austin 500K |
| `Problem Criteria.csv` | **Operational hours, delivery times (8am), shipment deadlines (5pm)**, max 1 truckload/supplier/day | Critical for daily scheduling |
| `Inbound Criteria.csv` | Max inbound quantity dimensions and weights per storage method | Bins: 12×12×12/30lbs, Racking: 15×15×15/100lbs, Pallet: 48×48×48/600lbs |
| `General Assuptions.csv` | Forklift widths (10ft), pallet/racking/bin details | Pallet: 10×4.25×24ft, Racking: 3×1.5×6ft |

## Known Issues & Insights

### Pallet Weight Capacity is the Bottleneck

- Volume capacity is **sufficient** across all facilities
- **Weight capacity for pallet storage** is the primary constraint
- Sacramento and Austin need significant pallet shelf expansion
- Columbus has a weight shortfall but **cannot be expanded** (project constraint)

### Solution Approach

- Redistribute heavy pallet items from Columbus to expanded Sacramento/Austin facilities
- Focus expansion budget on pallet shelving (not bins/racking/hazmat)
- Use flexible allocation across facilities to work around Columbus limitation

### Tiered Pricing for Sacramento

Sacramento expansion uses 2-tier pricing:
- First 100K sqft: $2/sqft
- Next 150K sqft: $4/sqft
- Model splits expansion into `sac_tier1` and `sac_tier2` variables

Austin has flat pricing: $1.5/sqft (up to 200K sqft)
