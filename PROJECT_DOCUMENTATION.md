# InkCredible Supplies Warehouse Expansion Optimization
## Complete Project Documentation

**ISyE 350 Course Project - Option 2: Expand Sacramento and/or Austin Facilities**

---

## 🔥 KEY UPDATE: Full Daily Time Granularity

This model now uses **DAILY indexing for ALL operational variables**:
- ✅ **Inventory tracked daily**: Know stock levels at end of each business day
- ✅ **Orders placed daily**: Specify exact day within month to place purchase orders
- ✅ **Deliveries arrive daily**: Track supplier deliveries arriving at 8am each day
- ✅ **Shipments fulfill daily**: Demand can be fulfilled any day (not just end of month)

**Why daily granularity?**
- **Supplier deliveries**: Arrive at specific times (8am), max 1 truck/supplier/day
- **Customer demand**: Occurs throughout the month, not just at month-end
- **Inventory flow**: Stock levels change daily as deliveries arrive and shipments leave
- **Operational planning**: Real warehouses operate daily, not monthly

**Total problem size**: **408,252 decision variables** across 2,520 business days (120 months × 21 days)

### Daily Operational Flow

```
Each Business Day (8am - 5pm):

8:00 AM  → Supplier deliveries arrive (max 1 truck/supplier/facility)
         → inventory[t, d, s, f] INCREASES
         → Constraint: deliveries[t, d, s, f] = orders[t-lead_time, d', s, f]

During  → Inventory held on shelves
Day     → Capacity constraints checked: volume, weight, package count
         → Inventory must be non-negative: inventory[t, d, s, f] >= 0

5:00 PM  → Customer shipments leave facility
         → inventory[t, d, s, f] DECREASES
         → Constraint: Sum_f(shipments[t, d, s, f]) >= daily_demand[t, d, s]

End of  → Daily inventory balance:
Day     → inventory[t, d, s, f] = inventory[t, d-1, s, f] + deliveries[t, d, s, f] - shipments[t, d, s, f]
```

