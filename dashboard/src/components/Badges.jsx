import { useState, useEffect } from 'react';
import { statsService } from '../services/api';
import { Card, Badge, LoadingSpinner, ErrorAlert } from './ui';

const MILESTONES = [
  { count: 10, label: '10 Detections' },
  { count: 50, label: '50 Detections' },
  { count: 100, label: '100 Detections' },
  { count: 5, label: '5 Species' },
  { count: 10, label: '10 Species' },
  { count: 20, label: '20 Species' },
];

export const BadgesCard = () => {
  const [species, setSpecies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [speciesRes, statsRes] = await Promise.all([
          statsService.getSpecies(365),
          statsService.getStats(365),
        ]);
        setSpecies(speciesRes.data.data);
        setStats(statsRes.data.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  const uniqueSpecies = stats?.unique_species || 0;
  const totalDetections = stats?.total_detections || 0;

  const earnedBadges = MILESTONES.filter((milestone) => {
    if (milestone.label.includes('Detection')) {
      return totalDetections >= milestone.count;
    } else if (milestone.label.includes('Species')) {
      return uniqueSpecies >= milestone.count;
    }
    return false;
  });

  return (
    <Card>
      <h3 className="text-lg font-semibold mb-4">🏅 Achievements</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {earnedBadges.length === 0 ? (
          <p className="col-span-full text-gray-500 text-center py-8">
            No badges yet
          </p>
        ) : (
          earnedBadges.map((badge, idx) => (
            <div key={idx} className="text-center">
              <div className="text-3xl mb-2">{badge.icon}</div>
              <p className="text-xs font-semibold text-gray-700">{badge.label}</p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
