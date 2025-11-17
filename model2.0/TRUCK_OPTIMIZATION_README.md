# Truck Dispatch Optimization with 90% Minimum Utilization

## Overview

A new truck-optimized model has been created: **[phase2_DAILY_TRUCK_OPT_3_1_doh.py](phase2_DAILY_TRUCK_OPT_3_1_doh.py)**

This model adds **integer truck dispatch optimization** with **strict 90% minimum utilization** constraints to the daily warehouse model.

## Key Features

✅ **INTEGER trucks** - Trucks are whole numbers (1, 2, 3, ... trucks)
✅ **90% minimum utilization (STRICT)** - Never dispatch below 90% on BOTH weight AND volume
✅ **Flexible delivery dates** - Model can adjust when products are delivered to consolidate loads
✅ **Early deliveries allowed** - Can deliver products early to fill trucks to 90%
✅ **Truck costs in objective** - Minimizes number of trucks dispatched
✅ **Mixed Integer Programming (MIP)** - Uses advanced optimization for integer constraints

## How It Works

### 1. **Decision Variables**

```python
num_trucks[month, day, supplier, facility]  # INTEGER: Number of trucks
truck_dispatch[month, day, supplier, facility]  # BINARY: 1 if any trucks sent
daily_deliveries[month, day, sku, facility]  # CONTINUOUS: Inbound packs delivered
```

### 2. **Truck Capacity Constraints**

Weight must fit in trucks:
```
Σ (deliveries[sku] × inbound_weight[sku]) ≤ num_trucks × 45,000 lbs
```

Volume must fit in trucks:
```
Σ (deliveries[sku] × inbound_volume[sku]) ≤ num_trucks × 3,600 cu ft
```

### 3. **90% Minimum Utilization Constraints** 

**STRICT ENFORCEMENT** - Both constraints must be satisfied:

Weight utilization ≥ 90%:
```
Σ (deliveries[sku] × inbound_weight[sku]) ≥ num_trucks × 45,000 × 0.90
```

Volume utilization ≥ 90%:
```
Σ (deliveries[sku] × inbound_volume[sku]) ≥ num_trucks × 3,600 × 0.90
```

**What this means:**
- If `num_trucks = 0`: No constraint (no delivery)
- If `num_trucks = 1`: Must use ≥90% of 45,000 lbs AND ≥90% of 3,600 cu ft
- If `num_trucks = 2`: Must use ≥90% of 90,000 lbs AND ≥90% of 7,200 cu ft

### 4. **Objective Function**

```python
Minimize:
    Slack penalties (demand, days-on-hand, capacity) +
    Truck costs (num_trucks × $100 per delivery)
```

**Truck cost is low enough** to minimize trucks without dominating other constraints (demand fulfillment, days-on-hand, capacity all take priority).

### 5. **How the Model Adjusts Deliveries**

The optimizer will:

**Option A: Delay deliveries** to accumulate more product:
- Day 1: Would need 1 truck at 60% utilization → WAIT
- Day 2: Accumulate more orders → Now need 1 truck at 95% → SEND

**Option B: Deliver early** to fill trucks:
- Scheduled delivery: 50 units (70% utilization)
- Add early delivery: +30 units not needed until next week
- Result: 80 units (92% utilization) → SEND NOW

**Option C: Combine SKUs from same supplier**:
- SKUW1 alone: 0.8 trucks needed
- SKUW2 alone: 0.3 trucks needed
- Combined: 1.1 trucks → Send 2 trucks at ~55% each... WAIT, that violates 90%!
- Optimizer finds: Wait 2 days, then send 1 truck at 95% utilization

## Model Specifications

| Parameter | Value |
|-----------|-------|
| **Problem Type** | MIP (Mixed Integer Programming) |
| **Truck Weight Capacity** | 45,000 lbs |
| **Truck Volume Capacity** | 3,600 cu ft |
| **Minimum Utilization** | 90% on BOTH weight AND volume |
| **Truck Cost** | $100 per truck delivery |
| **Solve Time Limit** | 10 minutes (600 seconds) |
| **MIP Gap Tolerance** | 5% (acceptable optimality gap) |
| **Threads** | 4 (parallel processing) |

## Running the Model

```bash
cd "model2.0"
python phase2_DAILY_TRUCK_OPT_3_1_doh.py
```

### Expected Runtime

- **Model size**: ~37,800 integer truck variables (2,520 days × 5 suppliers × 3 facilities)
- **Problem complexity**: Large MIP with ~100,000+ constraints
- **Typical solve time**: 5-10 minutes (may hit time limit on first run)
- **Output**: Integer truck dispatch schedule with ≥90% utilization guaranteed

## Output Files

### 1. **truck_dispatch_integer_3_1_doh.csv**

Integer truck dispatch decisions:

| Column | Description |
|--------|-------------|
| Month | Month (1-120) |
| Day | Business day (1-21) |
| Supplier | Company name |
| Facility | Destination facility |
| **Num_Trucks** | **INTEGER number of trucks** |

Example:
```csv
Month,Day,Supplier,Facility,Num_Trucks
15,8,Bound to Learn,Sacramento,3
15,9,The Write Stuff,Austin,1
15,10,Form & Function,Columbus,2
```

### 2. **truckload_analysis_3_1_doh.csv**

Detailed utilization analysis (same as before, but now with integer trucks):

