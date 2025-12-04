#!/usr/bin/env python3
"""
Continuous bird call detection system for Raspberry Pi
Records, analyzes, and stores bird detections with no gaps in coverage
"""

import sqlite3
import time
import signal
import sys
from datetime import datetime
from multiprocessing import Process, Queue, Event, cpu_count
from queue import Empty, Full
import numpy as np
import sounddevice as sd
from birdnetlib import RecordingBuffer
from birdnetlib.analyzer import Analyzer
import os
from scipy.io.wavfile import write as wav_write
import traceback

# Force unbuffered output for systemd
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 3.0  # seconds per analysis chunk
OVERLAP = 0.5  # 50% overlap between chunks
CHANNELS = 1
DTYPE = 'float32'

# Queue sizes (tune based on your Pi's performance)
SAMPLES_QUEUE_SIZE = 10  # ~30 seconds of audio buffered
RESULTS_QUEUE_SIZE = 100  # Should be plenty for detections

# Detection thresholds
MIN_CONFIDENCE = 0.01  # BirdNET confidence threshold (lowered for testing)

# Deduplication settings
DEDUP_METHOD = 'time_window'  # 'time_window' or 'temporal_overlap'
DEDUP_WINDOW_SECONDS = 5.0  # For time_window method: ignore same species within N seconds

# Database configuration
DB_PATH = 'bird_detections.db'
AUDIO_SAVE_DIR = 'detected_audio'


def log(msg):
    """Helper function to ensure logging works in multiprocessing"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def find_usb_audio_device():
    """Find USB microphone device index"""
    try:
        devices = sd.query_devices()
        log("\n=== Available Audio Devices ===")
        for i, device in enumerate(devices):
            log(f"[{i}] {device['name']}")
            log(f"    Inputs: {device['max_input_channels']}, Outputs: {device['max_output_channels']}")
        log("=" * 40 + "\n")
        
        for i, device in enumerate(devices):
            name = device['name'].lower()
            if 'usb' in name or 'webcam' in name or '0x' in name:
                if device['max_input_channels'] > 0:
                    log(f"Found USB audio device at index {i}: {device['name']}")
                    return i
        
        # If no USB device found, find default input
        default_input = sd.default.device[0]
        log(f"WARNING: No USB device found, using default input device: {default_input}")
        return default_input
    except Exception as e:
        log(f"ERROR detecting audio device: {e}")
        traceback.print_exc()
        log("Falling back to device index 1")
        return 1


# Auto-detect audio device or use hardcoded value
AUDIO_DEVICE = find_usb_audio_device() if os.getenv('AUTO_DETECT_AUDIO', '1') == '1' else 1


def setup_database():
    """Initialize SQLite database with detections table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            common_name TEXT NOT NULL,
            scientific_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON detections(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    log(f"Database initialized at {DB_PATH}")
    os.makedirs(AUDIO_SAVE_DIR, exist_ok=True)
    log(f"Audio save directory created at {AUDIO_SAVE_DIR}")


def recording_worker(samples_queue, stop_event):
    """
    Continuously records audio and pushes overlapping chunks to queue.
    Ensures no gaps in audio coverage.
    """
    # Reconfigure stdout/stderr for this process
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    # Force ALSA backend for systemd compatibility
    os.environ['SDL_AUDIODRIVER'] = 'alsa'
    
    try:
        log("Recording worker started")
        log(f"Using audio device index: {AUDIO_DEVICE}")
        
        # Query device info
        devices = sd.query_devices()
        device_info = devices[AUDIO_DEVICE]
        log(f"Device info: {device_info}")
        
        # Verify device has input channels
        if device_info['max_input_channels'] < 1:
            log(f"ERROR: Device {AUDIO_DEVICE} has no input channels!")
            stop_event.set()
            return
            
    except Exception as e:
        log(f"ERROR in recording worker initialization: {e}")
        traceback.print_exc()
        stop_event.set()
        return
    
    chunk_samples = int(SAMPLE_RATE * CHUNK_DURATION)
    hop_samples = int(SAMPLE_RATE * CHUNK_DURATION * (1 - OVERLAP))
    
    # Buffer to hold audio for creating overlapping chunks
    buffer = np.zeros(chunk_samples, dtype=DTYPE)
    buffer_pos = 0
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal buffer_pos
        if status:
            log(f"Recording status: {status}")
        
        # Copy incoming audio to buffer
        audio = indata[:, 0].copy()  # Get mono channel
        
        # Fill buffer and emit chunks
        for i in range(len(audio)):
            buffer[buffer_pos] = audio[i]
            buffer_pos += 1
            
            # When buffer is full, emit chunk and shift buffer
            if buffer_pos >= chunk_samples:
                chunk = buffer.copy()
                timestamp = datetime.now().isoformat()
                
                # Try to put in queue (blocks if full - this is intentional)
                try:
                    samples_queue.put((timestamp, chunk), timeout=1.0)
                except Full:
                    log("WARNING: Samples queue full! Analysis cannot keep up.")
                
                # Shift buffer by hop size to create overlap
                buffer[:chunk_samples - hop_samples] = buffer[hop_samples:]
                buffer_pos = chunk_samples - hop_samples
    
    # Start continuous recording
    try:
        log("Opening audio stream...")
        log(f"Stream parameters: rate={SAMPLE_RATE}, device={AUDIO_DEVICE}, channels={CHANNELS}, dtype={DTYPE}")
        
        # Set a timeout for stream initialization
        import threading
        
        stream = None
        exception_holder = [None]
        
        def open_stream():
            try:
                nonlocal stream
                stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    device=AUDIO_DEVICE,
                    channels=CHANNELS,
                    dtype=DTYPE,
                    callback=audio_callback,
                    blocksize=2048,
                    latency='high'
                )
                stream.start()
            except Exception as e:
                exception_holder[0] = e
        
        # Try to open stream with timeout
        thread = threading.Thread(target=open_stream, daemon=True)
        thread.start()
        thread.join(timeout=10.0)  # 10 second timeout
        
        if thread.is_alive():
            log("ERROR: Audio stream open timed out after 10 seconds!")
            log("This usually means ALSA/audio system is blocked.")
            stop_event.set()
            return
        
        if exception_holder[0]:
            raise exception_holder[0]
        
        if stream is None:
            log("ERROR: Stream object is None after thread completion")
            stop_event.set()
            return
        
        log(f"Recording started: {SAMPLE_RATE}Hz, {CHUNK_DURATION}s chunks, {OVERLAP*100}% overlap")
        
        while not stop_event.is_set():
            time.sleep(0.1)
        
        log("Stopping stream...")
        stream.stop()
        stream.close()
        log("Stream closed")
        
    except Exception as e:
        log(f"FATAL ERROR starting audio stream: {e}")
        traceback.print_exc()
        stop_event.set()  # Signal other workers to stop
    
    log("Recording worker stopped")


