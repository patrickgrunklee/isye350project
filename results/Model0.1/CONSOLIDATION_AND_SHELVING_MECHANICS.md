# CONSOLIDATION & SHELVING MECHANICS EXPLAINED

**How InkCredible Supplies Receives, Repacks, and Stores Inventory**

---

## 🎯 OVERVIEW

InkCredible Supplies receives products from suppliers in **inbound packs** (large wholesale boxes) and can optionally **repack** them into smaller **sell packs** (customer-ready units) for storage and shipment.

### Key Concepts

1. **Inbound Pack**: How supplier ships product (bulk packaging)
2. **Sell Pack**: How customer receives product (retail packaging)
3. **Consolidation**: Breaking down inbound packs into smaller sell packs
4. **Storage Type**: Where product is stored (Bins, Racking, Pallet, Hazmat)
5. **Capacity Constraints**: Volume, weight, and package count limits per shelf

---

## 📦 CONSOLIDATION RATIOS BY SKU

### High-Consolidation SKUs (Efficient Storage)

| SKU | Category | Supplier | Consolidation Ratio | Inbound Pack | Sell Pack | Storage |
|-----|----------|----------|---------------------|--------------|-----------|---------|
| **SKUW1** | Writing Utensils | International | **144:1** | 10×10×6" (15 lbs) | 3×6×1" (1 lb) | **Bins** |
| **SKUW2** | Writing Utensils | International | **120:1** | 10×10×8" (25 lbs) | 6×3×2" (2 lbs) | **Bins** |
| **SKUW3** | Writing Utensils | International | **120:1** | 10×10×8" (25 lbs) | 6×3×2" (2 lbs) | **Bins** |
| **SKUE1** | Electronics | International | **100:1** | 10×10×10" (30 lbs) | 2×2×2" (0.25 lbs) | **Bins** |
| **SKUA3** | Art Supplies | Domestic | **100:1** | 9×12×4" (10 lbs) | 9×12×4" (10 lbs) | **Racking** |

**Key Insight**: Writing utensils and small electronics have the **highest consolidation ratios** (100:1 to 144:1), meaning 1 inbound pack contains 100-144 customer units.

---

### Medium-Consolidation SKUs

| SKU | Category | Supplier | Consolidation Ratio | Inbound Pack | Sell Pack | Storage |
|-----|----------|----------|---------------------|--------------|-----------|---------|
| **SKUT2** | Textbooks | Domestic | **64:1** | 48×48×20" (550 lbs) | 10×14×3" (8 lbs) | **Pallet** |
| **SKUT3** | Textbooks | Domestic | **64:1** | 48×48×20" (550 lbs) | 10×14×3" (8 lbs) | **Pallet** |
| **SKUE2** | Electronics | International | **60:1** | 48×48×48" (520 lbs) | 14×10×3" (8 lbs) | **Pallet** |
| **SKUA2** | Art Supplies | Domestic | **35:1** | 10×10×7" (12 lbs) | 7×5×2" (2 lbs) | **Hazmat** |
| **SKUC2** | Chairs | Domestic | **24:1** | 48×48×48" (200 lbs) | 20×36×5" (20 lbs) | **Pallet** |
| **SKUE3** | Electronics | International | **24:1** | 48×48×48" (400 lbs) | 20×14×4" (15 lbs) | **Pallet** |
| **SKUA1** | Art Supplies | Domestic | **15:1** | 5×5×5" (8 lbs) | 4×4×1" (2 lbs) | **Hazmat** |

**Key Insight**: Textbooks and electronics shipped on pallets have **moderate consolidation** (24:1 to 64:1).

---

### Low/No-Consolidation SKUs (Furniture)

| SKU | Category | Supplier | Consolidation Ratio | Inbound Pack | Sell Pack | Storage |
|-----|----------|----------|---------------------|--------------|-----------|---------|
| **SKUT1** | Textbooks | Domestic | **3:1** | 10×14×9" (25 lbs) | 10×14×3" (8 lbs) | **Racking** |
| **SKUT4** | Textbooks | Domestic | **3:1** | 10×14×9" (25 lbs) | 10×14×3" (8 lbs) | **Racking** |
| **SKUD1** | Desks | Domestic | **1:1 ❌** | 36×24×5" (30 lbs) | 36×24×5" (30 lbs) | **Pallet** |
| **SKUD2** | Desks | Domestic | **1:1 ❌** | 48×48×48" (75 lbs) | 48×36×20" (75 lbs) | **Pallet** |
| **SKUD3** | Desks | Domestic | **1:1 ❌** | 48×48×48" (35 lbs) | 24×36×36" (35 lbs) | **Pallet** |
| **SKUC1** | Chairs | Domestic | **1:1 ❌** | 48×40×20" (60 lbs) | 48×40×20" (60 lbs) | **Pallet** |

