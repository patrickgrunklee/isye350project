"""
STOCHASTIC STORAGE IMPACT ANALYSIS
===================================

This script connects stochastic delay analysis to warehouse expansion requirements.

Process:
1. Load stochastic delay results (supplier-based)
2. Calculate average delay per SKU-facility pair
3. Compute effective DOH increase needed
4. Re-run optimization model with increased DOH
5. Compare storage requirements: Baseline vs. Stochastic scenarios
6. Quantify "cost of uncertainty"
"""

import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DOH_DOMESTIC_BASE = 4
DOH_INTERNATIONAL_BASE = 14
SCENARIO_NAME = f"{DOH_INTERNATIONAL_BASE}_{DOH_DOMESTIC_BASE}_doh"

RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase2_DAILY")
STOCHASTIC_RESULTS_DIR = RESULTS_DIR / f"stochastic_supplier_{SCENARIO_NAME}"
STORAGE_IMPACT_DIR = RESULTS_DIR / f"storage_impact_{SCENARIO_NAME}"
STORAGE_IMPACT_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print("STOCHASTIC STORAGE IMPACT ANALYSIS")
print("="*100)
print(f"\nBaseline Scenario: {SCENARIO_NAME}")
print(f"  Domestic DOH: {DOH_DOMESTIC_BASE} days")
print(f"  International DOH: {DOH_INTERNATIONAL_BASE} days")
print()

def load_stochastic_summary(k_factor, mean_delay):
    """Load summary results from stochastic simulation."""
    summary_file = STOCHASTIC_RESULTS_DIR / f"supplier_summary_k{k_factor}_mu{mean_delay}.csv"

    if not summary_file.exists():
        print(f"WARNING: Summary file not found: {summary_file}")
        return None

    df = pd.read_csv(summary_file)
    return df.iloc[0]  # Single row summary

def calculate_effective_doh(avg_delay_days, base_doh):
    """
    Calculate effective DOH needed to cover delays.

    Effective DOH = Base DOH + Average Delay Days

    This represents the total inventory buffer needed to maintain service levels
    when deliveries face stochastic delays.
    """
    return base_doh + avg_delay_days

def run_expanded_capacity_model(doh_domestic, doh_international, scenario_label):
    """
    Run the optimization model with increased DOH to determine new capacity requirements.

    Args:
        doh_domestic: New domestic DOH (including delay buffer)
        doh_international: New international DOH (including delay buffer)
        scenario_label: Label for this scenario (e.g., "catastrophic_1.0_21")

    Returns:
        Dictionary with expansion requirements
    """
    print(f"\nRunning optimization with adjusted DOH:")
    print(f"  Domestic: {doh_domestic:.1f} days (base: {DOH_DOMESTIC_BASE})")
    print(f"  International: {doh_international:.1f} days (base: {DOH_INTERNATIONAL_BASE})")

    script_dir = Path(__file__).parent
    parameterized_script = script_dir / "phase2_DAILY_parameterized.py"

    cmd = [
        'python',
        str(parameterized_script),
        '--doh_intl', str(int(doh_international)),
        '--doh_dom', str(int(doh_domestic)),
        '--scenario_name', f"stochastic_{scenario_label}",
        '--max_time', '300'
    ]

    print(f"Command: {' '.join(cmd)}")
    print("Solving... (this may take a few minutes)")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR running model:")
        print(f"Return code: {result.returncode}")
        print(f"\nSTDERR:\n{result.stderr}")
        return None

    # Parse results
    results_file = RESULTS_DIR / f"stochastic_{scenario_label}" / f"expansion_requirements_stochastic_{scenario_label}.csv"

    if not results_file.exists():
        print(f"ERROR: Results file not found: {results_file}")
        return None

    results_df = pd.read_csv(results_file)

    expansion = {
        'sacramento_shelves': results_df[results_df['Facility'] == 'Sacramento']['Expansion_Shelves'].iloc[0] if len(results_df[results_df['Facility'] == 'Sacramento']) > 0 else 0,
        'austin_shelves': results_df[results_df['Facility'] == 'Austin']['Expansion_Shelves'].iloc[0] if len(results_df[results_df['Facility'] == 'Austin']) > 0 else 0,
        'total_shelves': results_df[results_df['Facility'] == 'Total']['Expansion_Shelves'].iloc[0] if len(results_df[results_df['Facility'] == 'Total']) > 0 else 0
    }

    print(f"\nExpansion Requirements:")
    print(f"  Sacramento: {expansion['sacramento_shelves']:,.0f} shelves")
    print(f"  Austin: {expansion['austin_shelves']:,.0f} shelves")
    print(f"  Total: {expansion['total_shelves']:,.0f} shelves")

    return expansion

