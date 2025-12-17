import './index.css';
import { StatsOverview, SpeciesLeaderboard } from './components/Stats';
import { RecentDetections } from './components/RecentDetections';
import { HeatmapCard, TrendsCard } from './components/Visualizations';
import { BadgesCard } from './components/Badges';
import { ExpandableCard } from './components/ExpandableCard';

function App() {
  return (
    <div className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">
          MagPi Bird Detection
        </h1>
        <p className="text-white/80">
          Real-time bird species detection and analytics dashboard
        </p>
      </div>

      {/* Stats Overview */}
      <StatsOverview />

      {/* Main Grid */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Detections */}
        <div className="lg:col-span-1">
          <RecentDetections />
        </div>

        {/* Species Leaderboard */}
        <div className="lg:col-span-1">
          <SpeciesLeaderboard />
        </div>

        {/* Badges */}
        <div className="lg:col-span-1">
          <BadgesCard />
        </div>
      </div>

      {/* Visualizations */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ExpandableCard title="Activity Heatmap">
          <HeatmapCard />
        </ExpandableCard>

        <ExpandableCard title="Seasonal Trends">
          <TrendsCard />
        </ExpandableCard>
      </div>

      {/* Footer */}
      <div className="mt-12 text-center text-white/60 text-sm">
        <p>
          MagPi &copy; {new Date().getFullYear()} • Bird Detection Dashboard
        </p>
      </div>
    </div>
  );
}

export default App;
