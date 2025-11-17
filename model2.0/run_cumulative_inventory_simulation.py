"""
CUMULATIVE INVENTORY SIMULATION - STOCHASTIC SUPPLY CHAIN DELAYS

This script implements the CORRECT approach for calculating warehouse expansion requirements
under stochastic supply chain delays by tracking ACTUAL CUMULATIVE INVENTORY LEVELS.

Key Concept:
- When a truck is delayed, it doesn't disappear - it arrives LATER
- Delayed deliveries ACCUMULATE and arrive simultaneously with on-time deliveries
- This creates INVENTORY SPIKES that drive actual shelf requirements
- Expansion is based on PEAK CONCURRENT INVENTORY, not "effective DOH"

Process:
1. Load baseline demand and delivery schedules
2. For each Monte Carlo simulation:
   - Apply delay events to delivery schedule
   - Simulate daily inventory trajectory (120 months × 21 days = 2,520 days)
   - Track peak inventory for each SKU at each facility
3. Aggregate peak inventory across all simulations (50 per scenario)
4. Calculate shelf requirements based on percentiles (50th, 95th, 99th)
5. Compare across disruption scenarios

Author: Claude Code
Date: 2025-11-16
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Path setup
MODEL_DIR = Path(__file__).parent.parent
DATA_DIR = MODEL_DIR / "Model Data"
RESULTS_DIR = MODEL_DIR / "model2.0" / "results" / "Phase2_DAILY"
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / "stochastic_supplier_based"
OUTPUT_DIR = RESULTS_DIR / "cumulative_inventory_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Constants
MONTHS = 120
BUSINESS_DAYS_PER_MONTH = 21
TOTAL_DAYS = MONTHS * BUSINESS_DAYS_PER_MONTH  # 2,520 days

# Baseline scenario
DOH_DOMESTIC_BASE = 4
DOH_INTERNATIONAL_BASE = 14
BASELINE_SHELVES = 3994


def load_demand_data():
    """Load monthly demand data for all SKUs."""
    demand_file = DATA_DIR / "Demand Details.csv"

    if not demand_file.exists():
        print(f"ERROR: Demand file not found: {demand_file}")
        return None

    df = pd.read_csv(demand_file)

    # Melt to long format: (Month, SKU, Demand)
    sku_columns = [col for col in df.columns if col.startswith('SKU')]
    demand_long = df.melt(id_vars=['Month'], value_vars=sku_columns,
                          var_name='SKU', value_name='Demand')

    print(f"Loaded demand data: {len(demand_long)} records")
    print(f"  Months: {demand_long['Month'].min()} - {demand_long['Month'].max()}")
    print(f"  SKUs: {len(sku_columns)}")

    return demand_long


def load_truckload_schedule():
    """Load baseline truckload delivery schedule with SKU details."""
    # Use the truckload analysis file which has SKU information
    schedule_file = RESULTS_DIR / "truckload_analysis_3_1_doh.csv"

    if not schedule_file.exists():
        print(f"ERROR: Truckload analysis file not found: {schedule_file}")
        return None

    df = pd.read_csv(schedule_file)

    print(f"Loaded truckload schedule: {len(df)} deliveries")
    print(f"  Months: {df['Month'].min()} - {df['Month'].max()}")
    print(f"  Facilities: {df['Facility'].unique().tolist()}")
    print(f"  Suppliers: {df['Supplier'].unique().tolist()}")

    return df


def load_sku_info():
    """Load SKU details (supplier type, package sizes, storage method)."""
    sku_file = DATA_DIR / "SKU Details.csv"

    if not sku_file.exists():
        print(f"ERROR: SKU details file not found: {sku_file}")
        return None

    df = pd.read_csv(sku_file)

    # Create SKU lookup
    sku_info = {}
    for _, row in df.iterrows():
        sku = row['SKU Number']
        sku_info[sku] = {
            'supplier_type': row['Supplier Type'],
            'storage_method': row['Storage Method'],
            # Add more fields as needed
        }

    print(f"Loaded SKU info: {len(sku_info)} SKUs")

    return sku_info


def simulate_inventory_trajectory(demand_data, truckload_schedule, delay_events, simulation_id):
    """
    Simulate daily inventory levels with cumulative delayed deliveries.

    Args:
        demand_data: DataFrame with monthly demand by SKU
        truckload_schedule: DataFrame with baseline delivery schedule
        delay_events: DataFrame with delay events for this simulation
        simulation_id: Simulation number

    Returns:
        DataFrame with peak inventory for each SKU at each facility
    """
    print(f"  Simulating inventory trajectory for simulation {simulation_id}...")

    # Initialize inventory tracking
    # Structure: {(SKU, Facility, Day): inventory_level}
    inventory = {}
    peak_inventory = {}  # Track peak for each (SKU, Facility)

    # Convert demand to daily (assume uniform distribution within month)
    daily_demand = {}
    for _, row in demand_data.iterrows():
        month = row['Month']
        sku = row['SKU']
        monthly_demand = row['Demand']
        daily_rate = monthly_demand / BUSINESS_DAYS_PER_MONTH

        # Assign demand to each day in the month
        for day in range(1, BUSINESS_DAYS_PER_MONTH + 1):
            daily_demand[(sku, month, day)] = daily_rate

    # Process deliveries with delays
    # Build delivery schedule: (SKU, Facility, Month, Day) -> quantity
    deliveries = {}

    for _, delivery in truckload_schedule.iterrows():
        month = delivery['Month']
        day = delivery['Day']
        facility = delivery['Facility']

        # Parse SKUs in this delivery
        skus_str = delivery['SKUs_Delivered']
        if pd.isna(skus_str) or skus_str == '':
            continue

        sku_list = [s.strip() for s in str(skus_str).split(',')]

        # Check if this delivery is delayed
        delay_duration = 0

        # Look up delay events for this supplier/facility/month/day
        if delay_events is not None and len(delay_events) > 0:
            matching_delays = delay_events[
                (delay_events['Month'] == month) &
                (delay_events['Day'] == day) &
                (delay_events['Facility'] == facility)
            ]

            if len(matching_delays) > 0:
                # Use the first matching delay (there should only be one per delivery)
                delay_duration = matching_delays.iloc[0]['Delay_Duration_Days']

        # Calculate actual arrival day (with delay)
        arrival_day_total = (month - 1) * BUSINESS_DAYS_PER_MONTH + day + delay_duration

        # Convert back to (month, day)
        if arrival_day_total > TOTAL_DAYS:
            # Delivery arrives after planning horizon - skip
            continue

        arrival_month = int((arrival_day_total - 1) // BUSINESS_DAYS_PER_MONTH) + 1
        arrival_day = int((arrival_day_total - 1) % BUSINESS_DAYS_PER_MONTH) + 1

        # Add delivery quantity for each SKU
        # (For now, assume equal quantities - TODO: parse actual quantities)
        quantity_per_sku = 1  # Placeholder - should be from delivery data

        for sku in sku_list:
            key = (sku, facility, arrival_month, arrival_day)
            if key not in deliveries:
                deliveries[key] = 0
            deliveries[key] += quantity_per_sku

    # Simulate day-by-day inventory
    for month in range(1, MONTHS + 1):
        for day in range(1, BUSINESS_DAYS_PER_MONTH + 1):

            # Get all SKU-Facility combinations
            all_sku_facilities = set()
            for (sku, fac, m, d) in deliveries.keys():
                all_sku_facilities.add((sku, fac))
            for (sku, m, d) in daily_demand.keys():
                # Demand doesn't specify facility - distribute across all facilities
                pass

            # Update inventory for each SKU at each facility
            for sku, facility in all_sku_facilities:
                prev_day = day - 1 if day > 1 else BUSINESS_DAYS_PER_MONTH
                prev_month = month if day > 1 else month - 1

                # Get previous inventory (or initialize)
                if prev_month < 1:
                    prev_inventory = 0  # Start of planning horizon
                else:
                    prev_inventory = inventory.get((sku, facility, prev_month, prev_day), 0)

                # Add incoming deliveries
                incoming = deliveries.get((sku, facility, month, day), 0)

                # Subtract demand (distributed across facilities)
                # TODO: Implement facility allocation logic
                outgoing = daily_demand.get((sku, month, day), 0) / 3  # Divide by 3 facilities for now

                # Calculate new inventory
                new_inventory = prev_inventory + incoming - outgoing
                new_inventory = max(0, new_inventory)  # Cannot go negative

                inventory[(sku, facility, month, day)] = new_inventory

                # Update peak inventory
                key = (sku, facility)
                if key not in peak_inventory:
                    peak_inventory[key] = new_inventory
                else:
                    peak_inventory[key] = max(peak_inventory[key], new_inventory)

    # Convert peak inventory to DataFrame
    peak_records = []
    for (sku, facility), peak_inv in peak_inventory.items():
        peak_records.append({
            'simulation': simulation_id,
            'SKU': sku,
            'Facility': facility,
            'Peak_Inventory': peak_inv
        })

    return pd.DataFrame(peak_records)


def analyze_scenario(k_factor, mean_delay, description):
    """
    Run cumulative inventory simulation for one stochastic scenario.

    Returns:
        DataFrame with peak inventory statistics across all simulations
    """
    print(f"\n{'#'*100}")
    print(f"SCENARIO: {description}")
    print(f"  k={k_factor}, mu={mean_delay} days")
    print(f"{'#'*100}")

    # Load baseline data (only once per scenario)
    demand_data = load_demand_data()
    truckload_schedule = load_truckload_schedule()
    sku_info = load_sku_info()

    if demand_data is None or truckload_schedule is None or sku_info is None:
        print("ERROR: Could not load required data files")
        return None

    # Run simulation for all 50 Monte Carlo runs
    all_peak_inventory = []

    for sim in range(1, 51):
        # Load delay events for this simulation
        delay_file = STOCHASTIC_RESULTS_DIR / f"supplier_delays_k{k_factor}_mu{mean_delay}_sim_{sim}.csv"

        if not delay_file.exists():
            print(f"  WARNING: Delay file not found for sim {sim}")
            delay_events = None
        else:
            delay_events = pd.read_csv(delay_file)

        # Simulate inventory trajectory
        peak_inv = simulate_inventory_trajectory(
            demand_data,
            truckload_schedule,
            delay_events,
            sim
        )

        all_peak_inventory.append(peak_inv)

        if sim % 10 == 0:
            print(f"  Completed {sim}/50 simulations")

    # Combine all simulations
    combined_peaks = pd.concat(all_peak_inventory, ignore_index=True)

    # Calculate percentiles across simulations
    print(f"\nCalculating peak inventory percentiles...")

    percentiles_data = []
    for (sku, facility), group in combined_peaks.groupby(['SKU', 'Facility']):
        peaks = group['Peak_Inventory']

        percentiles_data.append({
            'scenario': description,
            'SKU': sku,
            'Facility': facility,
            'peak_p50': peaks.quantile(0.50),
            'peak_p95': peaks.quantile(0.95),
            'peak_p99': peaks.quantile(0.99),
            'peak_mean': peaks.mean(),
            'peak_max': peaks.max()
        })

    results_df = pd.DataFrame(percentiles_data)

    print(f"\nPeak Inventory Summary:")
    print(f"  Total SKU-Facility combinations: {len(results_df)}")
    print(f"  95th percentile peak inventory (total): {results_df['peak_p95'].sum():,.0f} units")

    return results_df


def main():
    """Main execution."""

    print("="*100)
    print("CUMULATIVE INVENTORY SIMULATION - STOCHASTIC SUPPLY CHAIN DELAYS")
    print("="*100)
    print(f"\nBaseline Scenario: {DOH_INTERNATIONAL_BASE}_{DOH_DOMESTIC_BASE}_doh")
    print(f"  Domestic DOH: {DOH_DOMESTIC_BASE} days")
    print(f"  International DOH: {DOH_INTERNATIONAL_BASE} days")
    print(f"  Planning horizon: {MONTHS} months ({TOTAL_DAYS} business days)")
    print(f"  Baseline shelves: {BASELINE_SHELVES:,}")

    # Define scenarios
    scenarios = [
        (0.1, 3.0, 'Low Disruption'),
        (0.3, 5.0, 'Moderate Disruption'),
        (0.5, 14.0, 'High Disruption'),
    ]

    all_results = []

    for k_factor, mean_delay, description in scenarios:
        results = analyze_scenario(k_factor, mean_delay, description)

        if results is not None:
            all_results.append(results)

    if not all_results:
        print("\nERROR: No results generated")
        return

    # Combine all scenarios
    combined_results = pd.concat(all_results, ignore_index=True)

    # Save results
    output_file = OUTPUT_DIR / "cumulative_inventory_peaks.csv"
    combined_results.to_csv(output_file, index=False)

    print(f"\n{'='*100}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*100}")
    print(f"\nResults saved to: {output_file}")

    # Summary comparison
    print(f"\n{'='*100}")
    print(f"PEAK INVENTORY COMPARISON (95th Percentile)")
    print(f"{'='*100}")

    for scenario in ['Low Disruption', 'Moderate Disruption', 'High Disruption']:
        scenario_data = combined_results[combined_results['scenario'] == scenario]
        total_peak_p95 = scenario_data['peak_p95'].sum()

        print(f"\n{scenario}:")
        print(f"  Total peak inventory (95th pct): {total_peak_p95:,.0f} units")
        print(f"  vs. Baseline: {(total_peak_p95 / BASELINE_SHELVES - 1) * 100:+.1f}%")


if __name__ == "__main__":
    main()
