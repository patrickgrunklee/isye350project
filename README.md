# InkCredible Supplies - Warehouse Expansion Optimization Model
## Option 2: Expand Sacramento and/or Austin Facilities

### Project Overview

This optimization model combines two key industrial engineering approaches:
1. **Multiperiod Modeling**: Planning procurement and inventory over 120 months (2026-2035)
2. **Set Packing**: Optimal allocation of SKUs to storage shelves considering weight and volume constraints

---

## Key Findings from Analysis

### Current Capacity Status

| Facility   | Current Size | Volume Utilization | Weight Utilization | Status |
|------------|--------------|-------------------|-------------------|--------|
| Columbus   | 1M sq ft     | 96.2%             | 47.8%             | ✓ Sufficient |
| Sacramento | 250K sq ft   | 815.7%            | 1333.1%           | ⚠️ Critical - Needs Expansion |
| Austin     | 500K sq ft   | 403.9%            | 978.3%            | ⚠️ Critical - Needs Expansion |

### Critical Bottleneck Identified

**PALLET STORAGE WEIGHT CAPACITY** is the primary constraint:
- Volume capacity is SUFFICIENT across all facilities
- **Weight capacity for pallets is INSUFFICIENT**

#### Specific Shortfalls (Weight Capacity):

| Facility   | Storage Type | Weight Shortfall | Additional Shelves Needed | Additional Space Needed |
|------------|--------------|------------------|---------------------------|------------------------|
| Columbus   | Pallet       | 974,673 lbs      | 1,625 shelves             | 145,327 sq ft          |
| Sacramento | Pallet       | 3,018,984 lbs    | 5,032 shelves             | 231,884 sq ft          |
| Austin     | Pallet       | 6,652,796 lbs    | 11,088 shelves            | 987,348 sq ft          |

**Problem**: Columbus cannot be expanded (per project constraints), but needs 145K sq ft more capacity!

**Solution**: Redistribute pallet storage from Columbus to Sacramento and Austin

---

## Model Files

### 1. `diagnostic_analysis.py`
**Purpose**: Analyze current vs. required capacity
**Output**: Detailed breakdown by facility and storage type

**Run**:
```bash
python diagnostic_analysis.py
```

### 2. `feasibility_check_model.py`
**Purpose**: Identify exact shortfalls using slack variables
**Output**: Specific capacity gaps by facility and storage type

**Features**:
- Slack variables identify WHERE shortfalls occur
- Calculates additional shelves/square footage needed
- Saves results to CSV for further analysis

**Run**:
```bash
python feasibility_check_model.py
```

### 3. `final_warehouse_model.py` (Main Model)
**Purpose**: Optimize expansion decisions to minimize cost
**Objective**: Minimize total expansion cost while meeting all demand

**Decision Variables**:
- Expansion square footage at Sacramento and Austin
- Additional shelves by storage type
- Storage allocation across facilities

**Constraints**:
- Sacramento expansion: 0-250K sq ft (tiered pricing: $2/sqft for first 100K, $4/sqft above)
- Austin expansion: 0-200K sq ft ($1.5/sqft)
- Volume capacity per storage type
- Weight capacity per storage type
- Total demand must be met across all facilities

**Run**:
```bash
python final_warehouse_model.py
```

---

## Data Files

All data located in `Model Data/` folder:

| File | Description |
|------|-------------|
| `Demand Details.csv` | Monthly demand for 18 SKUs over 120 months |
| `SKU Details.csv` | Dimensions, weight, storage method for each SKU |
| `Lead TIme.csv` | Lead times and days-on-hand by SKU and facility |
| `Shelving Count.csv` | Current shelving capacity by facility and type |
| `Shelving Dimensions.csv` | Physical dimensions and capacity of each shelf type |
| `Floorplan Layout.csv` | Square footage allocation by department |
| `Problem Criteria.csv` | Operational hours and requirements |
| `General Assuptions.csv` | Forklift widths, pallet dimensions, etc. |

---

## Key Assumptions

1. **Working Days**: 21 business days per month (50 weeks/year)
2. **Days on Hand**: Items must be stored for specified days before shipping
3. **Storage Types**:
   - **Bins**: Small items (writing utensils, art supplies, electronics accessories)
   - **Racking**: Medium items (textbooks)
   - **Pallet**: Large/heavy items (desks, chairs)
   - **Hazmat**: Hazardous materials (glue, adhesives)
4. **Demand Fulfillment**: Any facility can fulfill demand from any region
5. **Peak Demand**: Model uses maximum monthly demand over 10-year period

---

## Optimization Approach

### Problem Type
**Mixed-Integer Linear Programming (MILP)** / **Linear Programming (LP)**

### Sets
- **S**: SKUs (18 items)
- **F**: Facilities (Columbus, Sacramento, Austin)
- **F_exp**: Expandable facilities (Sacramento, Austin)
- **ST**: Storage types (Bins, Racking, Pallet, Hazmat)
- **T**: Time periods (120 months) - used in full multiperiod model

