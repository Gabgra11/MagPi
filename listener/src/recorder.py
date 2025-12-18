"""
Audio recording worker for continuous audio capture using circular buffer.
"""
import numpy as np
import pyaudio
from collections import deque
from queue import Queue
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger("magpi-listener")


class AudioBuffer:
    """Circular buffer for audio data."""
    
    def __init__(self, sample_rate: int, duration_seconds: int, 
                 sample_duration: int):
        self.sample_rate = sample_rate
        self.duration_seconds = duration_seconds
        self.sample_duration = sample_duration
        self.buffer_size = sample_rate * duration_seconds
        self.sample_size = sample_rate * sample_duration
        
        self.buffer = deque(maxlen=self.buffer_size)
        self.lock = threading.RLock()
    
    def add_chunk(self, chunk: np.ndarray):
        """Add audio chunk to buffer."""
        with self.lock:
            for sample in chunk:
                self.buffer.append(sample)
    
    def get_sample(self) -> np.ndarray:
        """Get latest sample from buffer."""
        with self.lock:
            if len(self.buffer) >= self.sample_size:
                # Get the last N samples
                sample = list(self.buffer)[-self.sample_size:]
                return np.array(sample, dtype=np.float32)
            return None
    
    def is_ready(self) -> bool:
        """Check if buffer has enough data."""
        with self.lock:
            return len(self.buffer) >= self.sample_size


class RecorderWorker:
    """Worker for recording audio from microphone."""
    
    def __init__(self, config, samples_queue: Queue):
        self.config = config
        self.samples_queue = samples_queue
        self.running = False
        self.audio_buffer = AudioBuffer(
            config.sample_rate,
            config.buffer_duration,
            config.sample_duration
        )
        self.p = None
        self.stream = None
    
    def setup_audio(self):
        """Setup PyAudio stream."""
        try:
            self.p = pyaudio.PyAudio()
            
            # Find device
            device_index = self.config.audio_device
            if device_index == -1:
                device_index = self.p.get_default_input_device_index()
            
            device_info = self.p.get_device_info_by_index(device_index)
            logger.info(f"Recording from: {device_info['name']}")
            
            # Create stream
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
                start=False
            )
            
            logger.info("Audio stream created successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to setup audio: {e}")
            logger.info("Running in mock mode - no real audio will be captured")
            # Return False to indicate mock mode
            return False
    
    def run(self):
        """Main recording loop."""
        try:
            audio_available = self.setup_audio()
            self.running = True
            
            if audio_available:
                self.stream.start_stream()
                logger.info("Recording started")
                self._run_real_audio()
            else:
                logger.info("Starting in mock mode")
                self._run_mock_audio()
        
        except Exception as e:
            logger.error(f"Recorder worker failed: {e}")
        
        finally:
            self.stop()
    
    def _run_real_audio(self):
        """Recording loop with real audio."""
        sample_interval = self.config.sample_duration
        last_sample_time = datetime.utcnow()
        
        while self.running:
            try:
                # Read chunk from stream
                data = self.stream.read(self.config.chunk_size, 
                                    exception_on_overflow=False)
                chunk = np.frombuffer(data, dtype=np.float32)
                
                # Add to buffer
                self.audio_buffer.add_chunk(chunk)
                
                # Check if we should send a sample
                now = datetime.utcnow()
                elapsed = (now - last_sample_time).total_seconds()
                
                buffer_ready = self.audio_buffer.is_ready()
                logger.info(
                    f"Buffer status: elapsed={elapsed:.2f}s, ready={buffer_ready}, "
                    f"buffer_len={len(self.audio_buffer.buffer)}, needed={self.audio_buffer.sample_size}"
                ) # TODO: Change back to debug or remove
                
                if elapsed >= sample_interval and buffer_ready:
                    sample = self.audio_buffer.get_sample()
                    if sample is not None:
                        logger.info(f"Queuing sample for analysis (size: {len(sample)} samples)")  # ADD THIS
                        self.samples_queue.put({
                            'audio': sample,
                            'timestamp': now,
                            'sample_rate': self.config.sample_rate
                        })
                        last_sample_time = now
            
            except Exception as e:
                logger.error(f"Error in recording loop: {e}")
                continue
    
    def _run_mock_audio(self):
        """Recording loop in mock mode (generates random audio)."""
        sample_interval = self.config.sample_duration
        last_sample_time = datetime.utcnow()
        
        while self.running:
            try:
                # Sleep a bit to avoid busy looping
                time.sleep(0.1)
                
                # Check if we should send a sample
                now = datetime.utcnow()
                elapsed = (now - last_sample_time).total_seconds()
                
                if elapsed >= sample_interval:
                    # Generate mock audio (silent audio with some noise)
                    mock_sample = np.random.normal(0, 0.01, 
                                                  self.config.sample_rate * sample_interval).astype(np.float32)
                    self.samples_queue.put({
                        'audio': mock_sample,
                        'timestamp': now,
                        'sample_rate': self.config.sample_rate,
                        'is_mock': True
                    })
                    last_sample_time = now
            
            except Exception as e:
                logger.error(f"Error in mock recording loop: {e}")
                continue
    
    def stop(self):
        """Stop recording."""
        self.running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
        
        if self.p:
            self.p.terminate()
        
        logger.info("Recording stopped")