**Variables**: All indexed by [t_month, t_day, s, f]
- `inventory[t, d, s, f]`: Stock at end of day d
- `orders[t, d, s, f]`: Orders placed on day d
- `deliveries[t, d, s, f]`: Deliveries arriving on day d at 8am
- `shipments[t, d, s, f]`: Shipments leaving on day d by 5pm

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Quick Start Commands](#quick-start-commands)
3. [Model Architecture](#model-architecture)
4. [Decision Variables Explained](#decision-variables-explained)
5. [Implementation Guide](#implementation-guide)
6. [Data Files & Structure](#data-files--structure)
7. [Results & Outputs](#results--outputs)
8. [Known Issues & Solutions](#known-issues--solutions)

---

## Project Overview

### What This Model Does

Full multiperiod warehouse expansion optimization model using Mixed-Integer Linear Programming (MILP) that answers:

1. **Strategic Question**: How much should we expand Sacramento and/or Austin facilities?
2. **Tactical Question**: When should we order inventory from suppliers (exact day)?
3. **Operational Question**: Which facilities should fulfill customer demand each month?

### Model Approach

**True multiperiod optimization** with:
- **Daily supplier order scheduling**: 120 months × 21 business days = 2,520 days
- Inventory balance equations with lead time considerations
- Dynamic demand fulfillment across 3 facilities
- Operational constraints: max 1 truck per supplier per day, 8am deliveries, 5pm shipments

### Planning Horizon

- **Duration**: 10 years (Jan 2026 - Dec 2035)
- **Months**: 120 time periods
- **Business days**: 2,520 days (21 days/month × 120 months)

### Facilities

- **Columbus**: Existing facility, **CANNOT expand** (per project constraints)
- **Sacramento**: Can expand up to 250,000 sqft (tiered pricing: $2/sqft first 100K, $4/sqft next 150K)
- **Austin**: Can expand up to 200,000 sqft (flat $1.5/sqft pricing)

### SKUs & Storage

- **18 SKUs** across 4 categories: Writing Utensils, Textbooks, Office Supplies, Art/Engineering Supplies
- **4 storage types**: Bins, Racking, Pallet, Hazmat
- **2 supplier types**: Domestic (12 SKUs, 3-15 day lead times), International (6 SKUs, 28-37 day lead times)

---

## Quick Start Commands

### Run Optimization

```bash
# PRIMARY MODEL (monthly - needs daily modification)
python optimization_model.py

# OR alternative implementation
python warehouse_optimization.py
```

### Diagnostic Tools

```bash
# Quick capacity analysis (no optimization)
python diagnostic_analysis.py

# Find capacity gaps with slack variables
python feasibility_check_model.py
```

### Data Utilities

```bash
# Convert Excel to CSV
python convert_excel_to_csv.py

# Clean up Excel files
python delete_excel_files.py
```

### Dependencies

```bash
pip install pandas numpy gamspy openpyxl rainbow-ansi
```

**Note**: Requires valid GAMS academic license from https://www.gams.com/

---

## Model Architecture

### Problem Size

**WITH FULL DAILY INDEXING** (recommended for complete operational planning):
- **408,252 decision variables**
  - 12 strategic expansion variables
  - **136,080 daily inventory variables** (120 months × 21 days × 18 SKUs × 3 facilities)
  - **136,080 daily order variables** (120 months × 21 days × 18 SKUs × 3 facilities)
  - **136,080 daily delivery variables** (computed from orders + lead times)
  - **136,080 daily shipment variables** (120 months × 21 days × 18 SKUs × 3 facilities)
- **~1,500,000 constraints**
  - Daily inventory balance for each day/SKU/facility
  - Daily demand fulfillment for each day/SKU
  - Daily capacity constraints (volume/weight) for each day/facility/storage type
  - Daily delivery limit (max 1 truck/supplier/day/facility)
- **Solve time**: Hours to days (requires commercial solver like CPLEX or Gurobi)

**WITH PARTIAL DAILY INDEXING** (orders only, simplified):
- **149,052 decision variables**
  - 12 strategic expansion variables
  - 6,480 monthly inventory variables
  - **136,080 daily order variables** (120 months × 21 days × 18 SKUs × 3 facilities)
  - 6,480 monthly shipment variables
- **~500,000 constraints**
- **Solve time**: Hours

**WITHOUT DAILY INDEXING** (monthly aggregation - for initial testing):
- **19,452 decision variables**
- **~100,000 constraints**
- **Solve time**: Minutes

### Model Type

- **Problem**: Linear Programming (LP) or Mixed-Integer Linear Programming (MILP)
- **Solver**: GAMSPy with GAMS backend
- **Objective**: Minimize total cost (expansion + inventory holding)

### Model Structure (GAMSPy Code Pattern)

```python
# 1. Initialize container
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sense, Sum
m = Container()

# 2. Define sets
t_month = Set(m, name="t_month", records=[str(i) for i in range(1, 121)])  # 120 months
t_day = Set(m, name="t_day", records=[str(i) for i in range(1, 22)])  # 21 days
s = Set(m, name="s", records=skus)  # 18 SKUs
f = Set(m, name="f", records=facilities)  # 3 facilities
st = Set(m, name="st", records=storage_types)  # 4 storage types

# 3. Parameters (data inputs)
demand = Parameter(m, name="demand", domain=[t_month, s])  # Monthly demand
lead_time = Parameter(m, name="lead_time", domain=[s, f])  # Lead times in days
days_on_hand = Parameter(m, name="days_on_hand", domain=[s, f])  # Safety stock days
sku_volume = Parameter(m, name="sku_volume", domain=s)  # Volume per unit
# ... more parameters

# 4. Decision variables - ALL DAILY INDEXED
expansion = Variable(m, name="expansion", domain=f_exp, type="positive")
add_shelves = Variable(m, name="add_shelves", domain=[f_exp, st], type="positive")
inventory = Variable(m, name="inventory", domain=[t_month, t_day, s, f], type="positive")  # DAILY!
orders = Variable(m, name="orders", domain=[t_month, t_day, s, f], type="positive")  # DAILY!
deliveries = Variable(m, name="deliveries", domain=[t_month, t_day, s, f], type="positive")  # DAILY!
shipments = Variable(m, name="shipments", domain=[t_month, t_day, s, f], type="positive")  # DAILY!

# 5. Equations (constraints) - DAILY
# Link orders to deliveries (arrival time mapping)
arrival_link = Equation(m, name="arrival_link", domain=[t_month, t_day, s, f])
arrival_link[t_month, t_day, s, f] = (
    deliveries[t_month, t_day, s, f] ==
    Sum([t_month.alias, t_day.alias].where[order_arrival_set[t_month.alias, t_day.alias, t_month, s, f]],
        orders[t_month.alias, t_day.alias, s, f])
)

# Daily inventory balance
inv_balance = Equation(m, name="inv_balance", domain=[t_month, t_day, s, f])
inv_balance[t_month, t_day, s, f] = (
    inventory[t_month, t_day, s, f] ==
    inventory[t_month, t_day.lag(1), s, f] +  # Previous day (handles month boundaries)
    deliveries[t_month, t_day, s, f] -  # Deliveries arriving today at 8am
    shipments[t_month, t_day, s, f]  # Shipments leaving today by 5pm
)

# Daily demand fulfillment
daily_demand = Parameter(m, name="daily_demand", domain=[t_month, t_day, s])  # From monthly demand / 21
demand_fulfill = Equation(m, name="demand_fulfill", domain=[t_month, t_day, s])
demand_fulfill[t_month, t_day, s] = Sum(f, shipments[t_month, t_day, s, f]) >= daily_demand[t_month, t_day, s]

# Daily capacity constraints (volume)
vol_cap = Equation(m, name="vol_cap", domain=[t_month, t_day, f, st])
vol_cap[t_month, t_day, f, st] = (
    Sum(s, inventory[t_month, t_day, s, f] * sku_volume[s]) <=
    (base_shelves[f, st] + add_shelves[f, st]) * shelf_volume[f, st]
)

# Daily delivery limit (max 1 truck per supplier per day)
max_deliveries = Equation(m, name="max_deliveries", domain=[t_month, t_day, supplier_type, f])
max_deliveries[t_month, t_day, supplier_type, f] = (
    Sum(s.where[sku_supplier[s, supplier_type] > 0],
        deliveries[t_month, t_day, s, f]) <= 1
)

# Objective - minimize total cost
total_cost = Variable(m, name="total_cost", type="free")
obj = Equation(m, name="obj")
obj[...] = total_cost == expansion_cost + Sum([t_month, t_day, s, f], holding_cost[s] * inventory[t_month, t_day, s, f])

# 6. Solve
model = Model(m, equations=m.getEquations(), problem="LP", sense=Sense.MIN, objective=total_cost)
model.solve()

# 7. Extract results
expansion_results = expansion.records
inventory_results = inventory.records
orders_results = orders.records
```

---

## Decision Variables Explained

### What Each Variable Solves For & What Data You Get

#### STRATEGIC EXPANSION VARIABLES (One-time decisions)

##### 1. `expansion[f]` - Total Square Footage to Add

**Solves for**: How much physical space (sqft) to add to Sacramento and/or Austin

**Domain**: f ∈ {Sacramento, Austin} (Columbus cannot expand)

**Output example**:
```
Sacramento: 150,000 sqft
Austin: 80,000 sqft
```

**Business use**: Capital budget allocation, construction planning

**Results file**: `expansion_decisions.csv`
- Columns: [facility, sqft_added, tier1_sqft, tier2_sqft, expansion_cost]

---

##### 2. `add_shelves[f, st]` - Shelves by Storage Type

**Solves for**: How many shelves of each type (Bins, Racking, Pallet, Hazmat) to add

**Domain**: f ∈ {Sacramento, Austin}, st ∈ {Bins, Racking, Pallet, Hazmat}

**Output example** (8 values):
```
Sacramento-Pallet: 500 shelves
Sacramento-Bins: 200 shelves
Austin-Pallet: 300 shelves
Austin-Bins: 150 shelves
...
```

**Business use**: Equipment procurement, installation scheduling

**Results file**: `shelf_additions.csv`
- Columns: [facility, storage_type, shelves_added, sqft_per_shelf, total_sqft, weight_capacity_lbs, volume_capacity_cuft]

**Relationship**: `expansion[f] = Sum_st(add_shelves[f, st] × avg_sqft_per_shelf[f, st])`

---

##### 3. `sac_tier1`, `sac_tier2` - Sacramento Pricing Tiers

**Solves for**: Cost optimization - how to split Sacramento expansion across pricing tiers

**Pricing**:
- tier1: First 100K sqft @ $2/sqft
- tier2: Next 150K sqft @ $4/sqft

**Output example**:
```
tier1: 100,000 sqft ($200,000 cost)
tier2: 50,000 sqft ($200,000 cost)
Total: 150,000 sqft ($400,000 cost)
```

**Business use**: Financial planning - model automatically uses cheaper tier first

**Constraint**: `sac_tier1 + sac_tier2 = expansion[Sacramento]`

---

#### OPERATIONAL INVENTORY VARIABLES (Daily decisions)

##### 4. `inventory[t_month, t_day, s, f]` - Inventory Levels (DAILY)

**Solves for**: Day-by-day inventory levels - how much stock is held at each location at end of each business day

**Domain**: t_month ∈ [1..120] months, t_day ∈ [1..21] business days, s ∈ 18 SKUs, f ∈ 3 facilities

**Output**: 136,080 values forming complete daily inventory trajectory

**Example**:
```
Month 15, Day 10, SKUW1 Ballpoint Pens, Sacramento: 5,000 units
Month 15, Day 11, SKUW1 Ballpoint Pens, Sacramento: 4,800 units (after 200 units shipped)
Month 15, Day 12, SKUW1 Ballpoint Pens, Sacramento: 6,200 units (after 1,400 unit delivery)
```

**Business use**:
- **Daily storage capacity tracking**: Know exact capacity usage each day
- **Intraday inventory visibility**: Track stock levels throughout the month
- **Peak day identification**: Find highest inventory days (not just months)
- **Working capital optimization**: Daily inventory investment tracking
- **Days-on-hand validation**: Ensure safety stock maintained daily (not just monthly average)

**Results file**: `inventory_levels_daily.csv`
- Columns: [month, day, date_string, sku, facility, units, volume_cuft, weight_lbs, holding_cost_dollars]

**Governed by**: Daily inventory balance equation
```
inventory[t_month, t_day, s, f] =
    inventory[t_month, t_day-1, s, f] +
    deliveries[t_month, t_day, s, f] -
    shipments[t_month, t_day, s, f]
```

**Key constraint**: Inventory must be non-negative every day (not just at month-end)
```
inventory[t_month, t_day, s, f] >= 0  for all t_month, t_day, s, f
```

---

##### 5. `deliveries[t_month, t_day, s, f]` - Supplier Deliveries Arriving (DAILY)

**Solves for**: Which orders arrive on which day (computed from orders placed earlier)

**Domain**: t_month ∈ [1..120] months, t_day ∈ [1..21] business days, s ∈ 18 SKUs, f ∈ 3 facilities

**Output**: 136,080 values showing day-by-day incoming deliveries

**Relationship to orders**:
```
deliveries[arrival_month, arrival_day, s, f] = orders[order_month, order_day, s, f]
where: arrival_day = order_day + lead_time[s, f] (accounting for month boundaries)
```

**Example**:
```
Order placed: Month 10, Day 5, SKUW1, Sacramento, 1,440 units
Lead time: 7 days
Delivery arrives: Month 10, Day 12, SKUW1, Sacramento, 1,440 units

Order placed: Month 10, Day 18, SKUT2, Austin, 640 units
Lead time: 15 days
Delivery arrives: Month 11, Day 12, SKUT2, Austin, 640 units (crosses month boundary)
```

**Operational constraint**: All deliveries arrive at 8am local time
- Max 1 truckload per supplier type per day per facility
- Domestic suppliers: Max 1 delivery/day across all domestic SKUs
- International suppliers: Max 1 delivery/day across all international SKUs

**Business use**:
- **Receiving dock scheduling**: Know exactly when trucks arrive
- **Labor planning**: Schedule receiving staff for delivery days
- **Warehouse workload**: Track daily receiving volume
- **Inventory replenishment**: When stock is added to inventory

**Results file**: `deliveries_daily.csv`
- Columns: [arrival_month, arrival_day, arrival_date, sku, facility, units_delivered, inbound_packs, order_month, order_day, order_date, lead_time_days, supplier_type]

---

##### 6. `orders[t_month, t_day, s, f]` - Purchase Orders (DAILY)

**Solves for**: Precise procurement timing - which DAY to order from suppliers

**Domain**: t_month ∈ [1..120], t_day ∈ [1..21], s ∈ 18 SKUs, f ∈ 3 facilities

**Output**: 136,080 values showing day-by-day order schedule

**Example**:
```
Month 10, Day 5, SKUT2 Textbooks, Austin: 1,200 units ordered
  → Arrives Month 12, Day 5 (if 42-day lead time)

Month 10, Day 18, SKUW1 Pens, Sacramento: 500 units ordered
  → Arrives Month 11, Day 4 (if 7-day lead time)
```

**Lead time handling**:
- Domestic SKUs: 3-15 days
- International SKUs: 28-37 days
- Arrival calculation: `arrival_day = (order_month-1)*21 + order_day + lead_time`

**Business use**:
- **Precise cash flow planning**: Know exact payment dates
- **Daily dock scheduling**: Coordinate receiving capacity
- **Labor planning**: Schedule staff for delivery days
- **Supplier coordination**: Provide exact PO dates

**Results file**: `order_schedule_daily.csv`
- Columns: [order_month, order_day, order_date_string, arrival_month, arrival_day, arrival_date_string, sku, facility, units_ordered, inbound_packs, lead_time_days, supplier_type]

**Key constraint**: Max 1 truckload per supplier type per day per facility
- Domestic suppliers: Max 1 delivery/day across all domestic SKUs
- International suppliers: Max 1 delivery/day across all international SKUs

**Inbound pack conversion**:
- Example: SKUW1 inbound pack = 144 units, sell pack = 12 units
- If orders = 1,440 units → 10 inbound packs ordered

---

##### 7. `shipments[t_month, t_day, s, f]` - Customer Fulfillment (DAILY)

**Solves for**: Which facility ships to meet customer demand on which specific day

**Domain**: t_month ∈ [1..120] months, t_day ∈ [1..21] business days, s ∈ 18 SKUs, f ∈ 3 facilities

**Output**: 136,080 values showing day-by-day distribution strategy

**Example**:
```
Month 20, Day 5, SKUA3 Office Supplies, demand = 100 units (daily):
  Columbus ships: 40 units
  Sacramento ships: 60 units
  Total: 100 units ✓

Month 20, Day 6, SKUA3 Office Supplies, demand = 120 units (daily):
  Columbus ships: 50 units
  Sacramento ships: 70 units
  Total: 120 units ✓

Month 20 total demand = 2,000 units (sum of all 21 days)
```

**Flexibility**: Any facility can ship any SKU on any day - model optimizes network dynamically

**Constraint**: `Sum_f(shipments[t_month, t_day, s, f]) >= demand[t_month, t_day, s]` for all t_month, t_day, s

**Daily demand calculation**: Monthly demand is distributed across 21 business days
- **Option 1 - Uniform**: `daily_demand[t_month, t_day, s] = monthly_demand[t_month, s] / 21`
- **Option 2 - Weighted**: Use actual daily demand pattern if available (e.g., higher on Mondays)

**Operational constraint**: All shipments must occur before 5pm deadline
- Shipments on day d use inventory available at end of day d
- Cannot ship more than available inventory: `shipments[t_month, t_day, s, f] <= inventory[t_month, t_day, s, f]`

**Business use**:
- **Daily shipping schedule**: Know exact daily workload for each facility
- **Transportation planning**: Daily truck scheduling and routing
- **Labor planning**: Schedule packing/shipping staff based on daily volumes
- **Customer service**: Track daily fulfillment performance
- **Peak day identification**: Find highest shipping days (not just months)
- **Regional allocation**: Optimize which facility serves which customers each day

**Results file**: `shipment_plan_daily.csv`
- Columns: [month, day, date_string, sku, facility, units_shipped, daily_demand, demand_fulfilled_pct, transportation_cost_dollars]

---

### Variable Relationships Diagram

```
┌──────────────────────────────┐         ┌──────────────────────────────────┐
│ STRATEGIC (One-time)         │         │ OPERATIONAL (DAILY)              │
├──────────────────────────────┤         ├──────────────────────────────────┤
│                              │         │                                  │
│  expansion[f]                │────────>│  inventory[t_month, t_day, s, f] │
│  (sqft to add)               │ Sets    │  (daily stock levels)            │
│                              │ max     │         ▲                        │
│  add_shelves[f, st]          │capacity │         │                        │
│  (shelves by type)           │ limits  │         │ Daily Inventory Balance│
│                              │         │         │                        │
│  sac_tier1, sac_tier2        │         │  orders[t_month, t_day, s, f]    │
│  (Sacramento pricing)        │         │  (daily purchase orders)         │
│                              │         │         │                        │
└──────────────────────────────┘         │         └─> Lead time days       │
                                         │                 ▼                │
                                         │  deliveries[t_month, t_day, s, f]│
                                         │  (daily arrivals at 8am)         │
                                         │         │                        │
                                         │         └─> Adds to inventory    │
                                         │                                  │
                                         │  shipments[t_month, t_day, s, f] │
                                         │  (daily demand fulfillment)      │
                                         │         │                        │
                                         │         └─> Meets daily demand   │
                                         │             (before 5pm)         │
                                         │                                  │
                                         └──────────────────────────────────┘

Daily Inventory Flow:
inventory[t, d, s, f] = inventory[t, d-1, s, f] + deliveries[t, d, s, f] - shipments[t, d, s, f]
                         ▲ End of yesterday      ▲ Arrives 8am today      ▲ Ships by 5pm today
```

---

## Implementation Guide

### Adding Daily Order Indexing to Current Model

Current models use **monthly** orders `orders[t, s, f]`. To implement **daily** scheduling:

#### Step 1: Add Daily Time Set

```python
# Current (monthly only):
months = list(range(1, 121))
t = Set(m, name="t", records=[str(i) for i in months])

# Add daily dimension:
DAYS_PER_MONTH = 21  # Business days per month
days = list(range(1, DAYS_PER_MONTH + 1))

t_month = Set(m, name="t_month", records=[str(i) for i in months])
t_day = Set(m, name="t_day", records=[str(i) for i in days])
```

#### Step 2: Modify Orders Variable

```python
# OLD:
orders = Variable(m, name="orders", domain=[t, s, f], type="positive")

# NEW:
orders = Variable(m, name="orders", domain=[t_month, t_day, s, f], type="positive")
```

#### Step 3: Create Arrival Time Mapping

```python
def calculate_arrival_time(order_month, order_day, lead_time_days, days_per_month=21):
    """Calculate arrival month and day given order timing and lead time."""
    total_order_days = (order_month - 1) * days_per_month + order_day
    total_arrival_days = total_order_days + lead_time_days

    arrival_month = ((total_arrival_days - 1) // days_per_month) + 1
    arrival_day = ((total_arrival_days - 1) % days_per_month) + 1

    return (arrival_month, arrival_day)

# Pre-compute arrival mapping for all order possibilities
arrival_mapping_data = []
for order_month in months:
    for order_day in days:
        for sku in skus:
            for facility in facilities:
                lt = lead_time_dict.get((sku, facility), 0)

                if lt > 0:
                    arrival_month, arrival_day = calculate_arrival_time(order_month, order_day, lt)

                    if arrival_month <= 120:  # Within planning horizon
                        arrival_mapping_data.append({
                            'order_month': str(order_month),
                            'order_day': str(order_day),
                            'arrival_month': str(arrival_month),
                            'sku': sku,
                            'facility': facility
                        })

# Create 5-dimensional set for valid order-arrival combinations
order_arrival_set = Set(m, name="order_arrival_set",
                       domain=[t_month, t_day, t_month, s, f],
                       records=[(d['order_month'], d['order_day'], d['arrival_month'],
                                d['sku'], d['facility'])
                               for d in arrival_mapping_data])
```

#### Step 4: Update Inventory Balance Equation

```python
inv_balance = Equation(m, name="inv_balance", domain=[t_month, s, f])

inv_balance[t_month, s, f] = (
    inventory[t_month, s, f] ==
    inventory[t_month.lag(1), s, f] +
    Sum([t_day, t_month.alias].where[order_arrival_set[t_month.alias, t_day, t_month, s, f]],
        orders[t_month.alias, t_day, s, f]) -
    shipments[t_month, s, f]
)
```

#### Step 5: Add Daily Delivery Constraints

```python
# SKU to supplier mapping
supplier_mapping = {
    'Domestic': [sku for sku in skus if not sku.startswith('SKUW') and not sku.startswith('SKUE')],
    'International': [sku for sku in skus if sku.startswith('SKUW') or sku.startswith('SKUE')]
}

# Track daily arrivals
daily_arrivals = Variable(m, name="daily_arrivals", domain=[t_month, t_day, s, f], type="positive")

# Link arrivals to orders
arrival_link = Equation(m, name="arrival_link", domain=[t_month, t_day, s, f])
arrival_link[t_month, t_day, s, f] = (
    daily_arrivals[t_month, t_day, s, f] ==
    Sum([t_month.alias, t_day.alias].where[order_arrival_set[t_month.alias, t_day.alias, t_month, s, f]],
        orders[t_month.alias, t_day.alias, s, f])
)

# Max 1 truck per supplier per day
max_deliveries = Equation(m, name="max_deliveries", domain=[t_month, t_day, supplier_type_set, f])
max_deliveries[t_month, t_day, supplier_type_set, f] = (
    Sum(s.where[sku_supplier[s, supplier_type_set] > 0],
        daily_arrivals[t_month, t_day, s, f]) <= 1
)
```

#### Step 6: Export Results with Dates

```python
import datetime

def month_day_to_date(month_idx, day_idx, start_date=datetime.date(2026, 1, 1)):
    """Convert month/day index to calendar date."""
    total_business_days = (month_idx - 1) * 21 + (day_idx - 1)
    calendar_days = int(total_business_days * 1.4)  # Approx conversion
    return start_date + datetime.timedelta(days=calendar_days)

# Process orders results
orders_results = []
for idx, row in orders.records.iterrows():
    if row['level'] > 0.01:  # Non-zero orders only
        order_month = int(row['t_month'])
        order_day = int(row['t_day'])
        sku = row['s']
        facility = row['f']
        units = row['level']

        lt_days = lead_time_dict.get((sku, facility), 0)
        arrival_month, arrival_day = calculate_arrival_time(order_month, order_day, lt_days)

        order_date = month_day_to_date(order_month, order_day)
        arrival_date = month_day_to_date(arrival_month, arrival_day)

        orders_results.append({
            'order_month': order_month,
            'order_day': order_day,
            'order_date': order_date.strftime('%Y-%m-%d'),
            'arrival_month': arrival_month,
            'arrival_day': arrival_day,
            'arrival_date': arrival_date.strftime('%Y-%m-%d'),
            'sku': sku,
            'facility': facility,
            'units_ordered': units,
            'lead_time_days': lt_days,
            'supplier_type': 'International' if sku.startswith('SKUW') or sku.startswith('SKUE') else 'Domestic'
        })

orders_df = pd.DataFrame(orders_results)
orders_df.to_csv(RESULTS_DIR / 'order_schedule_daily.csv', index=False)
```

---

## Data Files & Structure

### Input Files (Model Data/)

#### 1. Demand Details.csv
- **Purpose**: Monthly demand forecast for each SKU
- **Structure**: 120 rows (months) × 18 columns (SKUs)
- **Example**:
```
Month,SKUW1,SKUW2,SKUT1,...
1,1250,800,45,...
2,1300,820,47,...
```

**Converting Monthly to Daily Demand**:

Since the model uses daily indexing but demand data is monthly, you must distribute monthly demand across 21 business days:

```python
# Option 1: Uniform distribution (simplest)
daily_demand_data = []
for month in range(1, 121):
    for day in range(1, 22):
        for sku in skus:
            monthly_demand = demand_df.loc[demand_df['Month'] == month, sku].values[0]
            daily_demand = monthly_demand / 21.0  # Evenly distribute
            daily_demand_data.append({
                't_month': str(month),
                't_day': str(day),
                'sku': sku,
                'Value': daily_demand
            })

daily_demand = Parameter(m, name="daily_demand", domain=[t_month, t_day, s],
                        records=pd.DataFrame(daily_demand_data))

# Option 2: Weighted distribution (more realistic)
# Account for day-of-week patterns if you have data
day_weights = {
    1: 1.2,   # Monday (higher)
    2: 1.1,   # Tuesday
    3: 1.0,   # Wednesday
    4: 1.0,   # Thursday
    5: 0.9,   # Friday (lower)
    # Repeat for 21 days
}

daily_demand_data = []
total_weight = sum(day_weights.values())
for month in range(1, 121):
    for day in range(1, 22):
        for sku in skus:
            monthly_demand = demand_df.loc[demand_df['Month'] == month, sku].values[0]
            weight = day_weights.get(day, 1.0)
            daily_demand = monthly_demand * (weight / total_weight)  # Weighted distribution
            daily_demand_data.append({
                't_month': str(month),
                't_day': str(day),
                'sku': sku,
                'Value': daily_demand
            })

# Option 3: Constraint approach (let model decide)
# Don't specify daily demand - only require monthly total is met
monthly_demand_constraint = Equation(m, name="monthly_demand", domain=[t_month, s])
monthly_demand_constraint[t_month, s] = (
    Sum([t_day, f], shipments[t_month, t_day, s, f]) >= monthly_demand[t_month, s]
)
# This gives model flexibility to shift demand fulfillment across days
```

**Recommendation**: Use **Option 1 (uniform)** for initial models, then **Option 3 (constraint)** for final model to give optimizer maximum flexibility.

#### 2. SKU Details.csv
- **Purpose**: SKU attributes (dimensions, weight, storage type, supplier)
- **Columns**: SKU, Length, Width, Height, Weight, Storage Method, Supplier Type, Inbound Pack Qty, Sell Pack Qty
- **Example**:
```
SKU,Length,Width,Height,Weight,Storage Method,Supplier Type,Inbound Pack,Sell Pack
SKUW1,6,4,2,0.5,Bin,International,144,12
SKUT2,11,8.5,2,34.375,Pallet,Domestic,64,1
```

#### 3. Lead Time.csv
- **Purpose**: Lead times in DAYS for each SKU-facility combination
- **Structure**: 18 rows (SKUs) × 4 columns (SKU, Columbus, Sacramento, Austin)
- **Example**:
```
SKU,Columbus,Sacramento,Austin
SKUW1,35,37,28
SKUT2,15,12,10
```

#### 4. Days on Hand.csv
- **Purpose**: Safety stock requirements (days of demand)
- **Structure**: 18 rows × 4 columns
- **Example**:
```
SKU,Columbus,Sacramento,Austin
SKUW1,7,7,7
SKUT2,14,14,14
```

#### 5. Shelving Details.csv
- **Purpose**: Existing capacity and shelving specifications
- **Columns**: Facility, Storage Type, Current Shelves, Shelf Volume (cuft), Shelf Weight Capacity (lbs), Avg sqft per Shelf
- **Example**:
```
Facility,Storage Type,Current Shelves,Shelf Volume,Shelf Weight,Avg sqft
Columbus,Bins,1000,50,500,10
Sacramento,Pallet,500,200,2000,25
```

### Output Files (results/)

#### 1. expansion_decisions.csv
```
facility,sqft_added,tier1_sqft,tier2_sqft,expansion_cost
Sacramento,150000,100000,50000,400000
Austin,80000,0,0,120000
```

#### 2. shelf_additions.csv
```
facility,storage_type,shelves_added,sqft_per_shelf,total_sqft,weight_capacity_lbs,volume_capacity_cuft
Sacramento,Pallet,500,25,12500,1000000,100000
Austin,Bins,200,10,2000,100000,10000
```

#### 3. inventory_levels.csv (6,480 rows)
```
month,sku,facility,units,volume_cuft,weight_lbs,holding_cost_dollars
1,SKUW1,Sacramento,5000,1000,2500,250
1,SKUT2,Austin,1200,4800,41250,600
```

#### 4. order_schedule_daily.csv (136,080 rows max)
```
order_month,order_day,order_date,arrival_month,arrival_day,arrival_date,sku,facility,units_ordered,lead_time_days,supplier_type
1,5,2026-01-08,1,12,2026-01-17,SKUW1,Sacramento,1440,7,International
2,15,2026-02-24,3,18,2026-03-27,SKUT2,Austin,640,28,Domestic
```

#### 5. shipment_plan.csv (6,480 rows)
```
month,sku,facility,units_shipped,demand_fulfilled_pct,transportation_cost_dollars
1,SKUW1,Columbus,500,40,250
1,SKUW1,Sacramento,750,60,375
```

---

## Known Issues & Solutions

### Issue 1: Pallet Weight Capacity is the Bottleneck

**Problem**: Volume capacity is sufficient, but **weight capacity for pallet storage** is the primary constraint

**Impact**:
- Columbus has weight shortfall but cannot expand
- Sacramento and Austin need significant pallet shelf expansion

**Solution**:
- Redistribute heavy pallet items from Columbus to expanded Sacramento/Austin
- Focus expansion budget on pallet shelving (not bins/racking/hazmat)
- Use flexible allocation to work around Columbus limitation

**Diagnostic command**:
```bash
python diagnostic_analysis.py  # Shows capacity bottlenecks
```

### Issue 2: Model Infeasibility

**Symptoms**: Solver returns "infeasible" status

**Debugging steps**:
1. Run `diagnostic_analysis.py` to see which facilities/storage types are over capacity
2. Run `feasibility_check_model.py` to see exact shortfall amounts
3. Check slack variable values in results CSVs
4. Increase expansion limits if needed
5. Verify data loading (check parsed dimensions/weights match CSV)

### Issue 3: Daily Model Solve Time Too Long

**Problem**: Daily order indexing increases solve time from minutes to hours

**Solutions**:
1. Use commercial solver (CPLEX, Gurobi) instead of free solvers
2. Enable parallel processing in solver settings
3. Use warm start from monthly solution
4. Reduce planning horizon for testing (e.g., 12 months instead of 120)
5. Aggregate lead times to nearest week for intermediate solution

### Issue 4: Windows UTF-8 Console Output

**Problem**: Special characters don't display correctly on Windows

**Solution**: Add to all Python files:
```python
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
```

---

## Important Constants

```python
# File paths
DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results")

# Time parameters
MONTHS = 120  # Total planning horizon
DAYS_PER_MONTH = 21  # Business days per month
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH  # 2,520 business days

# Operational constraints
DELIVERY_TIME = 8  # 8am local time (all suppliers)
SHIPMENT_DEADLINE = 17  # 5pm local time (all customer shipments)
MAX_TRUCKLOADS_PER_SUPPLIER_PER_DAY = 1

# Cost parameters
SAFETY_STOCK_MULTIPLIER = 1.0  # Adjust for sensitivity analysis
```

---

## Key Insights for Business Decisions

### From Expansion Variables
- Total capital investment required
- Mix of storage types needed (bins vs. pallets vs. racking)
- Timing of construction projects
- Return on investment analysis
- Tier pricing optimization (Sacramento)

### From Daily Inventory Variables
- **Peak storage days** (exact day with highest capacity usage, not just month)
- **Intraday inventory patterns** (how stock levels fluctuate within month)
- **Daily working capital** requirements
- **Safety stock validation** (ensured daily, not just monthly average)
- **Capacity utilization by day** (identify which specific days hit capacity limits)

### From Daily Order & Delivery Variables
- **Daily receiving schedule** (exact days trucks arrive at 8am)
- **Dock workload planning** (how many deliveries each day)
- **Supplier constraint compliance** (verify max 1 truck/supplier/day)
- **Cash outflow timing** (payments typically due on delivery)
- Supplier order patterns (consistent vs. lumpy ordering)
- Daily cash flow requirements
- Lead time impact on ordering decisions
- Optimal order quantities
- Receiving dock workload planning

### From Daily Shipment Variables
- **Daily shipping workload** (exact number of units to ship each day)
- **Labor scheduling** (staff needed for packing/loading each day)
- **Transportation planning** (daily truck scheduling and routing)
- **Peak shipping days** (identify busiest fulfillment days, not just months)
- **Demand fulfillment flexibility** (model can shift orders across days within month)
- **Primary vs. backup facilities** (which facility serves which customers on which days)

---

## Model Comparison: Monthly vs. Daily Indexing

### Option 1: Monthly Aggregation (Simplified)
**Variables**: 19,452
**Solve time**: Minutes
**Use for**: Initial feasibility testing, strategic planning
**Limitation**:
- Cannot specify exact day for orders/deliveries/shipments
- Demand assumed to occur at month-end
- No intramonth inventory tracking

### Option 2: Partial Daily (Orders Only)
**Variables**: 149,052 (orders daily, inventory/shipments monthly)
**Solve time**: Hours
**Use for**: Order timing optimization with simplified inventory
**Limitation**:
- Inventory still monthly (no daily tracking)
- Demand still monthly
- Cannot model daily capacity constraints

### Option 3: Full Daily Indexing (RECOMMENDED)
**Variables**: 408,252 (ALL variables daily)
**Solve time**: Hours to days
**Use for**: Complete operational planning
**Benefits**:
- **Exact dates** for all operations (orders, deliveries, shipments)
- **Daily inventory tracking** (know stock levels each day)
- **Daily capacity validation** (ensure volume/weight limits met each day)
- **Realistic constraints** (max 1 delivery/supplier/day, 8am arrivals, 5pm shipments)
- **Demand flexibility** (can fulfill customer orders any day, not just month-end)

**Recommendation**: Use **Option 3 (Full Daily)** for this project since operational constraints (delivery times, daily truck limits) require daily granularity.

---

## Summary

This model provides **complete end-to-end optimization** for warehouse expansion and operations with **full daily time granularity**:

### Decision Levels

1. **Strategic (One-time)**:
   - How much to expand each facility (Sacramento/Austin)
   - Capital investment optimization with tiered pricing

2. **Tactical (One-time)**:
   - How much shelving of each type to install (Bins, Racking, Pallet, Hazmat)
   - Equipment procurement planning

3. **Operational (Daily - 2,520 business days)**:
   - **When to order** (exact day within each month)
   - **When deliveries arrive** (tracking 8am arrivals with lead times)
   - **Daily inventory levels** (end-of-day stock at each facility)
   - **When to ship** (which facility fulfills demand which day by 5pm)

### Why Full Daily Indexing Matters

**Operational Realities**:
- Supplier deliveries arrive at **specific times** (8am), not "sometime during month"
- Delivery capacity is **limited daily** (max 1 truck/supplier/day/facility)
- Customer demand occurs **throughout the month**, not all at month-end
- Inventory levels **fluctuate daily** as deliveries arrive and shipments leave
- Capacity constraints must be **satisfied daily**, not just monthly average

**Planning Precision**:
- **Exact dates** for placing purchase orders
- **Day-by-day receiving schedule** for dock planning
- **Daily labor requirements** for receiving and shipping
- **Precise cash flow** timing (payments on delivery dates)

### Model Size

**Total**: **408,252 decision variables, ~1,500,000 constraints**
- 12 strategic expansion variables
- 136,080 daily inventory variables
- 136,080 daily order variables
- 136,080 daily delivery variables
- 136,080 daily shipment variables

**Planning Horizon**: 2,520 business days (120 months × 21 days) = 10 years (2026-2035)

**Objective**: Minimize total cost = expansion investment + daily inventory holding costs

**Solver Requirements**: Commercial solver (CPLEX or Gurobi) with parallel processing recommended
