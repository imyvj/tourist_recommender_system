#!/usr/bin/env python
"""
Step 2b: Generate Google Maps URLs for tourist-only POIs.
Reads philippines_poi_catalog_tourist.csv and writes:
  - poi_urls_tourist.csv            (resolved rows with place_id-based URLs)
  - poi_urls_tourist_unresolved.csv (ZERO_RESULTS / LOW_CONFIDENCE / API_ERROR rows)

Uses the Places API "Find Place From Text" to get a specific place_id per POI,
then builds https://www.google.com/maps/place/?q=place_id:<id> which always opens
a single place page (not a search-results list).

Requires GOOGLE_MAPS_API_KEY in a .env file at the project root.

Usage:
  uv run python src/02b_generate_tourist_urls.py              # test: first 20 uncached rows
  uv run python src/02b_generate_tourist_urls.py --limit 100  # larger batch
  uv run python src/02b_generate_tourist_urls.py --limit 0    # all uncached rows
"""

import argparse
import os
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from tqdm import tqdm

from utils import load_config, setup_logging, ensure_dirs


FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
NAME_SCORE_THRESHOLD = 60   # min acceptable name similarity (0-100)
MAX_DISTANCE_KM = 5.0       # reject if returned place is farther than this from OSM coords
CALL_DELAY_SEC = 0.1        # stay well under API rate limits


def _haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _name_score(input_name, returned_name):
    a, b = input_name.lower(), returned_name.lower()
    # partial_ratio handles "Chowking" inside "Chowking Rbcc Baclaran Roxas" (score ~100)
    # token_sort_ratio handles reordered words
    return max(fuzz.partial_ratio(a, b), fuzz.token_sort_ratio(a, b))


def resolve_place_id(name, lat, lng, api_key):
    """
    Call Find Place From Text with a 500 m location bias.
    Returns: (status, place_id, resolved_name, resolved_lat, resolved_lng, reason)
    Possible statuses: "resolved", "low_confidence", "zero_results", "api_error"
    """
    params = {
        "input": name,
        "inputtype": "textquery",
        "fields": "place_id,name,geometry",
        "locationbias": f"circle:500@{lat},{lng}",
        "key": api_key,
    }

    try:
        resp = requests.get(FIND_PLACE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return "api_error", None, None, None, None, str(exc)

    api_status = data.get("status", "")

    if api_status == "ZERO_RESULTS":
        return "zero_results", None, None, None, None, "ZERO_RESULTS"

    if api_status not in ("OK",):
        return "api_error", None, None, None, None, f"API status: {api_status}"

    candidates = data.get("candidates", [])
    if not candidates:
        return "zero_results", None, None, None, None, "empty candidates"

    c = candidates[0]
    place_id = c.get("place_id")
    resolved_name = c.get("name", "")
    loc = c.get("geometry", {}).get("location", {})
    resolved_lat, resolved_lng = loc.get("lat"), loc.get("lng")

    # Coordinate sanity check — catches geographically wrong matches
    if resolved_lat is not None and resolved_lng is not None:
        dist_km = _haversine_km(lat, lng, resolved_lat, resolved_lng)
        if dist_km > MAX_DISTANCE_KM:
            return (
                "low_confidence", place_id, resolved_name,
                resolved_lat, resolved_lng,
                f"distance={dist_km:.1f}km>{MAX_DISTANCE_KM}km",
            )

    score = _name_score(name, resolved_name)
    if score < NAME_SCORE_THRESHOLD:
        return (
            "low_confidence", place_id, resolved_name,
            resolved_lat, resolved_lng,
            f"name_similarity={score}",
        )

    return "resolved", place_id, resolved_name, resolved_lat, resolved_lng, ""


def load_cache(cache_path):
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"osm_id": str})
    return pd.DataFrame(
        columns=["osm_id", "status", "place_id", "resolved_name", "resolved_lat", "resolved_lng", "reason"]
    )


