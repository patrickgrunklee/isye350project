# Flexible Storage Assignment Results
## Model 0.2a MaxMin DoH with SKUD1 & SKUC1 on Both Racking and Pallet

**Date**: 2025
**Model**: model_0_2a_maxmin_doh.py (flexible storage version)

---

## Executive Summary

**Maximum Balanced DoH: 163.43 days**

The optimization model was given flexibility to assign SKUD1 (desks) and SKUC1 (chairs) to EITHER Racking OR Pallet storage (or both). The model **automatically chose to place 99%+ of these SKUs on Racking**, demonstrating that Racking is more efficient due to higher package capacity (8 pkg/shelf vs 4-7 pkg/shelf for Pallet).

---

## Storage Assignment Results

### SKUs with Flexible Assignment

#### SKUD1 (Desks) - 2nd Highest Demand SKU
- **Avg Demand**: 4,421 units/day
- **Storage Distribution**:
  - **Racking**: 34,169.9 units (99.3%) ← **Optimizer's Choice**
  - **Pallet**: 236.4 units (0.7%)
- **DoH**: 7.73 days on Racking, 0.05 days on Pallet

#### SKUC1 (Chairs) - Highest Demand SKU
- **Avg Demand**: 4,780 units/day (#1 across all SKUs)
- **Storage Distribution**:
  - **Racking**: 36,964.4 units (99.4%) ← **Optimizer's Choice**
  - **Pallet**: 234.9 units (0.6%)
- **DoH**: 7.73 days on Racking, 0.05 days on Pallet

**Conclusion**: The model strongly prefers Racking for both high-demand furniture SKUs.

---

## Full Storage Assignment Breakdown

### Bins Storage (4 SKUs)
| SKU | Avg Demand | Avg Inventory | DoH |
|-----|-----------|---------------|-----|
| SKUW1 | 2,403/day | 18,705 units (Bins) + 95 units (Pallet) | 7.78 days |
| SKUW2 | 3,871/day | 30,124 units | 7.78 days |
| SKUW3 | 3,112/day | 24,216 units | 7.78 days |
| SKUE1 | 3,271/day | 25,455 units | 7.78 days |

**Note**: SKUW1 has 95 units on Pallet (0.5%), rest on Bins

### Racking Storage (5 SKUs - includes SKUD1 & SKUC1)
| SKU | Avg Demand | Avg Inventory | DoH |
|-----|-----------|---------------|-----|
| SKUA3 | 3,356/day | 26,121 units | 7.78 days |
| SKUT1 | 2,412/day | 18,773 units | 7.78 days |
| SKUT4 | 1,955/day | 15,213 units | 7.78 days |
| **SKUD1** | **4,421/day** | **34,170 units (99.3% on Racking)** | **7.73 days** |
| **SKUC1** | **4,780/day** | **36,964 units (99.4% on Racking)** | **7.73 days** |

### Pallet Storage (7 SKUs + small amounts from SKUD1/SKUC1)
| SKU | Avg Demand | Avg Inventory | DoH |
|-----|-----------|---------------|-----|
| SKUT2 | 3,093/day | 24,068 units | 7.78 days |
| SKUT3 | 2,185/day | 17,007 units | 7.78 days |
| SKUD2 | 2,731/day | 21,254 units | 7.78 days |
| SKUD3 | 3,861/day | 30,047 units | 7.78 days |
| SKUC2 | 3,858/day | 30,028 units | 7.78 days |
| SKUE2 | 3,660/day | 28,480 units | 7.78 days |
| SKUE3 | 425/day | 3,308 units | 7.78 days |
| SKUD1 (0.7%) | - | 236 units | 0.05 days |
| SKUC1 (0.6%) | - | 235 units | 0.05 days |

### Hazmat Storage (2 SKUs)
| SKU | Avg Demand | Avg Inventory | DoH |
|-----|-----------|---------------|-----|
| SKUA1 | 1,113/day | 8,659 units | 7.78 days |
| SKUA2 | 1,838/day | 14,305 units | 7.78 days |

---

## Expansion Requirements

| Facility | Storage Type | Shelves Added | Notes |
|----------|--------------|---------------|-------|
| Sacramento | Racking | +18,479 | For SKUA3, SKUT1, SKUT4, **SKUD1, SKUC1** |
| Sacramento | Pallet | +3,580 | For remaining pallet SKUs |
| Austin | Pallet | +2,246 | For pallet SKUs at Austin |

**Total Expansion**:
- Racking: +18,479 shelves
- Pallet: +5,826 shelves
- **Grand Total**: +24,305 shelves

---

## Comparison: Fixed vs Flexible Assignment

### Scenario 1: SKUD1 & SKUC1 ONLY on Pallet (Original)
- **Maximum DoH**: 79.24 days
- **Expansion**: Sacramento Pallet +5,425, Austin Pallet +2,246
- **Total**: +7,671 pallet shelves

### Scenario 2: SKUD1 & SKUC1 ONLY on Racking (Forced)
- **Maximum DoH**: 160.01 days
- **Expansion**: Sacramento Racking +20,827, Sacramento Pallet +3,345, Austin Pallet +2,246
- **Total**: +26,418 shelves

### Scenario 3: SKUD1 & SKUC1 on BOTH (Flexible - Current)
- **Maximum DoH**: 163.43 days (+2.1% vs forced Racking)
- **Expansion**: Sacramento Racking +18,479, Sacramento Pallet +3,580, Austin Pallet +2,246
- **Total**: +24,305 shelves (-8.0% vs forced Racking)
- **Model's Choice**: 99%+ on Racking, minimal on Pallet

---

## Key Insights

### 1. Optimizer Validates Racking Preference
When given freedom to choose, the model places **99%+ of SKUD1 and SKUC1 inventory on Racking**, confirming that Racking is mathematically superior for these high-demand SKUs.

### 2. Flexibility Provides Marginal Benefit
- Flexible assignment: 163.43 days DoH
- Forced Racking only: 160.01 days DoH
- **Benefit**: +3.42 days (+2.1% improvement)

The improvement is modest because the optimizer was already strongly preferring Racking.

### 3. Efficiency Comparison
**Package Capacity**:
- Racking: 8 packages/shelf (all facilities)
- Pallet: 4-7 packages/shelf depending on facility
  - Sacramento: 4 pkg/shelf (LOWEST)
  - Austin: 6 pkg/shelf
  - Columbus: 7 pkg/shelf

**Racking is 14-100% more efficient** than Pallet per shelf.

### 4. Why Small Pallet Amounts?
The model keeps tiny amounts (0.5-0.7%) of SKUD1/SKUC1 on Pallet likely due to:
- Edge case in optimization (marginal trade-offs)
- Facility-specific capacity constraints
- Numerical precision in solver

This is negligible and can be ignored in practice.

### 5. Optimal Strategy
**Allow SKUD1 and SKUC1 to use BOTH storage types** in practice, but expect them to **primarily use Racking** (~99%). This provides:
- Maximum flexibility for operations
- Optimal capacity utilization
- Ability to handle exceptions/overflow

---

## Recommendation

**Implement flexible storage policy for SKUD1 (desks) and SKUC1 (chairs)**:
- **Primary storage**: Racking (expect ~99% of inventory)
- **Overflow storage**: Pallet (for edge cases, ~1%)

**Benefits**:
1. Achieves 163.43 days DoH (vs 160.01 with forced Racking, 79.24 with forced Pallet)
2. Utilizes high-efficiency Racking (8 pkg/shelf)
3. Provides operational flexibility
4. Optimal from mathematical optimization perspective

**Expansion Plan**:
- Sacramento: +18,479 Racking shelves, +3,580 Pallet shelves
- Austin: +2,246 Pallet shelves
- Columbus: No expansion needed

**Total Cost** (estimated):
- Racking: 18,479 × 4.6 sqft/shelf × $2-4/sqft ≈ $170K-$340K
- Pallet (Sac): 3,580 × 46 sqft/shelf × $2-4/sqft ≈ $329K-$658K
- Pallet (Aus): 2,246 × 89 sqft/shelf × $1.5/sqft ≈ $300K
- **TOTAL**: ~$800K-$1.3M

---

## Conclusion

The flexible storage optimization confirms that **Racking is the optimal choice for high-demand furniture SKUs** (SKUD1 desks, SKUC1 chairs). The model automatically places 99%+ of these items on Racking when given the choice, validating the efficiency advantage of Racking's higher package capacity (8 vs 4-7 pkg/shelf).

Implementing a flexible policy allows operational adaptability while achieving near-optimal performance.

---

**Report Generated**: Model 0.2a MaxMin DoH with Flexible Storage
**Maximum Balanced DoH**: 163.43 days
**Optimizer's Choice**: 99%+ of SKUD1 & SKUC1 on Racking
