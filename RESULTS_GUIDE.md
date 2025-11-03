# Complete Guide to Result Files

## Current Files in `results/` Folder

Based on what's in your results directory, here's what each file contains:

### 📊 Summary Files (Human-Readable)

#### 1. `full_daily_expansion_summary.csv`
**What it is**: High-level summary of expansion decisions and total costs
**Columns**:
- `Facility` (Sacramento, Austin, TOTAL)
- `Expansion_sqft` (square feet to add)
- `Cost_USD` (expansion cost)

**Use this to**: Get the bottom line - how much expansion, how much cost

---

#### 2. `full_daily_monthly_inventory.csv`
**What it is**: Same as `var_monthly_inventory.csv` (see below)
**Size**: 6,480 rows (120 months × 18 SKUs × 3 facilities)
**Units**: SELL PACKS

**Use this to**: Track inventory levels over time

---

#### 3. `weight_shortfalls.csv`
**What it is**: Legacy file from `feasibility_check_model.py`
**Columns**: Facility, Storage Type, Weight Shortfall (lbs)

**Use this to**: See which facilities/storage types have weight capacity issues

---

### 🔢 Detailed Variable Files (All Decision Variables)

#### 4. `var_expansion.csv`
**Decision Variable**: How much to expand each facility
**Rows**: 2 (Sacramento, Austin)
**Columns**:
- `f_exp` (facility)
- `level` (square feet to add)
- `marginal` (shadow price - how much cost would change if we forced 1 more sqft)

**Key insight**: Look at `level` column for expansion amounts

---

#### 5. `var_sacramento_tiers.csv`
**What it is**: Breakdown of Sacramento expansion into pricing tiers
**Rows**: 2 (Tier 1, Tier 2)
**Columns**:
- `Tier` (pricing tier description)
- `sqft` (square feet in this tier)
- `cost_usd` (cost for this tier)

**Sacramento pricing**:
- Tier 1: First 100K sqft @ $2/sqft
- Tier 2: Next 150K sqft @ $4/sqft

---

#### 6. `var_add_shelves.csv`
**Decision Variable**: Additional shelves by facility and storage type
**Rows**: ~8 (Sacramento & Austin × 4 storage types)
**Columns**:
- `f_exp` (facility)
- `st` (storage type: Bins, Racking, Pallet, Hazmat)
- `level` (number of shelves to add)

**Use this to**: Determine equipment purchasing - how many pallets, racks, bins, hazmat shelves to buy

---

#### 7. `var_monthly_inventory.csv`
**Decision Variable**: Inventory held at each facility each month
**Rows**: 6,480 (120 months × 18 SKUs × 3 facilities)
**Columns**:
- `t_month` (month 1-120)
- `s` (SKU: SKUW1, SKUT2, etc.)
- `f` (facility: Columbus, Sacramento, Austin)
- `level` (inventory amount in SELL PACKS)

**Use this to**:
- Plot inventory trajectories over time
- Identify peak inventory months
- See which facility holds what inventory

---

#### 8. `var_monthly_deliveries.csv`
**Decision Variable**: How many inbound packs to order each month
**Rows**: 6,480 (120 months × 18 SKUs × 3 facilities)
**Columns**:
- `t_month` (month 1-120)
- `s` (SKU)
- `f` (facility)
- `level` (number of INBOUND PACKS to order)

**IMPORTANT**: Units are **INBOUND PACKS**, not sell packs
- To convert to sell packs: `deliveries × inbound_qty[sku]`
- Example: 10 inbound packs of SKUW1 = 10 × 12 = 120 sell packs

**Use this to**:
- Create purchase orders to suppliers
- Plan delivery schedules
- Calculate total inbound shipments

---

#### 9. `var_monthly_shipments.csv`
**Decision Variable**: How many units to ship from each facility each month
**Rows**: 6,480 (120 months × 18 SKUs × 3 facilities)
**Columns**:
- `t_month` (month 1-120)
- `s` (SKU)
- `f` (facility)
- `level` (units shipped in SELL PACKS)

**Constraint**: `Sum across facilities >= demand[month, sku]`

**Use this to**:
- Plan outbound logistics
- See which facility fulfills which demand
- Identify primary vs backup facilities

---

#### 10. `var_packages_on_shelf.csv`
**Decision Variable**: How packages are stored by storage type
**Rows**: 25,920 (120 months × 18 SKUs × 3 facilities × 4 storage types)
**Columns**:
- `t_month` (month 1-120)
- `s` (SKU)
- `f` (facility)
- `st` (storage type)
- `level` (number of packages)

**Note**: Each SKU uses only ONE storage type (from SKU Details.csv)
- So most rows will be 0 (only the matching storage type has packages)

**Use this to**:
- Verify packages fit on shelves
- Check storage allocation across types

---

#### 11. `var_total_cost.csv`
**Objective Value**: Total cost the model minimized
**Rows**: 1
**Columns**:
- `Variable` ("Total_Cost")
- `Value_USD` (objective function value)

**IMPORTANT**:
- If value is very high (e.g., $449 billion), it includes TRUCK SLACK PENALTIES
- True expansion cost = Sacramento cost + Austin cost (from expansion_summary.csv)
- Truck penalties = $10,000 per extra delivery beyond limit

**Interpretation**:
- Low cost (~$0-$1M): Expansion cost only, no truck violations
- High cost (~$100M+): Heavy truck penalty costs included

---

### 📁 Missing Files (Should be exported if model runs with repacking/truck constraints)

