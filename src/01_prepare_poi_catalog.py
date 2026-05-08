#!/usr/bin/env python
"""
Step 1: Extract POIs from Geofabrik shapefile and create master catalog
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from utils import load_config, setup_logging, ensure_dirs

def load_shapefile(shp_path):
    """Load the Geofabrik shapefile"""
    logger.info(f"Loading shapefile from {shp_path}")
    gdf = gpd.read_file(shp_path)
    logger.info(f"Loaded {len(gdf)} rows")
    return gdf

def filter_tourism_pois(gdf, keep_categories):
    """Filter only tourism-relevant POIs"""
    # Flatten keep categories from config
    keep_set = set(keep_categories)

    logger.info(f"Keeping {len(keep_set)} POI categories")

    # Debug: show actual dataset categories
    logger.info(
        f"Sample fclass values: {sorted(gdf['fclass'].dropna().unique())[:30]}"
    )

    filtered = gdf[gdf['fclass'].isin(keep_set)].copy()

    logger.info(f"Filtered rows: {len(filtered)}")

    return filtered

def extract_coordinates(gdf):
    gdf = gdf.copy()
    gdf['latitude'] = gdf.geometry.y
    gdf['longitude'] = gdf.geometry.x
    return gdf

def map_final_category(fclass):
    """Map OSM fclass to thesis finalCategory"""
    f = str(fclass).lower()
    
    # Accommodation
    if f in ['hotel', 'motel', 'guesthouse', 'hostel', 'chalet', 'alpine_hut', 'camp_site', 'caravan_site', 'wilderness_hut']:
        return 'Accommodation'
    # Food/Drink
    if f in ['restaurant', 'cafe', 'fast_food', 'pub', 'bar', 'biergarten', 'bakery', 'ice_cream', 'food_court', 'beverages']:
        return 'Food/Drink'
    # Attractions
    if f in ['museum', 'gallery', 'artwork', 'arts_centre', 'cinema', 'theatre', 'theme_park', 'attraction', 
             'archaeological', 'castle', 'fort', 'ruins', 'monument', 'memorial', 'tower', 'viewpoint', 
             'lighthouse', 'observation_tower', 'zoo']:
        return 'Attraction'
    # Nature & parks
    if f in ['park', 'garden', 'nature_reserve', 'beach', 'dog_park', 'fountain', 'golf_course', 'ice_rink', 
             'picnic_site', 'playground', 'sports_centre', 'sports_hall', 'stadium', 'swimming_pool', 'track', 'water_park']:
        return 'Park/Nature'
    # Retail
    if f in ['shop', 'mall', 'department_store', 'supermarket', 'marketplace', 'gift_shop', 'clothes', 
             'shoe_shop', 'sports_shop', 'bookshop', 'stationery', 'toy_shop', 'jeweller', 'florist', 
             'outdoor_shop', 'bicycle_shop', 'car_dealership', 'travel_agent']:
        return 'Retail'
    # Health
    if f in ['chemist', 'pharmacy', 'clinic', 'hospital', 'dentist', 'doctors', 'veterinary']:
        return 'Health'
    # Public service
    if f in ['bank', 'atm', 'post_office', 'police', 'fire_station', 'library', 'university', 
             'college', 'kindergarten', 'school', 'town_hall', 'courthouse', 'embassy', 'consulate']:
        return 'Public Service'
    # Default
    return 'Other'

def clean_data(pois):
    """Remove rows with missing names and duplicates"""
    before = len(pois)
    pois = pois.dropna(subset=['name'])
    pois = pois[pois['name'].str.strip() != '']
    pois = pois.drop_duplicates(subset=['name', 'latitude', 'longitude'])
    logger.info(f"Removed {before - len(pois)} rows with missing or duplicate names")
    return pois

def save_catalog(pois, output_path):
    """Save POI catalog to CSV"""
    pois.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"Saved {len(pois)} POIs to {output_path}")
    return pois

if __name__ == "__main__":

    # Setup
    config = load_config()
    logger = setup_logging()

    ensure_dirs([
        config['data']['processed_dir'],
        config['data']['final_dir']
    ])

    # Resolve project root (IMPORTANT FIX)
    project_root = Path(__file__).resolve().parent.parent

    shp_path = project_root / config['geofabrik']['shp_path']

    # Load data
    gdf = load_shapefile(shp_path)

    # Filter POIs
    filtered = filter_tourism_pois(
        gdf,
        config['poi_categories']['keep']
    )

    # Extract coordinates
    filtered = extract_coordinates(filtered)

    # Map categories
    filtered['finalCategory'] = filtered['fclass'].apply(map_final_category)

    # Clean
    cleaned = clean_data(filtered)

    # Final columns
    final_pois = cleaned[
        ['osm_id', 'name', 'fclass', 'finalCategory', 'latitude', 'longitude']
    ]

    # Output path
    output_path = Path(config['data']['final_dir']) / "philippines_poi_catalog.csv"

    # Save
    save_catalog(final_pois, output_path)

    logger.info("Step 1 completed successfully!")