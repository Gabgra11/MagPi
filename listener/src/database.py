"""
Database management for storing bird detections.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import threading

logger = logging.getLogger("magpi-listener")


class Detection:
    """Represents a bird detection."""
    
    def __init__(self, species: str, confidence: float, timestamp: datetime, 
                 details: Optional[Dict] = None):
        self.species = species
        self.confidence = confidence
        self.timestamp = timestamp
        self.details = details or {}


class DetectionDatabase:
    """SQLite database for storing bird detections."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Detections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species ON detections(species)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_species_timestamp 
                ON detections(species, timestamp)
            """)
            
            # Statistics cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def add_detection(self, detection: Detection, lat: Optional[float] = None,
                     lon: Optional[float] = None) -> int:
        """Add a detection to the database."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO detections 
                    (species, confidence, timestamp, latitude, longitude, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(detection.species),
                    float(detection.confidence),
                    str(detection.timestamp.isoformat()),
                    float(lat) if lat is not None else None,
                    float(lon) if lon is not None else None,
                    str(detection.details) if detection.details else None
                ))
                conn.commit()
                return cursor.lastrowid
    
    def get_recent_detections(self, limit: int = 100, 
                            offset: int = 0) -> List[Dict]:
        """Get recent detections."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM detections 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    if d.get('details') and isinstance(d['details'], bytes):
                        try:
                            d['details'] = d['details'].decode('utf-8')
                        except:
                            d['details'] = None
                    result.append(d)
                return result
    
    def get_detections_by_species(self, species: str, 
                                 days: int = 7) -> List[Dict]:
        """Get detections for a specific species in the last N days."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT * FROM detections 
                    WHERE species = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                """, (species, since.isoformat()))
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    if d.get('details') and isinstance(d['details'], bytes):
                        try:
                            d['details'] = d['details'].decode('utf-8')
                        except:
                            d['details'] = None
                    result.append(d)
                return result
    
    def get_all_species(self, days: int = 7) -> List[Tuple[str, int]]:
        """Get all detected species with counts for the last N days."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT species, COUNT(*) as count 
                    FROM detections 
                    WHERE timestamp >= ?
                    GROUP BY species 
                    ORDER BY count DESC
                """, (since.isoformat(),))
                
                return cursor.fetchall()
    
    def get_stats(self, days: int = 7) -> Dict:
        """Get overall statistics."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(days=days)
                
                # Total detections
                cursor.execute("""
                    SELECT COUNT(*) FROM detections WHERE timestamp >= ?
                """, (since.isoformat(),))
                total_detections = cursor.fetchone()[0]
                
                # Unique species
                cursor.execute("""
                    SELECT COUNT(DISTINCT species) FROM detections 
                    WHERE timestamp >= ?
                """, (since.isoformat(),))
                unique_species = cursor.fetchone()[0]
                
                # Average confidence
                cursor.execute("""
                    SELECT AVG(confidence) FROM detections 
                    WHERE timestamp >= ?
                """, (since.isoformat(),))
                avg_confidence = cursor.fetchone()[0] or 0
                
                # Top species
                cursor.execute("""
                    SELECT species, COUNT(*) as count 
                    FROM detections 
                    WHERE timestamp >= ?
                    GROUP BY species 
                    ORDER BY count DESC 
                    LIMIT 10
                """, (since.isoformat(),))
                top_species = [{"species": row[0], "count": row[1]} 
                               for row in cursor.fetchall()]
                
                return {
                    "total_detections": total_detections,
                    "unique_species": unique_species,
                    "avg_confidence": round(avg_confidence, 3),
                    "top_species": top_species,
                    "period_days": days
                }
    
    def check_duplicate(self, species: str, window_seconds: int) -> bool:
        """Check if a recent detection of this species exists within window."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(seconds=window_seconds)
                
                cursor.execute("""
                    SELECT COUNT(*) FROM detections 
                    WHERE species = ? AND timestamp >= ?
                    LIMIT 1
                """, (species, since.isoformat()))
                
                count = cursor.fetchone()[0]
                return count > 0
    
    def cleanup_old_detections(self, days: int = 90):
        """Remove detections older than N days."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff = datetime.utcnow() - timedelta(days=days)
                
                cursor.execute("""
                    DELETE FROM detections WHERE timestamp < ?
                """, (cutoff.isoformat(),))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old detections")
    
    def get_hourly_activity(self, days: int = 7) -> List[Dict]:
        """Get hourly activity data for heatmap visualization."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                        COUNT(*) as count,
                        AVG(confidence) as avg_confidence
                    FROM detections 
                    WHERE timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour
                """, (since.isoformat(),))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_activity(self, days: int = 365) -> List[Dict]:
        """Get daily activity data for trends."""
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                since = datetime.utcnow() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT 
                        strftime('%Y-%m-%d', timestamp) as date,
                        COUNT(*) as count,
                        COUNT(DISTINCT species) as unique_species
                    FROM detections 
                    WHERE timestamp >= ?
                    GROUP BY date
                    ORDER BY date
                """, (since.isoformat(),))
                
                return [dict(row) for row in cursor.fetchall()]
