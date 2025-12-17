import { useStats, useSpecies } from '../hooks/useStats';
import { Card, Stat, LoadingSpinner, ErrorAlert } from './ui';

export const StatsOverview = () => {
  const { stats, loading, error } = useStats(7);
  const { species } = useSpecies(7);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <Stat
          label="Total Detections"
          value={stats?.total_detections || 0}
        />
      </Card>
      <Card>
        <Stat label="Unique Species" value={stats?.unique_species || 0} />
      </Card>
      <Card>
        <Stat
          label="Avg Confidence"
          value={`${((stats?.avg_confidence || 0) * 100).toFixed(1)}%`}
        />
      </Card>
      <Card>
        <Stat label="Period" value={`${stats?.period_days || 0} days`} />
      </Card>
    </div>
  );
};

export const SpeciesLeaderboard = () => {
  const { species, loading, error } = useSpecies(7);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <Card>
      <h3 className="text-lg font-semibold mb-4">Top Species This Week</h3>
      <div className="space-y-2">
        {species.slice(0, 10).map((sp, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between p-3 bg-white/50 rounded-lg"
          >
            <div className="flex items-center gap-3">
              <span className="font-bold text-lg text-purple-600">#{idx + 1}</span>
              <span className="font-semibold text-gray-900">{sp.species}</span>
            </div>
            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold">
              {sp.count}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
};