def analyze_scenario(k_factor, mean_delay, description):
    """Analyze storage impact for one stochastic scenario."""
    print("\n" + "#"*100)
    print(f"SCENARIO: {description}")
    print(f"  k={k_factor}, μ={mean_delay} days")
    print("#"*100)

    # Load stochastic results
    summary = load_stochastic_summary(k_factor, mean_delay)

    if summary is None:
        print(f"ERROR: Could not load stochastic results for k={k_factor}, μ={mean_delay}")
        return None

    # Calculate average delay per truck (used as proxy for delay per delivery)
    avg_truck_days = summary['avg_truck_days_delay']
    avg_trucks = summary['avg_truck_impacts']
    avg_delay_per_delivery = avg_truck_days / avg_trucks if avg_trucks > 0 else 0

    print(f"\nStochastic Delay Statistics:")
    print(f"  Total truck-days delay: {avg_truck_days:,.0f}")
    print(f"  Total trucks affected: {avg_trucks:,.0f}")
    print(f"  Average delay per delivery: {avg_delay_per_delivery:.2f} days")

    # Calculate effective DOH (simplified: apply same delay to both domestic and international)
    # In reality, delays differ by supplier type, but this gives conservative estimate
    effective_doh_domestic = calculate_effective_doh(avg_delay_per_delivery, DOH_DOMESTIC_BASE)
    effective_doh_international = calculate_effective_doh(avg_delay_per_delivery, DOH_INTERNATIONAL_BASE)

    print(f"\nEffective DOH Requirements:")
    print(f"  Domestic: {DOH_DOMESTIC_BASE} days → {effective_doh_domestic:.1f} days ({effective_doh_domestic/DOH_DOMESTIC_BASE:.2f}× increase)")
    print(f"  International: {DOH_INTERNATIONAL_BASE} days → {effective_doh_international:.1f} days ({effective_doh_international/DOH_INTERNATIONAL_BASE:.2f}× increase)")

    # Run optimization with new DOH
    scenario_label = f"{description.lower().replace(' ', '_')}_k{k_factor}_mu{int(mean_delay)}"
    expansion = run_expanded_capacity_model(
        effective_doh_domestic,
        effective_doh_international,
        scenario_label
    )

    if expansion is None:
        return None

    # Calculate impact vs baseline
    baseline_total = 3994  # From baseline run

    impact = {
        'scenario': description,
        'k_factor': k_factor,
        'mean_delay': mean_delay,
        'avg_delay_per_delivery': avg_delay_per_delivery,
        'effective_doh_domestic': effective_doh_domestic,
        'effective_doh_international': effective_doh_international,
        'baseline_shelves': baseline_total,
        'stochastic_shelves': expansion['total_shelves'],
        'additional_shelves': expansion['total_shelves'] - baseline_total,
        'percent_increase': ((expansion['total_shelves'] / baseline_total) - 1) * 100,
        'sacramento_shelves': expansion['sacramento_shelves'],
        'austin_shelves': expansion['austin_shelves']
    }

    print(f"\n{'='*100}")
    print(f"STORAGE IMPACT SUMMARY - {description}")
    print(f"{'='*100}")
    print(f"  Baseline expansion: {baseline_total:,.0f} shelves")
    print(f"  Stochastic expansion: {expansion['total_shelves']:,.0f} shelves")
    print(f"  Additional capacity needed: {impact['additional_shelves']:,.0f} shelves ({impact['percent_increase']:.1f}% increase)")
    print(f"  Sacramento: +{expansion['sacramento_shelves'] - 2884:,.0f} shelves")
    print(f"  Austin: +{expansion['austin_shelves'] - 1110:,.0f} shelves")

    return impact

def main():
    """Main execution."""

    # Scenarios to analyze (matching stochastic simulation)
    scenarios = [
        (0.3, 7.0, 'Moderate Disruption'),
        (0.6, 14.0, 'Severe Disruption'),
        (1.0, 21.0, 'Catastrophic Disruption'),
    ]

    results = []

    for k, mu, desc in scenarios:
        impact = analyze_scenario(k, mu, desc)
        if impact:
            results.append(impact)

    if not results:
        print("\nERROR: No results generated. Check stochastic simulation outputs.")
        return

    # Create summary comparison table
    print("\n\n" + "="*100)
    print("FINAL COMPARISON: STORAGE REQUIREMENTS ACROSS SCENARIOS")
    print("="*100)

    results_df = pd.DataFrame(results)

    # Save detailed results
    output_file = STORAGE_IMPACT_DIR / "stochastic_storage_impact_summary.csv"
    results_df.to_csv(output_file, index=False)

    print(f"\nScenario Comparison:")
    print(results_df[['scenario', 'avg_delay_per_delivery', 'baseline_shelves',
                      'stochastic_shelves', 'additional_shelves', 'percent_increase']].to_string(index=False))

    print(f"\n\nResults saved to: {output_file}")

    print("\n" + "="*100)
    print("KEY INSIGHTS:")
    print("="*100)

    for _, row in results_df.iterrows():
        print(f"\n{row['scenario']}:")
        print(f"  Average delay: {row['avg_delay_per_delivery']:.1f} days per delivery")
        print(f"  Storage increase: {row['additional_shelves']:,.0f} shelves (+{row['percent_increase']:.1f}%)")
        print(f"  Cost of uncertainty: Need to expand {row['percent_increase']:.1f}% MORE than baseline")

if __name__ == "__main__":
    main()