#### `full_daily_repacking_decisions.csv`
**Should contain**: Which SKUs to repack at which facilities
**Columns**: `s` (SKU), `f` (facility), `level` (1 = repack, 0 = store as inbound)
**Status**: Only created if repacking is enabled (currently enabled in latest version)

---

#### `full_daily_truck_violations.csv`
**Should contain**: Months/suppliers/facilities that exceed 1 truck/day limit
**Columns**:
- `t_month` (month)
- `sup` (supplier: Domestic, International)
- `f` (facility)
- `level` (extra deliveries needed beyond 21/month)

**Status**: Only created if truck_slack > 0 (violations occur)

---

#### `full_daily_additional_shelves.csv`
**Should contain**: Same as `var_add_shelves.csv` but filtered to only shelves with level > 0.5
**Status**: Only created if shelves need to be added

---

## How to Use These Files

### Quick Analysis in Excel

1. **Open** `var_monthly_inventory.csv`
2. **Create PivotTable**:
   - Rows: `t_month`
   - Columns: `s` (SKU)
   - Values: Sum of `level`
3. **Result**: Inventory by month by SKU

### Python Analysis

```python
import pandas as pd
from pathlib import Path

results = Path('results')

# Load all key variables
expansion = pd.read_csv(results / 'var_expansion.csv')
shelves = pd.read_csv(results / 'var_add_shelves.csv')
inventory = pd.read_csv(results / 'var_monthly_inventory.csv')
deliveries = pd.read_csv(results / 'var_monthly_deliveries.csv')
shipments = pd.read_csv(results / 'var_monthly_shipments.csv')

# Total expansion cost
summary = pd.read_csv(results / 'full_daily_expansion_summary.csv')
print(f"Total expansion: {summary['Expansion_sqft'].sum():,.0f} sqft")
print(f"Total cost: ${summary['Cost_USD'].sum():,.2f}")

# Peak inventory by SKU
peak_inv = inventory.groupby('s')['level'].max().sort_values(ascending=False)
print("\nPeak inventory by SKU:")
print(peak_inv)

# Total deliveries by facility
total_deliveries = deliveries.groupby('f')['level'].sum()
print("\nTotal inbound packs ordered by facility:")
print(total_deliveries)
```

### Power BI / Tableau

1. **Import** all `var_*.csv` files
2. **Create relationships**:
   - Link `t_month` across tables
   - Link `s` (SKU) across tables
   - Link `f` (facility) across tables
3. **Build dashboards**:
   - Line charts: Inventory over time
   - Bar charts: Expansion by facility
   - Heatmaps: Deliveries by month × facility

## File Relationships

```
full_daily_expansion_summary.csv  ← Summarizes → var_expansion.csv + var_sacramento_tiers.csv

var_add_shelves.csv ← Determines → var_packages_on_shelf.csv
                                    (shelves constrain packages)

var_monthly_deliveries.csv → var_monthly_inventory.csv → var_monthly_shipments.csv
(orders)                      (stored)                    (fulfilled)

Inventory balance: inventory[t] = inventory[t-1] + deliveries[t] - shipments[t]
```

## Quick Answers from Files

**Q: How much expansion do we need?**
→ `full_daily_expansion_summary.csv` - check "TOTAL" row

**Q: Which storage type needs the most shelves?**
→ `var_add_shelves.csv` - sort by `level` descending

**Q: When is peak inventory?**
→ `var_monthly_inventory.csv` - group by `t_month`, find max

**Q: Do we violate truck limits?**
→ Check if `full_daily_truck_violations.csv` exists and has rows

**Q: Which facility fulfills most demand?**
→ `var_monthly_shipments.csv` - group by `f`, sum `level`

**Q: What's the true expansion cost (excluding penalties)?**
→ `full_daily_expansion_summary.csv` - look at individual facility costs, ignore TOTAL if it's huge

## Files NOT in Results Folder

These are input data files (in `Model Data/` folder), not outputs:
- `Demand Details.csv`
- `SKU Details.csv`
- `Lead TIme.csv`
- `Shelving Count.csv`
- `Shelving Dimensions.csv`

## Summary Table

| File | Type | Rows | What It Shows | Key Column |
|------|------|------|---------------|------------|
| `full_daily_expansion_summary.csv` | Summary | 3 | Total expansion & costs | `Cost_USD` |
| `var_expansion.csv` | Variable | 2 | Sqft by facility | `level` |
| `var_sacramento_tiers.csv` | Summary | 2 | Sacramento pricing | `sqft` |
| `var_add_shelves.csv` | Variable | 8 | Shelves to add | `level` |
| `var_monthly_inventory.csv` | Variable | 6,480 | Inventory over time | `level` (sell packs) |
| `var_monthly_deliveries.csv` | Variable | 6,480 | Orders to suppliers | `level` (inbound packs) |
| `var_monthly_shipments.csv` | Variable | 6,480 | Outbound fulfillment | `level` (sell packs) |
| `var_packages_on_shelf.csv` | Variable | 25,920 | Package allocation | `level` (packages) |
| `var_total_cost.csv` | Objective | 1 | Total cost (with penalties) | `Value_USD` |
| `full_daily_monthly_inventory.csv` | Variable | 6,480 | Same as var_monthly_inventory | `level` |
| `weight_shortfalls.csv` | Legacy | varies | Weight capacity gaps | `Shortfall` |

**Total files**: 11 currently in folder
**Potential additional files**: 3 (repacking decisions, truck violations, additional shelves - only if applicable)