def analyzing_worker(samples_queue, results_queue, stop_event, worker_id=0):
    """
    Pulls audio samples from queue and analyzes for bird calls.
    Pushes detections to results queue.
    """
    # Reconfigure stdout/stderr for this process
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    log(f"Analyzing worker {worker_id} started")
    
    try:
        # Initialize BirdNET analyzer
        log(f"Worker {worker_id}: Initializing BirdNET analyzer...")
        analyzer = Analyzer()
        log(f"Worker {worker_id}: BirdNET analyzer initialized")
    except Exception as e:
        log(f"ERROR: Worker {worker_id} failed to initialize analyzer: {e}")
        traceback.print_exc()
        return
    
    processed_count = 0
    
    while not stop_event.is_set() or not samples_queue.empty():
        try:
            timestamp, audio_data = samples_queue.get(timeout=1.0)
        except Empty:
            continue
        
        try:
            # Debug: Check audio data
            audio_level = np.abs(audio_data).mean()
            audio_max = np.abs(audio_data).max()
            if processed_count % 20 == 0:  # Every 20 samples
                log(f"Worker {worker_id}: Audio - mean: {audio_level:.4f}, "
                    f"max: {audio_max:.4f}, shape: {audio_data.shape}, "
                    f"dtype: {audio_data.dtype}")
            
            # Create RecordingBuffer object for analysis
            recording = RecordingBuffer(
                analyzer,
                audio_data,
                SAMPLE_RATE,
                min_conf=MIN_CONFIDENCE,
            )
            
            recording.analyze()
            
            # Log detection results
            num_detections = len(recording.detections) if recording.detections else 0
            if processed_count % 20 == 0 or num_detections > 0:
                log(f"Worker {worker_id}: Processed sample, detections: {num_detections}")

            # Process detections
            if recording.detections:
                # Save audio clip for each detection
                for detection in recording.detections:
                    # Save audio segment as WAV file
                    species = detection['common_name'].replace(' ', '_')
                    det_time = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{det_time}_{species}_worker{worker_id}.wav"
                    filepath = os.path.join(AUDIO_SAVE_DIR, filename)
                    wav_write(filepath, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
                    log(f"Saved detected audio: {filepath}")
                    
                    result = {
                        'timestamp': timestamp,
                        'common_name': detection['common_name'],
                        'scientific_name': detection['scientific_name'],
                        'confidence': detection['confidence'],
                        'start_time': detection['start_time'],
                        'end_time': detection['end_time']
                    }
                    
                    results_queue.put(result)
            
            processed_count += 1
            if processed_count % 100 == 0:
                log(f"Worker {worker_id}: Processed {processed_count} samples")
        
        except Exception as e:
            log(f"Error analyzing sample: {e}")
            traceback.print_exc()
    
    log(f"Analyzing worker {worker_id} stopped after processing {processed_count} samples")


def database_worker(results_queue, stop_event):
    """
    Pulls detection results from queue and writes to database.
    Batches writes for efficiency and deduplicates detections.
    """
    # Reconfigure stdout/stderr for this process
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    log("Database worker started")
    log(f"Deduplication method: {DEDUP_METHOD}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    batch = []
    batch_size = 10
    last_commit = time.time()
    commit_interval = 5.0  # Commit every 5 seconds
    
    written_count = 0
    skipped_count = 0
    
    def is_duplicate_time_window(result):
        """Check if same species detected within time window"""
        # Parse the timestamp
        result_time = datetime.fromisoformat(result['timestamp'])
        window_start = (result_time.timestamp() - DEDUP_WINDOW_SECONDS)
        
        cursor.execute(
            '''SELECT COUNT(*) FROM detections
               WHERE scientific_name = ?
               AND strftime('%s', timestamp) > ?''',
            (result['scientific_name'], window_start)
        )
        count = cursor.fetchone()[0]
        return count > 0
    
    def is_duplicate_temporal_overlap(result):
        """Check if same species with overlapping time range exists"""
        # Parse the timestamp to get approximate absolute times
        result_time = datetime.fromisoformat(result['timestamp'])
        
        # Convert relative detection times to absolute
        abs_start = result_time.timestamp() + result['start_time']
        abs_end = result_time.timestamp() + result['end_time']
        
        # Check for overlapping detections of same species
        # Overlap occurs if: new_start < existing_end AND new_end > existing_start
        cursor.execute(
            '''SELECT id, confidence, start_time, end_time, timestamp
               FROM detections
               WHERE scientific_name = ?
               AND strftime('%s', timestamp) + end_time > ?
               AND strftime('%s', timestamp) + start_time < ?
               ORDER BY confidence DESC
               LIMIT 1''',
            (result['scientific_name'], abs_start, abs_end)
        )
        
        existing = cursor.fetchone()
        if existing:
            existing_id, existing_conf = existing[0], existing[1]
            # If existing has higher confidence, this is a duplicate
            # If this has higher confidence, delete the existing one
            if result['confidence'] > existing_conf:
                cursor.execute('DELETE FROM detections WHERE id = ?', (existing_id,))
                return False  # Not a duplicate, we're replacing the old one
            return True
        return False
    
    while not stop_event.is_set() or not results_queue.empty():
        try:
            result = results_queue.get(timeout=1.0)
            
            # Check for duplicates based on configured method
            is_dup = False
            if DEDUP_METHOD == 'time_window':
                is_dup = is_duplicate_time_window(result)
            elif DEDUP_METHOD == 'temporal_overlap':
                is_dup = is_duplicate_temporal_overlap(result)
            
            if is_dup:
                skipped_count += 1
            else:
                batch.append(result)
        except Empty:
            pass
        
        # Write batch if it's full or enough time has passed
        if batch and (len(batch) >= batch_size or
                     time.time() - last_commit > commit_interval):
            try:
                cursor.executemany(
                    '''INSERT INTO detections
                       (timestamp, common_name, scientific_name, confidence, start_time, end_time)
                       VALUES (:timestamp, :common_name, :scientific_name, :confidence,
                               :start_time, :end_time)''',
                    batch
                )
                conn.commit()
                written_count += len(batch)
                log(f"Wrote {len(batch)} detections to database "
                    f"(total: {written_count}, duplicates skipped: {skipped_count})")
                batch = []
                last_commit = time.time()
            except Exception as e:
                log(f"Error writing to database: {e}")
                traceback.print_exc()
                batch = []  # Clear batch to avoid repeated errors
    
    # Write any remaining results
    if batch:
        cursor.executemany(
            '''INSERT INTO detections
               (timestamp, common_name, scientific_name, confidence, start_time, end_time)
               VALUES (:timestamp, :common_name, :scientific_name, :confidence,
                       :start_time, :end_time)''',
            batch
        )
        conn.commit()
        written_count += len(batch)
    
    conn.close()
    log(f"Database worker stopped after writing {written_count} detections "
        f"({skipped_count} duplicates skipped)")


def monitor_worker(samples_queue, results_queue, stop_event):
    """
    Monitors queue depths to detect if system is falling behind.
    """
    # Reconfigure stdout/stderr for this process
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    log("Monitor worker started")
    
    while not stop_event.is_set():
        samples_depth = samples_queue.qsize()
        results_depth = results_queue.qsize()
        
        if samples_depth > SAMPLES_QUEUE_SIZE * 0.8:
            log(f"WARNING: Samples queue is {samples_depth}/{SAMPLES_QUEUE_SIZE} - "
                f"analysis may be falling behind!")
        
        if results_depth > RESULTS_QUEUE_SIZE * 0.8:
            log(f"WARNING: Results queue is {results_depth}/{RESULTS_QUEUE_SIZE} - "
                f"database writes may be falling behind!")
        
        time.sleep(10)  # Check every 10 seconds
    
    log("Monitor worker stopped")


def main():
    """
    Main coordinator process.
    Sets up database, queues, workers, and handles shutdown.
    """
    log("=" * 60)
    log("Bird Call Detection System - Starting")
    log("=" * 60)
    
    # Initialize database
    setup_database()
    
    # Create queues with size limits
    samples_queue = Queue(maxsize=SAMPLES_QUEUE_SIZE)
    results_queue = Queue(maxsize=RESULTS_QUEUE_SIZE)
    
    # Create stop event for coordinated shutdown
    stop_event = Event()
    
    # Determine number of analyzer workers
    # Leave 1 CPU for recording/db/monitor
    num_analyzers = 2  # max(1, cpu_count() - 1)
    log(f"Starting {num_analyzers} analyzer worker(s)")
    
    # Create worker processes
    workers = []
    
    # Recording worker
    rec_worker = Process(target=recording_worker,
                        args=(samples_queue, stop_event),
                        name="Recorder")
    workers.append(rec_worker)
    
    # Analyzer workers
    for i in range(num_analyzers):
        analyzer = Process(target=analyzing_worker,
                          args=(samples_queue, results_queue, stop_event, i),
                          name=f"Analyzer-{i}")
        workers.append(analyzer)
    
    # Database worker
    db_worker = Process(target=database_worker,
                       args=(results_queue, stop_event),
                       name="Database")
    workers.append(db_worker)
    
    # Monitor worker
    mon_worker = Process(target=monitor_worker,
                        args=(samples_queue, results_queue, stop_event),
                        name="Monitor")
    workers.append(mon_worker)
    
    # Start all workers
    for worker in workers:
        log(f"Starting {worker.name}...")
        worker.start()
        log(f"Started {worker.name} (PID: {worker.pid})")
        time.sleep(0.5)  # Small delay between worker starts
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        log("\n" + "=" * 60)
        log("Shutdown signal received - stopping workers...")
        log("=" * 60)
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log("\n" + "=" * 60)
    log("System running - Press Ctrl+C to stop")
    log("=" * 60 + "\n")
    
    # Check if workers are actually running
    time.sleep(2)
    for worker in workers:
        if not worker.is_alive():
            log(f"ERROR: {worker.name} died immediately after starting!")
            stop_event.set()
            break
    
    # Wait for all workers to finish
    try:
        for worker in workers:
            worker.join()
    except KeyboardInterrupt:
        stop_event.set()
        for worker in workers:
            worker.join(timeout=5)
            if worker.is_alive():
                log(f"Force terminating {worker.name}")
                worker.terminate()
    
    log("\n" + "=" * 60)
    log("Bird Call Detection System - Stopped")
    log("=" * 60)


if __name__ == '__main__':
    main()