**Key Insight**: Desks and most chairs have **1:1 ratio** (cannot repack) - must be stored and shipped as received from supplier.

**Exception**: SKUC2 (chairs) can be partially consolidated (24:1) despite furniture category.

---

## 🏗️ STORAGE TYPES & CAPACITY

### Bins Storage

**Best For**: Small items (writing utensils, small electronics)

| Facility | Dimensions (L×W×H) | Volume per Shelf | Package Capacity | Weight Max | Current Shelves |
|----------|-------------------|------------------|------------------|------------|-----------------|
| **Columbus** | Auto (flexible) | 1.73 cu ft | 1 package/shelf | N/A | 647,680 shelves |
| **Sacramento** | 1.25×1.25×4 ft | 6.25 cu ft | **3 packages/shelf** | N/A | 14,400 shelves |
| **Austin** | 1.25×1.25×4 ft | 6.25 cu ft | **3 packages/shelf** | N/A | 19,688 shelves |

**SKUs Using Bins**:
- SKUW1, SKUW2, SKUW3 (writing utensils) - **144:1, 120:1 ratios**
- SKUE1 (electronics) - **100:1 ratio**

**Example - SKUW1 at Sacramento**:
```
1 inbound pack (10×10×6") = 144 sell packs (3×6×1" each)
After unpacking: 144 small boxes (0.0104 cu ft each)
Shelf capacity: 6.25 cu ft / 0.0104 cu ft = ~600 sell packs per shelf
Package limit: 3 packages per shelf
→ Storage bottleneck: Package count (not volume)
```

---

### Racking Storage

**Best For**: Medium items (textbooks, art supplies)

| Facility | Dimensions (L×W×H) | Volume per Shelf | Package Capacity | Weight Max | Current Shelves |
|----------|-------------------|------------------|------------------|------------|-----------------|
| **Columbus** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 15,600 shelves |
| **Sacramento** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 13,078 shelves |
| **Austin** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 11,424 shelves |

**SKUs Using Racking**:
- SKUA3 (art supplies) - **100:1 ratio**
- SKUT1, SKUT4 (textbooks) - **3:1 ratio**

**Example - SKUT1 at Columbus**:
```
1 inbound pack (10×14×9") = 3 sell packs (10×14×3" each)
Sell pack volume: 0.243 cu ft
Shelf capacity: 27 cu ft / 0.243 cu ft = ~111 sell packs per shelf
Package limit: 8 packages per shelf
→ Storage bottleneck: Package count (allows ~24 sell packs max if stored as 8 inbound packs)
```

---

### Pallet Storage

**Best For**: Large/heavy items (furniture, textbooks, electronics)

| Facility | Dimensions (L×W×H) | Volume per Shelf | Package Capacity | Weight Max/Shelf | Current Shelves |
|----------|-------------------|------------------|------------------|------------------|-----------------|
| **Columbus** | 10×4.25×24 ft | 1,020 cu ft | **7 packages/shelf** | 600 lbs | 3,080 shelves |
| **Sacramento** | 5×4.25×24 ft | 510 cu ft | **4 packages/shelf** | 600 lbs | 1,100 shelves |
| **Austin** | 10×4.25×18 ft | 765 cu ft | **6 packages/shelf** | 600 lbs | 1,484 shelves |

**SKUs Using Pallet**:
- **Furniture (1:1)**: SKUD1-3, SKUC1 (desks & chairs)
- **Textbooks (64:1)**: SKUT2, SKUT3 (pallet-shipped textbooks)
- **Electronics (60:1, 24:1)**: SKUE2, SKUE3
- **Chairs (24:1)**: SKUC2

