import { useState, useEffect } from 'react';
import { detectionService } from '../services/api';
import { Card, LoadingSpinner, ErrorAlert } from './ui';
import { format } from 'date-fns';

export const RecentDetections = ({ limit = 20 }) => {
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetections = async () => {
      try {
        const response = await detectionService.getRecent(limit);
        setDetections(response.data.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDetections();
    const interval = setInterval(fetchDetections, 5000);

    return () => clearInterval(interval);
  }, [limit]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <Card>
      <h3 className="text-lg font-semibold mb-4">Recent Detections</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {detections.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No detections yet</p>
        ) : (
          detections.map((detection) => (
            <div
              key={detection.id}
              className="flex items-center justify-between p-3 bg-white/50 rounded-lg hover:bg-white/80 transition-colors"
            >
              <div>
                <p className="font-semibold text-gray-900">{detection.species}</p>
                <p className="text-xs text-gray-500">
                  {format(new Date(detection.timestamp), 'MMM dd, HH:mm:ss')}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-blue-600">
                  {(detection.confidence * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
