# Stochastic Supply Chain Delay Analysis
## InkCredible Supplies Warehouse Optimization

---

## Executive Summary

This analysis quantifies the impact of supply chain uncertainty on warehouse capacity requirements using a **supplier-level stochastic delay model**. Results show that even moderate supply chain disruptions require nearly **doubling warehouse capacity** to maintain service levels.

---

## Problem Statement

### The Challenge
- **Deterministic models assume perfect delivery reliability** - all shipments arrive exactly on schedule
- **Real-world supply chains face stochastic delays** - weather, port congestion, equipment failures, etc.
- **Question**: How much additional warehouse capacity is needed to buffer against delivery uncertainty?

### Why Supplier-Level Delays Matter
When a supplier's truckload is delayed, it affects:
- **All SKUs on that truck simultaneously** (correlated delays)
- **All trucks in that delivery** (avg. 32.6 trucks per event)
- **Multiple facilities** depending on delivery routes

This creates a **multiplication effect** where single delay events compound across the supply chain.

---

## Mathematical Formulation

### Stochastic Delay Model

We model supply chain disruptions using a **two-stage stochastic process**:

#### Stage 1: Delay Event Frequency (Poisson Distribution)
```
Number of delay events per month ~ Poisson(λ)

where: λ = k × deliveries_per_month

k = disruption intensity factor
  - k = 0.1 → Low disruption (10% of deliveries delayed)
  - k = 0.3 → Moderate disruption (30% of deliveries delayed)
  - k = 0.5 → High disruption (50% of deliveries delayed)
```

**Interpretation**: The Poisson distribution models random, independent delay occurrences. Higher `k` values indicate more frequent disruptions.

#### Stage 2: Delay Duration (Exponential Distribution)
```
Delay duration (days) ~ Exponential(μ)

where: μ = mean delay duration in days

μ = 3 days  → Low severity (quick recovery)
μ = 5 days  → Moderate severity (typical port delays)
μ = 14 days → High severity (major disruptions)
```

**Interpretation**: The exponential distribution models memoryless delay durations. The mean parameter μ represents average time to resolution.

### Supplier-Level Delay Structure

Delays occur at the **(Supplier, Facility, Day)** level:

```python
For each (Supplier, Facility) pair:
  For each month t in planning horizon:
    # Stage 1: How many delay events?
    num_events ~ Poisson(λ = k × deliveries_per_month)

    For each event e in num_events:
      # Stage 2: How long is the delay?
      delay_duration ~ Exponential(μ)

      # Select which delivery is affected
      affected_delivery = random_sample(month_deliveries)

      # Impact metrics
      trucks_affected = affected_delivery.trucks_needed
      skus_affected = affected_delivery.skus_delivered
      truck_days_delay = trucks_affected × delay_duration
```

### Storage Impact Calculation

#### Effective Days-on-Hand (DOH)
When deliveries are delayed, facilities must hold additional safety stock:

```
Effective DOH = Base DOH + Average Delay Per Delivery

Base DOH (Deterministic):
  - Domestic suppliers: 4 days
  - International suppliers: 14 days

Average Delay Per Delivery:
  = Total Truck-Days Delay / Total Trucks Affected
```

#### Storage Scaling Relationship
Inventory requirements scale linearly with DOH:

```
Storage Required = (Daily Demand) × DOH

Therefore:
New Storage     Base Storage × (New DOH / Base DOH)
─────────────── = ───────────────────────────────────
Base Storage              1

Percent Increase = ((New DOH / Base DOH) - 1) × 100%
```

#### Weighted Average Multiplier
Since domestic and international SKUs have different base DOH:

```
Inventory Split:
  - Domestic SKUs: 12/18 = 66.7% of inventory
  - International SKUs: 6/18 = 33.3% of inventory

Weighted Multiplier =
  (0.667 × Domestic_DOH_Multiplier) +
  (0.333 × International_DOH_Multiplier)

Total Shelves Needed = Base Shelves × Weighted Multiplier
```

