"""
STOCHASTIC OPTIMIZATION ANALYSIS - ACTUAL PHASE 2 MODEL
========================================================

This script runs the ACTUAL Phase 2 optimization model with stochastic delays
instead of using linear scaling approximations.

Process:
1. Load all 50 Monte Carlo simulation delay files
2. Calculate percentile-based effective DOH (50th, 95th, 99th)
3. Generate lead time files for each scenario
4. Run phase2_DAILY_parameterized.py (actual optimization)
5. Extract REAL expansion requirements from solver
6. Compare baseline vs. stochastic scenarios

This gives TRUE storage requirements accounting for:
- Volume/weight capacity constraints
- Facility allocation optimization
- Storage type breakdown (Bins, Racking, Pallet, Hazmat)
- Tiered pricing
- Maximum expansion limits
"""

import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DOH_DOMESTIC_BASE = 4
DOH_INTERNATIONAL_BASE = 14
BASELINE_SHELVES = 3994  # From 14_4_doh baseline run

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / "stochastic_supplier_14_4_doh"
OPTIMIZATION_RESULTS_DIR = RESULTS_DIR / "stochastic_optimization_analysis"
OPTIMIZATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print("STOCHASTIC OPTIMIZATION ANALYSIS - ACTUAL PHASE 2 MODEL")
print("="*100)
print(f"\nBaseline Scenario: 14_4_doh")
print(f"  Domestic DOH: {DOH_DOMESTIC_BASE} days")
print(f"  International DOH: {DOH_INTERNATIONAL_BASE} days")
print(f"  Baseline shelves: {BASELINE_SHELVES:,}")
print()

def load_all_simulation_delays(k_factor, mean_delay):
    """
    Load delay data from all 50 Monte Carlo simulations.

    Returns:
        DataFrame with all delay events across all simulations
    """
    print(f"\nLoading delay data from 50 simulations (k={k_factor}, mu={mean_delay})...")

    all_delays = []
    loaded_count = 0

    for sim in range(1, 51):
        delay_file = STOCHASTIC_RESULTS_DIR / f"supplier_delays_k{k_factor}_mu{mean_delay}_sim_{sim}.csv"
        if delay_file.exists():
            df = pd.read_csv(delay_file)
            df['simulation'] = sim
            all_delays.append(df)
            loaded_count += 1

    if not all_delays:
        print(f"ERROR: No simulation files found")
        return None

    combined_delays = pd.concat(all_delays, ignore_index=True)
    print(f"  Loaded {loaded_count} simulation files")
    print(f"  Total delay events: {len(combined_delays):,}")

    return combined_delays

def calculate_delay_percentiles(combined_delays):
    """
    Calculate delay duration percentiles across all simulations.

    Returns:
        Dictionary with percentile values
    """
    if combined_delays is None or len(combined_delays) == 0:
        return None

    delays = combined_delays['Delay_Duration_Days']

    percentiles = {
        'min': delays.min(),
        'p25': delays.quantile(0.25),
        'p50': delays.quantile(0.50),  # Median
        'mean': delays.mean(),
        'p75': delays.quantile(0.75),
        'p95': delays.quantile(0.95),  # 95% service level
        'p99': delays.quantile(0.99),  # 99% service level
        'max': delays.max()
    }

    print(f"\nDelay Duration Percentiles:")
    print(f"  Minimum: {percentiles['min']:.2f} days")
    print(f"  25th percentile: {percentiles['p25']:.2f} days")
    print(f"  50th percentile (median): {percentiles['p50']:.2f} days")
    print(f"  Mean: {percentiles['mean']:.2f} days")
    print(f"  75th percentile: {percentiles['p75']:.2f} days")
    print(f"  95th percentile: {percentiles['p95']:.2f} days")
    print(f"  99th percentile: {percentiles['p99']:.2f} days")
    print(f"  Maximum: {percentiles['max']:.2f} days")

    return percentiles

