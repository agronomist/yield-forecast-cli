"""
Visualize ARPS Yield Predictions for All 81 Fields
Creates a ranked horizontal bar plot similar to the original 68-field visualization
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def create_arps_ranked_plot():
    """Create a ranked horizontal bar plot for all ARPS yield predictions."""
    
    # Read ARPS yield predictions
    df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    
    print(f"Loaded {len(df)} fields")
    
    # Sort by grain yield (ascending for horizontal bar plot)
    df = df.sort_values('Grain Yield (ton/ha)', ascending=True).reset_index(drop=True)
    
    # Calculate statistics
    mean_yield = df['Grain Yield (ton/ha)'].mean()
    median_yield = df['Grain Yield (ton/ha)'].median()
    q1_yield = df['Grain Yield (ton/ha)'].quantile(0.25)
    q3_yield = df['Grain Yield (ton/ha)'].quantile(0.75)
    min_yield = df['Grain Yield (ton/ha)'].min()
    max_yield = df['Grain Yield (ton/ha)'].max()
    
    print(f"\nStatistics:")
    print(f"  Mean: {mean_yield:.2f} ton/ha")
    print(f"  Median: {median_yield:.2f} ton/ha")
    print(f"  Range: {min_yield:.2f} - {max_yield:.2f} ton/ha")
    
    # Create figure with appropriate height for all fields
    fig_height = max(20, len(df) * 0.25)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    
    # Prepare data
    field_names = df['Field Name'].values
    yields = df['Grain Yield (ton/ha)'].values
    
    # Create y positions
    y_pos = np.arange(len(field_names))
    
    # Create color gradient based on yield
    # Use a colormap that goes from red (low) -> yellow (medium) -> green (high)
    norm = plt.Normalize(vmin=min_yield, vmax=max_yield)
    cmap = plt.cm.RdYlGn
    colors = cmap(norm(yields))
    
    # Plot horizontal bars
    bars = ax.barh(y_pos, yields, color=colors, edgecolor='black', linewidth=0.5)
    
    # Add vertical lines for mean, median, and quartiles
    ax.axvline(x=mean_yield, color='black', linestyle='--', linewidth=2, 
               label=f'Mean: {mean_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axvline(x=median_yield, color='black', linestyle='-', linewidth=2, 
               label=f'Median: {median_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axvline(x=q1_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q1: {q1_yield:.2f} ton/ha', alpha=0.6, zorder=9)
    ax.axvline(x=q3_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q3: {q3_yield:.2f} ton/ha', alpha=0.6, zorder=9)
    
    # Add yield values at the end of each bar
    for i, (y, val) in enumerate(zip(y_pos, yields)):
        ax.text(val + 0.1, y, f'{val:.2f}', 
                va='center', ha='left', fontsize=6, fontweight='bold')
    
    # Customize axes
    ax.set_yticks(y_pos)
    ax.set_yticklabels(field_names, fontsize=7)
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Field Name', fontsize=14, fontweight='bold')
    
    # Title with statistics
    title = (f'ARPS Yield Predictions - {len(df)} Fields Ranked by Yield\n'
             f'Data Source: PlanetScope 3m Daily | Mean: {mean_yield:.2f} ton/ha | '
             f'Range: {min_yield:.2f} - {max_yield:.2f} ton/ha')
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Set x-axis limits
    ax.set_xlim(0, max_yield * 1.15)
    
    # Legend
    ax.legend(loc='lower right', fontsize=10, framealpha=0.95, 
              title='Statistics', title_fontsize=11)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figures
    output_png = 'yield_arps_all_81_fields_ranked.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to: {output_png}")
    
    output_pdf = 'yield_arps_all_81_fields_ranked.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    return fig, ax


def create_arps_boxplot():
    """Create a box plot for all ARPS yield predictions."""
    
    df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    
    # Sort by grain yield (descending)
    df = df.sort_values('Grain Yield (ton/ha)', ascending=False).reset_index(drop=True)
    
    # Calculate statistics
    mean_yield = df['Grain Yield (ton/ha)'].mean()
    median_yield = df['Grain Yield (ton/ha)'].median()
    q1_yield = df['Grain Yield (ton/ha)'].quantile(0.25)
    q3_yield = df['Grain Yield (ton/ha)'].quantile(0.75)
    min_yield = df['Grain Yield (ton/ha)'].min()
    max_yield = df['Grain Yield (ton/ha)'].max()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(18, 12))
    
    # Prepare data
    field_names = df['Field Name'].values
    yields = df['Grain Yield (ton/ha)'].values
    
    # Create x positions
    x_pos = np.arange(len(field_names))
    
    # Create color gradient
    norm = plt.Normalize(vmin=min_yield, vmax=max_yield)
    cmap = plt.cm.RdYlGn
    colors = cmap(norm(yields))
    
    # Plot bars
    bars = ax.bar(x_pos, yields, color=colors, edgecolor='black', linewidth=0.5)
    
    # Add horizontal lines for statistics
    ax.axhline(y=mean_yield, color='black', linestyle='--', linewidth=2, 
               label=f'Mean: {mean_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axhline(y=median_yield, color='black', linestyle='-', linewidth=2, 
               label=f'Median: {median_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axhline(y=q1_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q1: {q1_yield:.2f} ton/ha', alpha=0.6, zorder=9)
    ax.axhline(y=q3_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q3: {q3_yield:.2f} ton/ha', alpha=0.6, zorder=9)
    
    # Customize axes
    ax.set_xticks(x_pos)
    ax.set_xticklabels(field_names, rotation=90, ha='right', fontsize=7)
    ax.set_xlabel('Field Name', fontsize=14, fontweight='bold')
    ax.set_ylabel('Grain Yield (ton/ha)', fontsize=14, fontweight='bold')
    
    # Title
    title = (f'ARPS Yield Predictions - {len(df)} Fields Ranked by Yield\n'
             f'Data Source: PlanetScope 3m Daily | Mean: {mean_yield:.2f} ton/ha | '
             f'Range: {min_yield:.2f} - {max_yield:.2f} ton/ha')
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Set y-axis limits
    ax.set_ylim(0, max_yield * 1.1)
    
    # Legend
    ax.legend(loc='upper right', fontsize=10, framealpha=0.95, 
              title='Statistics', title_fontsize=11)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figures
    output_png = 'yield_arps_all_81_fields_boxplot.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved boxplot to: {output_png}")
    
    output_pdf = 'yield_arps_all_81_fields_boxplot.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    return fig, ax


def print_field_comparison():
    """Print comparison showing new fields."""
    
    df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    
    # List of new field names
    new_fields = [
        'Cassina Lote 1', 'Centeno Lote 1', 'Centeno Lote 2', 'Centeno Lote 3',
        'Centeno Lote 4', 'Centeno Lote 5', 'Don Adolfo Lote 1', 'Don Adolfo Lote 2',
        'Ferito Lote 2', 'Giuggia Lote 1', 'La Pobladora Lote 14', 'La Pobladora Lote 15'
    ]
    
    # Mark new fields
    df['Field Type'] = df['Field Name'].apply(
        lambda x: 'New (2024)' if x in new_fields else 'Original (2023)'
    )
    
    print("\n" + "=" * 81)
    print("FIELD COMPARISON - ORIGINAL VS NEW")
    print("=" * 81)
    
    print(f"\nTotal Fields: {len(df)}")
    print(f"  Original Fields: {len(df[df['Field Type'] == 'Original (2023)'])}")
    print(f"  New Fields: {len(df[df['Field Type'] == 'New (2024)'])}")
    
    print("\nYield Statistics by Field Type:")
    comparison = df.groupby('Field Type')['Grain Yield (ton/ha)'].agg(['mean', 'median', 'std', 'min', 'max', 'count'])
    print(comparison.to_string())
    
    print("\n" + "─" * 81)
    print("Top 10 Highest Yielding Fields:")
    print("─" * 81)
    top10 = df.nlargest(10, 'Grain Yield (ton/ha)')[['Field Name', 'Grain Yield (ton/ha)', 'Field Type']]
    for i, row in top10.iterrows():
        marker = "🆕" if row['Field Type'] == 'New (2024)' else "  "
        print(f"{marker} {row['Field Name']:40} {row['Grain Yield (ton/ha)']:6.2f} ton/ha")
    
    print("\n" + "─" * 81)
    print("New Fields Performance:")
    print("─" * 81)
    new_df = df[df['Field Type'] == 'New (2024)'].sort_values('Grain Yield (ton/ha)', ascending=False)
    for i, row in new_df.iterrows():
        print(f"  {row['Field Name']:40} {row['Grain Yield (ton/ha)']:6.2f} ton/ha")
    
    print("\n" + "=" * 81)


if __name__ == "__main__":
    print("\n" + "=" * 81)
    print("CREATING ARPS YIELD VISUALIZATIONS - ALL 81 FIELDS")
    print("=" * 81)
    
    try:
        # Print comparison
        print_field_comparison()
        
        print("\n" + "─" * 81)
        print("Creating visualizations...")
        print("─" * 81)
        
        # Create ranked plot (horizontal bars)
        print("\n1. Creating ranked horizontal bar plot...")
        create_arps_ranked_plot()
        
        # Create box plot (vertical bars)
        print("\n2. Creating boxplot with vertical bars...")
        create_arps_boxplot()
        
        print("\n" + "=" * 81)
        print("✓ VISUALIZATIONS COMPLETE")
        print("=" * 81)
        print("\nCreated files:")
        print("  - yield_arps_all_81_fields_ranked.png")
        print("  - yield_arps_all_81_fields_ranked.pdf")
        print("  - yield_arps_all_81_fields_boxplot.png")
        print("  - yield_arps_all_81_fields_boxplot.pdf")
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("Please ensure yield_predictions_arps_all_fields.csv exists")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

