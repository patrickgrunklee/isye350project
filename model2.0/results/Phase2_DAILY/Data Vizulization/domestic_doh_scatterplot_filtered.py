import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load data from full matrix CSV
csv_path = Path(__file__).parent.parent / "doh_full_matrix_summary.csv"
df = pd.read_csv(csv_path)

print(f"Loaded {len(df)} scenarios from full matrix")

# Filter for International DOH = 0 (to isolate domestic DOH effects)
intl_doh_fixed = 0
df_domestic = df[df['International_DoH'] == intl_doh_fixed].copy()

# Apply independent capacity constraints filter for each facility
df_sac_filtered = df_domestic[df_domestic['Sacramento_Shelves'] <= 2815].copy()
df_austin_filtered = df_domestic[df_domestic['Austin_Shelves'] <= 2250].copy()

# For total, use intersection (both must be within limits)
df_total_filtered = df_domestic[
    (df_domestic['Sacramento_Shelves'] <= 2815) &
    (df_domestic['Austin_Shelves'] <= 2250)
].copy()

df_sac_filtered = df_sac_filtered.sort_values('Domestic_DoH')
df_austin_filtered = df_austin_filtered.sort_values('Domestic_DoH')
df_total_filtered = df_total_filtered.sort_values('Domestic_DoH')

# Calculate total expansion for total filtered set
df_total_filtered['Total_Expansion'] = df_total_filtered['Sacramento_Shelves'] + df_total_filtered['Austin_Shelves']

# Find next points beyond the filter (for visualization)
df_sac_next = df_domestic[df_domestic['Sacramento_Shelves'] > 2815].copy()
df_sac_next = df_sac_next.sort_values('Domestic_DoH')
sac_next_point = df_sac_next.iloc[0] if len(df_sac_next) > 0 else None

df_austin_next = df_domestic[df_domestic['Austin_Shelves'] > 2250].copy()
df_austin_next = df_austin_next.sort_values('Domestic_DoH')
austin_next_point = df_austin_next.iloc[0] if len(df_austin_next) > 0 else None

df_total_next = df_domestic[
    (df_domestic['Sacramento_Shelves'] > 2815) |
    (df_domestic['Austin_Shelves'] > 2250)
].copy()
df_total_next = df_total_next.sort_values('Domestic_DoH')
total_next_point = df_total_next.iloc[0] if len(df_total_next) > 0 else None
if total_next_point is not None:
    total_next_expansion = total_next_point['Sacramento_Shelves'] + total_next_point['Austin_Shelves']
else:
    total_next_expansion = None

# Set modern style
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')

# Color palette matching the 3D plot
sacramento_color = '#2E86AB'
austin_color = '#A23B72'
total_color = '#F18F01'

# Line plots with markers - INDEPENDENT FILTERS
ax.plot(df_sac_filtered['Domestic_DoH'], df_sac_filtered['Sacramento_Shelves'],
        color=sacramento_color, marker='o', linewidth=2.5, markersize=8,
        label='Sacramento Shelves', alpha=0.9)

# Add faded connection to next Sacramento point
if sac_next_point is not None and len(df_sac_filtered) > 0:
    last_sac = df_sac_filtered.iloc[-1]
    ax.plot([last_sac['Domestic_DoH'], sac_next_point['Domestic_DoH']],
            [last_sac['Sacramento_Shelves'], sac_next_point['Sacramento_Shelves']],
            color=sacramento_color, linewidth=2.5, alpha=0.3, linestyle='--')
    ax.plot(sac_next_point['Domestic_DoH'], sac_next_point['Sacramento_Shelves'],
            marker='o', markersize=8, color=sacramento_color, alpha=0.3)

ax.plot(df_austin_filtered['Domestic_DoH'], df_austin_filtered['Austin_Shelves'],
        color=austin_color, marker='^', linewidth=2.5, markersize=8,
        label='Austin Shelves', alpha=0.9)

# Add faded connection to next Austin point
if austin_next_point is not None and len(df_austin_filtered) > 0:
    last_austin = df_austin_filtered.iloc[-1]
    ax.plot([last_austin['Domestic_DoH'], austin_next_point['Domestic_DoH']],
            [last_austin['Austin_Shelves'], austin_next_point['Austin_Shelves']],
            color=austin_color, linewidth=2.5, alpha=0.3, linestyle='--')
    ax.plot(austin_next_point['Domestic_DoH'], austin_next_point['Austin_Shelves'],
            marker='^', markersize=8, color=austin_color, alpha=0.3)

ax.plot(df_total_filtered['Domestic_DoH'], df_total_filtered['Total_Expansion'],
        color=total_color, marker='s', linewidth=3, markersize=8,
        label='Total Expansion', alpha=0.9, linestyle='--')

# Add faded connection to next Total point
if total_next_point is not None and total_next_expansion is not None and len(df_total_filtered) > 0:
    last_total = df_total_filtered.iloc[-1]
    ax.plot([last_total['Domestic_DoH'], total_next_point['Domestic_DoH']],
            [last_total['Total_Expansion'], total_next_expansion],
            color=total_color, linewidth=3, alpha=0.3, linestyle='--')
    ax.plot(total_next_point['Domestic_DoH'], total_next_expansion,
            marker='s', markersize=8, color=total_color, alpha=0.3)

# Add capacity constraint lines
ax.axhline(y=2810, color=sacramento_color, linestyle=':', linewidth=2,
           label='Sacramento Capacity (2,810)', alpha=0.6)
ax.axhline(y=2250, color=austin_color, linestyle=':', linewidth=2,
           label='Austin Capacity (2,250)', alpha=0.6)
ax.axhline(y=5060, color='#666666', linestyle=':', linewidth=2.5,
           label='Max Pallet Capacity (5,060)', alpha=0.8)

# Labels and title
ax.set_xlabel('Domestic DOH', fontsize=13, fontweight='bold')
ax.set_ylabel('Number of Shelves Required', fontsize=13, fontweight='bold')
ax.set_title('Warehouse Expansion vs Domestic DOH',
            fontsize=14, fontweight='bold', pad=15)

# Grid styling
ax.grid(True, linestyle='--', alpha=0.4, linewidth=0.8)
ax.set_axisbelow(True)

# Set y-axis to start at 0
ax.set_ylim(bottom=0)
ax.set_xlim(left=0)

# Legend with better positioning for more items
legend = ax.legend(loc='upper left', fontsize=10, frameon=True,
                   shadow=True, fancybox=True, framealpha=0.95, ncol=2)
legend.get_frame().set_facecolor('white')

# Format y-axis with thousands separator
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

# Add text annotation showing filter criteria
annotation_text = f'Sac: {len(df_sac_filtered)}/{len(df_domestic)} | Austin: {len(df_austin_filtered)}/{len(df_domestic)} | Total: {len(df_total_filtered)}/{len(df_domestic)}'
ax.text(0.98, 0.02, annotation_text,
        transform=ax.transAxes, fontsize=9, verticalalignment='bottom',
        horizontalalignment='right', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Tight layout
plt.tight_layout()
plt.show()
