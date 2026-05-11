#!/usr/bin/env python
"""
Step 1b: Split POI catalog into tourist-relevant and non-tourist files.
Reads philippines_poi_catalog.csv and writes:
  - philippines_poi_catalog_tourist.csv
  - philippines_poi_catalog_non_tourist.csv
"""

import pandas as pd
from pathlib import Path
from utils import load_config, setup_logging, ensure_dirs

TOURIST_FCLASS = {
    # Accommodation
    "alpine_hut", "camp_site", "caravan_site", "chalet", "guesthouse",
    "hostel", "hotel", "motel", "wilderness_hut",
    # Food & drink
    "bakery", "bar", "biergarten", "cafe", "fast_food", "food_court", "pub", "restaurant",
    # Cultural & heritage
    "archaeological", "arts_centre", "artwork", "attraction", "castle", "cinema",
    "fort", "fountain", "lighthouse", "memorial", "monument", "museum",
    "observation_tower", "ruins", "theatre", "theme_park", "tower",
    "wayside_cross", "wayside_shrine", "water_mill", "windmill", "zoo",
    # Nature & recreation
    "beach", "garden", "golf_course", "ice_rink", "park", "picnic_site", "swimming_pool",
    # Entertainment
    "nightclub", "stadium",
    # Shopping & tourism services
    "gift_shop", "mall", "marketplace", "tourist_info", "travel_agent",
    # Viewpoints & landmarks
    "viewpoint",
    # Tourism mobility
    "bicycle_rental", "car_rental",
}


def filter_tourist_pois(catalog_path, tourist_out, non_tourist_out):
    df = pd.read_csv(catalog_path)
    logger.info(f"Loaded {len(df)} POIs from {catalog_path}")

    is_tourist = df["fclass"].isin(TOURIST_FCLASS)
    tourist_df = df[is_tourist].reset_index(drop=True)
    non_tourist_df = df[~is_tourist].reset_index(drop=True)

    tourist_df.to_csv(tourist_out, index=False)
    non_tourist_df.to_csv(non_tourist_out, index=False)

    logger.info(f"Tourist POIs:     {len(tourist_df):>6}  -> {tourist_out}")
    logger.info(f"Non-tourist POIs: {len(non_tourist_df):>6}  -> {non_tourist_out}")

    logger.info("Tourist category breakdown:")
    for cat, count in tourist_df["finalCategory"].value_counts().items():
        logger.info(f"  {cat:<20} {count}")

    logger.info("Non-tourist fclass sample (top 10):")
    for fclass, count in non_tourist_df["fclass"].value_counts().head(10).items():
        logger.info(f"  {fclass:<25} {count}")

    return tourist_df, non_tourist_df


if __name__ == "__main__":
    config = load_config()
    logger = setup_logging()

    ensure_dirs([config["data"]["final_dir"]])

    final_dir = Path(config["data"]["final_dir"])
    catalog_path = final_dir / "philippines_poi_catalog.csv"
    tourist_out = final_dir / "philippines_poi_catalog_tourist.csv"
    non_tourist_out = final_dir / "philippines_poi_catalog_non_tourist.csv"

    filter_tourist_pois(catalog_path, tourist_out, non_tourist_out)

    logger.info("Step 1b completed successfully!")
