"""Main entry point for the bird detection listener."""
import signal
import sys
import logging
from queue import Queue
from threading import Thread
import time

from config import load_config, setup_logging
from database import DetectionDatabase
from recorder import RecorderWorker
from analyzer import AnalyzerWorker
from db_writer import DbWriterWorker
from api import ListenerAPI


class ListenerService:
    def __init__(self):
        self.listener_config, self.db_config = load_config()
        self.logger = setup_logging(self.listener_config.log_level)
        self.logger.info("Initializing Listener Service...")
        
        self.db = DetectionDatabase(self.db_config.db_path)
        self.samples_queue = Queue(maxsize=100)
        self.detections_queue = Queue(maxsize=100)
        
        self.recorder = RecorderWorker(self.listener_config, self.samples_queue)
        self.analyzers = [
            AnalyzerWorker(
                self.listener_config,
                self.samples_queue,
                self.detections_queue
            )
            for _ in range(self.listener_config.num_workers)
        ]
        self.db_writer = DbWriterWorker(
            self.listener_config,
            self.db,
            self.detections_queue
        )
        
        self.api = ListenerAPI(self.listener_config, self.db)
        self.threads = []
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Listener Service initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start all workers."""
        try:
            self.logger.info("Starting Listener Service...")
            
            # Start recorder in thread
            recorder_thread = Thread(
                target=self.recorder.run,
                name="RecorderWorker",
                daemon=False
            )
            recorder_thread.start()
            self.threads.append(recorder_thread)
            
            # Start analyzer workers
            for i, analyzer in enumerate(self.analyzers):
                analyzer_thread = analyzer.start()
                analyzer_thread.name = f"AnalyzerWorker-{i+1}"
                self.threads.append(analyzer_thread)
            
            # Start database writer
            db_writer_thread = self.db_writer.start()
            db_writer_thread.name = "DbWriterWorker"
            self.threads.append(db_writer_thread)
            
            # Start API server in thread
            api_thread = Thread(
                target=self.api.run,
                name="APIServer",
                daemon=True
            )
            api_thread.start()
            self.threads.append(api_thread)
            
            self.logger.info("All workers started successfully")
            self.logger.info(
                f"API Server running on "
                f"{self.listener_config.api_host}:"
                f"{self.listener_config.api_port}"
            )
            
            # Wait for threads
            for thread in self.threads:
                if not thread.daemon:
                    thread.join()
        
        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop all workers."""
        self.logger.info("Stopping all workers...")
        self.running = False
        
        # Stop recorder
        self.recorder.stop()
        
        # Stop analyzers
        for analyzer in self.analyzers:
            analyzer.stop()
            # Send poison pill
            self.samples_queue.put(None)
        
        # Stop database writer
        self.db_writer.stop()
        self.detections_queue.put(None)
        
        # Wait for threads to finish
        for thread in self.threads:
            if not thread.daemon and thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("All workers stopped")


def main():
    """Main entry point."""
    try:
        service = ListenerService()
        service.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
