# MONTH 1 (January 2026) - DETAILED OPERATIONAL ANALYSIS

## EXECUTIVE SUMMARY

**All demand was fulfilled at 100% for all 18 SKUs in Month 1.**

Total operations:
- **Total Demand**: 511,059 sell packs across all SKUs
- **Total Shipped**: 511,059 sell packs (100% fulfillment)
- **Total Deliveries**: 180,599 inbound packs received
- **Delivery Events**: 137 individual delivery transactions across 3 facilities

---

## DEMAND FULFILLMENT BY SKU

| SKU | Supplier | Demand | Shipped | Fulfillment | Deliveries (Inbound Packs) |
|-----|----------|--------|---------|-------------|----------------------------|
| SKUW1 | International | 21,440 | 21,440 | 100.0% | 149 |
| SKUW2 | International | 28,159 | 28,159 | 100.0% | 235 |
| SKUW3 | International | 27,136 | 27,136 | 100.0% | 226 |
| SKUA1 | Domestic | 12,495 | 12,495 | 100.0% | 833 |
| SKUA2 | Domestic | 15,406 | 15,406 | 100.0% | 440 |
| SKUA3 | Domestic | 31,657 | 31,657 | 100.0% | 317 |
| SKUT1 | Domestic | 22,821 | 22,821 | 100.0% | 7,607 |
| SKUT2 | Domestic | 37,530 | 37,530 | 100.0% | 586 |
| SKUT3 | Domestic | 20,175 | 20,175 | 100.0% | 315 |
| SKUT4 | Domestic | 18,741 | 18,741 | 100.0% | 6,247 |
| SKUD1 | Domestic | 41,374 | 41,374 | 100.0% | 41,374 |
| SKUD2 | Domestic | 29,450 | 29,450 | 100.0% | 29,450 |
| SKUD3 | Domestic | 39,063 | 39,063 | 100.0% | 39,063 |
| SKUC1 | Domestic | 50,731 | 50,731 | 100.0% | 50,731 |
| SKUC2 | Domestic | 40,169 | 40,169 | 100.0% | 1,674 |
| SKUE1 | International | 31,574 | 31,574 | 100.0% | 316 |
| SKUE2 | International | 38,560 | 38,560 | 100.0% | 645 |
| SKUE3 | International | 4,578 | 4,578 | 100.0% | 391 |

**Key Insights:**
- Desks (SKUD1-3) and Chairs (SKUC1-2) require 1:1 inbound-to-sell pack ratio (cannot be consolidated)
- Writing utensils (SKUW1-3) have efficient consolidation: 149 inbound packs → 21,440 sell packs
- Electronics (SKUE1-3) also benefit from consolidation: 316 inbound packs → 31,574 sell packs

---

## FACILITY OPERATIONS - MONTH 1

### Columbus (Non-expandable facility)

**Operational Metrics:**
- **Deliveries**: 94,897 inbound packs
- **Delivery Events**: 46 transactions (avg 2,063 packs/event)
- **Shipments**: 218,605 sell packs (42.8% of total demand)
- **Peak Daily Inventory**: 38,584 sell packs
- **End-of-Month Inventory**: 4,808 sell packs

**Key Observations:**
- Columbus handled the largest share of shipments despite being non-expandable
- High inventory throughput with relatively low end-of-month inventory
- 46 delivery events across 21 days = ~2.2 deliveries/day on average

---

### Sacramento (Expandable facility)

**Operational Metrics:**
- **Deliveries**: 85,250 inbound packs
- **Delivery Events**: 49 transactions (avg 1,740 packs/event)
- **Shipments**: 239,463 sell packs (46.8% of total demand)
- **Peak Daily Inventory**: 124 sell packs
- **End-of-Month Inventory**: 60 sell packs

**Key Observations:**
- Sacramento handled the HIGHEST share of shipments (46.8%)
- Very low inventory levels (peak 124 packs) - likely using just-in-time approach
- 49 delivery events = ~2.3 deliveries/day
- Model suggests Sacramento operates with minimal inventory buffer

