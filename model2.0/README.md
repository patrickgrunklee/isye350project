# Model 2.0 - InkCredible Supplies Warehouse Optimization

**Complete two-phase optimization model with original and smoothed demand scenarios**

## Overview

This folder contains the complete Model 2.0 implementation for the InkCredible Supplies warehouse expansion optimization project (ISyE 350).

**Model Type:** Two-phase Mixed-Integer Linear Programming (MILP)
- **Phase 1:** Set packing configuration generation (3D bin packing + pure-SKU continuous packing)
- **Phase 2:** Multiperiod inventory optimization (120 months, 2026-2035)

**Key Features:**
- Pure-SKU continuous packing (no discrete item limits for single-SKU shelves)
- All facilities forced to 99%+ utilization before expansion
- Columbus hard constraint (cannot expand)
- 4 different Days-on-Hand (DoH) safety stock policies
- Original vs Smoothed demand comparison

---

## Folder Structure

```
model2.0/
├── README.md                                      # This file
├── FINAL_ALL_FACILITIES_99PCT_RESULTS.txt        # Original demand results summary
├── SMOOTHED_DEMAND_COMPARISON.txt                # Smoothed vs original comparison
│
├── Model Data/                                    # Input data files
│   ├── Demand Details.csv                        # Original 120-month demand
│   ├── Demand Details_SMOOTHED.csv               # Smoothed demand (top 2 peaks removed)
│   ├── SKU Details.csv                           # SKU dimensions, weights, storage types
│   ├── Shelving Count.csv                        # Current shelf capacity
│   ├── Shelving Dimensions.csv                   # Shelf physical dimensions
│   ├── Lead TIme_14_3_business_days.csv         # 10/3 DoH policy
│   ├── Lead TIme_5_2_business_days.csv          # 5/2 DoH policy
│   ├── Lead TIme_3_1_business_days.csv          # 3/1 DoH policy
│   └── Lead TIme_0_0_business_days.csv          # 0/0 DoH policy (no safety stock)
│
├── results/
│   ├── Phase1_SetPacking/
│   │   ├── packing_configurations_3d.csv         # 56 discrete 3D bin packing configs
│   │   └── packing_configurations_pure_sku.csv   # 209 total configs (56 + 153 pure-SKU)
│   ├── Phase2_Multiperiod/                       # Original demand results (generated at runtime)
│   └── Phase2_SMOOTHED/                          # Smoothed demand results (generated at runtime)
│
├── phase1_set_packing.py                         # Phase 1: Generate 3D bin packing configs
│
├── phase2_pure_sku_shelves_10_3_doh_ALL99pct.py # Original demand - 10/3 DoH
├── phase2_pure_sku_shelves_5_2_doh_ALL99pct.py  # Original demand - 5/2 DoH
├── phase2_pure_sku_shelves_3_1_doh_ALL99pct.py  # Original demand - 3/1 DoH (RECOMMENDED)
├── phase2_pure_sku_shelves_0_0_doh_ALL99pct.py  # Original demand - 0/0 DoH
│
├── phase2_SMOOTHED_10_3_doh.py                   # Smoothed demand - 10/3 DoH
├── phase2_SMOOTHED_5_2_doh.py                    # Smoothed demand - 5/2 DoH
├── phase2_SMOOTHED_3_1_doh.py                    # Smoothed demand - 3/1 DoH
├── phase2_SMOOTHED_0_0_doh.py                    # Smoothed demand - 0/0 DoH
│
├── create_smoothed_demand.py                     # Utility: Create smoothed demand dataset
├── analyze_capacity_drivers.py                   # Analysis: Which SKUs drive requirements
├── analyze_pallet_constraints.py                 # Analysis: Pallet-specific constraints
└── compare_capacities.py                         # Analysis: Weight capacity comparison
```

---

## Quick Start

### Prerequisites

```bash
pip install pandas numpy gamspy openpyxl
```

### Install GAMSPy License

```bash
python install_licenses.py
# Or set environment variable:
set GAMSLICE_STRING=d81a3160-ec06-4fb4-9543-bfff870b9ecb
```

### Run Complete Analysis

**Step 1: Generate smoothed demand (if not already created)**
```bash
python create_smoothed_demand.py
```

**Step 2: Run original demand models**
```bash
python phase2_pure_sku_shelves_10_3_doh_ALL99pct.py
python phase2_pure_sku_shelves_5_2_doh_ALL99pct.py
python phase2_pure_sku_shelves_3_1_doh_ALL99pct.py  # RECOMMENDED
python phase2_pure_sku_shelves_0_0_doh_ALL99pct.py
```