def generate_urls(poi_catalog_path, output_path, unresolved_path, cache_path, api_key, limit):
    df = pd.read_csv(poi_catalog_path, dtype={"osm_id": str})
    logger.info(f"Loaded {len(df)} tourist POIs from {poi_catalog_path}")

    cache_df = load_cache(cache_path)
    cached_ids = set(cache_df["osm_id"])

    to_process = df[~df["osm_id"].isin(cached_ids)].copy()
    cached_skipped = len(df) - len(to_process)

    if limit > 0:
        to_process = to_process.head(limit)
    logger.info(
        f"To process: {len(to_process)} rows  |  cached/skipped: {cached_skipped}"
        + (f"  |  limit: {limit}" if limit > 0 else "  |  limit: none")
    )

    new_rows = []
    api_calls = 0

    for _, row in tqdm(to_process.iterrows(), total=len(to_process), desc="Resolving"):
        status, place_id, resolved_name, resolved_lat, resolved_lng, reason = resolve_place_id(
            row["name"], row["latitude"], row["longitude"], api_key
        )
        new_rows.append({
            "osm_id": str(row["osm_id"]),
            "status": status,
            "place_id": place_id,
            "resolved_name": resolved_name,
            "resolved_lat": resolved_lat,
            "resolved_lng": resolved_lng,
            "reason": reason,
        })
        api_calls += 1
        time.sleep(CALL_DELAY_SEC)

    # Persist cache
    if new_rows:
        updated_cache = pd.concat([cache_df, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        updated_cache = cache_df.copy()
    updated_cache.to_csv(cache_path, index=False)

    # Build outputs from everything in cache (accumulates across runs)
    merged = df.merge(updated_cache, on="osm_id", how="inner")

    resolved_df = merged[merged["status"] == "resolved"].copy()
    unresolved_df = merged[merged["status"] != "resolved"].copy()

    resolved_df["google_maps_url"] = resolved_df["place_id"].apply(
        lambda pid: f"https://www.google.com/maps/place/?q=place_id:{pid}"
    )

    resolved_df[
        ["osm_id", "name", "fclass", "finalCategory", "latitude", "longitude", "place_id", "google_maps_url"]
    ].to_csv(output_path, index=False)

    unresolved_df[
        ["osm_id", "name", "fclass", "finalCategory", "latitude", "longitude", "status", "reason"]
    ].to_csv(unresolved_path, index=False)

    # Summary
    n_res = (updated_cache["status"] == "resolved").sum()
    n_low = (updated_cache["status"] == "low_confidence").sum()
    n_zero = (updated_cache["status"] == "zero_results").sum()
    n_err = (updated_cache["status"] == "api_error").sum()

    logger.info("=" * 50)
    logger.info(f"  resolved:            {n_res:>6}")
    logger.info(f"  low_confidence:      {n_low:>6}")
    logger.info(f"  zero_results:        {n_zero:>6}")
    logger.info(f"  api_errors:          {n_err:>6}")
    logger.info(f"  cached_skipped:      {cached_skipped:>6}")
    logger.info(f"  api_calls_this_run:  {api_calls:>6}")
    logger.info(f"  -> {output_path}  ({len(resolved_df)} rows)")
    logger.info(f"  -> {unresolved_path}  ({len(unresolved_df)} rows)")
    logger.info("=" * 50)


if __name__ == "__main__":
    load_dotenv()

    config = load_config()
    logger = setup_logging()

    processed_dir = Path(config["data"]["processed_dir"])
    final_dir = Path(config["data"]["final_dir"])

    ensure_dirs([processed_dir, final_dir])

    parser = argparse.ArgumentParser(description="Generate place-id-based Google Maps URLs for tourist POIs")
    parser.add_argument("--input",      default=None, help="Override input catalog CSV path")
    parser.add_argument("--output",     default=None, help="Override resolved output CSV path")
    parser.add_argument("--unresolved", default=None, help="Override unresolved output CSV path")
    parser.add_argument("--cache",      default=None, help="Override cache CSV path")
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max uncached rows to process this run (default: 20). Use 0 for no limit.",
    )
    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise RuntimeError("Set GOOGLE_MAPS_API_KEY in the .env file at the project root.")

    poi_catalog  = Path(args.input)      if args.input      else final_dir    / "philippines_poi_catalog_tourist.csv"
    output       = Path(args.output)     if args.output     else processed_dir / "poi_urls_tourist.csv"
    unresolved   = Path(args.unresolved) if args.unresolved else processed_dir / "poi_urls_tourist_unresolved.csv"
    cache        = Path(args.cache)      if args.cache      else processed_dir / "place_id_cache.csv"

    generate_urls(poi_catalog, output, unresolved, cache, api_key, args.limit)

    logger.info("Step 2b completed successfully!")