---

### Austin (Expandable facility)

**Operational Metrics:**
- **Deliveries**: 452 inbound packs
- **Delivery Events**: 42 transactions (avg 11 packs/event)
- **Shipments**: 52,991 sell packs (10.4% of total demand)
- **Peak Daily Inventory**: 124 sell packs
- **End-of-Month Inventory**: 60 sell packs

**Key Observations:**
- Austin handled smallest share (10.4%) but still significant volume
- Very small delivery sizes (avg 11 packs/event) suggest specialized items
- Similar low-inventory strategy to Sacramento (peak 124 packs)
- 42 delivery events across 21 days = 2 deliveries/day

---

## SUPPLIER DELIVERY ANALYSIS

### Domestic Suppliers (12 SKUs)
- **Total Deliveries**: 180,037 inbound packs
- **SKUs**: SKUA1-3, SKUT1-4, SKUD1-3, SKUC1-2

**Constraint Check:**
- Maximum 1 truck per supplier per day per facility
- With 21 business days, max = 21 trucks per supplier per month per facility
- Model appears to be within constraint (need to check truck_slack data)

### International Suppliers (6 SKUs)
- **Total Deliveries**: 562 inbound packs
- **SKUs**: SKUW1-3, SKUE1-3

**Lead Time Considerations:**
- International lead times: 28-37 days
- Month 1 deliveries likely ordered well before simulation start
- Higher consolidation ratios help reduce delivery frequency

---

## INVENTORY MANAGEMENT

### End-of-Month Inventory Distribution

| Facility | End Inventory | Peak Inventory | Turnover |
|----------|--------------|----------------|----------|
| Columbus | 4,808 packs | 38,584 packs | 45.5x |
| Sacramento | 60 packs | 124 packs | 3,991x |
| Austin | 60 packs | 124 packs | 883x |

**Observations:**
- Sacramento and Austin operate with extremely lean inventory (60 packs EOH)
- Columbus maintains higher inventory levels (4,808 packs)
- Sacramento has highest turnover ratio, suggesting efficient operations

---

## CAPACITY UTILIZATION (To be analyzed with shelving data)

### Storage Types Used
The model tracks packages on shelves by storage type:
- **Bins**: Small items (writing utensils, art supplies)
- **Racking**: Medium items (textbooks)
- **Pallet**: Large/heavy items (desks, chairs, electronics)
- **Hazmat**: Hazardous materials (if any)

*Detailed capacity analysis requires parsing var_packages_on_shelf.csv*

---

## TRUCK DELIVERY COMPLIANCE

**Constraint**: Maximum 1 truck per supplier per day per facility

*Need to check var_truck_slack.csv to identify any violations*
- If truck_slack > 0, additional trucks were needed beyond the limit
- Model penalizes slack at $10,000 per extra truck per day

---

## DAY-BY-DAY ACTIVITY TIMELINE

*To be generated: Daily breakdown showing which SKUs were delivered/shipped each day*

This would show:
- Day 1: SKUW1, SKUA1, SKUD1, SKUC1 deliveries
- Day 2: SKUW2, SKUA3, SKUT1 deliveries
- etc.

---

## RECOMMENDATIONS

1. **Columbus Inventory**: Consider why Columbus maintains higher inventory (4,808 packs) vs other facilities (60 packs each)

2. **Austin Utilization**: Austin handles only 10.4% of demand - investigate if capacity is underutilized

3. **Delivery Patterns**: Review if ~2 deliveries/day per facility is optimal or if consolidation is possible

4. **Lead Times**: Verify international supplier lead times (28-37 days) are factored into ordering schedules

5. **Capacity Analysis**: Need to compare peak inventory (38,584 packs at Columbus) against current shelving capacity

---

**Generated from**: 3-month test run of full_daily_warehouse_model.py
**Data Source**: results/var_daily_*.csv files