**Step 3: Run smoothed demand models**
```bash
python phase2_SMOOTHED_10_3_doh.py
python phase2_SMOOTHED_5_2_doh.py
python phase2_SMOOTHED_3_1_doh.py
python phase2_SMOOTHED_0_0_doh.py
```

**Step 4: Review results**
- Original results: `FINAL_ALL_FACILITIES_99PCT_RESULTS.txt`
- Smoothed comparison: `SMOOTHED_DEMAND_COMPARISON.txt`

---

## Model Results Summary

### Original Demand Results

| Scenario | Total Expansion | Sacramento | Austin |
|----------|----------------|------------|--------|
| 10/3 days | 7,210 shelves | 1,514 | 5,696 |
| 5/2 days | 6,697 shelves | 392 | 6,305 |
| **3/1 days** | **6,511 shelves** | **0** | **6,511** |
| 0/0 days | 6,507 shelves | 0 | 6,507 |

**Recommended:** 3/1 DoH policy (International: 3 days, Domestic: 1 day)

### Smoothed Demand Results

| Scenario | Total Expansion | Sacramento | Austin | Reduction |
|----------|----------------|------------|--------|-----------|
| 10/3 days | 3,490 shelves | 725 | 2,765 | **51.6%** |
| 5/2 days | 3,151 shelves | 0 | 3,151 | **53.0%** |
| 3/1 days | 3,131 shelves | 0 | 3,131 | **51.9%** |
| 0/0 days | 3,127 shelves | 0 | 3,127 | **51.9%** |

**Key Insight:** Demand volatility (peak months) drives ~52% of capacity requirements

---

## Key Model Features

### Phase 1: Set Packing
- **3D bin packing:** Greedy first-fit decreasing algorithm
- **6 orientations tested** per package
- **Pure-SKU continuous packing:** Shelves dedicated to single SKU use volume-only approach
- **Output:** 209 packing configurations (56 discrete + 153 pure-SKU)

### Phase 2: Multiperiod Optimization
- **Time horizon:** 120 months (2026-2035)
- **Facilities:** Columbus (cannot expand), Sacramento, Austin
- **Storage types:** Bins, Racking, Pallet, Hazmat
- **Decision variables:**
  - Expansion square footage
  - Additional shelves by type
  - Monthly inventory levels
  - Monthly shipments
- **Key constraints:**
  - Demand fulfillment each month
  - Days-on-hand safety stock
  - Volume/weight capacity per shelf
  - All facilities at 99%+ utilization if any expansion needed
  - Columbus hard constraint (no expansion allowed)

### Special Features
- **Furniture volume-only packing:** SKUD3 (22/shelf), SKUC1 (20/shelf)
- **Weight per item (not per shelf):** Columbus Pallet: 7 items × 600 lbs = 4,200 lbs total
- **Traditional safety stock:** inventory ≥ (monthly_demand / 21 days) × DoH_days

---

## Key Insights

### 1. Peak Demand Drives Requirements
- July 2035 and July 2034 are peak months for almost all SKUs
- These 2 months alone drive ~52% of capacity requirements
- Consider temporary 3PL storage for peak months

### 2. Safety Stock Has Minimal Impact
- 0/0 DoH: 6,507 shelves
- 3/1 DoH: 6,511 shelves
- Difference: Only 4 shelves (0.06%)
- Peak demand levels (not safety stock) drive requirements

### 3. Top 5 Bottleneck SKUs
1. **SKUC1** (Chairs): 33.5% of requirement
2. **SKUD3** (Desks): 22.2%
3. **SKUD2** (Desks): 18.0%
4. **SKUD1** (Desks): 9.7%
5. **SKUE2** (Electronics): 6.4%

Furniture items are volume-limited despite optimal packing.

### 4. Strategic Options
- **Option A:** Build for smoothed demand (3,131 shelves) + temporary overflow
- **Option B:** Demand management (smooth July peaks)
- **Option C:** Hybrid approach (build for 80th percentile + temporary overflow)

---

## Technical Notes

### GAMSPy Model Structure