def calculate_truck_weighted_delay(combined_delays):
    """
    Calculate average delay weighted by number of trucks affected.

    Large delays affecting many trucks should have more impact.
    """
    if 'Trucks_Affected' not in combined_delays.columns:
        return combined_delays['Delay_Duration_Days'].mean()

    total_truck_days = (combined_delays['Trucks_Affected'] *
                       combined_delays['Delay_Duration_Days']).sum()
    total_trucks = combined_delays['Trucks_Affected'].sum()

    weighted_avg = total_truck_days / total_trucks if total_trucks > 0 else 0

    print(f"\nTruck-Weighted Delay:")
    print(f"  Total truck-days: {total_truck_days:,.0f}")
    print(f"  Total trucks affected: {total_trucks:,.0f}")
    print(f"  Weighted average delay: {weighted_avg:.2f} days")

    return weighted_avg

def generate_lead_time_file(doh_domestic, doh_international):
    """
    Generate lead time file for specified DOH values.

    Returns:
        Path to generated lead time file
    """
    # Load template
    template_file = DATA_DIR / "Lead TIme.csv"

    if not template_file.exists():
        print(f"ERROR: Template file not found: {template_file}")
        return None

    df = pd.read_csv(template_file)

    # Generate output filename with stochastic prefix to avoid conflicts with DOH matrix files
    output_file = DATA_DIR / f"Lead TIme_STOCHASTIC_{int(doh_international)}_{int(doh_domestic)}_business_days.csv"

    # Always regenerate to ensure correct DOH values (no caching)
    print(f"  Generating lead time file: {output_file.name}")

    # Modify DOH columns
    # Column names: 'Columbus - Days on Hand', 'Sacramento - Days on Hand', 'Austin Days on Hand'
    for idx, row in df.iterrows():
        supplier_type = row['Supplier Type']
        doh = doh_international if supplier_type == 'International' else doh_domestic

        # Update DOH columns for each facility (note different naming format for Austin)
        df.at[idx, 'Columbus - Days on Hand'] = doh
        df.at[idx, 'Sacramento - Days on Hand'] = doh
        df.at[idx, 'Austin Days on Hand'] = doh

    # Save
    df.to_csv(output_file, index=False)
    print(f"  Generated: {output_file}")

    return output_file

def run_phase2_optimization(doh_domestic, doh_international, scenario_name):
    """
    Run the actual Phase 2 optimization model with specified DOH values.

    Returns:
        Dictionary with optimization results
    """
    print(f"\n{'='*100}")
    print(f"Running Phase 2 Optimization: {scenario_name}")
    print(f"{'='*100}")
    print(f"  Domestic DOH: {doh_domestic:.2f} days")
    print(f"  International DOH: {doh_international:.2f} days")

    # Ensure lead time file exists
    lead_time_file = generate_lead_time_file(doh_domestic, doh_international)
    if lead_time_file is None:
        return None

    # Run optimization
    script_dir = Path(__file__).parent
    parameterized_script = script_dir / "phase2_DAILY_parameterized.py"

    if not parameterized_script.exists():
        print(f"ERROR: Script not found: {parameterized_script}")
        return None

    cmd = [
        'python',
        str(parameterized_script),
        '--doh_intl', str(int(doh_international)),
        '--doh_dom', str(int(doh_domestic)),
        '--scenario_name', scenario_name,
        '--max_time', '300'
    ]

    print(f"\nExecuting: {' '.join(cmd)}")
    print("Solving optimization model (this may take several minutes)...")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"\nERROR: Optimization failed (return code {result.returncode})")
        print(f"\nSTDERR:\n{result.stderr}")
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")
        return None

    print(f"Optimization completed in {elapsed:.1f} seconds")

    # Load results
    results_file = RESULTS_DIR / scenario_name / f"expansion_requirements_{scenario_name}.csv"

    if not results_file.exists():
        print(f"ERROR: Results file not found: {results_file}")
        return None

    results_df = pd.read_csv(results_file)

    # Extract key metrics
    sac_row = results_df[results_df['Facility'] == 'Sacramento']
    aus_row = results_df[results_df['Facility'] == 'Austin']
    tot_row = results_df[results_df['Facility'] == 'Total']

    optimization_results = {
        'scenario_name': scenario_name,
        'doh_domestic': doh_domestic,
        'doh_international': doh_international,

        # Sacramento
        'sacramento_shelves': sac_row['Expansion_Shelves'].iloc[0] if len(sac_row) > 0 else 0,

        # Austin
        'austin_shelves': aus_row['Expansion_Shelves'].iloc[0] if len(aus_row) > 0 else 0,

        # Total
        'total_shelves': tot_row['Expansion_Shelves'].iloc[0] if len(tot_row) > 0 else 0,

        'solve_time': elapsed
    }

    print(f"\nOptimization Results:")
    print(f"  Sacramento: {optimization_results['sacramento_shelves']:,.0f} shelves")
    print(f"  Austin: {optimization_results['austin_shelves']:,.0f} shelves")
    print(f"  Total: {optimization_results['total_shelves']:,.0f} shelves")

    return optimization_results

