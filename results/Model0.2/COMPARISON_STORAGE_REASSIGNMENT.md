# Impact of Moving SKUD1 & SKUC1 from Pallet to Racking
## Model 0.2a MaxMin DoH Analysis

---

## BEFORE: Original Configuration

### Storage Assignments:
- **Pallet**: 9 SKUs (SKUT2, SKUT3, SKUD1, SKUD2, SKUD3, SKUC1, SKUC2, SKUE2, SKUE3)
- **Racking**: 3 SKUs (SKUA3, SKUT1, SKUT4)
- **Bins**: 4 SKUs (SKUW1-3, SKUE1)
- **Hazmat**: 2 SKUs (SKUA1-2)

### Results:
- **Maximum Balanced DoH**: 79.24 days
- **Expansion Required**:
  - Sacramento Pallet: +5,425 shelves
  - Austin Pallet: +2,246 shelves
  - **TOTAL PALLET**: +7,671 shelves
  - Sacramento Racking: 0 shelves (excess capacity)
  - **TOTAL RACKING**: 0 shelves

### Bottleneck:
Pallet storage constraining DoH to only 79 days due to:
- 9 SKUs competing for limited pallet capacity
- Low package capacity per shelf (4-7 packages)
- High-demand SKUs concentrated in Pallet

---

## AFTER: SKUD1 & SKUC1 Moved to Racking

### Storage Assignments:
- **Pallet**: 7 SKUs (SKUT2, SKUT3, SKUD2, SKUD3, SKUC2, SKUE2, SKUE3) **[-2 SKUs]**
- **Racking**: 5 SKUs (SKUA3, SKUT1, SKUT4, SKUD1, SKUC1) **[+2 SKUs]**
- **Bins**: 4 SKUs (unchanged)
- **Hazmat**: 2 SKUs (unchanged)

### Results:
- **Maximum Balanced DoH**: 160.01 days **[+102% IMPROVEMENT!]**
- **Expansion Required**:
  - Sacramento Racking: +20,827 shelves **[NEW]**
  - Sacramento Pallet: +3,345 shelves **[-38% reduction]**
  - Austin Pallet: +2,246 shelves (unchanged)
  - **TOTAL PALLET**: +5,591 shelves **[-27% reduction]**
  - **TOTAL RACKING**: +20,827 shelves

### New Bottleneck:
Racking storage now the constraint, but achieves DOUBLE the DoH!

---

## Comparison Summary

| Metric | BEFORE | AFTER | Change |
|--------|--------|-------|--------|
| **Maximum Balanced DoH** | 79.24 days | 160.01 days | **+102%** 🎯 |
| **Pallet SKUs** | 9 | 7 | -2 |
| **Racking SKUs** | 3 | 5 | +2 |
| **Pallet Expansion** | +7,671 shelves | +5,591 shelves | **-27%** ✅ |
| **Racking Expansion** | 0 shelves | +20,827 shelves | +20,827 |
| **Sacramento Pallet** | +5,425 shelves | +3,345 shelves | **-38%** ✅ |
| **Sacramento Racking** | 0 shelves | +20,827 shelves | +20,827 |

---

## Why This Works: The Two SKUs Moved

### SKUC1 (Chairs) - HIGHEST DEMAND SKU
- **Average Demand**: 100,377 units/month (4,780 units/day)
- **Rank**: #1 highest demand across ALL 18 SKUs
- **Old Storage**: Pallet (4-7 packages/shelf)
- **New Storage**: Racking (8 packages/shelf) **[+14-100% more capacity per shelf]**

### SKUD1 (Desks) - 2nd HIGHEST DEMAND SKU
- **Average Demand**: 92,841 units/month (4,421 units/day)
- **Rank**: #2 highest demand across ALL 18 SKUs
- **Old Storage**: Pallet (4-7 packages/shelf)
- **New Storage**: Racking (8 packages/shelf) **[+14-100% more capacity per shelf]**

### Combined Impact:
- **Total Demand**: 193,218 units/month (9,201 units/day)
- **Percentage**: 27% of original pallet demand
- **Effect**: Removed the two most demanding SKUs from pallet bottleneck

---

## Key Insights

### 1. DoH Achievement DOUBLED
- **79.24 → 160.01 days (+80.77 days improvement)**
- This is a massive improvement in safety stock capability
- Demonstrates that the right storage assignment can dramatically improve performance

### 2. Pallet Pressure Relieved
- Pallet expansion reduced by 2,080 shelves (-27%)
- Sacramento pallet expansion cut by 2,080 shelves (-38%)
- Only 7 SKUs now on pallet (from 9)