---

## Model Implementation

### Data Sources
1. **Truckload Schedule**: 28,778 delivery events over 120 months
   - Source: [truckload_analysis_3_1_doh.csv](results/Phase2_DAILY/truckload_analysis_3_1_doh.csv)
   - Contains: Month, Day, Facility, Supplier, Trucks_Needed, SKUs_Delivered

2. **Supplier Information**: 5 suppliers across 2 categories
   - **Domestic**: Canvas & Co., Bound to Learn, Form & Function
   - **International**: The Write Stuff, VoltEdge

3. **Baseline Storage Requirements**: 3,994 shelves
   - Sacramento: 2,884 shelves (72%)
   - Austin: 1,110 shelves (28%)

### Monte Carlo Simulation
- **50 independent simulations** per scenario
- **120-month planning horizon** (10 years)
- **Statistical outputs**: Mean ± Standard Deviation across simulations

### Key Metrics Tracked
1. **Total Delay Events**: Number of disruptions over 10 years
2. **Trucks Affected**: Number of truck deliveries delayed
3. **Truck-Days Delay**: trucks × delay_duration (captures full impact)
4. **SKUs Affected**: Number of SKU deliveries impacted
5. **Storage Requirements**: Additional shelves needed

---

## Scenario Analysis

### Scenario Definitions

| Scenario | k Factor | μ (days) | Interpretation |
|----------|----------|----------|----------------|
| **Baseline** | 0.0 | 0 | Deterministic (no delays) |
| **Low Disruption** | 0.1 | 3 | 10% of deliveries delayed by avg. 3 days |
| **Moderate Disruption** | 0.3 | 5 | 30% of deliveries delayed by avg. 5 days |
| **High Disruption** | 0.5 | 14 | 50% of deliveries delayed by avg. 14 days |

### Scenario Context
- **Low**: Routine disruptions (minor weather, traffic delays)
- **Moderate**: Seasonal volatility (holiday rush, port congestion)
- **High**: Major disruptions (natural disasters, labor strikes, pandemics)

---

## Results Summary

### Delay Event Statistics

| Scenario | Delay Events | Trucks Affected | Truck-Days Delay | Avg. Delay/Delivery |
|----------|--------------|-----------------|------------------|---------------------|
| **Low** | 2,873 ± 55 | 93,529 ± 2,857 | 283,033 ± 12,800 | 3.03 days |
| **Moderate** | 8,659 ± 113 | 283,067 ± 5,882 | 1,414,166 ± 44,959 | 5.00 days |
| **High** | 14,374 ± 99 | 467,828 ± 6,020 | 6,543,086 ± 121,696 | 13.99 days |

**Key Observation**: Over 10 years, high disruption scenario results in 14,374 delay events affecting 468,000 truck deliveries - nearly **50% of all shipments**.

### Storage Impact Analysis

| Scenario | Effective DOH (Domestic) | Effective DOH (International) | Additional Shelves | % Increase |
|----------|--------------------------|-------------------------------|--------------------| -----------|
| **Baseline** | 4 days | 14 days | 0 | 0% |
| **Low** | 7.0 days | 17.0 days | +2,302 | +57.6% |
| **Moderate** | 9.0 days | 19.0 days | +3,801 | +95.2% |
| **High** | 18.0 days | 28.0 days | +10,640 | +266.4% |

### Facility-Level Breakdown

#### Moderate Disruption Scenario (Most Realistic)
- **Sacramento**: 2,884 → 5,620 shelves (+2,736 additional)
- **Austin**: 1,110 → 2,174 shelves (+1,064 additional)
- **Total**: 3,994 → 7,795 shelves (+3,801 additional)

**Cost Implication**: Moderate supply chain uncertainty requires **95% more warehouse capacity** than deterministic planning assumes.

---

## Key Insights

