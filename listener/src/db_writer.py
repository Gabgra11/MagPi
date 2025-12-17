"""
Database writer worker for storing detections.
"""
from queue import Queue, Empty
import logging
import threading
from datetime import datetime

from database import Detection, DetectionDatabase

logger = logging.getLogger("magpi-listener")


class DbWriterWorker:
    """Worker for writing detections to database."""
    
    def __init__(self, config, db: DetectionDatabase, 
                 detections_queue: Queue):
        self.config = config
        self.db = db
        self.detections_queue = detections_queue
        self.running = False
        self.lat = config.birdnet_location_lat
        self.lon = config.birdnet_location_lon
    
    def run(self):
        """Main database writing loop."""
        try:
            logger.info("Database writer worker started")
            
            while self.running:
                try:
                    # Get detection from queue with timeout
                    detection_data = self.detections_queue.get(timeout=1)
                    
                    if detection_data is None:
                        # Poison pill, stop processing
                        break
                    
                    # Check for duplicates
                    species = detection_data['species']
                    confidence = detection_data['confidence']
                    timestamp = detection_data['timestamp']
                    
                    if self.db.check_duplicate(
                        species, 
                        self.config.duplicate_window
                    ):
                        logger.debug(
                            f"Ignoring duplicate detection: {species} "
                            f"(within {self.config.duplicate_window}s)"
                        )
                        continue
                    
                    # Create detection and save
                    detection = Detection(
                        species=species,
                        confidence=confidence,
                        timestamp=timestamp,
                        details=detection_data.get('details', {})
                    )
                    
                    detection_id = self.db.add_detection(
                        detection,
                        lat=self.lat,
                        lon=self.lon
                    )
                    
                    logger.info(
                        f"Detection saved: {species} "
                        f"(confidence: {confidence:.2f}) "
                        f"[ID: {detection_id}]"
                    )
                
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in writer loop: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Database writer worker failed: {e}")
        
        finally:
            logger.info("Database writer worker stopped")
    
    def start(self) -> threading.Thread:
        """Start writer worker in a thread."""
        self.running = True
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop writer worker."""
        self.running = False
