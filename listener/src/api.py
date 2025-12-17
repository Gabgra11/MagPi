"""
API server for the listener service.
Provides REST endpoints for the dashboard.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
from functools import wraps

logger = logging.getLogger("magpi-listener")


class ListenerAPI:
    """REST API for the listener service."""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.app = Flask(__name__)
        CORS(self.app)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        @self.app.route('/api/detections', methods=['GET'])
        def get_detections():
            """Get recent detections."""
            try:
                limit = request.args.get('limit', 100, type=int)
                offset = request.args.get('offset', 0, type=int)
                species = request.args.get('species', None)
                
                if species:
                    detections = self.db.get_detections_by_species(species)
                else:
                    detections = self.db.get_recent_detections(limit, offset)
                
                return jsonify({
                    'success': True,
                    'data': detections,
                    'count': len(detections)
                })
            except Exception as e:
                logger.error(f"Error getting detections: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """Get statistics."""
            try:
                days = request.args.get('days', 7, type=int)
                stats = self.db.get_stats(days)
                
                return jsonify({
                    'success': True,
                    'data': stats
                })
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/species', methods=['GET'])
        def get_species():
            """Get all detected species."""
            try:
                days = request.args.get('days', 7, type=int)
                species_list = self.db.get_all_species(days)
                
                data = [
                    {
                        'species': s[0],
                        'count': s[1]
                    }
                    for s in species_list
                ]
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data)
                })
            except Exception as e:
                logger.error(f"Error getting species: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/heatmap', methods=['GET'])
        def get_heatmap():
            """Get hourly activity data for heatmap."""
            try:
                days = request.args.get('days', 7, type=int)
                data = self.db.get_hourly_activity(days)
                
                return jsonify({
                    'success': True,
                    'data': data
                })
            except Exception as e:
                logger.error(f"Error getting heatmap data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/trends', methods=['GET'])
        def get_trends():
            """Get daily activity trends."""
            try:
                days = request.args.get('days', 365, type=int)
                data = self.db.get_daily_activity(days)
                
                return jsonify({
                    'success': True,
                    'data': data
                })
            except Exception as e:
                logger.error(f"Error getting trends: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """Get current configuration."""
            try:
                config_dict = {
                    'audio_device': self.config.audio_device,
                    'sample_rate': self.config.sample_rate,
                    'min_confidence': self.config.min_confidence,
                    'duplicate_window': self.config.duplicate_window,
                    'location': {
                        'lat': self.config.birdnet_location_lat,
                        'lon': self.config.birdnet_location_lon,
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': config_dict
                })
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'success': False,
                'error': 'Endpoint not found'
            }), 404
    
    def run(self):
        """Start the API server."""
        self.app.run(
            host=self.config.api_host,
            port=self.config.api_port,
            debug=False,
            threaded=True
        )
