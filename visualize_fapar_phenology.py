"""
Visualize fAPAR Time Series with Phenological Stages

Creates plots showing fAPAR progression over time for each field,
with phenological stages marked as vertical lines.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np


def plot_field_fapar_phenology(field_name, fapar_data, phenology_data, ax=None):
    """
    Plot fAPAR time series for a field with phenological stages.
    
    Args:
        field_name: Name of the field
        fapar_data: fAPAR time series data for the field
        phenology_data: Phenology data for the field
        ax: Matplotlib axis (if None, creates new figure)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    
    # Extract fAPAR time series
    time_series = fapar_data.get('ndvi_time_series', [])
    
    if not time_series:
        return False
    
    # Prepare data
    dates = []
    fapar_values = []
    ndvi_values = []
    
    for obs in time_series:
        # Use the middle date of the week
        date_from = datetime.strptime(obs['from'], '%Y-%m-%d')
        date_to = datetime.strptime(obs['to'], '%Y-%m-%d')
        mid_date = date_from + (date_to - date_from) / 2
        
        dates.append(mid_date)
        fapar_values.append(obs.get('fapar_mean', 0))
        ndvi_values.append(obs.get('ndvi_mean', 0))
    
    # Plot fAPAR line
    ax.plot(dates, fapar_values, 'o-', linewidth=2, markersize=6, 
            color='green', label='fAPAR', alpha=0.8)
    
    # Add NDVI on secondary axis
    ax2 = ax.twinx()
    ax2.plot(dates, ndvi_values, 's--', linewidth=1.5, markersize=4,
             color='darkgreen', label='NDVI', alpha=0.5)
    
    # Plot phenological stages as vertical lines
    stage_dates = phenology_data.get('stage_dates', {})
    variety = phenology_data.get('variety', 'Unknown')
    
    # Stage colors
    stage_colors = {
        'sowing': 'brown',
        'emergence': 'orange',
        'tillering': 'gold',
        'stem_extension': 'yellowgreen',
        'heading': 'limegreen',
        'anthesis': 'cyan',
        'grain_fill': 'blue',
        'maturity': 'purple'
    }
    
    stage_labels = {
        'sowing': 'Sowing',
        'emergence': 'Emergence',
        'tillering': 'Tillering',
        'stem_extension': 'Stem Ext.',
        'heading': 'Heading',
        'anthesis': 'Anthesis',
        'grain_fill': 'Grain Fill',
        'maturity': 'Maturity'
    }
    
    # Track which stages were plotted
    plotted_stages = []
    
    for stage, date_str in stage_dates.items():
        if date_str and date_str != 'N/A':
            try:
                stage_date = datetime.strptime(date_str, '%Y-%m-%d')
                color = stage_colors.get(stage, 'gray')
                label = stage_labels.get(stage, stage.replace('_', ' ').title())
                
                ax.axvline(stage_date, color=color, linestyle='--', 
                          linewidth=2, alpha=0.7, label=label)
                
                plotted_stages.append(label)
            except:
                pass
    
    # Formatting
    variety_name = fapar_data.get('variety', variety)
    sowing_date = fapar_data.get('sowing_date', 'Unknown')
    
    ax.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax.set_ylabel('fAPAR', fontsize=11, fontweight='bold', color='green')
    ax2.set_ylabel('NDVI', fontsize=11, fontweight='bold', color='darkgreen')
    
    ax.tick_params(axis='y', labelcolor='green')
    ax2.tick_params(axis='y', labelcolor='darkgreen')
    
    title = f'{field_name}\n{variety_name} | Sowing: {sowing_date}'
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    ax2.set_ylim(0, 1)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    
    # Only include fAPAR, NDVI, and actual plotted stages in legend
    ax.legend(lines1 + lines2, labels1 + labels2, 
             loc='upper left', fontsize=8, ncol=2)
    
    return True


