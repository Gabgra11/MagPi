"""
BirdNET analysis worker for detecting bird species in audio.
"""
import numpy as np
from queue import Queue, Empty
import logging
import threading
from datetime import datetime
import importlib.util

logger = logging.getLogger("magpi-listener")


class BirdNETAnalyzer:
    """Wrapper for BirdNET-Lite model."""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.labels = None
        self._init_model()
    
    def _init_model(self):
        """Initialize BirdNET-Lite model."""
        try:
            # Try to import birdnetlib
            spec = importlib.util.find_spec("birdnetlib")
            if spec is None:
                logger.warning("birdnetlib not found, using mock analyzer")
                return
            
            from birdnetlib import Recording
            self.Recording = Recording
            logger.info("BirdNET-Lite loaded successfully")
            
        except ImportError:
            logger.warning("BirdNET-Lite not available, using mock analyzer")
            self.Recording = None
    
    def analyze(self, audio: np.ndarray, sample_rate: int) -> list:
        """
        Analyze audio for bird species.
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
        
        Returns:
            List of detections with format:
            {
                'species': 'Species Name',
                'confidence': 0.95,
                'start_time': 0.5,
                'end_time': 1.5
            }
        """
        try:
            if self.Recording is None:
                # Use mock detection for testing
                return self._mock_analyze(audio, sample_rate)
            
            # Use BirdNET-Lite
            # Save audio to temporary file for analysis
            import tempfile
            import soundfile as sf
            import os
            
            # Create temp file but don't auto-delete
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # Write audio to temp file
                sf.write(tmp_path, audio, sample_rate)
                
                # Run analysis
                recording = self.Recording(
                    tmp_path,
                    lat=self.config.birdnet_location_lat,
                    lon=self.config.birdnet_location_lon,
                    min_conf=self.config.min_confidence,  # Add this
                )
                
                recording.analyze()
                
                # Process results
                detections = []
                for detection in recording.detections:
                    if detection['confidence'] >= self.config.min_confidence:
                        detections.append({
                            'species': str(detection['scientific_name']),
                            'confidence': float(detection['confidence']),
                            'start_time': float(detection['start_time']),
                            'end_time': float(detection['end_time'])
                        })
                
                logger.info(f"BirdNET found {len(detections)} detections")
                return detections
            
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error in analysis: {e}", exc_info=True)
            return []
    
    def _mock_analyze(self, audio: np.ndarray, sample_rate: int) -> list:
        """Mock analyzer for testing without BirdNET."""
        # Simple detection based on audio energy
        # In production, this would use actual BirdNET
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio ** 2))
        
        # Mock species based on energy levels
        mock_species = [
            "American Robin",
            "Black-capped Chickadee",
            "Common Grackle",
            "Northern Cardinal",
            "Blue Jay"
        ]
        
        detections = []
        
        # Only "detect" if there's significant audio energy
        if rms > 0.01:
            # Random confidence based on energy
            confidence = float(min(0.99, 0.5 + (float(rms) * 10)))
            
            # Use energy hash to pick species
            species_idx = int(float(rms) * 1000) % len(mock_species)
            
            detections.append({
                'species': mock_species[species_idx],
                'confidence': confidence,
                'start_time': float(0.0),
                'end_time': float(len(audio) / sample_rate)
            })
        
        return detections


class AnalyzerWorker:
    """Worker for analyzing audio samples."""
    
    def __init__(self, config, samples_queue: Queue, detections_queue: Queue):
        self.config = config
        self.samples_queue = samples_queue
        self.detections_queue = detections_queue
        self.running = False
        self.analyzer = BirdNETAnalyzer(config)
    
    def run(self):
        """Main analysis loop."""
        try:
            logger.info("Analyzer worker started")
            
            while self.running:
                try:
                    # Get sample from queue with timeout
                    sample_data = self.samples_queue.get(timeout=1)
                    
                    if sample_data is None:
                        # Poison pill, stop processing
                        break
                    
                    # Analyze
                    audio = sample_data['audio']
                    timestamp = sample_data['timestamp']
                    sample_rate = sample_data['sample_rate']
                    
                    detections = self.analyzer.analyze(audio, sample_rate)
                    
                    # Send detections to queue
                    if detections:
                        for detection in detections:
                            self.detections_queue.put({
                                'species': detection['species'],
                                'confidence': detection['confidence'],
                                'timestamp': timestamp,
                                'details': {
                                    'start_time': detection.get('start_time', 0),
                                    'end_time': detection.get('end_time', 0)
                                }
                            })
                
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in analyzer loop: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Analyzer worker failed: {e}")
        
        finally:
            logger.info("Analyzer worker stopped")
    
    def start(self) -> threading.Thread:
        """Start analyzer worker in a thread."""
        self.running = True
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop analyzer worker."""
        self.running = False
