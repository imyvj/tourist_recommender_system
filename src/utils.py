import os
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path

def load_config(config_path="config.yaml"):
    """Load configuration file"""
     # project root = parent of src
    project_root = Path(__file__).resolve().parent.parent

    full_path = project_root / config_path

    with open(full_path, "r") as f:
        config = yaml.safe_load(f)

    return config

def setup_logging(log_dir="logs"):
    """Setup logging configuration"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_dirs(paths):
    """Create directories if they don't exist"""
    for path in paths:
        os.makedirs(path, exist_ok=True)

def save_dataframe(df, path, logger=None):
    """Save dataframe with logging"""
    df.to_csv(path, index=False, encoding='utf-8')
    if logger:
        logger.info(f"Saved {len(df)} rows to {path}")