def create_all_field_plots_pdf():
    """Create a PDF with fAPAR plots for all fields."""
    
    print("\n" + "=" * 80)
    print("CREATING fAPAR TIME SERIES PLOTS WITH PHENOLOGICAL STAGES")
    print("=" * 80)
    
    # Load data
    print("\nLoading data...")
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('phenology_analysis_results.json', 'r') as f:
        phenology_data = json.load(f)
    
    # Create dictionary for easy lookup
    phenology_dict = {f['field_name']: f for f in phenology_data['fields']}
    
    fields = fapar_data['fields']
    print(f"✓ Loaded data for {len(fields)} fields")
    
    # Create PDF
    output_pdf = 'fapar_phenology_timeseries.pdf'
    
    with PdfPages(output_pdf) as pdf:
        print(f"\nGenerating plots...")
        
        for idx, (field_name, field_fapar) in enumerate(fields.items(), 1):
            if idx % 10 == 0:
                print(f"  Progress: {idx}/{len(fields)} fields...")
            
            # Get phenology data
            field_pheno = phenology_dict.get(field_name, {})
            
            # Create plot
            fig, ax = plt.subplots(figsize=(14, 7))
            success = plot_field_fapar_phenology(field_name, field_fapar, field_pheno, ax)
            
            if success:
                plt.tight_layout()
                pdf.savefig(fig, dpi=150)
                plt.close(fig)
            else:
                plt.close(fig)
                print(f"  Warning: No data for {field_name}")
    
    print(f"\n✓ Saved all plots to: {output_pdf}")
    return output_pdf


