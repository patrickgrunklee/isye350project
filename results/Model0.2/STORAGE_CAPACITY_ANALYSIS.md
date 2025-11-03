# Storage Capacity Analysis by Type
## InkCredible Supplies - Model 0.2a MaxMin DoH Results

**Date**: 2025
**Model**: model_0_2a_maxmin_doh.py
**Objective**: Maximize minimum Days-on-Hand (DoH) across all 18 SKUs

---

## Executive Summary

**Maximum Achievable DoH: 79.24 days** (balanced across all SKUs)

**Capacity Bottleneck: PALLET STORAGE**
- Pallet storage requires significant expansion (+7,671 shelves total)
- Bins, Racking, and Hazmat have **EXCESS CAPACITY** - no expansion needed

---

## Findings by Storage Type

### 1. BINS STORAGE ✅ EXCESS CAPACITY

**SKUs Using Bins**: 4 SKUs (all International)
- SKUW1, SKUW2, SKUW3 (writing utensils)
- SKUE1 (electronics)

**Current Capacity**:
- Columbus: 647,680 shelves
- Sacramento: 14,400 shelves
- Austin: 19,688 shelves
- **TOTAL**: 681,768 shelves

**Shelf Dimensions**:
- Columbus: Auto (12"×12"×12") = 100 packages/shelf
- Sacramento: 1.25'×1.25'×4' = 3 packages/shelf
- Austin: 1.25'×1.25'×4' = 3 packages/shelf

**Demand** (Average Monthly):
- SKUW1: 50,472 units/month
- SKUW2: 81,285 units/month
- SKUW3: 65,344 units/month
- SKUE1: 68,687 units/month
- **TOTAL**: 265,788 units/month (~12,657 units/day)

**Capacity Utilization**: ~18% at peak demand
**Expansion Needed (MaxMin Model)**: **ZERO** ✅

**Conclusion**: Bins have massive excess capacity. Columbus Bins alone can handle the entire demand for bin SKUs.

---

### 2. RACKING STORAGE ✅ EXCESS CAPACITY

**SKUs Using Racking**: 3 SKUs (all Domestic)
- SKUA3 (art supplies/adhesives)
- SKUT1, SKUT4 (textbooks)

**Current Capacity**:
- Columbus: 15,600 shelves
- Sacramento: 13,078 shelves
- Austin: 11,424 shelves
- **TOTAL**: 40,102 shelves

**Shelf Dimensions**: 3'×1.5'×6' = 27 cu ft
- **Package Capacity**: 8 packages/shelf (ALL facilities)
- **Weight Limit**: 100 lbs/shelf
- **Total Package Capacity**: 40,102 shelves × 8 = **320,816 packages**

**Demand** (Average Monthly):
- SKUA3: 70,485 units/month (~3,356 units/day)
- SKUT1: 50,656 units/month (~2,412 units/day)
- SKUT4: 41,050 units/month (~1,955 units/day)
- **TOTAL**: 162,191 units/month (~7,723 units/day)

**Peak Monthly Demand**: 344,301 units

**Inbound Pack Conversion** (for capacity calculation):
- SKUA3: Inbound = 100 units (consolidation 100:100) → 1 pack per 100 units
- SKUT1: Inbound = 3 units → 1 pack per 3 units
- SKUT4: Inbound = 3 units → 1 pack per 3 units

**Rough Capacity Utilization**:
- At 79.24 days DoH: Need ~611,000 units inventory
- Assuming worst case (no consolidation): ~203,000 packages
- Capacity: 320,816 packages
- **Utilization**: ~63% ✅

**Expansion Needed (MaxMin Model)**: **ZERO** ✅

**Conclusion**: Racking has sufficient capacity even at 79 days DoH for all racking SKUs.

---

### 3. PALLET STORAGE ❌ BOTTLENECK

**SKUs Using Pallet**: 9 SKUs (50% of all SKUs!)
- SKUT2, SKUT3 (textbooks - heavy pallets)
- SKUD1, SKUD2, SKUD3 (desks - furniture)
- SKUC1, SKUC2 (chairs - furniture)
- SKUE2, SKUE3 (electronics - large items)

**Current Capacity**:
- Columbus: 3,080 shelves
- Sacramento: 1,100 shelves
- Austin: 1,484 shelves
- **TOTAL**: 5,664 shelves

**Shelf Dimensions**:
- Columbus: 10'×4.25'×24' = 1,020 cu ft, **7 packages/shelf**
- Sacramento: 5'×4.25'×24' = 510 cu ft, **4 packages/shelf**
- Austin: 10'×4.25'×18' = 765 cu ft, **6 packages/shelf**

**Total Current Package Capacity**:
- Columbus: 3,080 × 7 = 21,560 packages
- Sacramento: 1,100 × 4 = 4,400 packages
- Austin: 1,484 × 6 = 8,904 packages
- **TOTAL**: 34,864 packages

**Demand** (Average Monthly):
- SKUC1 (chairs): 100,377 units/month - **HIGHEST DEMAND SKU**
- SKUD1 (desks): 92,841 units/month
- SKUD3 (desks): 81,078 units/month
- SKUC2 (chairs): 81,027 units/month
- SKUE2 (electronics): 76,849 units/month
- SKUT2, SKUT3 (textbooks): ~65,000 & 46,000 units/month
- SKUD2 (desks): 57,350 units/month
- SKUE3 (electronics): 8,927 units/month (lowest)
- **TOTAL**: 710,263 units/month (~33,822 units/day)

**Peak Monthly Demand**: 1,303,036 units across all 9 pallet SKUs

**Why Pallet is the Bottleneck**:
1. **9 SKUs** (half of all SKUs) compete for pallet storage
2. **Highest demand SKUs** are in pallet storage (chairs, desks)
3. **Low package capacity per shelf**: Only 4-7 packages/shelf vs 8 for racking, 100 for bins
4. **Small total capacity**: Only 5,664 shelves total vs 40,102 for racking

**Expansion Required (MaxMin Model to achieve 79.24 days DoH)**:
- **Sacramento Pallet**: +5,425 shelves
- **Austin Pallet**: +2,246 shelves
- **TOTAL**: +7,671 shelves (+135% increase!)

**Post-Expansion Capacity**:
- Sacramento: 1,100 + 5,425 = 6,525 shelves × 4 pkg/shelf = 26,100 packages
- Austin: 1,484 + 2,246 = 3,730 shelves × 6 pkg/shelf = 22,380 packages
- Columbus: 3,080 shelves × 7 pkg/shelf = 21,560 packages (unchanged)
- **NEW TOTAL**: 13,335 shelves, ~70,040 packages (+101% increase in package capacity)

---

### 4. HAZMAT STORAGE ✅ EXCESS CAPACITY

**SKUs Using Hazmat**: 2 SKUs (Domestic)
- SKUA1 (art supplies/adhesives)
- SKUA2 (art supplies/adhesives)

**Current Capacity**:
- Columbus: 9,200 shelves
- Sacramento: 948 shelves
- Austin: 2,680 shelves
- **TOTAL**: 12,828 shelves

**Demand** (Average Monthly):
- SKUA1: 23,366 units/month
- SKUA2: 38,600 units/month
- **TOTAL**: 61,966 units/month (~2,951 units/day)

**Expansion Needed (MaxMin Model)**: **ZERO** ✅

**Conclusion**: Hazmat has excess capacity.

---

## Summary Table

| Storage Type | SKUs | Current Shelves | Expansion Needed | Status |
|--------------|------|-----------------|------------------|---------|
| **Bins** | 4 | 681,768 | 0 | ✅ Excess Capacity |
| **Racking** | 3 | 40,102 | 0 | ✅ Excess Capacity |
| **Pallet** | 9 | 5,664 | +7,671 (+135%) | ❌ **BOTTLENECK** |
| **Hazmat** | 2 | 12,828 | 0 | ✅ Excess Capacity |

---

## Key Insights

1. **Pallet storage is the sole capacity bottleneck**
   - Requires 135% expansion to achieve 79 days DoH
   - Holds 50% of SKUs but only 7% of total shelves (5,664 of 740,362)
   - Package capacity per shelf is very low (4-7 vs 8-100 for other types)

2. **All other storage types have excess capacity**
   - Bins: Massive overcapacity (Columbus bins alone could handle entire demand)
   - Racking: Comfortable capacity (~37% spare at 79 days DoH)
   - Hazmat: Adequate capacity

3. **High-demand SKUs concentrate in Pallet storage**
   - Top 5 demand SKUs (SKUC1, SKUD1, SKUW2, SKUD3, SKUC2) include 4 pallet SKUs
   - Pallet handles ~710,000 units/month vs 265,000 for bins, 162,000 for racking

4. **Expansion should focus exclusively on pallet shelving**
   - Sacramento: +5,425 pallet shelves
   - Austin: +2,246 pallet shelves
   - No investment needed in other storage types

---

## Recommendation

**Focus all expansion investment on Pallet storage at Sacramento and Austin facilities.**

The constraint is NOT overall warehouse space, but specifically the number of pallet shelves and their low package capacity. Consider:
1. Adding pallet shelves as specified (7,671 new shelves)
2. Investigating if higher-capacity pallet configurations are possible
3. Potential to redistribute some pallet SKUs to other facilities if logistics allow

Current excess capacity in Bins and Racking represents an opportunity cost - these areas are underutilized.

---

**Report Generated**: Model 0.2a MaxMin DoH Analysis
**Maximum Balanced DoH Achievable**: 79.24 days (with pallet expansion)