def analyze_scenario(k_factor, mean_delay, description):
    """
    Full analysis for one stochastic scenario.

    Returns:
        Dictionary with comprehensive results
    """
    print(f"\n{'#'*100}")
    print(f"SCENARIO: {description}")
    print(f"  k={k_factor}, mu={mean_delay} days")
    print(f"{'#'*100}")

    # Step 1: Load all 50 simulation delays
    combined_delays = load_all_simulation_delays(k_factor, mean_delay)

    if combined_delays is None:
        print(f"ERROR: Could not load delay data")
        return None

    # Step 2: Calculate percentiles
    percentiles = calculate_delay_percentiles(combined_delays)
    truck_weighted = calculate_truck_weighted_delay(combined_delays)

    # Step 3: Run optimization for different service levels
    results = {
        'scenario': description,
        'k_factor': k_factor,
        'mean_delay': mean_delay,
        'num_delay_events': len(combined_delays),

        # Delay statistics
        'delay_min': percentiles['min'],
        'delay_p25': percentiles['p25'],
        'delay_p50': percentiles['p50'],
        'delay_mean': percentiles['mean'],
        'delay_p75': percentiles['p75'],
        'delay_p95': percentiles['p95'],
        'delay_p99': percentiles['p99'],
        'delay_max': percentiles['max'],
        'delay_truck_weighted': truck_weighted
    }

    # Run optimization for 50th percentile (median)
    print(f"\n{'='*100}")
    print(f"OPTIMIZATION 1/3: 50th Percentile Service Level")
    print(f"{'='*100}")
    doh_dom_50 = DOH_DOMESTIC_BASE + percentiles['p50']
    doh_intl_50 = DOH_INTERNATIONAL_BASE + percentiles['p50']
    scenario_name_50 = f"stochastic_50pct_{description.lower().replace(' ', '_')}"

    opt_50 = run_phase2_optimization(doh_dom_50, doh_intl_50, scenario_name_50)

    if opt_50:
        results['doh_domestic_50pct'] = doh_dom_50
        results['doh_international_50pct'] = doh_intl_50
        results['shelves_50pct'] = opt_50['total_shelves']
        results['sacramento_shelves_50pct'] = opt_50['sacramento_shelves']
        results['austin_shelves_50pct'] = opt_50['austin_shelves']

    # Run optimization for 95th percentile (recommended)
    print(f"\n{'='*100}")
    print(f"OPTIMIZATION 2/3: 95th Percentile Service Level (RECOMMENDED)")
    print(f"{'='*100}")
    doh_dom_95 = DOH_DOMESTIC_BASE + percentiles['p95']
    doh_intl_95 = DOH_INTERNATIONAL_BASE + percentiles['p95']
    scenario_name_95 = f"stochastic_95pct_{description.lower().replace(' ', '_')}"

    opt_95 = run_phase2_optimization(doh_dom_95, doh_intl_95, scenario_name_95)

    if opt_95:
        results['doh_domestic_95pct'] = doh_dom_95
        results['doh_international_95pct'] = doh_intl_95
        results['shelves_95pct'] = opt_95['total_shelves']
        results['sacramento_shelves_95pct'] = opt_95['sacramento_shelves']
        results['austin_shelves_95pct'] = opt_95['austin_shelves']

    # Run optimization for 99th percentile (conservative)
    print(f"\n{'='*100}")
    print(f"OPTIMIZATION 3/3: 99th Percentile Service Level")
    print(f"{'='*100}")
    doh_dom_99 = DOH_DOMESTIC_BASE + percentiles['p99']
    doh_intl_99 = DOH_INTERNATIONAL_BASE + percentiles['p99']
    scenario_name_99 = f"stochastic_99pct_{description.lower().replace(' ', '_')}"

    opt_99 = run_phase2_optimization(doh_dom_99, doh_intl_99, scenario_name_99)

    if opt_99:
        results['doh_domestic_99pct'] = doh_dom_99
        results['doh_international_99pct'] = doh_intl_99
        results['shelves_99pct'] = opt_99['total_shelves']
        results['sacramento_shelves_99pct'] = opt_99['sacramento_shelves']
        results['austin_shelves_99pct'] = opt_99['austin_shelves']

    return results

