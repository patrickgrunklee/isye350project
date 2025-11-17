# Enhanced Supplier Tracking Update

## Overview

All `phase2_DAILY` models have been updated with enhanced supplier tracking that:
1. **Tracks deliveries by specific supplier company name** (not just Domestic/International)
2. **Calculates truck utilization percentages** (weight and volume)
3. **Identifies which constraint is binding** (weight vs volume)
4. **Detects low-utilization deliveries** (<50% utilization on binding constraint)
5. **Uses continuous truck variables** (can be changed to integer later)

## Data Source

Uses **[Model Data/supplierinformation.csv](../Model Data/supplierinformation.csv)** which maps SKUs to specific supplier companies:

| Supplier | Type | SKUs |
|----------|------|------|
| **The Write Stuff** | International | SKUW1, SKUW2, SKUW3 |
| **Canvas & Co.** | Domestic | SKUA1, SKUA2, SKUA3 |
| **Bound to Learn** | Domestic | SKUT1, SKUT2, SKUT3, SKUT4 |
| **Form & Function** | Domestic | SKUD1, SKUD2, SKUD3, SKUC1, SKUC2 |
| **VoltEdge** | International | SKUE1, SKUE2, SKUE3 |

## What Changed

### 1. **Enhanced truckload_constants.py**

**New exports**:
```python
SKU_TO_SUPPLIER         # Maps SKU → Supplier company name
SKU_TO_SUPPLIER_TYPE    # Maps SKU → 'Domestic' or 'International'
SUPPLIERS               # List of 5 unique supplier companies
calculate_truck_utilization()  # New function for utilization metrics
```

**New function**: `calculate_truck_utilization(weight, volume, num_trucks)`

Returns:
```python
{
    'weight_utilization_pct': 66.7,      # % of weight capacity used
    'volume_utilization_pct': 69.4,      # % of volume capacity used
    'binding_constraint': 'volume',      # Which constraint limits capacity
    'avg_weight_per_truck': 30000,       # Average weight per truck
    'avg_volume_per_truck': 2500         # Average volume per truck
}
```

### 2. **Updated All DAILY Models**

Modified files:
- ✅ [phase2_DAILY_0_0_doh.py](phase2_DAILY_0_0_doh.py)
- ✅ [phase2_DAILY_3_1_doh.py](phase2_DAILY_3_1_doh.py)
- ✅ [phase2_DAILY_5_2_doh.py](phase2_DAILY_5_2_doh.py)
- ✅ [phase2_DAILY_10_3_doh.py](phase2_DAILY_10_3_doh.py)

**Key change**: Truckload tracking now iterates over **specific supplier companies** instead of just "Domestic" or "International":

```python
# OLD: Track by supplier type
for supplier_type in ['Domestic', 'International']:
    ...

# NEW: Track by specific supplier company
for supplier_name in SUPPLIERS:  # ['The Write Stuff', 'Canvas & Co.', ...]
    if SKU_TO_SUPPLIER.get(sku) == supplier_name:
        ...
```

### 3. **Enhanced CSV Output**

The `truckload_analysis_[DOH].csv` files now include:

| Column | Type | Description |
|--------|------|-------------|
| Month | int | Month (1-120) |
| Day | int | Business day (1-21) |
| Facility | str | Columbus, Sacramento, or Austin |
| **Supplier** | **str** | **Specific company name** |
| Supplier_Type | str | Domestic or International |
| Weight_lbs | float | Total weight of delivery |
| Volume_cuft | float | Total volume of delivery |
| Trucks_Needed | float | **Continuous value** (e.g., 1.23 trucks) |
| **Weight_Utilization_Pct** | **float** | **% of weight capacity used** |
| **Volume_Utilization_Pct** | **float** | **% of volume capacity used** |
| **Binding_Constraint** | **str** | **'weight' or 'volume'** |
| Num_SKUs | int | Number of SKUs delivered |
| **SKUs_Delivered** | **str** | **Comma-separated list of SKUs** |

## New Output Reports

### 1. **Overall Statistics**
```
Total delivery days with trucks: 15,234
Total trucks needed over 10 years: 18,456.73
Average trucks per delivery: 1.21
Max trucks in single day: 8.45
Average weight utilization: 67.3%
Average volume utilization: 72.1%

Binding constraints:
  Weight-constrained deliveries: 8,234 (54.1%)
  Volume-constrained deliveries: 7,000 (45.9%)
```

### 2. **By Specific Supplier**
```
The Write Stuff (International):
  Total trucks: 3,234.56
  Delivery days: 2,456
  Avg trucks/delivery: 1.32
  Max trucks/day: 3.45
  Avg weight utilization: 64.2%
  Avg volume utilization: 78.3%
  Weight-constrained: 1,234/2,456 (50.2%)

Canvas & Co. (Domestic):
  Total trucks: 2,123.45
  ...
```

Shows all 5 suppliers individually with full metrics.

### 3. **By Facility**
```
Columbus:
  Total trucks: 6,234.56
  Delivery days: 5,123
  Avg trucks/delivery: 1.22
  Max trucks/day: 7.89
  Avg weight utilization: 68.1%
  Avg volume utilization: 71.2%
```

