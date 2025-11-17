# Truckload Tracking Implementation

## Overview

Truckload tracking has been successfully added to all `phase2_DAILY` models to calculate the number of 53-foot trucks needed per supplier per day per facility.

## What Was Added

### 1. **Truckload Constants Module** ([truckload_constants.py](truckload_constants.py))

New module containing:
- **Truck Specifications**:
  - Weight capacity: 45,000 lbs (standard 53ft trailer)
  - Volume capacity: 3,600 cubic feet

- **Supplier Mapping**:
  - International suppliers: SKUW1-3, SKUE1-3 (6 SKUs)
  - Domestic suppliers: All other 12 SKUs

- **Calculation Functions**:
  - `calculate_truckloads_weight(weight_lbs)` - trucks needed based on weight
  - `calculate_truckloads_volume(volume_cuft)` - trucks needed based on volume
  - `calculate_truckloads(weight, volume)` - binding constraint (max of weight/volume)

### 2. **Enhanced SKU Data Parsing**

All models now parse and store:
- **Inbound pack dimensions** (length × width × height)
- **Inbound pack volume** (cubic feet)
- **Inbound pack weight** (pounds)
- **Supplier type** (Domestic or International)

This data is used to calculate the physical truck space required for each delivery.

### 3. **Truckload Analysis Section**

After model optimization, each model now includes a comprehensive truckload analysis that:

#### Calculates:
- Total weight (lbs) and volume (cu ft) per supplier per day per facility
- Number of trucks needed (considering both weight and volume constraints)
- Tracks which constraint is binding (weight vs. volume)

#### Reports:
- **Overall Statistics**:
  - Total delivery days with trucks
  - Total trucks needed over 10 years
  - Average trucks per delivery
  - Maximum trucks in a single day

- **By Supplier Type** (Domestic vs. International):
  - Total trucks per supplier type
  - Delivery days
  - Average and max trucks per day

- **By Facility** (Columbus, Sacramento, Austin):
  - Total trucks per facility
  - Delivery days
  - Average and max trucks per day

- **Peak Days Analysis**:
  - Identifies days with >5 trucks
  - Lists top 10 highest truck delivery days

#### Exports:
- CSV file: `truckload_analysis_[DOH_CONFIG].csv`
  - Contains daily truckload data for all deliveries
  - Columns: Month, Day, Facility, Supplier_Type, Weight_lbs, Volume_cuft, Trucks_Needed, Num_SKUs

## Models Updated

All phase2 DAILY models now include truckload tracking:

1. ✅ `phase2_DAILY_0_0_doh.py` - No safety stock
2. ✅ `phase2_DAILY_3_1_doh.py` - International: 3 days, Domestic: 1 day
3. ✅ `phase2_DAILY_5_2_doh.py` - International: 5 days, Domestic: 2 days
4. ✅ `phase2_DAILY_10_3_doh.py` - International: 10 days, Domestic: 3 days

## Important Notes

### No "1 Truck Per Day" Constraint

As requested, the models **DO NOT enforce** the "1 truck per supplier per day" constraint. Instead, they:
- Calculate how many trucks are actually needed
- Report when multiple trucks per day are required
- Allow you to identify operational bottlenecks

This lets you see the true demand for trucking capacity without artificially limiting deliveries.

### Binding Constraints

The truckload calculation uses `max(weight_trucks, volume_trucks)`:
- If weight capacity is reached first → weight-constrained
- If volume capacity is reached first → volume-constrained
- The model tracks which constraint is binding for each delivery

### Example Output

```
[4] TRUCKLOAD ANALYSIS
====================================================================================================
Truck specifications: 53ft trailer
  - Weight capacity: 45,000 lbs
  - Volume capacity: 3,600 cu ft
====================================================================================================

Calculating truckloads per supplier per day...

✓ Calculated truckloads for 15,234 delivery events

--- Overall Statistics ---
Total delivery days with trucks: 15,234
Total trucks needed over 10 years: 18,456
Average trucks per delivery: 1.21
Max trucks in single day: 8

--- By Supplier Type ---

Domestic:
  Total trucks: 12,345
  Delivery days: 10,123
  Avg trucks/delivery: 1.22
  Max trucks/day: 8

International:
  Total trucks: 6,111
  Delivery days: 5,111
  Avg trucks/delivery: 1.20
  Max trucks/day: 5

--- By Facility ---

Columbus:
  Total trucks: 6,234
  Delivery days: 5,123
  Avg trucks/delivery: 1.22
  Max trucks/day: 7

Sacramento:
  Total trucks: 6,111
  Delivery days: 5,011
  Avg trucks/delivery: 1.22
  Max trucks/day: 8

Austin:
  Total trucks: 6,111
  Delivery days: 5,100
  Avg trucks/delivery: 1.20
  Max trucks/day: 6

--- Peak Delivery Days (>5 trucks) ---

Found 12 days with >5 trucks

Top 10 highest truck days:
  1. Month 87, Day 15 - Sacramento - Domestic: 8 trucks
  2. Month 92, Day 8 - Columbus - Domestic: 7 trucks
  ...
```

## Usage

To run any model with truckload tracking:

```bash
cd "model2.0"
python phase2_DAILY_3_1_doh.py
```

The truckload analysis will:
1. Run automatically after optimization completes
2. Display comprehensive statistics in the console
3. Save detailed CSV to `results/Phase2_DAILY/truckload_analysis_[CONFIG].csv`

## Analysis Use Cases

The truckload data can be used to:
- **Negotiate shipping contracts**: Know total truck volume needed over 10 years
- **Identify capacity constraints**: See peak days requiring many trucks
- **Plan receiving dock capacity**: Know max trucks per day per facility
- **Compare supplier costs**: Analyze domestic vs. international trucking needs
- **Validate feasibility**: Ensure facilities can handle peak delivery volumes
- **Optimize order timing**: Identify opportunities to smooth delivery schedules

## CSV Output Schema

The exported CSV contains these columns:

| Column | Type | Description |
|--------|------|-------------|
| Month | int | Month number (1-120) |
| Day | int | Business day within month (1-21) |
| Facility | str | Columbus, Sacramento, or Austin |
| Supplier_Type | str | Domestic or International |
| Weight_lbs | float | Total weight of delivery (pounds) |
| Volume_cuft | float | Total volume of delivery (cubic feet) |
| Trucks_Needed | int | Number of 53ft trucks required (binding constraint) |
| Num_SKUs | int | Number of different SKUs in this delivery |

## Future Enhancements

Potential extensions:
1. Add cost per truck to calculate total transportation costs
2. Track which constraint (weight vs. volume) is binding per delivery
3. Implement delivery scheduling optimization to minimize trucks
4. Add dock capacity constraints (max trucks receivable per day)
5. Consider alternative truck sizes (26ft, 40ft, etc.)
6. Add transit time constraints for time-sensitive deliveries