def main():
    """Main execution."""

    # Scenarios to analyze
    scenarios = [
        (0.1, 3.0, 'Low Disruption'),
        (0.3, 5.0, 'Moderate Disruption'),
        (0.5, 14.0, 'High Disruption'),
    ]

    all_results = []

    for k, mu, desc in scenarios:
        result = analyze_scenario(k, mu, desc)
        if result:
            all_results.append(result)

    if not all_results:
        print("\nERROR: No results generated")
        return

    # Create comprehensive results DataFrame
    results_df = pd.DataFrame(all_results)

    # Save detailed results
    output_file = OPTIMIZATION_RESULTS_DIR / "stochastic_optimization_results.csv"
    results_df.to_csv(output_file, index=False)

    print(f"\n\n{'='*100}")
    print(f"FINAL COMPARISON: ACTUAL OPTIMIZATION RESULTS")
    print(f"{'='*100}")

    # Summary table
    summary_cols = [
        'scenario',
        'shelves_50pct', 'shelves_95pct', 'shelves_99pct'
    ]

    print(f"\nStorage Requirements by Service Level:")
    print(results_df[summary_cols].to_string(index=False))

    # Calculate increases vs baseline
    print(f"\n\nIncrease vs. Baseline ({BASELINE_SHELVES:,} shelves):")
    for _, row in results_df.iterrows():
        print(f"\n{row['scenario']}:")
        print(f"  50th percentile: +{row['shelves_50pct'] - BASELINE_SHELVES:,.0f} shelves "
              f"(+{((row['shelves_50pct']/BASELINE_SHELVES - 1) * 100):.1f}%)")
        print(f"  95th percentile: +{row['shelves_95pct'] - BASELINE_SHELVES:,.0f} shelves "
              f"(+{((row['shelves_95pct']/BASELINE_SHELVES - 1) * 100):.1f}%) <- RECOMMENDED")
        print(f"  99th percentile: +{row['shelves_99pct'] - BASELINE_SHELVES:,.0f} shelves "
              f"(+{((row['shelves_99pct']/BASELINE_SHELVES - 1) * 100):.1f}%)")

    # Facility breakdown (95th percentile - recommended)
    print(f"\n\nFacility Breakdown (95th Percentile Service Level):")
    for _, row in results_df.iterrows():
        print(f"\n{row['scenario']}:")
        print(f"  Sacramento: {row['sacramento_shelves_95pct']:,.0f} shelves")
        print(f"  Austin: {row['austin_shelves_95pct']:,.0f} shelves")
        print(f"  Total: {row['shelves_95pct']:,.0f} shelves")

    print(f"\n\nResults saved to: {output_file}")

    print(f"\n{'='*100}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*100}")
    print(f"\nKey Takeaway:")
    print(f"  These are ACTUAL optimization results, not linear approximations.")
    print(f"  The model accounts for all real constraints:")
    print(f"    - Volume and weight capacity limits")
    print(f"    - Facility allocation optimization")
    print(f"    - Storage type breakdown")
    print(f"    - Tiered pricing for Sacramento")
    print(f"    - Maximum expansion limits")
    print(f"\nRecommendation: Use 95th percentile results for presentation")
    print(f"  - Balances service level (95% coverage) with cost")
    print(f"  - Industry standard for capacity planning")
    print(f"  - Defensible to stakeholders")

if __name__ == "__main__":
    main()
