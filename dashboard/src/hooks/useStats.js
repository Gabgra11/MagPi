import { useState, useEffect } from 'react';
import { statsService } from '../services/api';

export const useStats = (days = 7, refreshInterval = 30000) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await statsService.getStats(days);
        setStats(response.data.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, refreshInterval);

    return () => clearInterval(interval);
  }, [days, refreshInterval]);

  return { stats, loading, error };
};

export const useSpecies = (days = 7, refreshInterval = 30000) => {
  const [species, setSpecies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSpecies = async () => {
      try {
        setLoading(true);
        const response = await statsService.getSpecies(days);
        setSpecies(response.data.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSpecies();
    const interval = setInterval(fetchSpecies, refreshInterval);

    return () => clearInterval(interval);
  }, [days, refreshInterval]);

  return { species, loading, error };
};
