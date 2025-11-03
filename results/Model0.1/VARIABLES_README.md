# Warehouse Optimization - All Decision Variables Export

This directory contains all decision variables from the warehouse optimization model.

## Files Exported

### 1. `var_expansion.csv`
**Square footage expansion by facility**
- Columns: `f_exp` (facility), `level` (sqft added), `marginal`, `lower`, `upper`, `scale`
- Shows how many square feet to add at Sacramento and Austin
- Columbus cannot be expanded (project constraint)

### 2. `var_sacramento_tiers.csv`
**Sacramento tiered pricing breakdown**
- Columns: `Tier`, `sqft`, `cost_usd`
- Tier 1: First 100K sqft @ $2/sqft
- Tier 2: Next 150K sqft @ $4/sqft
- Total Sacramento max: 250K sqft

### 3. `var_add_shelves.csv`
**Additional shelves by facility and storage type**
- Columns: `f_exp` (facility), `st` (storage type), `level` (number of shelves), `marginal`, `lower`, `upper`, `scale`
- Storage types: Bins, Racking, Pallet, Hazmat
- Shows how many shelves of each type to add

### 4. `var_monthly_inventory.csv`
**Inventory levels over time**
- Columns: `t_month` (month 1-120), `s` (SKU), `f` (facility), `level` (inventory units), `marginal`, `lower`, `upper`, `scale`
- **Size**: 120 months × 18 SKUs × 3 facilities = 6,480 rows
- Units are in SELL PACKS
- Shows end-of-month inventory at each facility for each SKU

### 5. `var_monthly_deliveries.csv`
**Order quantities (supplier deliveries)**
- Columns: `t_month` (month 1-120), `s` (SKU), `f` (facility), `level` (number of inbound packs), `marginal`, `lower`, `upper`, `scale`
- **Size**: 120 months × 18 SKUs × 3 facilities = 6,480 rows
- Units are in INBOUND PACKS
- Shows how many inbound packs to order each month
- Convert to sell packs by multiplying by inbound_qty[sku]

### 6. `var_monthly_shipments.csv`
**Customer fulfillment (outbound shipments)**
- Columns: `t_month` (month 1-120), `s` (SKU), `f` (facility), `level` (units shipped), `marginal`, `lower`, `upper`, `scale`
- **Size**: 120 months × 18 SKUs × 3 facilities = 6,480 rows
- Units are in SELL PACKS
- Shows which facility fulfills demand each month
- Constraint: Sum across facilities >= monthly demand

### 7. `var_packages_on_shelf.csv`
**Storage allocation by storage type**
- Columns: `t_month` (month 1-120), `s` (SKU), `f` (facility), `st` (storage type), `level` (number of packages), `marginal`, `lower`, `upper`, `scale`
- **Size**: 120 months × 18 SKUs × 3 facilities × 4 storage types = 25,920 rows
- Shows how packages are distributed across storage types
- Each SKU uses only one storage type (determined by Storage Method column)

### 8. `var_total_cost.csv`
**Total expansion cost (objective value)**
- Columns: `Variable`, `Value_USD`
- Single row with total optimization objective value
- **Note**: If value is very high (e.g., $449B), it includes slack penalties for truck limit violations
- True expansion cost = Sacramento expansion cost + Austin expansion cost

## Model Configuration

- **Time horizon**: 120 months (2026-2035)
- **SKUs**: 18 products
- **Facilities**: 3 (Columbus, Sacramento, Austin)
- **Expandable facilities**: Sacramento (max +250K sqft), Austin (max +200K sqft)
- **Storage types**: Bins, Racking, Pallet, Hazmat
- **Repacking**: Disabled (all SKUs stored in inbound pack format)
- **Days-on-hand safety stock**: Disabled (to avoid infeasibility)
- **Truck constraints**: Enabled with slack penalties ($10K per extra delivery)

## Key Relationships

### Inventory Balance
```
inventory[t] = inventory[t-1] + deliveries[t] * inbound_qty - shipments[t]
```

### Package-Inventory Link
```
inventory[t, s, f] = Sum(packages_on_shelf[t, s, f, st]) * inbound_qty[s]
```
Since repacking is disabled, each package is an inbound pack containing `inbound_qty[s]` sell packs.

### Demand Fulfillment
```
Sum_f(shipments[t, s, f]) >= demand[t, s]
```
Any facility can fulfill demand for any SKU.

## Interpreting Results

### Current Model Results:
- **Expansion needed**: 0 sqft (current capacity sufficient)
- **Total cost**: Very high due to truck slack penalties
- **Implication**: Demand can be met without expansion, but truck delivery constraints are violated

### Truck Constraint Issue:
The model includes a penalty of $10,000 per truck delivery beyond the limit (21 deliveries/month/supplier).
Peak monthly demand for many SKUs exceeds what can be delivered in 21 trucks, causing high slack penalties.

To fix this:
1. Implement daily delivery scheduling instead of monthly aggregation
2. Adjust truck constraints to reflect realistic multi-truck scenarios
3. Remove truck constraints entirely if they're not binding in practice

## Usage Examples

### Python - Load and Analyze Variables

```python
import pandas as pd
from pathlib import Path

results_dir = Path('results')

# Load expansion decisions
expansion = pd.read_csv(results_dir / 'var_expansion.csv')
print("Expansion by facility:")
print(expansion[['f_exp', 'level']])

# Load monthly inventory and plot for a specific SKU
inventory = pd.read_csv(results_dir / 'var_monthly_inventory.csv')
sku_inv = inventory[inventory['s'] == 'SKUW1']

# Group by month to see total inventory across all facilities
monthly_total = sku_inv.groupby('t_month')['level'].sum()
print(f"\nSKUW1 total inventory over time:")
print(monthly_total.head())

# Load deliveries and check order schedule
deliveries = pd.read_csv(results_dir / 'var_monthly_deliveries.csv')
orders = deliveries[deliveries['level'] > 0.1]  # Filter non-zero orders
print(f"\nTotal order events: {len(orders)}")
```

### Excel - Pivot Tables
1. Open `var_monthly_inventory.csv` in Excel
2. Create PivotTable:
   - Rows: `t_month`
   - Columns: `s` (SKU)
   - Values: Sum of `level`
3. This shows total inventory by SKU by month across all facilities

## Notes

- All variable records include `marginal`, `lower`, `upper`, `scale` columns from GAMSPy
- `level` column contains the actual optimized value
- `marginal` column shows shadow prices (sensitivity analysis)
- Rows with `level` ≈ 0 may appear due to numerical precision (treat as 0)

## Generated By

Model: `full_daily_warehouse_model.py`
Date: 2025 (based on model execution)
Solver: CPLEX (via GAMSPy)
Problem Type: LP (Linear Programming)