### 3. Racking Capacity Utilized
- Original model: Racking had EXCESS capacity (0 expansion needed)
- New model: Racking now utilized, requires expansion
- BUT: Racking has higher package capacity (8 vs 4-7), so more efficient

### 4. Shelf Capacity Efficiency Matters
- **Pallet**: 4-7 packages/shelf depending on facility
  - Columbus: 7 pkg/shelf
  - Sacramento: 4 pkg/shelf (LOWEST)
  - Austin: 6 pkg/shelf
- **Racking**: 8 packages/shelf (ALL facilities - HIGHEST)

Moving high-demand SKUs to higher-capacity storage type improves system performance

### 5. Trade-off Analysis
- **Before**: Needed +7,671 pallet shelves to get 79 days DoH
- **After**: Need +5,591 pallet + 20,827 racking shelves to get 160 days DoH
- **Total shelves**: 7,671 → 26,418 (+244% more shelves)
- **But**: Get 102% more DoH for 244% more shelves
- **DoH per shelf added**: 0.0103 days/shelf → 0.0061 days/shelf

### 6. Cost Implications
**Shelf Area Comparison** (from Shelving Dimensions.csv):
- Pallet shelf area: Much larger (10' x 4.25' x 24' at Columbus)
- Racking shelf area: Smaller (3' x 1.5' x 6' = 27 cu ft)

**Cost per sqft** (from expansion costs):
- Sacramento: $2-4/sqft (tiered)
- Austin: $1.5/sqft

**Average sqft per shelf** (calculated from Shelving Count.csv):
- Pallet: ~89 sqft/shelf (Columbus), ~46 sqft/shelf (Sacramento), ~89 sqft/shelf (Austin)
- Racking: ~10 sqft/shelf (Columbus), ~4.6 sqft/shelf (Sacramento), ~10 sqft/shelf (Austin)

**Expansion Cost Estimate**:
- **BEFORE**: 7,671 pallet shelves
  - Sacramento: 5,425 × 46 sqft = 249,550 sqft × $2-4 = ~$500K-$1M
  - Austin: 2,246 × 89 sqft = 199,894 sqft × $1.5 = ~$300K
  - **TOTAL**: ~$800K-$1.3M

- **AFTER**: 5,591 pallet + 20,827 racking shelves
  - Sacramento Pallet: 3,345 × 46 sqft = 153,870 sqft × $2-4 = ~$308K-$616K
  - Sacramento Racking: 20,827 × 4.6 sqft = 95,804 sqft × $2-4 = ~$192K-$383K
  - Austin Pallet: 2,246 × 89 sqft = 199,894 sqft × $1.5 = ~$300K
  - **TOTAL**: ~$800K-$1.3M

**Cost is similar, but DoH doubles!**

---

## Recommendation

**STRONGLY RECOMMEND** moving SKUD1 and SKUC1 to Racking storage.

**Benefits**:
1. **102% improvement in Days-on-Hand** (79 → 160 days)
2. **27% reduction in Pallet expansion** needed
3. **Similar total cost** but dramatically better performance
4. **Utilizes Racking's higher package capacity** (8 vs 4-7 pkg/shelf)
5. **More balanced capacity utilization** across storage types

**Considerations**:
- Need to verify that SKUD1 (desks) and SKUC1 (chairs) are physically compatible with Racking dimensions
- Current racking: 3' × 1.5' × 6' (27 cu ft)
- SKUD1 sell pack: 36" × 24" × 5" = 3' × 2' × 0.42' = 2.5 cu ft ✅ (fits)
- SKUC1 sell pack: 48" × 40" × 20" = 4' × 3.33' × 1.67' = 22.2 cu ft ❌ (TIGHT FIT)

**SKUC1 may be too large for racking shelves** - need to verify physical feasibility.

**Alternative**: Try moving only SKUD1 to Racking (keep SKUC1 on Pallet) to see intermediate results.

---

## Conclusion

Moving high-demand SKUs from low-capacity Pallet storage (4-7 pkg/shelf) to high-capacity Racking storage (8 pkg/shelf) **doubles the achievable Days-on-Hand** while reducing Pallet expansion requirements.

This demonstrates the importance of optimal storage type assignment based on:
1. Demand volume
2. Shelf package capacity
3. Physical product dimensions

The model clearly shows **Racking is more efficient** for high-volume items when physically feasible.

---

**Report Generated**: Model 0.2a MaxMin DoH Comparison
**Date**: 2025