def create_sample_plots():
    """Create sample plots for a few representative fields."""
    
    print("\n" + "─" * 80)
    print("Creating sample plots (top 6 fields by yield)...")
    print("─" * 80)
    
    # Load data
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('phenology_analysis_results.json', 'r') as f:
        phenology_data = json.load(f)
    
    with open('yield_predictions.csv') as f:
        df_yield = pd.read_csv(f)
    
    # Get top fields
    top_fields = df_yield.nlargest(6, 'Grain Yield (ton/ha)')['Field Name'].values
    
    # Create dictionary for easy lookup
    phenology_dict = {f['field_name']: f for f in phenology_data['fields']}
    
    # Create 2x3 grid
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    axes = axes.flatten()
    
    for idx, field_name in enumerate(top_fields):
        ax = axes[idx]
        
        field_fapar = fapar_data['fields'].get(field_name, {})
        field_pheno = phenology_dict.get(field_name, {})
        
        plot_field_fapar_phenology(field_name, field_fapar, field_pheno, ax)
        
        # Add yield annotation
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        ax.text(0.98, 0.98, f'Yield: {yield_val:.2f} ton/ha',
               transform=ax.transAxes, fontsize=10,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.suptitle('Top 6 Fields: fAPAR Progression with Phenological Stages',
                 fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    output_file = 'fapar_phenology_top6_fields.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved sample plots to: {output_file}")
    
    plt.savefig('fapar_phenology_top6_fields.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: fapar_phenology_top6_fields.pdf")
    
    return fig


def create_comparison_plots():
    """Create comparison plots: high vs low yielding fields."""
    
    print("\n" + "─" * 80)
    print("Creating comparison: High vs Low yielding fields...")
    print("─" * 80)
    
    # Load data
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('phenology_analysis_results.json', 'r') as f:
        phenology_data = json.load(f)
    
    with open('yield_predictions.csv') as f:
        df_yield = pd.read_csv(f)
    
    # Get high and low yielding fields
    high_fields = df_yield.nlargest(3, 'Grain Yield (ton/ha)')['Field Name'].values
    low_fields = df_yield.nsmallest(3, 'Grain Yield (ton/ha)')['Field Name'].values
    
    # Create dictionary for easy lookup
    phenology_dict = {f['field_name']: f for f in phenology_data['fields']}
    
    # Create 2x3 grid
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    
    # Top row: High yielding
    for idx, field_name in enumerate(high_fields):
        ax = axes[0, idx]
        
        field_fapar = fapar_data['fields'].get(field_name, {})
        field_pheno = phenology_dict.get(field_name, {})
        
        plot_field_fapar_phenology(field_name, field_fapar, field_pheno, ax)
        
        # Add yield annotation
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        ax.text(0.98, 0.98, f'HIGH: {yield_val:.2f} ton/ha',
               transform=ax.transAxes, fontsize=10, fontweight='bold',
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    # Bottom row: Low yielding
    for idx, field_name in enumerate(low_fields):
        ax = axes[1, idx]
        
        field_fapar = fapar_data['fields'].get(field_name, {})
        field_pheno = phenology_dict.get(field_name, {})
        
        plot_field_fapar_phenology(field_name, field_fapar, field_pheno, ax)
        
        # Add yield annotation
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        ax.text(0.98, 0.98, f'LOW: {yield_val:.2f} ton/ha',
               transform=ax.transAxes, fontsize=10, fontweight='bold',
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
    
    plt.suptitle('fAPAR Comparison: High vs Low Yielding Fields',
                 fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    output_file = 'fapar_phenology_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved comparison plots to: {output_file}")
    
    plt.savefig('fapar_phenology_comparison.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: fapar_phenology_comparison.pdf")
    
    return fig


def create_summary_statistics():
    """Print summary statistics of fAPAR patterns."""
    
    print("\n" + "=" * 80)
    print("fAPAR PATTERN SUMMARY")
    print("=" * 80)
    
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('yield_predictions.csv') as f:
        df_yield = pd.read_csv(f)
    
    all_peak_fapar = []
    all_mean_fapar = []
    
    for field_name, field_data in fapar_data['fields'].items():
        time_series = field_data.get('ndvi_time_series', [])
        
        if time_series:
            fapar_values = [obs.get('fapar_mean', 0) for obs in time_series 
                           if obs.get('fapar_mean') is not None]
            
            if fapar_values:
                peak = max(fapar_values)
                mean = np.mean(fapar_values)
                
                all_peak_fapar.append(peak)
                all_mean_fapar.append(mean)
    
    print(f"\nAll Fields:")
    print(f"  Peak fAPAR - Mean: {np.mean(all_peak_fapar):.3f}, Range: {np.min(all_peak_fapar):.3f}-{np.max(all_peak_fapar):.3f}")
    print(f"  Mean fAPAR - Mean: {np.mean(all_mean_fapar):.3f}, Range: {np.min(all_mean_fapar):.3f}-{np.max(all_mean_fapar):.3f}")
    
    # High vs low yielders
    high_fields = df_yield.nlargest(10, 'Grain Yield (ton/ha)')['Field Name'].values
    low_fields = df_yield.nsmallest(10, 'Grain Yield (ton/ha)')['Field Name'].values
    
    high_peak = []
    low_peak = []
    
    for field_name, field_data in fapar_data['fields'].items():
        time_series = field_data.get('ndvi_time_series', [])
        
        if time_series:
            fapar_values = [obs.get('fapar_mean', 0) for obs in time_series 
                           if obs.get('fapar_mean') is not None]
            
            if fapar_values:
                peak = max(fapar_values)
                
                if field_name in high_fields:
                    high_peak.append(peak)
                elif field_name in low_fields:
                    low_peak.append(peak)
    
    print(f"\nHigh Yielding Fields (top 10):")
    print(f"  Peak fAPAR: {np.mean(high_peak):.3f}")
    
    print(f"\nLow Yielding Fields (bottom 10):")
    print(f"  Peak fAPAR: {np.mean(low_peak):.3f}")
    
    print(f"\nDifference:")
    print(f"  High vs Low: {((np.mean(high_peak) - np.mean(low_peak))/np.mean(low_peak)*100):.1f}% higher peak fAPAR")


if __name__ == "__main__":
    try:
        # Create summary statistics
        create_summary_statistics()
        
        # Create sample plots
        print("\n" + "─" * 80)
        print("CREATING VISUALIZATIONS")
        print("─" * 80)
        
        create_sample_plots()
        create_comparison_plots()
        
        # Create full PDF
        print("\n" + "─" * 80)
        create_all_field_plots_pdf()
        
        print("\n" + "=" * 80)
        print("✓ VISUALIZATION COMPLETE")
        print("=" * 80)
        
        print("\nFiles created:")
        print("  1. fapar_phenology_top6_fields.png - Top 6 fields")
        print("  2. fapar_phenology_comparison.png - High vs Low comparison")
        print("  3. fapar_phenology_timeseries.pdf - All 68 fields (comprehensive)")
        
        print("\n💡 The PDF contains all fields, while PNGs show key examples")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