### 1. Cost of Uncertainty is Substantial
Even with **moderate disruptions** (30% of deliveries delayed by 5 days):
- Warehouse capacity must nearly **double** (+95%)
- Represents **3,801 additional shelves** beyond baseline
- Equivalent to **~$7.6M in additional expansion costs** (at $2,000/shelf)

### 2. Multiplication Effect
Each supplier delay event affects:
- **1.66 SKUs** on average (multiple products per truckload)
- **32.6 trucks** on average (large consolidated shipments)
- Creates **compounding impact** across the supply chain

### 3. Non-Linear Risk Scaling
Storage requirements scale **super-linearly** with disruption severity:
- Low disruption (k=0.1): +58% capacity
- Moderate disruption (k=0.3): +95% capacity (2.6× higher than low)
- High disruption (k=0.5): +266% capacity (4.6× higher than low)

**Implication**: Small increases in supply chain volatility drive disproportionately large capacity needs.

### 4. International vs. Domestic Suppliers
- **Domestic suppliers** more sensitive to delays (lower base DOH)
  - Moderate scenario: 4 → 9 days (2.25× increase)
- **International suppliers** have higher baseline buffer
  - Moderate scenario: 14 → 19 days (1.36× increase)

### 5. Strategic Implications

#### Option A: Build Excess Capacity
- Expand to accommodate worst-case scenarios
- **Pros**: Service level protection
- **Cons**: High capital costs, underutilized space in normal conditions

#### Option B: Risk-Based Planning
- Size for moderate disruption scenario
- Accept occasional service failures in extreme events
- **Pros**: Balanced cost-risk tradeoff
- **Cons**: Requires contingency planning

#### Option C: Supply Chain Diversification
- Reduce delay correlation by using multiple suppliers per SKU
- Invest in supply chain visibility and expedited shipping options
- **Pros**: Reduces storage needs through operational flexibility
- **Cons**: Higher operational complexity

---

## Validation and Assumptions

### Model Assumptions
1. **Independence**: Delay events are independent across time (Poisson assumption)
2. **Memoryless**: Delay durations follow exponential distribution (memoryless property)
3. **Correlated SKUs**: All SKUs on a supplier's truck are delayed together
4. **Linear Scaling**: Storage requirements scale linearly with DOH
5. **Stationary Process**: Delay parameters (k, μ) remain constant over 10 years

### Limitations
1. **Does not model**:
   - Seasonal variation in delay frequency
   - Learning/adaptation over time
   - Expedited shipping responses
   - Demand variability (assumes deterministic demand)

2. **Simplifying assumptions**:
   - Average delay applied uniformly to domestic/international
   - Linear inventory-storage relationship
   - No truck capacity constraints modeled in response

### Model Validation
- **Statistical rigor**: 50 Monte Carlo simulations per scenario
- **Data-driven parameters**: Based on actual truckload schedule (28,778 events)
- **Sensitivity analysis**: Three scenarios spanning reasonable disruption levels

---

## Technical Details

### File Structure
```
model2.0/
├── phase2_STOCHASTIC_SUPPLIER_BASED_14_4_doh.py
│   └── Main stochastic simulation engine
├── estimate_stochastic_storage_impact.py
│   └── Storage requirement estimation
└── results/Phase2_DAILY/
    ├── stochastic_supplier_14_4_doh/
    │   ├── supplier_summary_k0.1_mu3.0.csv
    │   ├── supplier_summary_k0.3_mu5.0.csv
    │   ├── supplier_summary_k0.5_mu14.0.csv
    │   └── supplier_mc_results_*.csv (50 simulation runs)
    └── stochastic_storage_impact_estimates.csv
```

### Key Output Files

#### 1. Supplier Summary (`supplier_summary_k{k}_mu{mu}.csv`)
Contains aggregate statistics:
- Scenario parameters (k, μ)
- Average delay events, trucks affected, truck-days delay
- SKU multiplication effect
- Domestic vs. international event counts

