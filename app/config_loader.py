# app/config_loader.py
import yaml
from typing import List, Dict, Any

def load_config(config_path: str) -> List[Dict[str, Any]]:
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config.get("models", [])
