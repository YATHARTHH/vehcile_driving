import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Trip } from '../types';
import { 
  Gauge, Navigation, Zap, Fuel, Activity, ArrowUpRight 
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line 
} from 'recharts';

export const Dashboard: React.FC = () => {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrips = async () => {
      try {
        const res = await api.get('/trips');
        setTrips(res.data);
      } catch (err) {
        console.error('Failed to fetch trips', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrips();
  }, []);

  // Compute Telematics Aggregates
  const totalDistance = trips.reduce((sum, t) => sum + (t.distance_km || 0), 0);
  const avgSpeed = trips.length > 0 ? (trips.reduce((sum, t) => sum + (t.avg_speed_kmph || 0), 0) / trips.length).toFixed(1) : '0';
  const totalFuel = trips.reduce((sum, t) => sum + (t.fuel_consumed || 0), 0);
  const avgEfficiency = totalFuel > 0 ? (totalDistance / totalFuel).toFixed(1) : '0';
  const peakRpm = trips.length > 0 ? Math.max(...trips.map(t => t.max_rpm || 0)) : 0;

  // Chart Data Preparation (Reverse chronologically for left-to-right timeline)
  const chartData = [...trips].reverse().map((t, idx) => ({
    name: t.trip_date || `Trip #${idx + 1}`,
    speed: t.avg_speed_kmph,
    rpm: t.max_rpm,
    fuel: t.fuel_consumed,
    distance: t.distance_km
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-slate-400">Loading Telematics Data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6 rounded-3xl border border-brand-500/20">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Telematics Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time driving scores, fuel telemetry, and vehicle health metrics
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/route-planner"
            className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-medium text-sm transition-all shadow-md glow-brand flex items-center space-x-2"
          >
            <Navigation className="w-4 h-4" />
            <span>Plan Route</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Distance</span>
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Navigation className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white">{totalDistance.toFixed(1)}</span>
            <span className="text-sm text-slate-400">km</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Speed</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Gauge className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white">{avgSpeed}</span>
            <span className="text-sm text-slate-400">km/h</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fuel Efficiency</span>
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Fuel className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white">{avgEfficiency}</span>
            <span className="text-sm text-slate-400">km/L</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Peak RPM</span>
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-white">{peakRpm}</span>
            <span className="text-sm text-slate-400">RPM</span>
          </div>
        </div>
      </div>

      {/* Telemetry Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Speed vs RPM Chart */}
        <div className="glass-card p-6 rounded-3xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="font-bold text-slate-100 text-lg">Speed & Engine Load Dynamics</h3>
              <p className="text-xs text-slate-400">Average Speed (km/h) vs Engine Max RPM over recent trips</p>
            </div>
            <Activity className="w-5 h-5 text-brand-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="speedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} 
                />
                <Area type="monotone" dataKey="speed" stroke="#10b981" fillOpacity={1} fill="url(#speedGrad)" name="Avg Speed (km/h)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Distance vs Fuel Chart */}
        <div className="glass-card p-6 rounded-3xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="font-bold text-slate-100 text-lg">Fuel Consumption Analysis</h3>
              <p className="text-xs text-slate-400">Trip Distance (km) vs Fuel Consumed (L)</p>
            </div>
            <Fuel className="w-5 h-5 text-amber-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} 
                />
                <Line type="monotone" dataKey="distance" stroke="#3b82f6" strokeWidth={2} name="Distance (km)" />
                <Line type="monotone" dataKey="fuel" stroke="#f59e0b" strokeWidth={2} name="Fuel (L)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Trips Table */}
      <div className="glass-card p-6 rounded-3xl overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-slate-100 text-lg">Recent Trip Records</h3>
          <span className="text-xs text-slate-400 font-mono">Total {trips.length} trips</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-dark-border text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Distance</th>
                <th className="py-3 px-4">Avg Speed</th>
                <th className="py-3 px-4">Max RPM</th>
                <th className="py-3 px-4">Fuel Consumed</th>
                <th className="py-3 px-4">Brake Events</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border text-sm font-medium">
              {trips.map((t) => (
                <tr key={t.id} className="hover:bg-dark-hover/60 transition-colors">
                  <td className="py-3.5 px-4 text-slate-300">{t.trip_date || 'N/A'}</td>
                  <td className="py-3.5 px-4 text-slate-200">{t.distance_km} km</td>
                  <td className="py-3.5 px-4 text-slate-200">{t.avg_speed_kmph} km/h</td>
                  <td className="py-3.5 px-4 text-slate-200">{t.max_rpm} RPM</td>
                  <td className="py-3.5 px-4 text-slate-200">{t.fuel_consumed} L</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      t.brake_events > 10 ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}>
                      {t.brake_events} events
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      to={`/trip/${t.id}`}
                      className="inline-flex items-center space-x-1 text-xs font-semibold text-brand-400 hover:text-brand-300 transition-colors"
                    >
                      <span>Analyze</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
