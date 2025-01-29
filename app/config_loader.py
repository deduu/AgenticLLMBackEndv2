# app/config_loader.py
import yaml
from typing import List, Dict, Any

def load_model_configs(config_path: str, model_size: str) -> List[Dict[str, Any]]:
    """
    Loads and returns a list of model configurations from a YAML file.

    Args:
        config_path (str): Path to the YAML file.
        model_size (str): "large", "small", or "all" to load all models

    Returns:
        List[Dict[str, Any]]: A list of model configurations, or an empty list on error.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            models: List[Dict[str, Any]] = []  # Initialize as empty list
            if model_size == "large":
                models = config.get("large_models", [])
            elif model_size == "medium":
                models = config.get("medium_models", [])
            elif model_size == "small":
                models = config.get("small_models", [])
            elif model_size == "all":
                if "large_models" in config:
                    models.extend(config["large_models"])
                if "small_models" in config:
                    models.extend(config["small_models"])
                if "models" in config:
                    models.extend(config["models"])
            else:
                print(f"Warning: Invalid model_size: {model_size}. Returning empty list.")
                return []
            return models
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

def load_embedding_configs(config_path: str) -> List[Dict[str, Any]]:
    """
    Loads and returns a list of embedding configurations from a YAML file.

    Args:
        config_path (str): The path to the YAML file containing the embedding configurations.

    Returns:
        List[Dict[str, Any]]: A list of embedding configuration dictionaries.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config.get("embeddings", [])

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