#### 2. Monte Carlo Results (`supplier_mc_results_k{k}_mu{mu}.csv`)
Contains 50 simulation runs with:
- Per-simulation delay events, trucks affected
- Storage requirements (if optimization run)
- Statistical distribution of outcomes

#### 3. Storage Impact Estimates (`stochastic_storage_impact_estimates.csv`)
Contains final capacity recommendations:
- Effective DOH by supplier type
- Additional shelves needed
- Facility-level breakdown (Sacramento/Austin)
- Percent increase over baseline

---

## Recommendations

### For Presentation
1. **Lead with the headline**: "Supply chain uncertainty requires 95% more warehouse capacity"
2. **Visualize the multiplication effect**: Show how one supplier delay affects 32.6 trucks
3. **Compare scenarios**: Side-by-side baseline vs. moderate disruption
4. **Quantify the cost**: Additional shelves × cost per shelf = total capital impact
5. **Discuss risk tolerance**: Which scenario should we design for?

### For Implementation
1. **Adopt moderate disruption scenario** (k=0.3, μ=5) as planning baseline
2. **Phase expansion**: Build initial capacity for low disruption, option for future expansion
3. **Invest in supply chain visibility**: Real-time tracking reduces uncertainty
4. **Develop contingency protocols**: Expedited shipping, alternative suppliers
5. **Monitor and update**: Recalibrate k and μ based on actual delay data

---

## References

### Key Equations
- Poisson Distribution: P(X = k) = (λ^k × e^(-λ)) / k!
- Exponential Distribution: f(x; μ) = (1/μ) × e^(-x/μ)
- Storage Scaling: New_Shelves = Base_Shelves × (Effective_DOH / Base_DOH)

### Data Sources
- Truckload Schedule: `truckload_analysis_3_1_doh.csv` (28,778 events, 937,536 trucks)
- Baseline Storage: 3,994 shelves (Sacramento: 2,884, Austin: 1,110)
- Supplier Types: 5 suppliers (3 domestic, 2 international)

### Model Parameters
- Planning Horizon: 120 months (10 years, 2026-2035)
- Business Days: 21 days per month
- Base DOH: 4 days (domestic), 14 days (international)
- Monte Carlo Simulations: 50 runs per scenario

---

## Appendix: Mathematical Derivations

### Expected Number of Delay Events
For a Poisson process with rate λ:
```
E[Events per month] = λ = k × deliveries_per_month

E[Events over 10 years] = λ × 120 months
```

### Expected Truck-Days Delay
```
E[Truck-Days] = E[Events] × E[Trucks per Event] × E[Delay Duration]

Where:
  E[Events] = λ × 120
  E[Trucks per Event] = 32.6 (empirical average)
  E[Delay Duration] = μ (exponential mean)

Therefore:
  E[Truck-Days] = (k × deliveries_per_month × 120) × 32.6 × μ
```

### Storage Requirement Formula
```
Required Inventory = Daily Demand × DOH

For mixed supplier types:
  Total Inventory = Σ (SKU_i Inventory)

  = Σ (Daily_Demand_i × DOH_i)

  = Σ_domestic (Demand_i × DOH_domestic) +
    Σ_international (Demand_i × DOH_international)

Storage Multiplier:
  M = (Σ_domestic (Demand_i × New_DOH_dom) + Σ_intl (Demand_i × New_DOH_intl)) /
      (Σ_domestic (Demand_i × Base_DOH_dom) + Σ_intl (Demand_i × Base_DOH_intl))

Simplified (assuming proportional demand):
  M ≈ (0.667 × DOH_dom_multiplier) + (0.333 × DOH_intl_multiplier)
```

---

**Document Version**: 1.0
**Date**: November 2025
**Analysis Period**: 2026-2035 (10 years)
**Model Type**: Supplier-Level Stochastic Delay with Monte Carlo Simulation
