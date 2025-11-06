"""
Visualization script for wheat phenology analysis results
"""

import json
from datetime import datetime
from collections import defaultdict


def print_timeline_chart(results):
    """Print a visual timeline of phenological stages."""
    print("\n" + "=" * 80)
    print("PHENOLOGICAL STAGE TIMELINE")
    print("=" * 80)
    
    # Group by variety
    by_variety = defaultdict(list)
    for result in results:
        by_variety[result['variety']].append(result)
    
    for variety, fields in sorted(by_variety.items()):
        print(f"\n{variety}:")
        print("─" * 80)
        
        # Sort by sowing date
        fields_sorted = sorted(fields, key=lambda x: x['sowing_date'])
        
        for field in fields_sorted[:5]:  # Show first 5 fields per variety
            stages = field['stage_dates']
            
            # Create visual timeline
            timeline = f"{field['field_name'][:30]:30} | "
            
            stage_symbols = {
                'sowing': '🌱',
                'emergence': '🌾',
                'tillering': '🌿',
                'stem_extension': '🌱',
                'heading': '🌾',
                'grain_fill': '🌾',
                'maturity': '✅'
            }
            
            achieved = []
            for stage, date in stages.items():
                if date:
                    achieved.append(stage_symbols.get(stage, '•'))
            
            timeline += ''.join(achieved)
            timeline += f" ({field['days_since_sowing']} days)"
            print(timeline)
        
        if len(fields_sorted) > 5:
            print(f"  ... and {len(fields_sorted) - 5} more fields")


def print_variety_comparison(results):
    """Print comparison of varieties."""
    print("\n" + "=" * 80)
    print("VARIETY PERFORMANCE COMPARISON")
    print("=" * 80)
    
    by_variety = defaultdict(list)
    for result in results:
        by_variety[result['variety']].append(result)
    
    comparison_data = []
    
    for variety, fields in by_variety.items():
        avg_gdd = sum(f['accumulated_gdd'] for f in fields) / len(fields)
        avg_days = sum(f['days_since_sowing'] for f in fields) / len(fields)
        
        # Count matured fields
        matured = sum(1 for f in fields if 'Maturity' in f['current_stage'])
        
        comparison_data.append({
            'variety': variety,
            'fields': len(fields),
            'avg_gdd': avg_gdd,
            'avg_days': avg_days,
            'matured': matured,
            'maturity_rate': (matured / len(fields)) * 100
        })
    
    # Sort by maturity rate
    comparison_data.sort(key=lambda x: x['maturity_rate'], reverse=True)
    
    print(f"\n{'Variety':20} {'Fields':8} {'Avg GDD':10} {'Avg Days':10} {'Matured':10} {'% Mature':10}")
    print("─" * 80)
    
    for data in comparison_data:
        print(f"{data['variety']:20} {data['fields']:8} "
              f"{data['avg_gdd']:10.1f} {data['avg_days']:10.1f} "
              f"{data['matured']:10} {data['maturity_rate']:9.1f}%")


def print_sowing_date_impact(results):
    """Analyze impact of sowing date on development."""
    print("\n" + "=" * 80)
    print("SOWING DATE IMPACT ON DEVELOPMENT")
    print("=" * 80)
    
    sowing_groups = defaultdict(list)
    
    for result in results:
        sowing_date = datetime.strptime(result['sowing_date'], '%Y-%m-%d')
        week_num = sowing_date.isocalendar()[1]
        sowing_groups[week_num].append(result)
    
    print(f"\n{'Sowing Week':15} {'Fields':8} {'Avg GDD':12} {'Stage Distribution':30}")
    print("─" * 80)
    
    for week, fields in sorted(sowing_groups.items()):
        avg_gdd = sum(f['accumulated_gdd'] for f in fields) / len(fields)
        
        # Count stages
        stage_counts = defaultdict(int)
        for f in fields:
            stage = f['current_stage'].split('(')[0].strip()
            stage_counts[stage] += 1
        
        stage_str = ", ".join([f"{stage[:10]}:{count}" for stage, count in stage_counts.items()])
        
        week_start = datetime.strptime(f'2025-W{week:02d}-1', '%Y-W%W-%w')
        week_label = week_start.strftime('%b %d')
        
        print(f"Week {week:2} ({week_label:6}) {len(fields):8} {avg_gdd:12.1f} {stage_str:30}")


