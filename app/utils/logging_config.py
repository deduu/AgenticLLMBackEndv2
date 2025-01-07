# app/utils/logging_config.py
import logging

def setup_logging():
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    return logger
