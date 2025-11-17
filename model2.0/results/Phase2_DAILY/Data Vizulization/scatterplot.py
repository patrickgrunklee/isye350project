import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

# Load data from full matrix CSV (excluding Scenario column)
csv_path = Path(__file__).parent.parent / "doh_full_matrix_summary.csv"
df = pd.read_csv(csv_path)

# Drop the Scenario column (third column)
df = df.drop(columns=['Scenario'])

print(f"Loaded {len(df)} scenarios from full matrix")

# Create meshgrid for surface plots
# Get unique values for each axis
domestic_vals = sorted(df['Domestic_DoH'].unique())
international_vals = sorted(df['International_DoH'].unique())

# Create 2D grids
X, Y = np.meshgrid(domestic_vals, international_vals)

# Reshape Sacramento data into 2D grid
Z_sac = np.zeros_like(X, dtype=float)
for i, intl in enumerate(international_vals):
    for j, dom in enumerate(domestic_vals):
        mask = (df['Domestic_DoH'] == dom) & (df['International_DoH'] == intl)
        Z_sac[i, j] = df.loc[mask, 'Sacramento_Shelves'].values[0]

# Reshape Austin data into 2D grid
Z_austin = np.zeros_like(X, dtype=float)
for i, intl in enumerate(international_vals):
    for j, dom in enumerate(domestic_vals):
        mask = (df['Domestic_DoH'] == dom) & (df['International_DoH'] == intl)
        Z_austin[i, j] = df.loc[mask, 'Austin_Shelves'].values[0]

# Set modern style
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(14, 9), facecolor='white')
ax = fig.add_subplot(111, projection='3d', facecolor='white')

# Modern color palette
sacramento_color = '#2E86AB'
austin_color = '#A23B72'

# Sacramento - surface plot (blanket)
surf_sac = ax.plot_surface(X, Y, Z_sac, color=sacramento_color, alpha=0.3,
                           edgecolor='none', shade=True, antialiased=True)

# Austin - surface plot (blanket)
surf_austin = ax.plot_surface(X, Y, Z_austin, color=austin_color, alpha=0.3,
                              edgecolor='none', shade=True, antialiased=True)

# Austin capacity cap at z=2250 (horizontal plane)
Z_cap_austin = np.ones_like(X) * 2250
cap_plane = ax.plot_surface(X, Y, Z_cap_austin, color='#666666', alpha=0.4,
                            edgecolor='#555555', linewidth=0.5, shade=False,
                            antialiased=True, label='Austin Cap (2250)')

# Sacramento - scatter plot for all 100 points (on top of surface)
ax.scatter(df["Domestic_DoH"], df["International_DoH"], df["Sacramento_Shelves"],
           c=sacramento_color, s=80, alpha=0.9, label='Sacramento Shelves',
           marker='o', edgecolors=sacramento_color, linewidths=1.5, depthshade=True)

# Austin - scatter plot for all 100 points (on top of surface)
ax.scatter(df["Domestic_DoH"], df["International_DoH"], df["Austin_Shelves"],
           c=austin_color, s=80, alpha=0.9, label='Austin Shelves',
           marker='^', edgecolors=austin_color, linewidths=1.5, depthshade=True)

# Enhanced labels with better formatting
ax.set_xlabel("Domestic Days-on-Hand", fontsize=12, fontweight='bold', labelpad=10)
ax.set_ylabel("International Days-on-Hand", fontsize=12, fontweight='bold', labelpad=10)
ax.set_zlabel("Number of Shelves", fontsize=12, fontweight='bold', labelpad=10)
ax.set_title("Warehouse Expansion: Full DoH Sensitivity Matrix (100 Scenarios)\nShelves Required vs Days-on-Hand Inventory",
             fontsize=14, fontweight='bold', pad=20)

# Customize grid for cleaner look
ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.8)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.xaxis.pane.set_edgecolor('#cccccc')
ax.yaxis.pane.set_edgecolor('#cccccc')
ax.zaxis.pane.set_edgecolor('#cccccc')

# Set Z-axis lower bound to 0
ax.set_zlim(bottom=0)
ax.set_xlim(left = 0)


# Legend with better styling
legend = ax.legend(loc='upper left', fontsize=11, frameon=True,
                   shadow=True, fancybox=True, framealpha=0.95)
legend.get_frame().set_facecolor('white')

# Better viewing angle
ax.view_init(elev=20, azim=45)

# Tight layout for better spacing
plt.tight_layout()
plt.show()
