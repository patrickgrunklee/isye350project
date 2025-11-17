# Post-Run Truck Utilization Analysis Tool

## Overview

**[analyze_truck_utilization.py](analyze_truck_utilization.py)** is a standalone analysis tool that evaluates truck efficiency for any phase2_DAILY model results.

## Key Features

✅ **Works with any DoH configuration** - Analyzes results from any model
✅ **No re-running required** - Uses existing truckload_analysis CSV files
✅ **Identifies inefficiencies** - Finds deliveries below 90% utilization
✅ **Calculates savings potential** - Estimates trucks saved from consolidation
✅ **Supplier & facility breakdowns** - Detailed analysis by dimension
✅ **Actionable recommendations** - Specific suggestions for improvement

## Usage

```bash
cd model2.0
python analyze_truck_utilization.py <doh_config>
```

### Examples

```bash
# Analyze 3/1 days-on-hand model
python analyze_truck_utilization.py 3_1_doh

# Analyze 5/2 days-on-hand model
python analyze_truck_utilization.py 5_2_doh

# Analyze 0/0 days-on-hand model
python analyze_truck_utilization.py 0_0_doh

# Analyze 10/3 days-on-hand model
python analyze_truck_utilization.py 10_3_doh
```

## Prerequisites

The corresponding `phase2_DAILY_*` model must have been run first to generate:
- `results/Phase2_DAILY/truckload_analysis_<doh_config>.csv`

## What It Analyzes

### 1. Overall Utilization
- Total trucks needed
- Average trucks per delivery
- Weight and volume utilization percentages
- Which constraint is binding (weight vs. volume)

### 2. Low Utilization Detection
- Identifies deliveries <90% on binding constraint
- Calculates potential truck savings
- Shows worst offenders with specific dates

### 3. By Supplier Analysis
- Trucks needed per supplier
- Utilization rates
- Low-utilization percentages

### 4. By Facility Analysis
- Trucks needed per facility
- Utilization rates
- Distribution across locations

### 5. Recommendations
- Volume vs. weight constraint guidance
- Consolidation opportunities
- SKU bundling suggestions

## Example Output

```
================================================================================
TRUCK UTILIZATION ANALYSIS - 3_1_DOH
================================================================================

Total trucks needed: 959,920.00
Average weight utilization: 89.5%
Average volume utilization: 99.5%

Volume-constrained: 9,570 (100.0%)

================================================================================
LOW UTILIZATION ANALYSIS (<90%)
================================================================================

Deliveries below 90% on binding constraint: 0 (0.0%)
Excellent! All deliveries meet 90% utilization threshold.

================================================================================
RECOMMENDATIONS
================================================================================

1. VOLUME-CONSTRAINED OPERATIONS
   - Trucks fill by space before weight
   - Unused weight capacity: ~4,715 lbs per truck

2. EXCELLENT UTILIZATION
   - All deliveries meet 90% threshold
   - Truck dispatch is already optimized
```

## Comparison: Analysis Tool vs. Truck-Optimized Model

| Feature | Analysis Tool | Truck-Optimized Model |
|---------|--------------|----------------------|
| **When runs** | After model completes | During optimization |
| **Input** | Existing CSV results | Optimizes from scratch |
| **Runtime** | Seconds | 10-30 minutes |
| **Enforces 90%** | No (reports only) | Yes (hard constraint) |
| **Adjusts deliveries** | No | Yes (can shift timing) |
| **Trucks** | Continuous | INTEGER |
| **Use case** | Quick assessment | Operational planning |

## When to Use Each

### Use the Analysis Tool When:
- ✅ Quickly checking existing results
- ✅ Comparing multiple DoH configurations
- ✅ Understanding current inefficiencies
- ✅ Don't need to re-optimize

### Use the Truck-Optimized Model When:
- ✅ Need enforceable 90% minimum
- ✅ Want integer truck dispatch schedule
- ✅ Can adjust delivery dates
- ✅ Creating operational truck schedule

## Files

**Input (required):**
- `results/Phase2_DAILY/truckload_analysis_<doh_config>.csv`

**Output (console only):**
- Utilization statistics
- Low utilization analysis
- Recommendations

## Integration with Existing Models

The analysis tool automatically works with:
- All phase2_DAILY_*_doh.py models (with truckload tracking)
- Any custom DoH configuration
- Both pure SKU and mixed storage approaches

No model modifications needed - just run the analysis after your model completes!

## Quick Start

```bash
# 1. Run your model (if not already done)
python phase2_DAILY_5_2_doh.py

# 2. Analyze truck utilization
python analyze_truck_utilization.py 5_2_doh

# 3. Review recommendations and identify savings opportunities
```

---

**Perfect for:** Quick assessments, sensitivity analysis, comparing DoH scenarios, and identifying optimization opportunities without expensive MIP solves.