```python
# Sets
s = SKUs (18)
f = Facilities (3: Columbus, Sacramento, Austin)
st = Storage types (4: Bins, Racking, Pallet, Hazmat)
t = Time periods (120 months)
c = Configurations (209 packing configs)

# Decision Variables
shelves_per_config[c]          # Number of shelves using each configuration
inventory[t, s, f]             # Inventory level (time-indexed)
shipments[t, s, f]             # Shipments (time-indexed)

# Slack Variables (for capacity violations)
slack_shelf_sac[st]            # Sacramento expansion needed
slack_shelf_austin[st]         # Austin expansion needed
# NO slack for Columbus (hard constraint)

# Key Constraints
- Demand fulfillment: Sum_f(shipments[t,s,f]) >= demand[t,s]
- Days-on-hand: inventory[t,s,f] >= (demand[t,s]/21) × DoH[s,f]
- Capacity: inventory[t,s,f] <= Sum_c(shelves[c] × capacity[c,s,f])
- 99% utilization: If any expansion, all facilities at 99%+ pallet utilization
```

### Time Complexity
- **Variables:** ~388,800 (120 months × 18 SKUs × 3 facilities × 60 decision types)
- **Constraints:** ~100,000+
- **Solve time:** 30-60 seconds per scenario (LP relaxation)

---

## File Descriptions

### Python Scripts

| File | Purpose | Output |
|------|---------|--------|
| `phase1_set_packing.py` | Generate 3D bin packing configs | `packing_configurations_3d.csv` |
| `phase2_pure_sku_shelves_*_ALL99pct.py` | Original demand optimization | Console output + slack variables |
| `phase2_SMOOTHED_*_doh.py` | Smoothed demand optimization | Console output + slack variables |
| `create_smoothed_demand.py` | Create smoothed demand dataset | `Demand Details_SMOOTHED.csv` |
| `analyze_capacity_drivers.py` | SKU-level capacity analysis | Console output |
| `analyze_pallet_constraints.py` | Pallet constraint analysis | Console output |
| `compare_capacities.py` | Weight capacity verification | Console output |

### Data Files

| File | Description | Rows | Key Columns |
|------|-------------|------|-------------|
| `Demand Details.csv` | Original monthly demand | 120 | Month, Year, 18 SKU columns |
| `Demand Details_SMOOTHED.csv` | Smoothed demand | 120 | Same as above (top 2 peaks replaced) |
| `SKU Details.csv` | SKU specifications | 18 | Dimensions, weight, storage type, consolidation |
| `Shelving Count.csv` | Current capacity | 12 | Facility, storage type, # shelves, weight limits |
| `Shelving Dimensions.csv` | Shelf specs | 12 | Facility, storage type, dimensions, package capacity |
| `Lead TIme_*.csv` | DoH policies | 18 | SKU, DoH by facility |

---

## Known Issues

### Columbus Bins Exception
- Columbus Bins: 60 lbs per item (not 66.14 lbs)
- Manually corrected in `Shelving Count.csv`

### Weight Capacity Interpretation
- Weight limits apply **per item**, not per shelf
- Total shelf capacity = (items/shelf) × (weight/item)
- Example: Columbus Pallet = 7 items × 600 lbs = 4,200 lbs total

### Pure-SKU Breakthrough
- Initially used discrete 7-item structure for all shelves
- Now: Single-SKU shelves use continuous volume-based packing
- Result: Massive capacity improvement (Columbus went from needing 22,580 to 0 shelves)

---

## Contact & Credits

**Course:** ISyE 350 - Introduction to Operations Research
**Project:** InkCredible Supplies Warehouse Expansion (Option 2)
**Optimization Tool:** GAMSPy (Python interface to GAMS)
**Solver:** LP relaxation (CPLEX/Gurobi recommended for large-scale)

**Academic License:**
- License 1: `d81a3160-ec06-4fb4-9543-bfff870b9ecb`
- License 2: `8c39a188-c68a-4295-9c9d-b65ac74bce78`

---

## Version History

**Model 2.0** (Current)
- Pure-SKU continuous packing implemented
- All facilities 99%+ utilization constraint
- Columbus hard constraint (cannot expand)
- Smoothed demand analysis added
- 4 DoH scenarios tested

**Model 1.x** (Previous versions - not included)
- Peak demand only (no multiperiod)
- Discrete packing for all shelves
- Per-shelf weight interpretation (incorrect)

---

## Next Steps

1. **Cost-Benefit Analysis:** Compare permanent CapEx vs temporary 3PL costs
2. **Demand Management:** Explore strategies to smooth July peak months
3. **Phased Expansion:** Build for smoothed demand first, evaluate peaks later
4. **Daily Scheduling:** Extend to daily time periods for supplier delivery scheduling
5. **Repacking Optimization:** Add binary repacking decisions (store as inbound vs repack to sell packs)

---

**Last Updated:** 2025-10-31
