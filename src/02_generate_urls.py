#!/usr/bin/env python
"""
Step 2: Generate Google Maps URLs for each POI
"""

import pandas as pd
import urllib.parse
from pathlib import Path
from utils import load_config, setup_logging, ensure_dirs


def create_google_maps_url(row):
    """Create Google Maps URL safely"""
    if pd.isna(row['name']) or pd.isna(row['latitude']) or pd.isna(row['longitude']):
        return None

    query = f"{row['name']} Philippines"
    encoded_query = urllib.parse.quote_plus(query)

    return f"https://www.google.com/maps/search/{encoded_query}/@{row['latitude']},{row['longitude']},17z"


def generate_urls(poi_catalog_path, output_path):
    logger.info(f"Loading POI catalog from {poi_catalog_path}")

    df = pd.read_csv(poi_catalog_path)

    logger.info(f"Generating URLs for {len(df)} POIs")

    df['google_maps_url'] = df.apply(create_google_maps_url, axis=1)

    # Remove invalid rows
    df = df.dropna(subset=['google_maps_url'])

    urls_df = df[
        ['osm_id', 'name', 'finalCategory', 'latitude', 'longitude', 'google_maps_url']
    ]

    urls_df.to_csv(output_path, index=False)

    logger.info(f"Saved {len(urls_df)} URLs to {output_path}")

    return urls_df


if __name__ == "__main__":

    config = load_config()
    logger = setup_logging()

    ensure_dirs([
        config['data']['processed_dir'],
        config['data']['final_dir']
    ])

    poi_catalog = f"{config['data']['final_dir']}/philippines_poi_catalog.csv"
    output = Path(config['data']['processed_dir']) / "poi_urls.csv"

    generate_urls(poi_catalog, output)

    logger.info("Step 2 completed successfully!")