**Example - SKUD1 at Columbus**:
```
1 inbound pack (36×24×5") = 1 sell pack (same dimensions)
Cannot consolidate - store as received
Sell pack volume: 2.5 cu ft
Shelf capacity: 1,020 cu ft / 2.5 cu ft = ~408 units per shelf
Package limit: 7 packages per shelf
→ Storage bottleneck: Package count (allows only 7 desks per shelf)
```

**Example - SKUT2 at Columbus (consolidation)**:
```
1 inbound pack (48×48×20" pallet) = 64 sell packs (10×14×3" textbooks)
Inbound volume: 26.67 cu ft
Sell pack volume: 0.243 cu ft each × 64 = 15.55 cu ft total
Space saved by unpacking: 26.67 - 15.55 = 11.12 cu ft (42% savings!)
Package limit: 7 packages per shelf
→ If stored as inbound: 7 pallets = 448 textbooks
→ If unpacked: 7 packages (repacked) = Still limited to 7 packages
```

---

### Hazmat Storage

**Best For**: Hazardous art supplies (adhesives, paints, chemicals)

| Facility | Dimensions (L×W×H) | Volume per Shelf | Package Capacity | Weight Max | Current Shelves |
|----------|-------------------|------------------|------------------|------------|-----------------|
| **Columbus** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 9,200 shelves |
| **Sacramento** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 948 shelves |
| **Austin** | 3×1.5×6 ft | 27 cu ft | **8 packages/shelf** | N/A | 2,680 shelves |

**SKUs Using Hazmat**:
- SKUA1 (15:1 ratio) - Small hazmat items
- SKUA2 (35:1 ratio) - Medium hazmat items

**Special Handling**: These items require specialized storage due to flammability or toxicity.

---

## ⚖️ VOLUME vs WEIGHT vs PACKAGE CONSTRAINTS

### The Three Capacity Limits

Every shelf has **THREE independent constraints**:

#### 1. **Volume Capacity** (cubic feet)
```
Sum of (packages × volume per package) ≤ Shelf volume capacity
```

**Example** (Columbus Pallet):
- Shelf volume: 1,020 cu ft
- SKUD1 desk: 2.5 cu ft each
- Max by volume: 1,020 / 2.5 = **408 desks**

#### 2. **Weight Capacity** (pounds)
```
Sum of (packages × weight per package) ≤ Shelf weight capacity
```

**Example** (Columbus Pallet):
- Shelf weight limit: 600 lbs
- SKUD1 desk: 30 lbs each
- Max by weight: 600 / 30 = **20 desks**

#### 3. **Package Count** (number of packages)
```
Number of packages on shelf ≤ Shelf package capacity
```

**Example** (Columbus Pallet):
- Shelf package limit: **7 packages**
- Regardless of size/weight
- Max by count: **7 desks**

### Which Constraint Binds?

For **Columbus Pallet storing SKUD1 desks**:
- Volume limit: 408 desks ✅
- Weight limit: 20 desks ⚠️
- Package limit: **7 desks** ❌ **BINDING CONSTRAINT**

**Result**: Can only store **7 desks per shelf** despite having space for 408 and weight capacity for 20.

---

## 🔄 MODEL REPACKING DECISIONS

### Current Model Behavior

The model includes **repacking decision variables** but they are **DISABLED** in current run:

```python
# From full_daily_warehouse_model.py line 391-393:
# Repacking decision - DISABLED to keep model linear
# (Assume all SKUs stored in inbound packs - no repacking)
# repack = Variable(m, name="repack_decision", domain=[s_set, f_set], type="binary")
```

**What This Means**:
- All SKUs are stored in **inbound pack format**
- Model does NOT break down SKUW1 (144:1) into 144 sell packs
- Instead: Stores 1 inbound pack containing 144 sell packs

### If Repacking Were Enabled

**Binary Decision per SKU per Facility**:
```
repack[s, f] = 1  →  Store as sell packs (unpacked)
repack[s, f] = 0  →  Store as inbound packs (as received)
```

**Constraint**:
```python
repack_constraint[s, f] = repack[s, f] <= can_consolidate[s]
```
Only SKUs with `can_consolidate = Yes` can be repacked.

**Volume/Weight Calculation**:
```python
volume_used[f, st] = Sum over s of (
    packages_on_shelf[s, f, st] * (
        repack[s, f] * sell_pack_volume[s] +
        (1 - repack[s, f]) * inbound_pack_volume[s]
    )
)
```