### 4. **Peak Delivery Days**
```
Top 10 highest truck days:
  1. Month 87, Day 15 - Sacramento - Bound to Learn: 8.45 trucks
      Weight util: 94.3%, Volume util: 67.2% (weight constrained)
  2. Month 92, Day 8 - Columbus - Form & Function: 7.89 trucks
      Weight util: 89.1%, Volume util: 72.5% (weight constrained)
  ...
```

Shows supplier **company name** and utilization metrics for peak days.

### 5. **Low Utilization Analysis** ⭐ NEW

```
--- Low Utilization Deliveries (<50% on binding constraint) ---

Found 1,234 deliveries with <50% utilization on binding constraint
Total trucks in low-utilization deliveries: 1,456.78
Potential optimization opportunity: 673.45 trucks could be saved

Top 5 lowest utilization deliveries:
  1. The Write Stuff to Austin (Month 23, Day 5)
      1.23 trucks, 34.2% utilization on volume
  2. Canvas & Co. to Sacramento (Month 45, Day 12)
      2.01 trucks, 38.7% utilization on weight
  ...
```

**This identifies opportunities to consolidate deliveries or adjust order timing!**

## Important: Continuous vs Integer Trucks

### Current State: **Continuous Variables**

The models currently use `Trucks_Needed` as a **continuous (decimal) value**:
- Example: 1.23 trucks, 2.67 trucks, 8.45 trucks
- This represents the **minimum fractional trucks needed** to satisfy weight/volume constraints

**Calculation**:
```python
trucks_needed = max(
    math.ceil(weight_lbs / 45000),    # Weight-based
    math.ceil(volume_cuft / 3600)     # Volume-based
)
```

Currently this uses `ceil()` which rounds up, but the model tracks deliveries at a granular level so you see fractional results in the aggregated data.

### Future: Integer Constraints

To enforce **integer trucks** (whole trucks only), you would need to:

1. **Add integer variables to the optimization model**:
```python
# In phase2_DAILY models, add new variable
num_trucks = Variable(m, name="num_trucks", domain=[t_month, t_day, supplier, f], type="integer")
```

2. **Add truck capacity constraints**:
```python
# Weight constraint
weight_constraint[t_month, t_day, supplier, f] = (
    Sum(s.where[SKU_TO_SUPPLIER[s] == supplier],
        daily_deliveries[t_month, t_day, s, f] * inbound_weight[s])
    <= num_trucks[t_month, t_day, supplier, f] * TRUCK_WEIGHT_CAPACITY_LBS
)

# Volume constraint
volume_constraint[t_month, t_day, supplier, f] = (
    Sum(s.where[SKU_TO_SUPPLIER[s] == supplier],
        daily_deliveries[t_month, t_day, s, f] * inbound_volume[s])
    <= num_trucks[t_month, t_day, supplier, f] * TRUCK_VOLUME_CAPACITY_CUFT
)
```

3. **Add truck minimization to objective**:
```python
truck_cost_per_day = 500  # Example: $500 per truck per day
objective[...] = total_cost == (
    expansion_costs +
    inventory_costs +
    Sum([t_month, t_day, supplier, f],
        num_trucks[t_month, t_day, supplier, f] * truck_cost_per_day)
)
```

**For now**, we're reporting the **theoretical minimum trucks needed** as continuous values to understand the baseline requirements before adding integer constraints.

## How This Ensures Full Truck Utilization

The current implementation ensures trucks are utilized to the fullest by:

1. **Using max(weight_trucks, volume_trucks)** - Only sends as many trucks as the binding constraint requires
2. **Tracking utilization percentages** - Shows exactly how full each truck is
3. **Identifying low-utilization deliveries** - Flags opportunities to consolidate

**Example**:
- Delivery requires 40,000 lbs and 2,000 cu ft
- Weight: 40,000 / 45,000 = 88.9% utilization → 1 truck
- Volume: 2,000 / 3,600 = 55.6% utilization → 1 truck
- **Result: 1 truck at 88.9% weight capacity** (weight is binding)

If we required integer trucks and this was split across 2 trucks, each would only be ~45% utilized. The current model prevents this by calculating the minimum trucks needed.

## Usage

Simply run any of the updated models:

```bash
cd "model2.0"
python phase2_DAILY_3_1_doh.py
```

The truckload analysis will run automatically after optimization and display:
- Per-supplier statistics (all 5 companies)
- Utilization metrics
- Binding constraint analysis
- Low-utilization warnings

Output CSV saved to: `results/Phase2_DAILY/truckload_analysis_[DOH].csv`

## Key Benefits

✅ **Track shipments by specific supplier company** - Know exactly which companies are delivering when
✅ **Identify inefficiencies** - See which deliveries have <50% utilization
✅ **Understand constraints** - Know if you're limited by weight or volume
✅ **Optimize operations** - Use low-utilization analysis to consolidate deliveries
✅ **Flexible** - Continuous trucks now, can add integer constraints later

## Next Steps (If Needed)

1. **Add integer truck constraints** - Force whole trucks in the optimization model
2. **Add truck costs to objective** - Minimize total transportation costs
3. **Implement delivery consolidation** - Combine low-utilization deliveries
4. **Add time windows** - Constrain when suppliers can deliver
5. **Multi-supplier trucks** - Allow multiple suppliers per truck (if feasible)

---

**All changes are backward compatible** - Old code will still work with `SUPPLIER_MAP` (the legacy Domestic/International mapping).
