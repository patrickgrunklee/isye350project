"""
CUMULATIVE INVENTORY SIMULATION V2 - WITH SHIP-IMMEDIATELY POLICY

Demonstrates how delayed deliveries ACCUMULATE in the warehouse, creating inventory spikes
that require more physical shelf space than traditional "effective DOH" calculations suggest.

Key Innovation:
- Delayed trucks don't increase DOH - they arrive LATER and pile up
- Multiple delayed deliveries arriving simultaneously = inventory spike
- Peak concurrent inventory drives actual shelf requirements
- **NEW**: Ship-immediately policy - DOH based on SCHEDULED arrival, not actual arrival

Ship-Immediately Policy:
- Each delivery has scheduled_day and actual_arrival_day
- Ship-by date = scheduled_day + DOH (based on ORIGINAL schedule)
- If actual_arrival_day >= ship_by_date: ship immediately (no additional holding)
- Otherwise: hold for remaining DOH days
- This minimizes inventory by not penalizing delays with extra holding time

Example: Delivery scheduled day 5, DOH=4, arrives day 9 (4 days late)
- Ship-by date = 5 + 4 = day 9
- Arrives day 9 → Ship immediately (not hold until day 13)

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
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / "stochastic_supplier_14_4_doh"
OUTPUT_DIR = RESULTS_DIR / "cumulative_inventory_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Constants
MONTHS = 120
DAYS_PER_MONTH = 21
TOTAL_DAYS = MONTHS * DAYS_PER_MONTH  # 2,520 business days
BASE_DOH = 4  # Base days-on-hand for shipment scheduling


def simulate_single_sku_inventory(monthly_demand, delay_events_df, sku_name="Example SKU"):
    """
    Simulate inventory trajectory for a single SKU with delivery delays.

    Implements SHIP-IMMEDIATELY POLICY:
    - DOH-based shipment schedule based on SCHEDULED arrival (not actual)
    - If goods arrive late (after ship-by date), ship immediately
    - Minimizes inventory by not penalizing delays with extra holding time

    Args:
        monthly_demand: List of monthly demand values (120 months)
        delay_events_df: DataFrame with delay events (Month, Day, Delay_Duration_Days)
        sku_name: Name of SKU for reporting

    Returns:
        dict with inventory trajectory and peak values
    """
    print(f"\n  Simulating {sku_name}...")

    # Initialize delivery schedule (baseline: deliver monthly demand at start of month)
    delivery_schedule = []  # List of {scheduled_day, quantity, actual_arrival_day, ship_by_date}

    for month in range(MONTHS):
        scheduled_day = month * DAYS_PER_MONTH + 1  # First day of each month
        quantity = monthly_demand[month]

        # Check if this delivery is delayed
        delay = 0

        if delay_events_df is not None and len(delay_events_df) > 0:
            # Convert day to (month, day)
            month_num = (scheduled_day - 1) // DAYS_PER_MONTH + 1
            day_in_month = (scheduled_day - 1) % DAYS_PER_MONTH + 1

            # Find matching delay event
            matching = delay_events_df[
                (delay_events_df['Month'] == month_num) &
                (delay_events_df['Day'] == day_in_month)
            ]

            if len(matching) > 0:
                delay = matching.iloc[0]['Delay_Duration_Days']

        # Calculate actual arrival and ship-by date
        actual_arrival_day = int(scheduled_day + delay)
        ship_by_date = scheduled_day + BASE_DOH  # Based on SCHEDULED arrival, not actual

        if actual_arrival_day <= TOTAL_DAYS:
            delivery_schedule.append({
                'scheduled_day': scheduled_day,
                'actual_arrival_day': actual_arrival_day,
                'ship_by_date': ship_by_date,
                'quantity': quantity,
                'delay': delay
            })

    # Build actual delivery and shipment schedules
    actual_deliveries = {}  # {day: quantity arriving}
    scheduled_shipments = {}  # {day: quantity to ship}

    num_delayed = 0
    total_delay_days = 0
    num_shipped_immediately = 0

    for delivery in delivery_schedule:
        arrival_day = delivery['actual_arrival_day']
        ship_by = delivery['ship_by_date']
        quantity = delivery['quantity']
        delay = delivery['delay']

        # Track arrivals
        if arrival_day not in actual_deliveries:
            actual_deliveries[arrival_day] = 0
        actual_deliveries[arrival_day] += quantity

        if delay > 0:
            num_delayed += 1
            total_delay_days += delay

        # Determine shipment schedule
        if arrival_day >= ship_by:
            # Ship immediately - goods arrive on/after ship-by date
            ship_day = arrival_day
            num_shipped_immediately += 1
        else:
            # Ship on scheduled ship-by date
            ship_day = ship_by

        # Add to shipment schedule
        if ship_day <= TOTAL_DAYS:
            if ship_day not in scheduled_shipments:
                scheduled_shipments[ship_day] = 0
            scheduled_shipments[ship_day] += quantity

    # Simulate daily inventory
    inventory_trajectory = []
    current_inventory = 0
    peak_inventory = 0
    days_above_baseline = 0
    total_shipments = 0

    for day in range(1, TOTAL_DAYS + 1):
        # Add incoming deliveries
        incoming = actual_deliveries.get(day, 0)

        # Subtract scheduled shipments
        outgoing = scheduled_shipments.get(day, 0)

        # Update inventory
        current_inventory = max(0, current_inventory + incoming - outgoing)
        total_shipments += outgoing

        # Track peak
        if current_inventory > peak_inventory:
            peak_inventory = current_inventory

        # Track how often inventory exceeds baseline
        baseline_inventory = monthly_demand[min((day - 1) // DAYS_PER_MONTH, len(monthly_demand) - 1)]
        if current_inventory > baseline_inventory * 1.5:  # 50% above baseline
            days_above_baseline += 1

        inventory_trajectory.append({
            'day': day,
            'inventory': current_inventory,
            'incoming': incoming,
            'outgoing': outgoing
        })

    avg_inventory = np.mean([d['inventory'] for d in inventory_trajectory])

    # Verification
    total_incoming = sum(actual_deliveries.values())
    shipment_verification = abs(total_shipments - total_incoming) < 0.01

    results = {
        'sku': sku_name,
        'peak_inventory': peak_inventory,
        'avg_inventory': avg_inventory,
        'peak_to_avg_ratio': peak_inventory / avg_inventory if avg_inventory > 0 else 0,
        'num_delayed_deliveries': num_delayed,
        'num_shipped_immediately': num_shipped_immediately,
        'total_delay_days': total_delay_days,
        'days_above_baseline': days_above_baseline,
        'pct_days_above_baseline': (days_above_baseline / TOTAL_DAYS) * 100,
        'trajectory': inventory_trajectory,
        'shipment_balance_ok': shipment_verification
    }

    print(f"    Peak inventory: {peak_inventory:,.0f} units")
    print(f"    Avg inventory: {avg_inventory:,.0f} units")
    print(f"    Peak/Avg ratio: {results['peak_to_avg_ratio']:.2f}x")
    print(f"    Delayed deliveries: {num_delayed}/{len(delivery_schedule)}")
    print(f"    Shipped immediately: {num_shipped_immediately}/{len(delivery_schedule)}")

    return results


def run_monte_carlo_scenario(k_factor, mean_delay, description):
    """
    Run cumulative inventory simulation across all Monte Carlo runs.

    Args:
        k_factor: Poisson parameter
        mean_delay: Mean delay duration (days)
        description: Scenario description

    Returns:
        DataFrame with aggregated results
    """
    print(f"\n{'#'*100}")
    print(f"SCENARIO: {description}")
    print(f"  k={k_factor}, mu={mean_delay} days")
    print(f"{'#'*100}")

    # Load demand data (use aggregate across all SKUs for simplicity)
    demand_file = DATA_DIR / "Demand Details.csv"
    demand_df = pd.read_csv(demand_file)

    # Get total demand across all SKUs per month
    sku_cols = [col for col in demand_df.columns if col.startswith('SKU')]
    demand_df['Total_Demand'] = demand_df[sku_cols].sum(axis=1)
    monthly_demand = demand_df['Total_Demand'].tolist()

    print(f"\nLoaded demand data:")
    print(f"  Months: {len(monthly_demand)}")
    print(f"  Total demand: {sum(monthly_demand):,.0f} units")
    print(f"  Monthly average: {np.mean(monthly_demand):,.0f} units")

    # Run simulation for all 50 Monte Carlo runs
    all_sim_results = []

    for sim in range(1, 51):
        # Load delay events for this simulation
        delay_file = STOCHASTIC_RESULTS_DIR / f"supplier_delays_k{k_factor}_mu{mean_delay}_sim_{sim}.csv"

        if not delay_file.exists():
            print(f"  WARNING: Delay file not found for simulation {sim}")
            delay_events = None
        else:
            delay_events = pd.read_csv(delay_file)

        # Run simulation
        sim_results = simulate_single_sku_inventory(
            monthly_demand,
            delay_events,
            sku_name=f"TotalInventory_Sim{sim}"
        )

        sim_results['simulation'] = sim
        sim_results['k_factor'] = k_factor
        sim_results['mean_delay'] = mean_delay
        sim_results['scenario'] = description

        all_sim_results.append(sim_results)

        if sim % 10 == 0:
            print(f"\n  Completed {sim}/50 simulations")

    # Aggregate results
    results_df = pd.DataFrame([
        {k: v for k, v in r.items() if k != 'trajectory'}
        for r in all_sim_results
    ])

    # Calculate statistics
    print(f"\n{'='*100}")
    print(f"CUMULATIVE INVENTORY IMPACT - {description}")
    print(f"{'='*100}")

    print(f"\nPeak Inventory Distribution:")
    print(f"  50th percentile: {results_df['peak_inventory'].quantile(0.50):,.0f} units")
    print(f"  95th percentile: {results_df['peak_inventory'].quantile(0.95):,.0f} units")
    print(f"  99th percentile: {results_df['peak_inventory'].quantile(0.99):,.0f} units")
    print(f"  Maximum: {results_df['peak_inventory'].max():,.0f} units")

    print(f"\nPeak/Average Inventory Ratio:")
    print(f"  Mean: {results_df['peak_to_avg_ratio'].mean():.2f}x")
    print(f"  95th percentile: {results_df['peak_to_avg_ratio'].quantile(0.95):.2f}x")

    print(f"\nInventory Spikes:")
    print(f"  Avg days above baseline (50%+): {results_df['pct_days_above_baseline'].mean():.1f}%")

    # Calculate capacity requirements
    baseline_avg_inventory = results_df['avg_inventory'].mean()
    peak_p95 = results_df['peak_inventory'].quantile(0.95)
    capacity_multiplier = peak_p95 / baseline_avg_inventory if baseline_avg_inventory > 0 else 0

    print(f"\nCapacity Requirements:")
    print(f"  Baseline avg inventory: {baseline_avg_inventory:,.0f} units")
    print(f"  Peak inventory (95th pct): {peak_p95:,.0f} units")
    print(f"  Capacity multiplier: {capacity_multiplier:.2f}x")
    print(f"  => Need {capacity_multiplier:.1f}x MORE shelf space than average inventory suggests!")

    return results_df


def main():
    """Main execution."""

    print("="*100)
    print("CUMULATIVE INVENTORY SIMULATION - WITH SHIP-IMMEDIATELY POLICY")
    print("="*100)
    print("\nDemonstrating how delayed deliveries ACCUMULATE and create inventory spikes")
    print("that require more physical space than traditional DOH calculations suggest.")
    print(f"\nSHIP-IMMEDIATELY POLICY (DOH={BASE_DOH} days):")
    print("  - Ship-by date based on SCHEDULED arrival, not actual arrival")
    print("  - If goods arrive late (after ship-by date), ship immediately")
    print("  - Minimizes inventory by not penalizing delays with extra holding time")
    print("  - Example: Scheduled day 5, DOH=4 => Ship by day 9")
    print("             If arrives day 9 (4 days late) => Ship immediately")

    # Define scenarios
    scenarios = [
        (0.1, 3.0, 'Low Disruption'),
        (0.3, 5.0, 'Moderate Disruption'),
        (0.5, 14.0, 'High Disruption'),
    ]

    all_results = []

    for k_factor, mean_delay, description in scenarios:
        results = run_monte_carlo_scenario(k_factor, mean_delay, description)
        if results is not None:
            all_results.append(results)

    if not all_results:
        print("\nERROR: No results generated")
        return

    # Combine and save
    combined_df = pd.concat(all_results, ignore_index=True)
    output_file = OUTPUT_DIR / "cumulative_inventory_impact_ship_immediately.csv"
    combined_df.to_csv(output_file, index=False)

    print(f"\n{'='*100}")
    print(f"ANALYSIS COMPLETE - SHIP-IMMEDIATELY POLICY")
    print(f"{'='*100}")
    print(f"\nResults saved to: {output_file}")

    # Final comparison
    print(f"\n{'='*100}")
    print(f"CAPACITY MULTIPLIER COMPARISON (95th Percentile)")
    print(f"{'='*100}")

    for scenario_name in ['Low Disruption', 'Moderate Disruption', 'High Disruption']:
        scenario_data = combined_df[combined_df['scenario'] == scenario_name]

        baseline_avg = scenario_data['avg_inventory'].mean()
        peak_p95 = scenario_data['peak_inventory'].quantile(0.95)
        multiplier = peak_p95 / baseline_avg if baseline_avg > 0 else 0
        pct_shipped_immediately = (scenario_data['num_shipped_immediately'].mean() / 120) * 100

        print(f"\n{scenario_name}:")
        print(f"  Avg inventory: {baseline_avg:,.0f} units")
        print(f"  Peak inventory (95th): {peak_p95:,.0f} units")
        print(f"  Capacity multiplier: {multiplier:.2f}x")
        print(f"  Avg % shipped immediately: {pct_shipped_immediately:.1f}%")

    print(f"\n{'='*100}")
    print(f"KEY INSIGHT - SHIP-IMMEDIATELY POLICY:")
    print(f"  DOH based on SCHEDULED arrival (not actual) minimizes inventory buildup.")
    print(f"  Delayed goods ship immediately when they arrive past their ship-by date.")
    print(f"  This reduces peak inventory spikes compared to traditional DOH approach.")
    print(f"  Peak inventory is still higher than average due to concurrent delayed arrivals,")
    print(f"  but the ship-immediately policy prevents double-penalization of delays.")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