**Trade-off**:
- **Repack = 1**: Takes more shelf space (144 small packages vs 1 large box) but better cube utilization
- **Repack = 0**: Uses package capacity efficiently but wastes cube space

---

## 📊 CAPACITY UTILIZATION EXAMPLE

### Scenario: Columbus Pallet Shelf with Mixed SKUs

**Shelf Capacity**:
- Volume: 1,020 cu ft
- Weight: 600 lbs
- Packages: **7 max**

**Stored SKUs** (all inbound pack format):
| SKU | Qty | Inbound Volume | Inbound Weight | Packages Used |
|-----|-----|----------------|----------------|---------------|
| SKUD1 (desk) | 3 | 2.5 cu ft × 3 = 7.5 cu ft | 30 lbs × 3 = 90 lbs | 3 |
| SKUT2 (textbook pallet) | 2 | 26.67 cu ft × 2 = 53.34 cu ft | 550 lbs × 2 = 1,100 lbs | 2 |
| SKUC1 (chair) | 2 | 22.2 cu ft × 2 = 44.4 cu ft | 60 lbs × 2 = 120 lbs | 2 |
| **TOTAL** | 7 items | **105.24 cu ft** | **1,310 lbs** | **7 packages** |

**Constraint Check**:
- ✅ Volume: 105.24 / 1,020 = **10.3% utilized** (plenty of space)
- ❌ Weight: 1,310 / 600 = **218% OVER LIMIT** ⚠️
- ✅ Package: 7 / 7 = **100% at limit**

**Result**: **INFEASIBLE** - Weight constraint violated!

**Solution**: Replace SKUT2 textbooks (550 lbs each) with lighter items or move to different shelf.

---

## 🎯 KEY INSIGHTS

### 1. Package Count is Often the Binding Constraint

Despite large volume capacity:
- Columbus Pallet: 1,020 cu ft but only **7 packages max**
- Sacramento Bins: 6.25 cu ft but only **3 packages max**

**Why This Matters**:
- High-consolidation SKUs (144:1) benefit less than expected
- Even if you unpack 144 small items, shelf package limit restricts storage

### 2. Weight Limits Matter for Heavy Items

Furniture (desks, chairs) and textbook pallets hit **weight limits** before volume:
- SKUT2: 550 lbs per pallet (single item uses 92% of 600 lb limit)
- SKUD2: 75 lbs per desk (8 desks = 600 lbs exactly)

### 3. Consolidation Saves Volume, Not Package Count

**SKUW1 Example**:
- Inbound: 1 package (10×10×6") = 0.347 cu ft
- Sell: 144 packages (3×6×1" each) = 144 × 0.0104 cu ft = 1.50 cu ft
- **Volume increase**: 1.50 / 0.347 = 4.3× more space if unpacked!
- **Package increase**: 1 → 144 packages (hits limits faster)

**Conclusion**: For bins with 3-package limit, better to store as inbound pack (1 package) than unpack (would need 48 shelves for 144 items).

### 4. Model Chose NOT to Expand

Despite these constraints, **$0 expansion** was optimal because:
- **Zero inventory strategy** means no accumulation
- Items received at 8am, shipped by 5pm (no overnight storage)
- **Package capacity never hit** due to JIT approach

---

## 📝 RECOMMENDATIONS

### For Realistic Model Run:

1. **Enable Days-On-Hand Constraint**
   - Will force inventory accumulation
   - Package constraints will start binding
   - Expansion likely needed

2. **Enable Repacking Decisions**
   - Let model choose: Store as inbound vs sell packs
   - May find optimal mix (e.g., repack SKUW1 but not SKUT2)

3. **Add Repacking Costs**
   - Labor cost to unpack/repack: $0.05-$0.10 per unit
   - Will discourage unnecessary repacking

4. **Review Package Capacity Limits**
   - Sacramento Pallet: Only **4 packages/shelf** (very restrictive)
   - May need to increase limits or add more shelves

---

**Report Generated**: 2025
**Purpose**: Explain consolidation mechanics, storage types, and capacity constraints
**Key Finding**: Package count limits often bind before volume/weight with current inventory strategy
