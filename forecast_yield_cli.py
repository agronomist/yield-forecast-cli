#!/usr/bin/env python3
"""
Wheat Yield Forecasting CLI Tool

This tool provides a command-line interface to forecast wheat yield for any field
using Sentinel-2 data via Statistical API.

Usage:
    python forecast_yield_cli.py <field.geojson>

The tool will:
1. Load the field geometry from GeoJSON
2. Prompt for planting date and variety
3. Fetch Sentinel-2 NDVI data
4. Fetch solar radiation (PAR) data
5. Calculate phenology stages
6. Calculate biomass accumulation
7. Predict final yield

Requirements:
    - Sentinel Hub OAuth credentials (CLIENT_ID and CLIENT_SECRET)
    - GeoJSON file with field polygon
    - Internet connection for API calls
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

import requests
import pandas as pd
import numpy as np

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# Rich for beautiful terminal output (Next.js-style prompts)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠ Warning: 'rich' package not found. Install with: pip install rich")
    print("   Falling back to basic prompts...")

# Inquirer for interactive selection
try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    print("⚠ Warning: 'inquirer' package not found. Install with: pip install inquirer")
    print("   Falling back to basic selection...")

# Import local modules
from sentinel_ndvi_fetcher import SentinelHubNDVIFetcher
from wheat_phenology_model import WheatPhenologyModel
from wheat_rue_values import WheatRUE
from calculate_fapar import calculate_fapar


class YieldForecastCLI:
    """CLI tool for wheat yield forecasting."""
    
    # Harvest index for yield calculation
    HARVEST_INDEX = 0.45
    HARVEST_INDEX_RANGE = (0.40, 0.50)
    
    # Available wheat varieties (comprehensive list based on CRONOTRIGO/FAUBA model)
    # Organized by breeder for easier selection
    VARIETIES = [
        # Don Mario (DM) Varieties
        "DM Alerce",
        "DM Algarrobo",
        "DM Aromo",
        "DM Ceibo",
        "DM Cóndor",
        "DM Guatambú",
        "DM Ñandubay",
        "DM Ñire",
        "DM Pehuen",
        "DM Quebracho",
        "DM Timbó",
        "DM Yaguareté",
        # ACA Varieties
        "ACA 303",
        "ACA 304",
        "ACA 315",
        "ACA 360",
        "ACA 365",
        "ACA 601",
        "ACA 602",
        "ACA Fresno",
        # Buck (BG) Varieties
        "BG 610",
        "BG 620",
        "BG 630",
        "BG 720",
        "BG 750",
        # Baguette Varieties
        "Baguette 601",
        "Baguette 620",
        "Baguette 750",
        # Bio4 Varieties
        "Bio4 Baguette 601",
        "Bio4 Baguette 620",
        # Klein Varieties
        "Klein Cacique",
        "Klein Guerrero",
        "Klein Proteo",
        "Klein Rayén",
        "Klein Sagitario",
        # Syngenta (SY) Varieties
        "SY 100",
        "SY 200",
        "SY 300",
        # Other Common Varieties
        "Bienvenido",
        "Cronox",
        "Relmo",
        "Sursem",
        "Taita",
        # Default option
        "Other (Default parameters)"
    ]
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the CLI tool.
        
        Args:
            client_id: Sentinel Hub OAuth client ID
            client_secret: Sentinel Hub OAuth client secret
        """
        self.ndvi_fetcher = SentinelHubNDVIFetcher(client_id, client_secret)
        self.client_id = client_id
        self.client_secret = client_secret
        self.console = Console() if RICH_AVAILABLE else None
        
    def load_geojson(self, geojson_path: str) -> Dict:
        """
        Load field geometry from GeoJSON file.
        
        Args:
            geojson_path: Path to GeoJSON file
            
        Returns:
            Dictionary with geometry and metadata
        """
        if self.console:
            self.console.print(f"\n[bold cyan]📁 Loading GeoJSON[/bold cyan]")
            self.console.print(f"[dim]{geojson_path}[/dim]")
        else:
            print(f"\n📁 Loading GeoJSON: {geojson_path}")
        
        try:
            with open(geojson_path, 'r') as f:
                data = json.load(f)
            
            # Handle FeatureCollection
            if data.get('type') == 'FeatureCollection':
                if len(data['features']) == 0:
                    raise ValueError("GeoJSON FeatureCollection is empty")
                feature = data['features'][0]
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
            # Handle Feature
            elif data.get('type') == 'Feature':
                geometry = data.get('geometry', {})
                properties = data.get('properties', {})
            # Handle direct geometry
            elif data.get('type') == 'Polygon':
                geometry = data
                properties = {}
            else:
                raise ValueError(f"Unsupported GeoJSON type: {data.get('type')}")
            
            if geometry.get('type') != 'Polygon':
                raise ValueError(f"Expected Polygon geometry, got: {geometry.get('type')}")
            
            # Extract coordinates
            coordinates = geometry['coordinates'][0]
            
            # Calculate center point for PAR fetching
            lons = [c[0] for c in coordinates]
            lats = [c[1] for c in coordinates]
            center_lon = sum(lons) / len(lons)
            center_lat = sum(lats) / len(lats)
            
            # Calculate bounding box
            bbox = [min(lons), min(lats), max(lons), max(lats)]
            
            result = {
                'geometry': geometry,
                'properties': properties,
                'coordinates': coordinates,
                'center': {'lon': center_lon, 'lat': center_lat},
                'bbox': bbox
            }
            
            if self.console:
                self.console.print(f"[green]✓[/green] Loaded field geometry")
                self.console.print(f"  [dim]Center:[/dim] {center_lat:.6f}°N, {center_lon:.6f}°E")
                self.console.print(f"  [dim]Bounding box:[/dim] {bbox}")
            else:
                print(f"✓ Loaded field geometry")
                print(f"  Center: {center_lat:.6f}°N, {center_lon:.6f}°E")
                print(f"  Bounding box: {bbox}")
            
            return result
            
        except FileNotFoundError:
            error_msg = f"File not found: {geojson_path}"
            if self.console:
                self.console.print(f"[red]✗ Error:[/red] {error_msg}")
            else:
                print(f"✗ Error: {error_msg}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {e}"
            if self.console:
                self.console.print(f"[red]✗ Error:[/red] {error_msg}")
            else:
                print(f"✗ Error: {error_msg}")
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error loading GeoJSON: {e}"
            if self.console:
                self.console.print(f"[red]✗ Error:[/red] {error_msg}")
            else:
                print(f"✗ Error: {error_msg}")
            sys.exit(1)
    
    def prompt_planting_date(self) -> str:
        """
        Prompt user for planting date (Next.js-style).
        
        Returns:
            Planting date in YYYY-MM-DD format
        """
        if self.console:
            self.console.print("\n[bold cyan]📅 Planting Date[/bold cyan]")
            self.console.print("[dim]Enter the date when the field was planted[/dim]")
        
        while True:
            if self.console:
                date_str = Prompt.ask(
                    "[bold]?[/bold] When was the field planted? (YYYY-MM-DD)"
                ).strip()
            else:
                date_str = input("\n📅 Enter planting date (YYYY-MM-DD): ").strip()
            
            try:
                # Validate date format
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Check if date is reasonable (not too far in future)
                if date_obj > datetime.now():
                    if self.console:
                        self.console.print("[yellow]⚠ Warning:[/yellow] Planting date is in the future.")
                        if not Confirm.ask("Continue anyway?", default=False):
                            continue
                    else:
                        if input("⚠ Warning: Planting date is in the future. Continue? (y/n): ").strip().lower() != 'y':
                            continue
                
                # Check if date is not too old (before 2020)
                if date_obj < datetime(2020, 1, 1):
                    if self.console:
                        self.console.print("[yellow]⚠ Warning:[/yellow] Planting date is before 2020.")
                        if not Confirm.ask("Continue anyway?", default=False):
                            continue
                    else:
                        if input("⚠ Warning: Planting date is before 2020. Continue? (y/n): ").strip().lower() != 'y':
                            continue
                
                if self.console:
                    self.console.print(f"[green]✓[/green] Planting date: [bold]{date_str}[/bold]")
                
                return date_str
                
            except ValueError:
                error_msg = "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-05-15)"
                if self.console:
                    self.console.print(f"[red]✗[/red] {error_msg}")
                else:
                    print(f"✗ {error_msg}")
    
    def prompt_variety(self) -> str:
        """
        Prompt user to select wheat variety (Next.js-style).
        
        Returns:
            Selected variety name
        """
        if self.console:
            self.console.print("\n[bold cyan]🌾 Wheat Variety[/bold cyan]")
            self.console.print("[dim]Select the wheat variety planted in this field[/dim]")
        
        # Use inquirer for interactive selection if available
        if INQUIRER_AVAILABLE:
            questions = [
                inquirer.List(
                    'variety',
                    message="Select wheat variety",
                    choices=self.VARIETIES,
                    carousel=True
                )
            ]
            answers = inquirer.prompt(questions)
            selected = answers['variety']
            
            if self.console:
                self.console.print(f"[green]✓[/green] Selected: [bold]{selected}[/bold]")
            else:
                print(f"✓ Selected: {selected}")
            
            return selected
        
        # Fallback to rich table or basic selection
        if self.console:
            # Create a styled table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("No.", style="cyan", width=4)
            table.add_column("Variety", style="green")
            
            for i, variety in enumerate(self.VARIETIES, 1):
                table.add_row(str(i), variety)
            
            self.console.print(table)
            
            while True:
                try:
                    choice = Prompt.ask(
                        "[bold]?[/bold] Select variety",
                        default="1"
                    ).strip()
                    choice_num = int(choice)
                    
                    if 1 <= choice_num <= len(self.VARIETIES):
                        selected = self.VARIETIES[choice_num - 1]
                        self.console.print(f"[green]✓[/green] Selected: [bold]{selected}[/bold]")
                        return selected
                    else:
                        self.console.print(f"[red]✗[/red] Please enter a number between 1 and {len(self.VARIETIES)}")
                except ValueError:
                    self.console.print("[red]✗[/red] Please enter a valid number")
        else:
            # Basic fallback
            print("\n🌾 Select wheat variety:")
            print("-" * 50)
            
            for i, variety in enumerate(self.VARIETIES, 1):
                print(f"  {i}. {variety}")
            
            print("-" * 50)
            
            while True:
                try:
                    choice = input("Enter number (1-9): ").strip()
                    choice_num = int(choice)
                    
                    if 1 <= choice_num <= len(self.VARIETIES):
                        selected = self.VARIETIES[choice_num - 1]
                        print(f"✓ Selected: {selected}")
                        return selected
                    else:
                        print(f"✗ Please enter a number between 1 and {len(self.VARIETIES)}")
                except ValueError:
                    print("✗ Please enter a valid number")
    
    def fetch_ndvi_data(
        self,
        field_name: str,
        geometry: Dict,
        bbox: List[float],
        planting_date: str,
        end_date: str = None
    ) -> List[Dict]:
        """
        Fetch NDVI data from Sentinel-2 Statistical API.
        
        Args:
            field_name: Name of the field
            geometry: GeoJSON geometry
            bbox: Bounding box
            planting_date: Planting date (YYYY-MM-DD)
            end_date: End date for data fetch (default: day before yesterday)
            
        Returns:
            List of NDVI observations
        """
        if self.console:
            self.console.print(f"\n[bold cyan]🛰️  Fetching Sentinel-2 NDVI data[/bold cyan]")
            self.console.print(f"  [dim]Planting date:[/dim] {planting_date}")
        else:
            print(f"\n🛰️  Fetching Sentinel-2 NDVI data...")
            print(f"   Planting date: {planting_date}")
        
        # Calculate end date (day before yesterday, but not before planting date)
        if end_date is None:
            today = datetime.now().date()
            day_before_yesterday = today - timedelta(days=2)
            planting_dt = datetime.strptime(planting_date, '%Y-%m-%d').date()
            # Use day before yesterday, but not before planting date
            end_dt = max(day_before_yesterday, planting_dt)
            end_date = end_dt.strftime('%Y-%m-%d')
        
        if self.console:
            self.console.print(f"  [dim]Time range:[/dim] {planting_date} to {end_date}")
        else:
            print(f"   Time range: {planting_date} to {end_date}")
        
        try:
            # Authenticate with progress
            if self.console:
                with self.console.status("[bold green]Authenticating with Sentinel Hub...") as status:
                    self.ndvi_fetcher.authenticate()
            else:
                self.ndvi_fetcher.authenticate()
            
            # Fetch NDVI data with progress
            if self.console:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console
                ) as progress:
                    task = progress.add_task("Fetching NDVI data...", total=None)
                    ndvi_data = self.ndvi_fetcher.fetch_ndvi_time_series(
                        field_name=field_name,
                        geometry=geometry,
                        sowing_date=planting_date,
                        end_date=end_date
                    )
                    progress.update(task, completed=True)
            else:
                ndvi_data = self.ndvi_fetcher.fetch_ndvi_time_series(
                    field_name=field_name,
                    geometry=geometry,
                    sowing_date=planting_date,
                    end_date=end_date
                )
            
            if ndvi_data:
                if self.console:
                    self.console.print(f"[green]✓[/green] Retrieved [bold]{len(ndvi_data)}[/bold] NDVI observations")
                else:
                    print(f"✓ Retrieved {len(ndvi_data)} NDVI observations")
                return ndvi_data
            else:
                if self.console:
                    self.console.print("[yellow]⚠ Warning:[/yellow] No NDVI data retrieved")
                else:
                    print("⚠ Warning: No NDVI data retrieved")
                return []
                
        except Exception as e:
            print(f"✗ Error fetching NDVI data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_par_data(
        self,
        latitude: float,
        longitude: float,
        planting_date: str,
        end_date: str = None
    ) -> List[Dict]:
        """
        Fetch PAR (Photosynthetically Active Radiation) data.
        
        Args:
            latitude: Field latitude
            longitude: Field longitude
            planting_date: Planting date (YYYY-MM-DD)
            end_date: End date (default: day before yesterday)
            
        Returns:
            List of daily PAR observations
        """
        if self.console:
            self.console.print(f"\n[bold cyan]☀️  Fetching solar radiation (PAR) data[/bold cyan]")
        else:
            print(f"\n☀️  Fetching solar radiation (PAR) data...")
        
        # Calculate end date (day before yesterday, but not before planting date)
        if end_date is None:
            today = datetime.now().date()
            day_before_yesterday = today - timedelta(days=2)
            planting_dt = datetime.strptime(planting_date, '%Y-%m-%d').date()
            # Use day before yesterday, but not before planting date
            end_dt = max(day_before_yesterday, planting_dt)
            end_date = end_dt.strftime('%Y-%m-%d')
        
        try:
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": planting_date,
                "end_date": end_date,
                "daily": "shortwave_radiation_sum",
                "timezone": "America/Argentina/Buenos_Aires"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            par_records = []
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            radiation_list = daily.get('shortwave_radiation_sum', [])
            
            for i, date in enumerate(dates):
                total_radiation = radiation_list[i] if radiation_list[i] is not None else None
                # Convert to PAR (48% of total solar radiation)
                par = total_radiation * 0.48 if total_radiation is not None else None
                
                if par is not None:
                    par_records.append({
                        'date': date,
                        'PAR_MJ': par
                    })
            
            if par_records:
                if self.console:
                    self.console.print(f"[green]✓[/green] Retrieved [bold]{len(par_records)}[/bold] daily PAR observations")
                else:
                    print(f"✓ Retrieved {len(par_records)} daily PAR observations")
                return par_records
            else:
                if self.console:
                    self.console.print("[yellow]⚠ Warning:[/yellow] No PAR data retrieved")
                else:
                    print("⚠ Warning: No PAR data retrieved")
                return []
                
        except Exception as e:
            error_msg = f"Error fetching PAR data: {e}"
            if self.console:
                self.console.print(f"[red]✗[/red] {error_msg}")
            else:
                print(f"✗ {error_msg}")
            return []
    
    def calculate_phenology(
        self,
        variety: str,
        planting_date: str,
        latitude: float,
        par_data: List[Dict]
    ) -> Dict:
        """
        Calculate phenology stages.
        
        Args:
            variety: Wheat variety
            planting_date: Planting date
            latitude: Field latitude
            par_data: PAR data (for date range)
            
        Returns:
            Dictionary with phenology stage dates
        """
        if self.console:
            self.console.print(f"\n[bold cyan]🌱 Calculating phenology stages[/bold cyan]")
        else:
            print(f"\n🌱 Calculating phenology stages...")
        
        try:
            # Initialize phenology model
            phenology = WheatPhenologyModel(variety, planting_date, latitude)
            
            # Get temperature data for GDD calculation
            # For now, use simplified approach based on days
            # In production, you'd fetch temperature data
            
            # Estimate growth stages based on days
            planting_dt = datetime.strptime(planting_date, '%Y-%m-%d')
            
            # Use typical values (in production, calculate GDD from temperature)
            stages = {
                'sowing': planting_date,
                'emergence': (planting_dt + timedelta(days=15)).strftime('%Y-%m-%d'),
                'tillering': (planting_dt + timedelta(days=35)).strftime('%Y-%m-%d'),
                'stem_extension': (planting_dt + timedelta(days=60)).strftime('%Y-%m-%d'),
                'heading': (planting_dt + timedelta(days=90)).strftime('%Y-%m-%d'),
                'anthesis': (planting_dt + timedelta(days=110)).strftime('%Y-%m-%d'),
                'grain_fill': (planting_dt + timedelta(days=125)).strftime('%Y-%m-%d'),
                'maturity': (planting_dt + timedelta(days=150)).strftime('%Y-%m-%d')
            }
            
            if self.console:
                self.console.print(f"[green]✓[/green] Calculated phenology stages")
            else:
                print(f"✓ Calculated phenology stages")
            return stages
            
        except Exception as e:
            error_msg = f"Error calculating phenology: {e}"
            if self.console:
                self.console.print(f"[red]✗[/red] {error_msg}")
            else:
                print(f"✗ {error_msg}")
            return {}
    
    def calculate_biomass_and_yield(
        self,
        field_name: str,
        variety: str,
        planting_date: str,
        ndvi_data: List[Dict],
        par_data: List[Dict],
        phenology_stages: Dict
    ) -> Dict:
        """
        Calculate biomass accumulation and yield.
        
        Args:
            field_name: Field name
            variety: Wheat variety
            planting_date: Planting date
            ndvi_data: NDVI observations
            par_data: Daily PAR data
            phenology_stages: Phenology stage dates
            
        Returns:
            Dictionary with yield prediction results
        """
        if self.console:
            self.console.print(f"\n[bold cyan]📊 Calculating biomass and yield[/bold cyan]")
        else:
            print(f"\n📊 Calculating biomass and yield...")
        
        try:
            # Convert NDVI to fAPAR
            fapar_weekly = []
            for obs in ndvi_data:
                if obs.get('ndvi_mean') is not None:
                    fapar = calculate_fapar(obs['ndvi_mean'])
                    fapar_weekly.append({
                        'from': obs.get('from', obs.get('date', '')),
                        'to': obs.get('to', obs.get('date', '')),
                        'fapar_mean': fapar
                    })
            
            if not fapar_weekly:
                print("✗ No valid fAPAR data")
                return {}
            
            # Interpolate fAPAR to daily
            planting_dt = datetime.strptime(planting_date, '%Y-%m-%d')
            par_df = pd.DataFrame(par_data)
            if par_df.empty:
                print("✗ No PAR data available")
                return {}
            
            par_df['date'] = pd.to_datetime(par_df['date'])
            end_date = par_df['date'].max()
            
            # Create daily fAPAR
            weekly_df = []
            for obs in fapar_weekly:
                week_start = datetime.strptime(obs['from'], '%Y-%m-%d')
                week_end = datetime.strptime(obs['to'], '%Y-%m-%d')
                mid_date = week_start + (week_end - week_start) / 2
                weekly_df.append({
                    'date': mid_date,
                    'fapar': obs['fapar_mean']
                })
            
            if not weekly_df:
                print("✗ No weekly fAPAR data")
                return {}
            
            weekly_df = pd.DataFrame(weekly_df).sort_values('date')
            date_range = pd.date_range(start=planting_dt, end=end_date, freq='D')
            daily_df = pd.DataFrame({'date': date_range})
            
            # Merge and interpolate
            combined = pd.concat([weekly_df, daily_df]).sort_values('date').drop_duplicates('date')
            combined['fapar'] = combined['fapar'].interpolate(method='linear', limit_direction='both')
            daily_fapar = combined[combined['date'].isin(date_range)].reset_index(drop=True)
            
            # Merge with PAR
            par_df['date'] = pd.to_datetime(par_df['date'])
            daily_df = pd.merge(daily_fapar, par_df, on='date', how='inner')
            
            # Calculate days since sowing
            daily_df['days_since_sowing'] = (daily_df['date'] - planting_dt).dt.days
            
            # Get growth stage and RUE for each day
            daily_df['growth_stage'] = daily_df['days_since_sowing'].apply(
                lambda days: self._get_growth_stage(days)
            )
            daily_df['RUE'] = daily_df['growth_stage'].apply(WheatRUE.get_rue_by_stage)
            
            # Calculate daily biomass
            daily_df['APAR'] = daily_df['fapar'] * daily_df['PAR_MJ']
            daily_df['daily_biomass_g_m2'] = daily_df['APAR'] * daily_df['RUE']
            
            # Calculate cumulative biomass
            daily_df['cumulative_biomass_g_m2'] = daily_df['daily_biomass_g_m2'].cumsum()
            
            # Get final biomass
            total_biomass_g_m2 = daily_df['daily_biomass_g_m2'].sum()
            total_biomass_kg_ha = total_biomass_g_m2 * 10
            total_biomass_ton_ha = total_biomass_kg_ha / 1000
            
            # Calculate yield
            grain_yield_ton_ha = total_biomass_ton_ha * self.HARVEST_INDEX
            grain_yield_kg_ha = grain_yield_ton_ha * 1000
            
            # Calculate yield range
            yield_low = total_biomass_ton_ha * self.HARVEST_INDEX_RANGE[0]
            yield_high = total_biomass_ton_ha * self.HARVEST_INDEX_RANGE[1]
            
            result = {
                'field_name': field_name,
                'variety': variety,
                'planting_date': planting_date,
                'total_biomass_g_m2': round(total_biomass_g_m2, 2),
                'total_biomass_kg_ha': round(total_biomass_kg_ha, 2),
                'total_biomass_ton_ha': round(total_biomass_ton_ha, 3),
                'grain_yield_kg_ha': round(grain_yield_kg_ha, 2),
                'grain_yield_ton_ha': round(grain_yield_ton_ha, 3),
                'yield_range_ton_ha': (round(yield_low, 3), round(yield_high, 3)),
                'harvest_index': self.HARVEST_INDEX,
                'days_of_data': len(daily_df),
                'ndvi_observations': len(ndvi_data),
                'par_days': len(par_data),
                'daily_data': daily_df.to_dict('records') if len(daily_df) <= 200 else None  # Limit size
            }
            
            print(f"✓ Calculated yield prediction")
            return result
            
        except Exception as e:
            print(f"✗ Error calculating yield: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_growth_stage(self, days_since_sowing: int) -> str:
        """Get growth stage based on days since sowing."""
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
    
    def print_results(self, results: Dict):
        """Print yield forecast results (Next.js-style)."""
        if not results:
            if self.console:
                self.console.print("\n[red]✗[/red] No results to display")
            else:
                print("\n✗ No results to display")
            return
        
        if self.console:
            # Create a beautiful results panel
            results_text = f"""
[bold]📍 Field:[/bold] {results['field_name']}
[bold]🌾 Variety:[/bold] {results['variety']}
[bold]📅 Planting Date:[/bold] {results['planting_date']}

[bold cyan]📊 Biomass Accumulation[/bold cyan]
  Total Biomass: [bold]{results['total_biomass_ton_ha']:.3f}[/bold] ton/ha
                  {results['total_biomass_kg_ha']:.0f} kg/ha

[bold green]🌾 Yield Prediction[/bold green]
  Grain Yield:  [bold]{results['grain_yield_ton_ha']:.3f}[/bold] ton/ha
                 {results['grain_yield_kg_ha']:.0f} kg/ha
  Yield Range:  {results['yield_range_ton_ha'][0]:.3f} - {results['yield_range_ton_ha'][1]:.3f} ton/ha

[bold yellow]📈 Data Summary[/bold yellow]
  NDVI Observations: {results['ndvi_observations']}
  PAR Days: {results['par_days']}
  Days Calculated: {results['days_of_data']}
  Harvest Index: {results['harvest_index']}
            """
            
            panel = Panel(
                results_text.strip(),
                title="[bold green]✓ Yield Forecast Results[/bold green]",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print("\n")
            self.console.print(panel)
        else:
            print("\n" + "=" * 80)
            print("YIELD FORECAST RESULTS")
            print("=" * 80)
            
            print(f"\n📍 Field: {results['field_name']}")
            print(f"🌾 Variety: {results['variety']}")
            print(f"📅 Planting Date: {results['planting_date']}")
            
            print(f"\n📊 Biomass Accumulation:")
            print(f"   Total Biomass: {results['total_biomass_ton_ha']:.3f} ton/ha")
            print(f"                   {results['total_biomass_kg_ha']:.0f} kg/ha")
            
            print(f"\n🌾 Yield Prediction:")
            print(f"   Grain Yield:  {results['grain_yield_ton_ha']:.3f} ton/ha")
            print(f"                  {results['grain_yield_kg_ha']:.0f} kg/ha")
            print(f"   Yield Range:  {results['yield_range_ton_ha'][0]:.3f} - {results['yield_range_ton_ha'][1]:.3f} ton/ha")
            
            print(f"\n📈 Data Summary:")
            print(f"   NDVI Observations: {results['ndvi_observations']}")
            print(f"   PAR Days: {results['par_days']}")
            print(f"   Days Calculated: {results['days_of_data']}")
            print(f"   Harvest Index: {results['harvest_index']}")
            
            print("\n" + "=" * 80)
        
        # Save results to JSON
        output_file = f"yield_forecast_{results['field_name'].replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        if self.console:
            self.console.print(f"\n[bold cyan]💾[/bold cyan] Results saved to: [bold]{output_file}[/bold]")
        else:
            print(f"\n💾 Results saved to: {output_file}")
    
    def run(self, geojson_path: str):
        """
        Run the complete yield forecasting workflow.
        
        Args:
            geojson_path: Path to GeoJSON file
        """
        if self.console:
            welcome_text = """
[bold]This tool will forecast wheat yield using:[/bold]
  • Sentinel-2 NDVI data (Statistical API)
  • Solar radiation (PAR) data
  • Phenology modeling
  • Radiation Use Efficiency (RUE) approach
            """
            
            panel = Panel(
                welcome_text.strip(),
                title="[bold cyan]🌾 Wheat Yield Forecasting Tool[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            print("=" * 80)
            print("WHEAT YIELD FORECASTING TOOL")
            print("=" * 80)
            print("\nThis tool will forecast wheat yield using:")
            print("  • Sentinel-2 NDVI data (Statistical API)")
            print("  • Solar radiation (PAR) data")
            print("  • Phenology modeling")
            print("  • Radiation Use Efficiency (RUE) approach")
            print("=" * 80)
        
        # Step 1: Load GeoJSON
        field_data = self.load_geojson(geojson_path)
        
        # Get field name from properties or filename
        field_name = field_data['properties'].get('name') or field_data['properties'].get('field_name')
        if not field_name:
            field_name = os.path.splitext(os.path.basename(geojson_path))[0]
        
        # Step 2: Prompt for inputs
        planting_date = self.prompt_planting_date()
        variety = self.prompt_variety()
        
        # Step 3: Fetch NDVI data
        ndvi_data = self.fetch_ndvi_data(
            field_name=field_name,
            geometry=field_data['geometry'],
            bbox=field_data['bbox'],
            planting_date=planting_date
        )
        
        if not ndvi_data:
            error_msg = "Cannot proceed without NDVI data"
            if self.console:
                self.console.print(f"\n[red]✗[/red] {error_msg}")
            else:
                print(f"\n✗ {error_msg}")
            sys.exit(1)
        
        # Step 4: Fetch PAR data
        par_data = self.fetch_par_data(
            latitude=field_data['center']['lat'],
            longitude=field_data['center']['lon'],
            planting_date=planting_date
        )
        
        if not par_data:
            error_msg = "Cannot proceed without PAR data"
            if self.console:
                self.console.print(f"\n[red]✗[/red] {error_msg}")
            else:
                print(f"\n✗ {error_msg}")
            sys.exit(1)
        
        # Step 5: Calculate phenology
        phenology_stages = self.calculate_phenology(
            variety=variety,
            planting_date=planting_date,
            latitude=field_data['center']['lat'],
            par_data=par_data
        )
        
        # Step 6: Calculate biomass and yield
        results = self.calculate_biomass_and_yield(
            field_name=field_name,
            variety=variety,
            planting_date=planting_date,
            ndvi_data=ndvi_data,
            par_data=par_data,
            phenology_stages=phenology_stages
        )
        
        if not results:
            error_msg = "Yield calculation failed"
            if self.console:
                self.console.print(f"\n[red]✗[/red] {error_msg}")
            else:
                print(f"\n✗ {error_msg}")
            sys.exit(1)
        
        # Step 7: Display results
        self.print_results(results)
        
        if self.console:
            self.console.print("\n[bold green]✓ Forecast complete![/bold green]")
        else:
            print("\n✓ Forecast complete!")


def get_credentials():
    """Get Sentinel Hub credentials from .env file, environment variables, or prompt user."""
    console = Console() if RICH_AVAILABLE else None
    
    # Try to load from .env file (already loaded at module level)
    client_id = os.getenv('SENTINEL_HUB_CLIENT_ID')
    client_secret = os.getenv('SENTINEL_HUB_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        if console:
            console.print("\n[yellow]⚠[/yellow] [bold]Sentinel Hub credentials not found[/bold]")
            console.print("[dim]Create a .env file with SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET[/dim]")
            console.print("[dim]Or set them as environment variables[/dim]")
            console.print("[dim]Or enter them now:[/dim]\n")
        else:
            print("\n⚠ Sentinel Hub credentials not found.")
            print("   Create a .env file with SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET")
            print("   Or set them as environment variables")
            print("   Or enter them now:\n")
        
        if not client_id:
            if console:
                client_id = Prompt.ask("[bold]?[/bold] Enter Sentinel Hub CLIENT_ID").strip()
            else:
                client_id = input("Enter Sentinel Hub CLIENT_ID: ").strip()
        if not client_secret:
            if console:
                client_secret = Prompt.ask("[bold]?[/bold] Enter Sentinel Hub CLIENT_SECRET", password=True).strip()
            else:
                client_secret = input("Enter Sentinel Hub CLIENT_SECRET: ").strip()
    
    return client_id, client_secret


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Wheat Yield Forecasting CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python forecast_yield_cli.py field.geojson
  SENTINEL_HUB_CLIENT_ID=xxx SENTINEL_HUB_CLIENT_SECRET=yyy python forecast_yield_cli.py field.geojson

Credentials:
  Create a .env file in the project root:
    SENTINEL_HUB_CLIENT_ID=your_client_id
    SENTINEL_HUB_CLIENT_SECRET=your_client_secret
  
  Or set environment variables:
    export SENTINEL_HUB_CLIENT_ID="your_client_id"
    export SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
  
  Or provide them interactively when prompted.
        """
    )
    
    parser.add_argument(
        'geojson',
        help='Path to GeoJSON file with field polygon'
    )
    
    parser.add_argument(
        '--client-id',
        help='Sentinel Hub OAuth client ID (overrides environment variable)'
    )
    
    parser.add_argument(
        '--client-secret',
        help='Sentinel Hub OAuth client secret (overrides environment variable)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    client_id = args.client_id or os.getenv('SENTINEL_HUB_CLIENT_ID')
    client_secret = args.client_secret or os.getenv('SENTINEL_HUB_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        client_id, client_secret = get_credentials()
    
    if not client_id or not client_secret:
        print("\n✗ Error: Sentinel Hub credentials are required")
        sys.exit(1)
    
    # Run the tool
    tool = YieldForecastCLI(client_id, client_secret)
    tool.run(args.geojson)


if __name__ == "__main__":
    main()

