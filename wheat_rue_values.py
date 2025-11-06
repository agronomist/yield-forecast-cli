"""
Wheat Radiation Use Efficiency (RUE) Values from Literature

This module provides RUE values for wheat based on literature review.
Values are provided for different growth stages to support yield prediction modeling.

RUE is expressed as: g dry matter / MJ absorbed PAR
"""

from typing import Dict


class WheatRUE:
    """
    Wheat Radiation Use Efficiency values from literature.
    
    These values represent the efficiency with which wheat converts
    absorbed photosynthetically active radiation (PAR) into biomass.
    """
    
    # Overall average RUE for wheat
    AVERAGE_RUE = 2.4  # g DM/MJ PAR (recommended baseline)
    
    # Range of reported values
    RUE_MIN = 2.0  # g DM/MJ PAR (conservative estimate)
    RUE_MAX = 2.8  # g DM/MJ PAR (optimal conditions)
    
    # RUE by growth stage (based on phenological development)
    RUE_BY_STAGE = {
        'Emergence': 2.0,           # Low efficiency, establishment phase
        'Tillering': 2.4,            # Increasing efficiency
        'Stem Extension': 2.7,       # Peak efficiency
        'Heading/Anthesis': 2.6,     # High efficiency maintained
        'Grain Fill': 2.2,           # Declining efficiency
        'Maturity': 1.8              # Lowest efficiency
    }
    
    # RUE by days after sowing (for continuous modeling)
    RUE_BY_DAYS = {
        (0, 20): 2.0,      # Emergence
        (20, 45): 2.4,     # Tillering
        (45, 75): 2.7,     # Stem Extension
        (75, 105): 2.6,    # Heading/Anthesis
        (105, 125): 2.3,   # Early Grain Fill
        (125, 145): 2.0,   # Late Grain Fill
        (145, 999): 1.8    # Maturity
    }
    
    # RUE by Zadoks scale
    RUE_BY_ZADOKS = {
        (10, 20): 2.0,     # Emergence
        (20, 29): 2.4,     # Tillering
        (30, 39): 2.7,     # Stem Extension
        (40, 69): 2.6,     # Heading/Anthesis
        (70, 85): 2.3,     # Early Grain Fill
        (85, 90): 2.0,     # Late Grain Fill
        (90, 92): 1.8      # Maturity
    }
    
    @staticmethod
    def get_rue_by_stage(stage: str) -> float:
        """
        Get RUE value for a specific growth stage.
        
        Args:
            stage: Growth stage name (e.g., 'Tillering', 'Grain Fill')
            
        Returns:
            RUE value in g DM/MJ PAR
        """
        # Handle stage names with Zadoks notation
        stage_clean = stage.split('(')[0].strip()
        
        # Map common variations
        stage_mappings = {
            'Stem Extension': 'Stem Extension',
            'Heading': 'Heading/Anthesis',
            'Anthesis': 'Heading/Anthesis',
            'Grain Fill': 'Grain Fill',
            'Flowering': 'Heading/Anthesis'
        }
        
        for key, value in stage_mappings.items():
            if key in stage_clean:
                stage_clean = value
                break
        
        return WheatRUE.RUE_BY_STAGE.get(stage_clean, WheatRUE.AVERAGE_RUE)
    
    @staticmethod
    def get_rue_by_days(days_since_sowing: int) -> float:
        """
        Get RUE value based on days since sowing.
        
        Args:
            days_since_sowing: Number of days since sowing
            
        Returns:
            RUE value in g DM/MJ PAR
        """
        for (min_days, max_days), rue in WheatRUE.RUE_BY_DAYS.items():
            if min_days <= days_since_sowing < max_days:
                return rue
        
        return WheatRUE.AVERAGE_RUE
    
    @staticmethod
    def get_rue_summary() -> Dict:
        """
        Get summary of all RUE values.
        
        Returns:
            Dictionary with RUE values and metadata
        """
        return {
            'description': 'Wheat Radiation Use Efficiency values from literature',
            'units': 'g dry matter / MJ absorbed PAR',
            'average_rue': WheatRUE.AVERAGE_RUE,
            'rue_range': (WheatRUE.RUE_MIN, WheatRUE.RUE_MAX),
            'rue_by_stage': WheatRUE.RUE_BY_STAGE,
            'source': 'Literature compilation (Sinclair & Muchow 1999, Kiniry et al. 1989)',
            'application': 'For biomass and yield prediction',
            'notes': [
                'RUE varies by growth stage',
                'Peak efficiency during stem extension',
                'Declining efficiency during senescence',
                'Values represent optimal to good conditions',
                'Adjust for stress (water, nitrogen, temperature)'
            ]
        }