def print_predicted_harvest_dates(results):
    """Estimate harvest dates for fields not yet mature."""
    print("\n" + "=" * 80)
    print("HARVEST READINESS FORECAST")
    print("=" * 80)
    
    mature_fields = [r for r in results if 'Maturity' in r['current_stage']]
    immature_fields = [r for r in results if 'Maturity' not in r['current_stage']]
    
    print(f"\nFields ready for harvest: {len(mature_fields)}")
    print(f"Fields still developing: {len(immature_fields)}")
    
    if immature_fields:
        print("\n" + "─" * 80)
        print("Fields approaching maturity (sorted by progress):")
        print("─" * 80)
        
        # Sort by progress
        immature_fields.sort(key=lambda x: x['stage_progress'], reverse=True)
        
        print(f"\n{'Field Name':30} {'Variety':15} {'Current Stage':25} {'Progress':10}")
        print("─" * 80)
        
        for field in immature_fields[:10]:
            progress_bar = '█' * int(field['stage_progress'] / 10) + '░' * (10 - int(field['stage_progress'] / 10))
            print(f"{field['field_name'][:30]:30} "
                  f"{field['variety'][:15]:15} "
                  f"{field['current_stage'][:25]:25} "
                  f"{progress_bar} {field['stage_progress']:.0f}%")


def print_critical_stages_report(results):
    """Report on fields at critical growth stages."""
    print("\n" + "=" * 80)
    print("CRITICAL GROWTH STAGES MONITORING")
    print("=" * 80)
    
    # Group by current stage
    by_stage = defaultdict(list)
    for result in results:
        stage = result['current_stage'].split('(')[0].strip()
        by_stage[stage].append(result)
    
    critical_stages = {
        'Heading/Anthesis': 'Critical for pollination - monitor weather conditions',
        'Grain Fill': 'Critical for yield - ensure adequate water and nutrients',
        'Maturity': 'Ready for harvest planning - monitor grain moisture'
    }
    
    for stage, message in critical_stages.items():
        if stage in by_stage:
            fields = by_stage[stage]
            print(f"\n{stage} - {len(fields)} fields")
            print(f"  ⚠️  {message}")
            
            # Show field names
            field_names = [f['field_name'] for f in fields[:10]]
            print(f"  Fields: {', '.join(field_names)}")
            if len(fields) > 10:
                print(f"  ... and {len(fields) - 10} more")


def main():
    """Main visualization function."""
    try:
        with open('phenology_analysis_results.json', 'r') as f:
            data = json.load(f)
        
        results = data['fields']
        
        print("\n" + "=" * 80)
        print("WHEAT PHENOLOGY VISUALIZATION REPORT")
        print("Las Petacas Wheat Fields")
        print(f"Analysis Date: {data['analysis_date']}")
        print("=" * 80)
        
        # Run all visualizations
        print_variety_comparison(results)
        print_timeline_chart(results)
        print_sowing_date_impact(results)
        print_critical_stages_report(results)
        print_predicted_harvest_dates(results)
        
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print("""
1. Harvest Planning:
   - Fields at Maturity stage should be prioritized for harvest
   - Monitor grain moisture content before harvesting
   - DM Alerce and DM Algarrobo varieties are mostly ready

2. Ongoing Management:
   - Fields in Grain Fill stage need adequate water
   - Monitor for diseases and pests, especially at heading stage
   - Weather monitoring is critical for harvest timing

3. Next Season Planning:
   - Consider variety selection based on maturity performance
   - Early-sown fields (May 21-23) showed good development
   - Evaluate variety performance for next year's planting decisions
        """)
        
    except FileNotFoundError:
        print("Error: phenology_analysis_results.json not found")
        print("Please run weather_phenology_analyzer.py first")


if __name__ == "__main__":
    main()