### Decision Variables
- `expansion[f]`: Square feet of expansion at facility f
- `add_shelves[f, st]`: Additional shelves of type st at facility f
- `storage_alloc[s, f]`: Units of SKU s stored at facility f
- `sac_tier1`, `sac_tier2`: Sacramento expansion in each pricing tier

### Objective Function
```
Minimize: Total_Cost = sac_tier1 * 2.0 + sac_tier2 * 4.0 + expansion[Austin] * 1.5
```

### Key Constraints

1. **Demand Fulfillment**:
   ```
   Sum over facilities (storage_alloc[s, f]) >= total_required_storage[s]  for all SKUs s
   ```

2. **Volume Capacity**:
   ```
   Sum over SKUs (storage_alloc[s, f] * sku_volume[s]) <=
   (current_shelves[f, st] + add_shelves[f, st]) * shelf_volume[f, st]
   ```

3. **Weight Capacity**:
   ```
   Sum over SKUs (storage_alloc[s, f] * sku_weight[s]) <=
   (current_shelves[f, st] + add_shelves[f, st]) * shelf_weight[f, st]
   ```

4. **Expansion Limits**:
   - Sacramento: ≤ 250,000 sq ft
   - Austin: ≤ 200,000 sq ft

5. **Expansion to Shelves Conversion**:
   ```
   expansion[f] = Sum over storage types (add_shelves[f, st] * avg_sqft_per_shelf[f, st])
   ```

---

## Results Directory

All optimization results saved to `results/` folder:

| File | Description |
|------|-------------|
| `expansion_summary.csv` | Total expansion and costs by facility |
| `additional_shelves.csv` | Shelves to add by facility and storage type |
| `storage_allocation_full.csv` | Complete allocation of SKUs to facilities |
| `volume_shortfalls.csv` | Volume capacity gaps (if any) |
| `weight_shortfalls.csv` | Weight capacity gaps (if any) |

---

## Next Steps & Recommendations

### Immediate Actions
1. **Review feasibility_check_model.py output** to understand capacity gaps
2. **Adjust expansion limits** if current limits (250K/200K sq ft) are insufficient
3. **Consider Columbus reallocation**: Move heavy pallet items from Columbus to expanded Sacramento/Austin

### Model Enhancements (Future Work)
1. **Add holding costs**: Include inventory carrying costs per SKU
2. **Add employee costs**: Factor in labor requirements for expanded facilities
3. **Add transportation costs**: Include inter-facility transfer costs
4. **Multiperiod inventory tracking**: Full 120-month inventory simulation
5. **Lead time optimization**: Determine optimal order timing
6. **Seasonal demand patterns**: Account for back-to-school peaks

### Strategic Considerations
- **Pallet storage is the constraint**: Focus expansion on pallet shelving
- **Weight vs. Volume**: Shelves have sufficient volume but insufficient weight capacity
- **Columbus bottleneck**: Consider redistributing heavy items to other facilities
- **Scalability**: Current expansion limits may be insufficient for 10-year demand growth

---

## Technical Requirements

### Python Packages
```
pandas
numpy
gamspy
pathlib
```

### Installation
```bash
pip install pandas numpy gamspy
```

### GAMS License
Requires valid GAMS license for GAMSPy. Academic licenses available at: https://www.gams.com/

---

## Contact & Support

For questions about the model:
1. Review diagnostic outputs first
2. Check feasibility_check_model.py results
3. Adjust parameters in model files as needed

---

## File Structure

```
Model/
├── README.md (this file)
├── diagnostic_analysis.py
├── feasibility_check_model.py
├── final_warehouse_model.py
├── optimization_model.py (initial version)
├── warehouse_optimization.py (simplified version)
├── Model Data/
│   ├── Demand Details.csv
│   ├── SKU Details.csv
│   ├── Lead TIme.csv
│   ├── Shelving Count.csv
│   ├── Shelving Dimensions.csv
│   ├── Floorplan Layout.csv
│   ├── Problem Criteria.csv
│   └── General Assuptions.csv
└── results/
    ├── expansion_summary.csv
    ├── additional_shelves.csv
    ├── storage_allocation_full.csv
    ├── volume_shortfalls.csv
    └── weight_shortfalls.csv
```

---

## Model Validation Checklist

- [x] Data loaded correctly (18 SKUs, 3 facilities, 120 months)
- [x] Peak demand calculated accurately
- [x] Storage requirements computed (demand * days_on_hand / working_days)
- [x] Current capacity assessed (volume and weight)
- [x] Feasibility check completed (slack variables identify gaps)
- [ ] Optimal solution found (minimize expansion cost)
- [ ] Results validated against business constraints
- [ ] Sensitivity analysis performed

---

**Last Updated**: 2025-01-XX
**Model Version**: 1.0
**Course**: ISyE 350 - Industrial and Systems Engineering Junior Design Laboratory
**Project**: InkCredible Supplies Warehouse Expansion - Option 2
