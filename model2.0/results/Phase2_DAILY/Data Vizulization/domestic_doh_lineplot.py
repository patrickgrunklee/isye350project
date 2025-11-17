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
df_domestic = df_domestic.sort_values('Domestic_DoH')

print(f"Filtered to {len(df_domestic)} scenarios with International DOH = {intl_doh_fixed}")

# Calculate total expansion
df_domestic['Total_Expansion'] = df_domestic['Sacramento_Shelves'] + df_domestic['Austin_Shelves']

# Set modern style
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')

# Color palette matching the 3D plot
sacramento_color = '#2E86AB'
austin_color = '#A23B72'
total_color = '#F18F01'

# Plot lines with markers
ax.plot(df_domestic['Domestic_DoH'], df_domestic['Sacramento_Shelves'],
        color=sacramento_color, marker='o', linewidth=2.5, markersize=8,
        label='Sacramento Shelves', alpha=0.9)

ax.plot(df_domestic['Domestic_DoH'], df_domestic['Austin_Shelves'],
        color=austin_color, marker='^', linewidth=2.5, markersize=8,
        label='Austin Shelves', alpha=0.9)

ax.plot(df_domestic['Domestic_DoH'], df_domestic['Total_Expansion'],
        color=total_color, marker='s', linewidth=3, markersize=8,
        label='Total Expansion', alpha=0.9, linestyle='--')

# Add maximum capacity constraint line
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

# Legend
legend = ax.legend(loc='upper left', fontsize=11, frameon=True,
                   shadow=True, fancybox=True, framealpha=0.95)
legend.get_frame().set_facecolor('white')

# Format y-axis with thousands separator
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

# Tight layout
plt.tight_layout()
plt.show()
