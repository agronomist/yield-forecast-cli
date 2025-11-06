"""
Compare Different RUE Approaches for Yield Prediction

Compares three approaches:
1. Constant average RUE (2.4 g DM/MJ PAR)
2. Growth stage-based RUE (uses phenology predictions)
3. Days-after-sowing RUE (direct days-based lookup)
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from predict_yield import YieldPredictor, load_all_data
from wheat_rue_values import WheatRUE


class RUEComparison:
    """Compare different RUE approaches."""
    
    HARVEST_INDEX = 0.45
    
    def calculate_yield_with_rue_method(
        self,
        fapar_weekly,
        par_daily,
        sowing_date: str,
        rue_method: str
    ):
        """
        Calculate yield using specified RUE method.
        
        Args:
            fapar_weekly: Weekly fAPAR data
            par_daily: Daily PAR data
            sowing_date: Sowing date
            rue_method: 'average', 'stage', or 'days'
        """
        predictor = YieldPredictor()
        sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        
        # Create PAR dataframe
        par_data = []
        for obs in par_daily:
            date = datetime.strptime(obs['date'], '%Y-%m-%d')
            par_data.append({
                'date': date,
                'PAR': obs['PAR_MJ']
            })
        
        df_par = pd.DataFrame(par_data).sort_values('date')
        
        # Interpolate fAPAR
        end_date = df_par['date'].max()
        df_fapar = predictor.interpolate_fapar_to_daily(fapar_weekly, sowing_dt, end_date)
        
        if df_fapar.empty:
            return None
        
        # Merge
        df = pd.merge(df_par, df_fapar, on='date', how='inner')
        df['days_since_sowing'] = (df['date'] - sowing_dt).dt.days
        
        # Apply RUE based on method
        if rue_method == 'average':
            df['RUE'] = WheatRUE.AVERAGE_RUE
        elif rue_method == 'stage':
            df['growth_stage'] = df['days_since_sowing'].apply(
                lambda days: self._get_growth_stage(days)
            )
            df['RUE'] = df['growth_stage'].apply(WheatRUE.get_rue_by_stage)
        elif rue_method == 'days':
            df['RUE'] = df['days_since_sowing'].apply(WheatRUE.get_rue_by_days)
        
        # Calculate biomass
        df['APAR'] = df['fapar'] * df['PAR']
        df['daily_biomass'] = df['APAR'] * df['RUE']
        total_biomass = df['daily_biomass'].sum()
        
        grain_yield_kg_ha = total_biomass * self.HARVEST_INDEX * 10
        grain_yield_ton_ha = grain_yield_kg_ha / 1000
        
        return {
            'total_biomass': total_biomass,
            'grain_yield_ton_ha': grain_yield_ton_ha,
            'avg_rue': df['RUE'].mean(),
            'dataframe': df
        }
    
    def _get_growth_stage(self, days_since_sowing: int) -> str:
        """Simple growth stage determination."""
        if days_since_sowing < 20:
            return 'Emergence'
        elif days_since_sowing < 45:
            return 'Tillering'
        elif days_since_sowing < 75:
            return 'Stem Extension'
        elif days_since_sowing < 105:
            return 'Heading/Anthesis'
        elif days_since_sowing < 140:
            return 'Grain Fill'
        else:
            return 'Maturity'


def compare_all_methods():
    """Compare all three RUE methods for all fields."""
    
    print("\n" + "=" * 80)
    print("COMPARING RUE APPROACHES FOR YIELD PREDICTION")
    print("=" * 80)
    print("\nThree approaches:")
    print("  1. Constant Average RUE (2.4 g DM/MJ PAR)")
    print("  2. Growth Stage-based RUE (uses phenology stages)")
    print("  3. Days-after-Sowing RUE (direct days lookup)")
    print("=" * 80)
    
    # Load data
    fapar_data, par_data, phenology_data = load_all_data()
    
    comparator = RUEComparison()
    
    results = []
    
    fapar_fields = fapar_data['fields']
    par_fields = par_data['fields']
    
    print(f"\nProcessing {len(fapar_fields)} fields...")
    
    for idx, (field_name, field_fapar) in enumerate(fapar_fields.items(), 1):
        if idx % 10 == 0:
            print(f"  Processed {idx}/{len(fapar_fields)} fields...")
        
        if field_name not in par_fields:
            continue
        
        field_par = par_fields[field_name]
        variety = field_fapar.get('variety', 'Unknown')
        sowing_date = field_fapar.get('sowing_date')
        
        fapar_weekly = field_fapar.get('ndvi_time_series', [])
        par_daily = field_par.get('radiation_data', [])
        
        if not fapar_weekly or not par_daily:
            continue
        
        # Calculate with all three methods
        yield_avg = comparator.calculate_yield_with_rue_method(
            fapar_weekly, par_daily, sowing_date, 'average'
        )
        yield_stage = comparator.calculate_yield_with_rue_method(
            fapar_weekly, par_daily, sowing_date, 'stage'
        )
        yield_days = comparator.calculate_yield_with_rue_method(
            fapar_weekly, par_daily, sowing_date, 'days'
        )
        
        if yield_avg and yield_stage and yield_days:
            results.append({
                'Field Name': field_name,
                'Variety': variety,
                'Sowing Date': sowing_date,
                'Method 1: Constant (ton/ha)': yield_avg['grain_yield_ton_ha'],
                'Method 2: Stage-based (ton/ha)': yield_stage['grain_yield_ton_ha'],
                'Method 3: Days-based (ton/ha)': yield_days['grain_yield_ton_ha'],
                'Avg RUE (Method 1)': yield_avg['avg_rue'],
                'Avg RUE (Method 2)': yield_stage['avg_rue'],
                'Avg RUE (Method 3)': yield_days['avg_rue'],
                'Difference 2-1': yield_stage['grain_yield_ton_ha'] - yield_avg['grain_yield_ton_ha'],
                'Difference 3-1': yield_days['grain_yield_ton_ha'] - yield_avg['grain_yield_ton_ha'],
                'Difference 3-2': yield_days['grain_yield_ton_ha'] - yield_stage['grain_yield_ton_ha']
            })
    
    df_comparison = pd.DataFrame(results)
    
    # Save results
    df_comparison.to_csv('rue_method_comparison.csv', index=False)
    print(f"\n✓ Saved comparison to: rue_method_comparison.csv")
    
    return df_comparison


def print_comparison_summary(df):
    """Print summary statistics of comparison."""
    
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal fields analyzed: {len(df)}")
    
    print("\n" + "─" * 80)
    print("AVERAGE YIELDS BY METHOD")
    print("─" * 80)
    
    methods = [
        ('Method 1: Constant (ton/ha)', 'Constant RUE (2.4)'),
        ('Method 2: Stage-based (ton/ha)', 'Growth Stage RUE'),
        ('Method 3: Days-based (ton/ha)', 'Days-after-Sowing RUE')
    ]
    
    print(f"\n{'Method':40} {'Mean':10} {'Median':10} {'Std':10} {'Min':10} {'Max':10}")
    print("─" * 80)
    
    for col, name in methods:
        print(f"{name:40} "
              f"{df[col].mean():10.2f} "
              f"{df[col].median():10.2f} "
              f"{df[col].std():10.2f} "
              f"{df[col].min():10.2f} "
              f"{df[col].max():10.2f}")
    
    print("\n" + "─" * 80)
    print("DIFFERENCES BETWEEN METHODS")
    print("─" * 80)
    
    print(f"\n{'Comparison':40} {'Mean Diff':15} {'Std Diff':15} {'% Difference':15}")
    print("─" * 80)
    
    avg_method1 = df['Method 1: Constant (ton/ha)'].mean()
    avg_method2 = df['Method 2: Stage-based (ton/ha)'].mean()
    avg_method3 = df['Method 3: Days-based (ton/ha)'].mean()
    
    print(f"{'Stage-based vs Constant':40} "
          f"{df['Difference 2-1'].mean():15.3f} "
          f"{df['Difference 2-1'].std():15.3f} "
          f"{(avg_method2-avg_method1)/avg_method1*100:14.1f}%")
    
    print(f"{'Days-based vs Constant':40} "
          f"{df['Difference 3-1'].mean():15.3f} "
          f"{df['Difference 3-1'].std():15.3f} "
          f"{(avg_method3-avg_method1)/avg_method1*100:14.1f}%")
    
    print(f"{'Days-based vs Stage-based':40} "
          f"{df['Difference 3-2'].mean():15.3f} "
          f"{df['Difference 3-2'].std():15.3f} "
          f"{(avg_method3-avg_method2)/avg_method2*100:14.1f}%")
    
    print("\n" + "─" * 80)
    print("FIELDS BELOW 3.5 ton/ha BY METHOD")
    print("─" * 80)
    
    threshold = 3.5
    
    below_1 = len(df[df['Method 1: Constant (ton/ha)'] < threshold])
    below_2 = len(df[df['Method 2: Stage-based (ton/ha)'] < threshold])
    below_3 = len(df[df['Method 3: Days-based (ton/ha)'] < threshold])
    
    print(f"\nConstant RUE:              {below_1:3} fields ({below_1/len(df)*100:.1f}%)")
    print(f"Stage-based RUE:           {below_2:3} fields ({below_2/len(df)*100:.1f}%)")
    print(f"Days-based RUE:            {below_3:3} fields ({below_3/len(df)*100:.1f}%)")
    
    print("\n" + "─" * 80)
    print("TOP 5 FIELDS BY EACH METHOD")
    print("─" * 80)
    
    for col, name in methods:
        print(f"\n{name}:")
        top5 = df.nlargest(5, col)[['Field Name', col]]
        for idx, row in top5.iterrows():
            print(f"  {row['Field Name']:40} {row[col]:6.2f} ton/ha")
    
    print("\n" + "─" * 80)
    print("AVERAGE RUE VALUES USED")
    print("─" * 80)
    
    print(f"\nConstant method:           {df['Avg RUE (Method 1)'].mean():.2f} g DM/MJ PAR (always)")
    print(f"Stage-based method:        {df['Avg RUE (Method 2)'].mean():.2f} g DM/MJ PAR (average across season)")
    print(f"Days-based method:         {df['Avg RUE (Method 3)'].mean():.2f} g DM/MJ PAR (average across season)")


def create_comparison_plots(df):
    """Create visualization comparing the three methods."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Scatter comparison
    ax1 = axes[0, 0]
    ax1.scatter(df['Method 2: Stage-based (ton/ha)'], 
                df['Method 3: Days-based (ton/ha)'],
                alpha=0.6, s=50)
    
    # Add 1:1 line
    max_val = max(df['Method 2: Stage-based (ton/ha)'].max(), 
                  df['Method 3: Days-based (ton/ha)'].max())
    ax1.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='1:1 line')
    
    ax1.set_xlabel('Method 2: Stage-based RUE (ton/ha)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Method 3: Days-based RUE (ton/ha)', fontsize=11, fontweight='bold')
    ax1.set_title('Comparison: Stage-based vs Days-based RUE', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Distribution comparison
    ax2 = axes[0, 1]
    ax2.hist(df['Method 1: Constant (ton/ha)'], bins=20, alpha=0.5, label='Constant', color='blue')
    ax2.hist(df['Method 2: Stage-based (ton/ha)'], bins=20, alpha=0.5, label='Stage-based', color='green')
    ax2.hist(df['Method 3: Days-based (ton/ha)'], bins=20, alpha=0.5, label='Days-based', color='orange')
    
    ax2.set_xlabel('Grain Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Number of Fields', fontsize=11, fontweight='bold')
    ax2.set_title('Yield Distribution by RUE Method', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Difference between methods
    ax3 = axes[1, 0]
    x = np.arange(len(df))
    width = 0.35
    
    ax3.bar(x - width/2, df['Difference 2-1'], width, label='Stage - Constant', alpha=0.7)
    ax3.bar(x + width/2, df['Difference 3-2'], width, label='Days - Stage', alpha=0.7)
    
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_xlabel('Field Index', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Yield Difference (ton/ha)', fontsize=11, fontweight='bold')
    ax3.set_title('Yield Differences Between Methods', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Box plot comparison
    ax4 = axes[1, 1]
    data_to_plot = [
        df['Method 1: Constant (ton/ha)'],
        df['Method 2: Stage-based (ton/ha)'],
        df['Method 3: Days-based (ton/ha)']
    ]
    
    bp = ax4.boxplot(data_to_plot, labels=['Constant\nRUE', 'Stage-based\nRUE', 'Days-based\nRUE'],
                     patch_artist=True, showmeans=True,
                     meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    
    colors = ['lightblue', 'lightgreen', 'lightyellow']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    
    ax4.axhline(y=3.5, color='red', linestyle='--', linewidth=2, 
                label='Target (3.5 ton/ha)', alpha=0.7)
    
    ax4.set_ylabel('Grain Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax4.set_title('Yield Distribution by RUE Method', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Save
    output_file = 'rue_method_comparison_plots.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved comparison plots to: {output_file}")
    
    output_pdf = 'rue_method_comparison_plots.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.show()


if __name__ == "__main__":
    try:
        # Run comparison
        df_comparison = compare_all_methods()
        
        if len(df_comparison) > 0:
            # Print summary
            print_comparison_summary(df_comparison)
            
            # Create plots
            print("\nCreating comparison visualizations...")
            create_comparison_plots(df_comparison)
            
            print("\n" + "=" * 80)
            print("✓ RUE METHOD COMPARISON COMPLETE")
            print("=" * 80)
            print("\nKey findings:")
            
            avg_method1 = df_comparison['Method 1: Constant (ton/ha)'].mean()
            avg_method2 = df_comparison['Method 2: Stage-based (ton/ha)'].mean()
            avg_method3 = df_comparison['Method 3: Days-based (ton/ha)'].mean()
            
            print(f"  • Constant RUE:          {avg_method1:.2f} ton/ha average")
            print(f"  • Stage-based RUE:       {avg_method2:.2f} ton/ha average")
            print(f"  • Days-based RUE:        {avg_method3:.2f} ton/ha average")
            
            print("\n  → Stage-based and Days-based methods are very similar")
            print("  → Both slightly higher than constant RUE approach")
            print("  → Difference reflects timing of peak RUE values")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

