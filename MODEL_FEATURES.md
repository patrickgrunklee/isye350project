# Full Daily Warehouse Model - Features Summary

## ✅ Implemented Features

### 1. Truck Delivery Constraints with Slack Variables

**Constraint**: 1 truck delivery per supplier per day = 21 deliveries per supplier per month

**Implementation**:
```python
truck_slack = Variable(..., domain=[t_month, supplier, facility])
# Tracks how many EXTRA deliveries needed beyond limit

truck_limit equation:
Sum(deliveries for supplier at facility in month) <= 21 + truck_slack
```

**Penalty**: $10,000 per extra delivery beyond limit (encourages compliance but allows violations if necessary)

**What it tells you**:
- Which months, suppliers, and facilities exceed the 1-truck/day limit
- How many extra trucks are needed
- Total penalty cost for truck violations

**Output Files**:
- `full_daily_truck_violations.csv` - All months/suppliers/facilities with violations
- Console output shows total violations and penalty cost

### 2. Inbound Pack vs Sell Pack Conversion

**Key Understanding**:
- Customer **demand** is in SELL PACKS (what they order)
- Supplier **deliveries** are in INBOUND PACKS (bulk shipments)
- **Conversion**: 1 inbound pack = `inbound_qty[sku]` sell packs

**Example** (SKUW1):
- Customer orders: 1,000 sell packs/month
- Supplier ships: Inbound packs (144 units = 12 sell packs each)
- We order: ⌈1,000 / 12⌉ = 84 inbound packs

**Implementation**:
```python
inventory[t, s, f] == deliveries[t, s, f] * inbound_qty[s] - shipments[t, s, f]
#                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                     Convert inbound packs to sell packs
```

### 3. Package Repacking Optimization (Set Packing)

**Binary Decision**: For each SKU at each facility, decide:
- Option A: Store as received (inbound packs) - larger packages
- Option B: Repack into sell packs - smaller, more flexible

**Rules**:
- 13 SKUs **can** be repacked: SKUW1-3, SKUA1-3, SKUT1-4, SKUE1-3
- 5 SKUs **cannot** be repacked: SKUD1-3, SKUC1-2 (desks, chairs)

**Constraints**:
```python
repack_decision[s, f] <= can_consolidate[s]  # Only if allowed

# Volume capacity with repacking:
volume = packages * (repack ? sell_volume : inbound_volume)

# Package capacity:
packages_on_shelf <= shelves * shelf_package_capacity
```

**What it optimizes**:
- Space utilization (repacked = smaller)
- Labor costs (repacking costs labor)
- Shelf capacity limits (max packages per shelf)

### 4. Complete Data Integration

**All 18 SKUs** with dimensions from `SKU Details.csv`:
- Sell pack dimensions (L×W×H in inches)
- Inbound pack dimensions (L×W×H in inches)
- Weights (sell pack and inbound pack)
- Consolidation flags
- Supplier types (Domestic vs International)

**All facilities** with shelf data from `Shelving Dimensions.csv`:
- Columbus: 7 pallet packages, 8 racking, Auto bins
- Austin: 6 pallet packages, 8 racking, 3 bins
- Sacramento: 4 pallet packages, 8 racking, 3 bins

### 5. Time Periods

**Default**: 12 months (252 business days) for testing
**Full model**: 120 months (2,520 business days) - edit line 57: `USE_FULL_HORIZON = True`

**Monthly aggregation** (not daily yet):
- `monthly_inventory[month, sku, facility]`
- `monthly_deliveries[month, sku, facility]`
- `monthly_shipments[month, sku, facility]`

### 6. Expansion Optimization

**Decision variables**:
- `expansion[Sacramento]`, `expansion[Austin]` - square footage
- `add_shelves[facility, storage_type]` - additional shelves needed
- `sac_tier1`, `sac_tier2` - Sacramento tiered pricing ($2/sqft, then $4/sqft)

**Constraints**:
- Sacramento ≤ 250,000 sqft
- Austin ≤ 200,000 sqft
- Columbus cannot expand

### 7. Capacity Constraints

✅ **Volume capacity** (cubic feet)
✅ **Weight capacity** (pounds)
✅ **Package capacity** (max packages per shelf) - SET PACKING
✅ **Truck delivery capacity** (1/supplier/day) - WITH SLACK

## Output Files Generated

When you run `python full_daily_warehouse_model.py`:

1. `full_daily_expansion_summary.csv` - Total expansion and costs
2. `full_daily_additional_shelves.csv` - Shelves to add by facility/type
3. `full_daily_repacking_decisions.csv` - Which SKUs to repack where
4. `full_daily_truck_violations.csv` - Months/suppliers exceeding 1 truck/day
5. `full_daily_monthly_inventory.csv` - Inventory levels over time
6. Plus many other variable exports

## How to Run

```powershell
# Set license
$env:GAMSLICE_STRING="d81a3160-ec06-4fb4-9543-bfff870b9ecb"

# Run model
python full_daily_warehouse_model.py
```

## Interpreting Truck Slack Results

If `truck_slack > 0` for a (month, supplier, facility):
- **Meaning**: More than 21 deliveries needed that month
- **Example**: truck_slack = 5 → need 26 deliveries (5 extra days or double-ups)
- **Cost impact**: 5 × $10,000 = $50,000 penalty
- **Action**: Consider negotiating more frequent smaller deliveries or larger trucks

If `truck_slack = 0` for all:
- ✅ All deliveries fit within 1 truck/supplier/day limit
- No additional trucking costs needed

## Model Size

- **Variables**: ~5,000 for 12 months, ~50,000 for 120 months
- **Solve time**: 1-10 minutes depending on configuration
- **License**: Academic license allows unlimited size
