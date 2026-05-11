#!/usr/bin/env python
"""
Step 2b: Generate Google Maps URLs for tourist-only POIs.
Reads philippines_poi_catalog_tourist.csv and writes poi_urls_tourist.csv.
The original poi_urls.csv (full catalog) is left untouched.
"""

import pandas as pd
import urllib.parse
from pathlib import Path
from utils import load_config, setup_logging, ensure_dirs


def create_google_maps_url(row):
    if pd.isna(row['name']) or pd.isna(row['latitude']) or pd.isna(row['longitude']):
        return None
    query = f"{row['name']} Philippines"
    encoded_query = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/{encoded_query}/@{row['latitude']},{row['longitude']},17z"


def generate_urls(poi_catalog_path, output_path):
    logger.info(f"Loading tourist POI catalog from {poi_catalog_path}")
    df = pd.read_csv(poi_catalog_path)
    logger.info(f"Generating URLs for {len(df)} tourist POIs")

    df['google_maps_url'] = df.apply(create_google_maps_url, axis=1)
    df = df.dropna(subset=['google_maps_url'])

    urls_df = df[['osm_id', 'name', 'fclass', 'finalCategory', 'latitude', 'longitude', 'google_maps_url']]
    urls_df.to_csv(output_path, index=False)

    logger.info(f"Saved {len(urls_df)} tourist URLs to {output_path}")
    return urls_df


if __name__ == "__main__":
    config = load_config()
    logger = setup_logging()

    ensure_dirs([
        config['data']['processed_dir'],
        config['data']['final_dir']
    ])

    poi_catalog = Path(config['data']['final_dir']) / "philippines_poi_catalog_tourist.csv"
    output = Path(config['data']['processed_dir']) / "poi_urls_tourist.csv"

    generate_urls(poi_catalog, output)

    logger.info("Step 2b completed successfully!")
