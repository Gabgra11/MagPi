"""
Configuration management for the listener service.
Loads configuration from environment variables.
"""
import os
from dataclasses import dataclass
from typing import Optional
import logging


@dataclass
class ListenerConfig:
    """Configuration for the listener service."""
    
    # Audio Recording Settings
    audio_device: int = -1  # Default device
    sample_rate: int = 48000
    chunk_size: int = 2048
    buffer_duration: int = 10  # seconds
    sample_duration: int = 5  # seconds for each analysis sample
    
    # Detection Settings
    min_confidence: float = 0.5
    duplicate_window: int = 30  # seconds to ignore duplicates
    
    # Worker Settings
    num_workers: int = 2
    
    # Database Settings
    db_path: str = "./data/detections.db"
    
    # BirdNET Settings
    birdnet_threads: int = 4
    birdnet_gpu: bool = False
    birdnet_location_lat: float = 40.7128
    birdnet_location_lon: float = -74.0060
    
    # API Settings
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    
    # Logging
    log_level: str = "INFO"


@dataclass
class DatabaseConfig:
    """Configuration for database."""
    
    db_path: str = "./data/detections.db"
    cleanup_enabled: bool = True
    cleanup_days: int = 90
    backup_enabled: bool = True
    backup_path: str = "./backups"


def load_config() -> tuple[ListenerConfig, DatabaseConfig]:
    """Load configuration from environment variables."""
    
    listener_config = ListenerConfig(
        audio_device=int(os.getenv("LISTENER_AUDIO_DEVICE", "-1")),
        sample_rate=int(os.getenv("LISTENER_SAMPLE_RATE", "48000")),
        chunk_size=int(os.getenv("LISTENER_CHUNK_SIZE", "2048")),
        buffer_duration=int(os.getenv("LISTENER_BUFFER_DURATION", "10")),
        sample_duration=int(os.getenv("LISTENER_SAMPLE_DURATION", "5")),
        min_confidence=float(os.getenv("LISTENER_MIN_CONFIDENCE", "0.5")),
        duplicate_window=int(os.getenv("LISTENER_DUPLICATE_WINDOW", "30")),
        num_workers=int(os.getenv("LISTENER_NUM_WORKERS", "2")),
        db_path=os.getenv("LISTENER_DB_PATH", "./data/detections.db"),
        birdnet_threads=int(os.getenv("BIRDNET_THREADS", "4")),
        birdnet_gpu=os.getenv("BIRDNET_GPU", "false").lower() == "true",
        birdnet_location_lat=float(os.getenv("BIRDNET_LOCATION_LAT", "40.7128")),
        birdnet_location_lon=float(os.getenv("BIRDNET_LOCATION_LON", "-74.0060")),
        api_port=int(os.getenv("API_SERVER_PORT", "8000")),
        api_host=os.getenv("API_SERVER_HOST", "0.0.0.0"),
        log_level=os.getenv("LISTENER_LOG_LEVEL", "INFO"),
    )
    
    db_config = DatabaseConfig(
        db_path=os.getenv("DATABASE_PATH", listener_config.db_path),
        cleanup_enabled=os.getenv("CLEANUP_ENABLED", "true").lower() == "true",
        cleanup_days=int(os.getenv("DATABASE_CLEANUP_DAYS", "90")),
        backup_enabled=os.getenv("BACKUP_ENABLED", "true").lower() == "true",
        backup_path=os.getenv("BACKUP_PATH", "./backups"),
    )
    
    return listener_config, db_config


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration."""
    
    logger = logging.getLogger("magpi-listener")
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure the named logger
    logger.setLevel(level)
    logger.propagate = False

    # Add a console handler only if none exists to avoid duplicate logs
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Also ensure the root logger is at least at the requested level so
    # library logs and propagation don't accidentally hide debug messages.
    root_logger = logging.getLogger()
    try:
        # Only raise root level if it's higher (less verbose) than requested
        if root_logger.level > level:
            root_logger.setLevel(level)
    except Exception:
        # Defensive: ignore if root logger can't be changed
        pass

    logger.debug(f"Logging configured (level={logging.getLevelName(level)})")

    return logger