def print_rue_summary():
    """Print a formatted summary of RUE values."""
    print("=" * 80)
    print("WHEAT RADIATION USE EFFICIENCY (RUE) VALUES")
    print("=" * 80)
    print("\nBased on literature review for wheat crops")
    print("Units: g dry matter / MJ absorbed PAR")
    
    print("\n" + "─" * 80)
    print("OVERALL VALUES")
    print("─" * 80)
    print(f"Average RUE (recommended):  {WheatRUE.AVERAGE_RUE} g DM/MJ PAR")
    print(f"Range:                       {WheatRUE.RUE_MIN} - {WheatRUE.RUE_MAX} g DM/MJ PAR")
    
    print("\n" + "─" * 80)
    print("RUE BY GROWTH STAGE")
    print("─" * 80)
    print(f"{'Growth Stage':25} {'RUE (g DM/MJ PAR)':20} {'Notes':30}")
    print("─" * 80)
    
    stage_notes = {
        'Emergence': 'Establishment phase',
        'Tillering': 'Increasing LAI',
        'Stem Extension': 'Peak efficiency',
        'Heading/Anthesis': 'Maximum biomass',
        'Grain Fill': 'Beginning senescence',
        'Maturity': 'Minimal growth'
    }
    
    for stage, rue in WheatRUE.RUE_BY_STAGE.items():
        note = stage_notes.get(stage, '')
        print(f"{stage:25} {rue:20.1f} {note:30}")
    
    print("\n" + "─" * 80)
    print("RUE BY DAYS AFTER SOWING")
    print("─" * 80)
    print(f"{'Days Range':20} {'RUE (g DM/MJ PAR)':20} {'Growth Stage':25}")
    print("─" * 80)
    
    day_stages = {
        (0, 20): 'Emergence',
        (20, 45): 'Tillering',
        (45, 75): 'Stem Extension',
        (75, 105): 'Heading/Anthesis',
        (105, 125): 'Early Grain Fill',
        (125, 145): 'Late Grain Fill',
        (145, 999): 'Maturity'
    }
    
    for days, rue in WheatRUE.RUE_BY_DAYS.items():
        stage = day_stages[days]
        day_range = f"{days[0]}-{days[1] if days[1] < 999 else '145+'}"
        print(f"{day_range:20} {rue:20.1f} {stage:25}")
    
    print("\n" + "=" * 80)
    print("APPLICATION NOTES")
    print("=" * 80)
    print("""
These RUE values can be used for:

1. Biomass Estimation:
   Daily_Biomass = fAPAR × PAR × RUE
   
2. Yield Prediction:
   Total_Biomass = Σ(Daily_Biomass)
   Yield = Total_Biomass × Harvest_Index
   
3. Growth Stage Tracking:
   Use phenology model to assign appropriate RUE
   
Key Points:
- RUE is highest during vegetative growth (stem extension)
- RUE declines during grain filling and maturity
- Values assume optimal to good growing conditions
- Adjust for known stress factors (water, N, temperature)
- Validate with actual yield data when available

References:
- Sinclair & Muchow (1999): Radiation use efficiency
- Kiniry et al. (1989): RUE in grain crops
- Kemanian et al. (2004): Wheat RUE estimation
    """)


def example_usage():
    """Show example usage of RUE functions."""
    print("\n" + "=" * 80)
    print("EXAMPLE USAGE")
    print("=" * 80)
    
    # Example 1: Get RUE by stage
    print("\nExample 1: Get RUE by growth stage")
    print("─" * 80)
    stage = "Stem Extension (Zadoks 30)"
    rue = WheatRUE.get_rue_by_stage(stage)
    print(f"Growth Stage: {stage}")
    print(f"RUE: {rue} g DM/MJ PAR")
    
    # Example 2: Get RUE by days
    print("\nExample 2: Get RUE by days since sowing")
    print("─" * 80)
    days = 80
    rue = WheatRUE.get_rue_by_days(days)
    print(f"Days since sowing: {days}")
    print(f"RUE: {rue} g DM/MJ PAR")
    
    # Example 3: Calculate biomass
    print("\nExample 3: Calculate daily biomass accumulation")
    print("─" * 80)
    fapar = 0.75  # from NDVI
    par_incident = 10.0  # MJ/m²/day
    rue = 2.6  # g DM/MJ PAR
    
    apar = fapar * par_incident  # absorbed PAR
    daily_biomass = apar * rue
    
    print(f"fAPAR: {fapar}")
    print(f"Incident PAR: {par_incident} MJ/m²/day")
    print(f"RUE: {rue} g DM/MJ PAR")
    print(f"Absorbed PAR: {apar} MJ/m²/day")
    print(f"Daily Biomass: {daily_biomass} g DM/m²/day")
    print(f"              = {daily_biomass * 10} kg DM/ha/day")


if __name__ == "__main__":
    # Print summary
    print_rue_summary()
    
    # Show examples
    example_usage()
    
    print("\n" + "=" * 80)
    print("RUE values are ready to use for yield prediction modeling")
    print("See wheat_RUE_literature_values.md for detailed documentation")
    print("=" * 80)