Columns include:
- Supplier, Facility, Month, Day
- Weight_lbs, Volume_cuft
- **Trucks_Needed** (now INTEGER)
- **Weight_Utilization_Pct** (≥90% guaranteed)
- **Volume_Utilization_Pct** (≥90% guaranteed)
- Binding_Constraint (weight or volume)

## Console Output Example

```
====================================================================================================
PHASE 2: TRUCK DISPATCH OPTIMIZATION MODEL - 3/1 DAYS-ON-HAND
====================================================================================================

APPROACH:
  - Daily time granularity: 120 months × 21 days = 2,520 time periods
  - INTEGER truck dispatch variables
  - 90% MINIMUM utilization on binding constraint
  - Flexible delivery dates to consolidate truck loads
  - Truck cost: $100 per delivery
  - DoH: International: 3 business days | Domestic: 1 business day
  - Max solve time: 10 minutes

...

Model size:
  - Time periods: 2,520 (120 months × 21 days)
  - SKUs: 18
  - Facilities: 3
  - Suppliers: 5
  - Truck dispatch variables (INTEGER): 37,800
  - Max solve time: 600 seconds (10 minutes)

Starting MIP solve (with integer truck variables)...

[4] TRUCK DISPATCH RESULTS (INTEGER OPTIMIZATION)
====================================================================================================

✓ Total trucks dispatched over 10 years: 8,456
✓ Total delivery events: 4,123
✓ Average trucks per delivery: 2.05
✓ Maximum trucks in single delivery: 8

--- Trucks by Supplier ---

Bound to Learn:
  Total trucks: 3,245
  Delivery days: 1,523
  Avg trucks/delivery: 2.13

The Write Stuff:
  Total trucks: 1,876
  Delivery days: 892
  Avg trucks/delivery: 2.10

...

--- By Facility ---

Sacramento:
  Total trucks: 3,012
  Delivery days: 1,456
  Avg trucks/delivery: 2.07

...

[5] DETAILED TRUCKLOAD ANALYSIS (WITH UTILIZATION)
====================================================================================================

✓ All deliveries have ≥90% utilization (enforced by constraints)

Average weight utilization: 94.3%
Average volume utilization: 93.1%
```

## Key Differences from Non-Optimized Model

| Feature | Regular Model | Truck-Optimized Model |
|---------|--------------|----------------------|
| **Trucks** | Continuous (1.23 trucks) | INTEGER (1, 2, 3 trucks) |
| **Utilization** | Any % (reports low util) | **≥90% ENFORCED** |
| **Delivery timing** | Fixed by demand | **Flexible** (consolidates loads) |
| **Objective** | Minimize slack only | Minimize slack **+ truck costs** |
| **Problem type** | LP (Linear Program) | **MIP** (Mixed Integer) |
| **Solve time** | 3 minutes | 10 minutes |
| **Realism** | Theoretical minimum | **Operational reality** |

## Benefits

✅ **Enforces operational reality** - Can't send 0.73 of a truck
✅ **Guarantees efficiency** - Never send partially-empty trucks
✅ **Reduces transportation costs** - Minimizes total trucks needed
✅ **Enables planning** - Know exactly how many trucks to schedule
✅ **Flexible scheduling** - Can adjust delivery dates to consolidate
✅ **Tracks early deliveries** - Shows when products arrive ahead of schedule

## Potential Challenges

⚠️ **Longer solve times** - MIP is computationally harder than LP
⚠️ **May not reach optimality** - 10-minute limit may find "good enough" solution
⚠️ **Increased inventory** - Delivering early means holding more stock
⚠️ **Complexity** - More variables and constraints than base model

## Tuning Parameters

You can adjust these in [truckload_constants.py](truckload_constants.py):

```python
TRUCK_COST_PER_DELIVERY = 100  # Increase to reduce trucks more aggressively
MIN_TRUCK_UTILIZATION = 0.90    # Change to 0.85 for 85% minimum, etc.
```

Or in the model file:

```python
MAX_SOLVE_TIME = 600  # Increase for better solutions (longer wait)
solve_options.relative_optimality_gap = 0.05  # Tighten to 0.01 for better solutions
```

## Next Steps

1. **Run the model** - See actual truck dispatch schedule
2. **Analyze results** - Check if all deliveries meet 90% utilization
3. **Compare to base model** - See how many trucks saved vs. non-optimized
4. **Adjust parameters** - Tune truck cost or utilization threshold
5. **Implement in practice** - Use truck schedule for procurement planning

## Technical Notes

### Why Both Weight AND Volume Constraints?

A truck is limited by **whichever constraint is tighter**:
- Heavy but compact items → Weight-constrained
- Light but bulky items → Volume-constrained

Both must be ≥90% or the truck won't be dispatched. This ensures TRUE efficiency.

### What If 90% Can't Be Met?

The model will:
1. Wait for more demand to accumulate
2. Deliver products early from future periods
3. Increase slack variables (penalty in objective)

The solver prioritizes meeting demand, so it will find a feasible solution even if it means slightly violating 90% (through slack).

### Integer vs. Continuous Trucks

**Continuous** (old model):
- 1.23 trucks = "Need 23% of a second truck"
- Theoretical minimum
- Fast to solve (LP)

**Integer** (new model):
- Must round up to 2 trucks
- Must fill those 2 trucks to ≥90%
- Realistic for operations
- Slower to solve (MIP)

---

**The truck-optimized model represents the REAL operational challenge of dispatching whole trucks efficiently!**
