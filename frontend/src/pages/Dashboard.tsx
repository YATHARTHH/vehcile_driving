import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Trip } from '../types';
import { 
  Gauge, Navigation, Fuel, Activity, ArrowUpRight, Search, Download, FileText, 
  CheckSquare, Square, X, BarChart2, Filter, CalendarCheck, MoreVertical,
  Radio, AlertTriangle, Compass, Play, Square as StopSquare, Zap
} from 'lucide-react';
import { useAuth } from '../store/authContext';
import { useTelemetryStream } from '../hooks/useTelemetryStream';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line,
  BarChart, Bar, PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis
} from 'recharts';

const COLOR_PALETTE = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#14b8a6', '#6366f1', '#ef4444',
  '#0ea5e9', '#a855f7'
];

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Real-time Telemetry WebSocket & Hot-State Streaming
  const { liveState, connectionStatus, isLive } = useTelemetryStream();

  // In-browser live simulation controls
  const [simInterval, setSimInterval] = useState<number | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  useEffect(() => {
    return () => {
      if (simInterval) window.clearInterval(simInterval);
    };
  }, [simInterval]);

  const triggerSimulationPacket = async (hazard: boolean = false) => {
    setIsSimulating(true);
    try {
      const targetSpeed = hazard ? 148.0 : Math.round(45 + Math.random() * 40);
      const targetRpm = hazard ? 6200 : Math.round(2000 + Math.random() * 1800);
      const targetFuelRate = hazard ? 9.5 : Number((3.6 + Math.random() * 2.2).toFixed(2));
      const targetLat = 37.7749 + (Math.random() - 0.5) * 0.01;
      const targetLon = -122.4194 + (Math.random() - 0.5) * 0.01;

      await api.post('/telemetry/ingest', {
        event_id: crypto.randomUUID(),
        event_timestamp: new Date().toISOString(),
        schema_version: 'v1.0.0',
        telemetry: {
          speed_kmph: targetSpeed,
          rpm: targetRpm,
          fuel_level_pct: 82.0,
          fuel_rate_lph: targetFuelRate,
          lat: targetLat,
          lon: targetLon,
          heading: Math.round(Math.random() * 360),
          brake_pressure_bar: hazard ? 15.0 : 0.0,
          engine_load_pct: hazard ? 94.0 : 48.0
        }
      });
    } catch (err) {
      console.error('Failed to trigger simulation packet', err);
    } finally {
      setIsSimulating(false);
    }
  };

  const toggleContinuousSimulation = () => {
    if (simInterval) {
      window.clearInterval(simInterval);
      setSimInterval(null);
    } else {
      triggerSimulationPacket(false);
      const id = window.setInterval(() => {
        triggerSimulationPacket(Math.random() < 0.12);
      }, 1000);
      setSimInterval(id);
    }
  };
  
  // Modals State
  const [showExportModal, setShowExportModal] = useState(false);
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [timeFilter, setTimeFilter] = useState('all');

  // Multi-Select Trip Comparison State
  const [selectedTripIds, setSelectedTripIds] = useState<number[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Advanced Filter Inputs State
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterMinDist, setFilterMinDist] = useState('');
  const [filterMaxDist, setFilterMaxDist] = useState('');
  const [filterMinSpeed, setFilterMinSpeed] = useState('');
  const [filterMaxSpeed, setFilterMaxSpeed] = useState('');

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

  // Filtered trips by Search Term & Advanced Filters
  const filteredTrips = trips.filter(t => {
    // Search term check
    const matchesSearch = 
      (t.trip_date && t.trip_date.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.start_location && t.start_location.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.end_location && t.end_location.toLowerCase().includes(searchTerm.toLowerCase()));
    
    if (!matchesSearch) return false;

    // Date range filter
    if (filterDateFrom && t.trip_date && t.trip_date < filterDateFrom) return false;
    if (filterDateTo && t.trip_date && t.trip_date > filterDateTo) return false;

    // Distance filter
    if (filterMinDist && t.distance_km < Number(filterMinDist)) return false;
    if (filterMaxDist && t.distance_km > Number(filterMaxDist)) return false;

    // Speed filter
    if (filterMinSpeed && t.avg_speed_kmph < Number(filterMinSpeed)) return false;
    if (filterMaxSpeed && t.avg_speed_kmph > Number(filterMaxSpeed)) return false;

    return true;
  });

  const resetFilters = () => {
    setSearchTerm('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterMinDist('');
    setFilterMaxDist('');
    setFilterMinSpeed('');
    setFilterMaxSpeed('');
    setShowFilterModal(false);
  };

  // Toggle trip selection for comparison
  const toggleSelectTrip = (id: number) => {
    setSelectedTripIds(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const selectAllFiltered = () => {
    if (selectedTripIds.length === filteredTrips.length) {
      setSelectedTripIds([]);
    } else {
      setSelectedTripIds(filteredTrips.map(t => t.id));
    }
  };

  // Compute Telematics Aggregates
  const totalDistance = trips.reduce((sum, t) => sum + (t.distance_km || 0), 0);
  const avgSpeed = trips.length > 0 ? (trips.reduce((sum, t) => sum + (t.avg_speed_kmph || 0), 0) / trips.length).toFixed(1) : '0';
  const totalFuel = trips.reduce((sum, t) => sum + (t.fuel_consumed || 0), 0);
  const totalTripsCount = trips.length;

  // Selected trips for comparison
  const selectedTrips = trips.filter(t => selectedTripIds.includes(t.id));

  // Chart Data Preparation (Chronological for left-to-right timeline)
  const chartData = [...filteredTrips].reverse().map((t, idx) => ({
    name: t.trip_date || `Trip #${idx + 1}`,
    distance: t.distance_km,
    avgSpeed: t.avg_speed_kmph,
    maxSpeed: t.max_speed,
    fuel: t.fuel_consumed,
    rpm: t.max_rpm,
    steering: t.steering_angle,
    brakeEvents: t.brake_events,
    angularVelocity: t.angular_velocity,
    acceleration: t.acceleration,
    gear: t.gear_position,
    tirePressure: t.tire_pressure || 32,
    engineLoad: t.engine_load || 45,
    throttle: t.throttle_position || 50,
    brakePressure: t.brake_pressure || 20,
    duration: t.trip_duration || 30,
    fuelEfficiency: t.fuel_consumed > 0 ? Number((t.distance_km / t.fuel_consumed).toFixed(2)) : 0,
    scatterX: idx
  }));

  // CSV Export Functionality
  const exportCSV = () => {
    const headers = [
      'Trip Date', 'Distance (km)', 'Avg Speed (km/h)', 'Max Speed (km/h)', 'Max RPM', 
      'Fuel Consumed (L)', 'Brake Events', 'Steering Angle', 'Angular Velocity', 
      'Acceleration', 'Gear Position', 'Tire Pressure (psi)', 'Engine Load (%)', 
      'Throttle Position (%)', 'Brake Pressure (psi)', 'Trip Duration (min)', 
      'Start Location', 'End Location'
    ];

    const rows = filteredTrips.map(t => [
      t.trip_date, t.distance_km, t.avg_speed_kmph, t.max_speed, t.max_rpm,
      t.fuel_consumed, t.brake_events, t.steering_angle, t.angular_velocity,
      t.acceleration, t.gear_position, t.tire_pressure, t.engine_load,
      t.throttle_position, t.brake_pressure, t.trip_duration,
      `"${t.start_location || ''}"`, `"${t.end_location || ''}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' 
      + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `vehicle_trips_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setShowExportModal(false);
  };

  // JSON Export Functionality
  const exportJSON = () => {
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(filteredTrips, null, 2)
    )}`;
    const link = document.createElement('a');
    link.setAttribute('href', jsonString);
    link.setAttribute('download', `vehicle_trips_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setShowExportModal(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-slate-400">Loading Telematics & Analytics Dashboard...</span>
        </div>
      </div>
    );
  }

  const maxEngineLoad = chartData.length > 0 ? Math.max(...chartData.map(d => d.engineLoad)) : 86.8;

  return (
    <div className="space-y-8 pb-12">
      {/* Welcome Title & Live Connection Status */}
      <div className="glass-card p-6 rounded-3xl border border-brand-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center glow-brand text-white shrink-0">
            <Gauge className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Vehicle Trip Analytics Dashboard</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Track and analyze your vehicle performance metrics, sensor telematics, and driving scores
            </p>
          </div>
        </div>

        {/* Live Stream Status Badge */}
        <div className="flex items-center space-x-3 shrink-0">
          <div className={`px-3.5 py-2 rounded-2xl border flex items-center space-x-2.5 text-xs font-semibold shadow-sm backdrop-blur-md ${
            isLive
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : connectionStatus === 'CONNECTING' || connectionStatus === 'AUTHENTICATING'
              ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
              : connectionStatus === 'RECONNECTING'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              : 'bg-slate-800/80 text-slate-400 border-slate-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              isLive ? 'bg-emerald-400 animate-ping' : 
              connectionStatus === 'CONNECTING' || connectionStatus === 'AUTHENTICATING' || connectionStatus === 'RECONNECTING' ? 'bg-amber-400 animate-pulse' : 'bg-slate-500'
            }`} />
            <Radio className="w-3.5 h-3.5" />
            <span>
              {isLive ? `LIVE STREAM (v${liveState?.state_version || 1})` : `STREAM: ${connectionStatus}`}
            </span>
          </div>
        </div>
      </div>

      {/* Real-time Telemetry Live Monitor Panel (Always Visible) */}
      <div className="glass-card p-6 rounded-3xl border border-brand-500/30 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-brand-950/20 relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-dark-border">
          <div className="flex items-center space-x-3">
            <div className={`w-3.5 h-3.5 rounded-full ${
              liveState ? 'bg-emerald-400 animate-ping' : isLive ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'
            }`} />
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <span className="text-xs font-bold uppercase tracking-widest text-brand-400">In-Flight Telemetry Stream</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  Vehicle: {liveState?.vehicle_id || user?.vehicle_number || 'MH12AB9999'}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Seq: #{liveState?.state_version || 0}
                </span>
                {simInterval && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/40 animate-pulse">
                    ● Simulator Active (1 Hz)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {liveState 
                  ? `Last updated ${new Date(liveState.event_timestamp || liveState.updated_at).toLocaleTimeString()} · Realtime WebSocket Broadcast`
                  : 'Vehicle Standby / Engine Off · WebSocket Gateway Ready & Listening'}
              </p>
            </div>
          </div>

          {/* Interactive Simulation & Test Controls */}
          <div className="flex items-center space-x-2 flex-wrap gap-y-2">
            <button
              onClick={toggleContinuousSimulation}
              disabled={isSimulating && !simInterval}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 border transition-all ${
                simInterval
                  ? 'bg-red-500/20 hover:bg-red-500/30 text-red-300 border-red-500/40'
                  : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border-emerald-500/40 shadow-sm'
              }`}
            >
              {simInterval ? <StopSquare className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{simInterval ? 'Stop Simulation' : 'Start Live Drive Stream'}</span>
            </button>

            <button
              onClick={() => triggerSimulationPacket(true)}
              disabled={isSimulating}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 border bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/40 transition-all"
              title="Dispatches an extreme speed & RPM hazard to test sub-second alert bypass"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Inject Hazard Alert</span>
            </button>

            <span className="px-2.5 py-1 rounded-xl text-xs font-semibold flex items-center space-x-1.5 border bg-slate-800 text-slate-300 border-slate-700">
              <Radio className={`w-3.5 h-3.5 ${isLive ? 'text-emerald-400 animate-pulse' : 'text-slate-400'}`} />
              <span>{connectionStatus}</span>
            </span>
          </div>
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
          <div className="bg-slate-900/70 p-4 rounded-2xl border border-dark-border">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Live Speed</span>
            <div className="flex items-baseline space-x-1 mt-1">
              <span className="text-3xl font-black text-white">
                {liveState ? liveState.speed_kmph.toFixed(1) : '0.0'}
              </span>
              <span className="text-xs text-slate-400 font-semibold">km/h</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div 
                className="bg-brand-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, ((liveState?.speed_kmph || 0) / 160) * 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-900/70 p-4 rounded-2xl border border-dark-border">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Engine RPM</span>
            <div className="flex items-baseline space-x-1 mt-1">
              <span className="text-3xl font-black text-white">
                {liveState ? Math.round(liveState.rpm) : '0'}
              </span>
              <span className="text-xs text-slate-400 font-semibold">RPM</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-300 ${
                  (liveState?.rpm || 0) > 4500 ? 'bg-red-500' : (liveState?.rpm || 0) > 3500 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, ((liveState?.rpm || 0) / 7000) * 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-900/70 p-4 rounded-2xl border border-dark-border">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Instant Fuel Rate</span>
            <div className="flex items-baseline space-x-1 mt-1">
              <span className="text-3xl font-black text-white">
                {liveState ? (liveState.fuel_rate_lph ?? 0).toFixed(2) : '0.00'}
              </span>
              <span className="text-xs text-slate-400 font-semibold">L/h</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div 
                className="bg-purple-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (((liveState?.fuel_rate_lph ?? 0)) / 25) * 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-900/70 p-4 rounded-2xl border border-dark-border">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">GPS Coordinates</span>
            <div className="text-sm font-bold font-mono text-white mt-1 truncate">
              {liveState?.lat != null ? liveState.lat.toFixed(4) : '37.7749'}, {liveState?.lon != null ? liveState.lon.toFixed(4) : '-122.4194'}
            </div>
            <div className="text-[11px] text-slate-400 mt-2 flex items-center space-x-1">
              <Compass className="w-3.5 h-3.5 text-brand-400" />
              <span>Heading: {liveState?.heading != null ? `${liveState.heading}°` : 'Standby'}</span>
            </div>
          </div>
        </div>

        {/* Live Alerts Stream */}
        {liveState?.active_alerts && liveState.active_alerts.length > 0 ? (
          <div className="mt-4 p-3.5 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="text-xs font-bold text-red-300 uppercase tracking-wider">Active Telemetry Alerts (Throttle Bypassed)</span>
              <div className="flex flex-wrap gap-2 pt-1">
                {liveState.active_alerts.map((alert, i) => (
                  <span 
                    key={i} 
                    className={`px-2 py-0.5 rounded-md text-xs font-medium border ${
                      alert.severity === 'CRITICAL' || alert.severity === 'HIGH'
                        ? 'bg-red-500/20 text-red-300 border-red-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    [{alert.code}] {alert.message}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-4 px-4 py-2.5 rounded-2xl bg-slate-900/50 border border-dark-border flex items-center justify-between text-xs text-slate-400">
            <span>● Vehicle Telemetry Nominal · No Active Mechanical or Safety Alerts</span>
            <span className="text-[11px] font-mono text-slate-500">Sub-second Alert Triggering Active</span>
          </div>
        )}
      </div>

      {/* 4 Main Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card p-5 rounded-2xl flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0">
            <Navigation className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Distance</span>
            <span className="text-2xl font-extrabold text-white">{totalDistance.toFixed(1)} km</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0">
            <Gauge className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Avg Speed</span>
            <span className="text-2xl font-extrabold text-white">{avgSpeed} km/h</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0">
            <Fuel className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Fuel</span>
            <span className="text-2xl font-extrabold text-white">{totalFuel.toFixed(1)} L</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
            <CalendarCheck className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Trips</span>
            <span className="text-2xl font-extrabold text-white">{totalTripsCount}</span>
          </div>
        </div>
      </div>

      {/* Recent Trip Summary Section */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Recent Trip Summary</h2>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Showing {filteredTrips.length} of {trips.length} trip records
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {selectedTripIds.length >= 2 && (
              <button
                onClick={() => setShowCompareModal(true)}
                className="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md glow-brand flex items-center space-x-2 transition-all"
              >
                <BarChart2 className="w-4 h-4" />
                <span>Compare {selectedTripIds.length} Trips</span>
              </button>
            )}

            <button
              onClick={() => setShowExportModal(true)}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-dark-border transition-all flex items-center space-x-2"
            >
              <Download className="w-4 h-4 text-brand-400" />
              <span>Export</span>
            </button>

            <button
              onClick={() => setShowFilterModal(true)}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-dark-border transition-all flex items-center space-x-2"
            >
              <Filter className="w-4 h-4 text-amber-400" />
              <span>Filter</span>
            </button>

            {/* Quick Search */}
            <div className="relative min-w-[200px]">
              <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search location/date..."
                className="w-full bg-slate-900/80 border border-dark-border rounded-xl pl-9 pr-4 py-2 text-slate-200 text-xs focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>
        </div>

        {/* Complete 16-Column Telemetry Table */}
        <div className="overflow-x-auto border border-dark-border rounded-2xl">
          <table className="w-full text-left border-collapse min-w-[1400px]">
            <thead>
              <tr className="bg-slate-900/90 border-b border-dark-border text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                <th className="py-3.5 px-3 w-10 text-center">
                  <button onClick={selectAllFiltered} className="text-slate-400 hover:text-white">
                    {selectedTripIds.length === filteredTrips.length && filteredTrips.length > 0 ? (
                      <CheckSquare className="w-4 h-4 text-brand-400" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="py-3.5 px-4">Trip Date</th>
                <th className="py-3.5 px-4">Distance</th>
                <th className="py-3.5 px-4">Avg Speed</th>
                <th className="py-3.5 px-4">Max Speed</th>
                <th className="py-3.5 px-4">Max RPM</th>
                <th className="py-3.5 px-4">Fuel</th>
                <th className="py-3.5 px-4">Brake Events</th>
                <th className="py-3.5 px-4">Steering Angle</th>
                <th className="py-3.5 px-4">Angular Vel</th>
                <th className="py-3.5 px-4">Acceleration</th>
                <th className="py-3.5 px-4">Gear</th>
                <th className="py-3.5 px-4">Tire Pressure</th>
                <th className="py-3.5 px-4">Engine Load</th>
                <th className="py-3.5 px-4">Throttle Pos</th>
                <th className="py-3.5 px-4">Brake Press</th>
                <th className="py-3.5 px-4">Duration</th>
                <th className="py-3.5 px-4 text-right">View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border text-xs font-medium">
              {filteredTrips.map((t) => {
                const isSelected = selectedTripIds.includes(t.id);
                return (
                  <tr key={t.id} className={`transition-colors ${isSelected ? 'bg-purple-500/10' : 'hover:bg-dark-hover/60'}`}>
                    <td className="py-3 px-3 text-center">
                      <button onClick={() => toggleSelectTrip(t.id)} className="text-slate-400 hover:text-white">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-purple-400" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                    <td className="py-3 px-4 text-white font-semibold">{t.trip_date || 'N/A'}</td>
                    <td className="py-3 px-4 text-slate-200">{t.distance_km} km</td>
                    <td className="py-3 px-4 text-slate-200">{t.avg_speed_kmph} km/h</td>
                    <td className="py-3 px-4 text-slate-200">{t.max_speed} km/h</td>
                    <td className="py-3 px-4 font-mono text-purple-300">{t.max_rpm}</td>
                    <td className="py-3 px-4 text-amber-300 font-semibold">{t.fuel_consumed} L</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        t.brake_events > 8 ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {t.brake_events}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{t.steering_angle}°</td>
                    <td className="py-3 px-4 text-slate-300">{t.angular_velocity}</td>
                    <td className="py-3 px-4 text-slate-300">{t.acceleration} m/s²</td>
                    <td className="py-3 px-4 text-slate-300">Gear {t.gear_position}</td>
                    <td className="py-3 px-4 text-slate-300">{t.tire_pressure || 32} psi</td>
                    <td className="py-3 px-4 text-slate-300">{t.engine_load || 45}%</td>
                    <td className="py-3 px-4 text-slate-300">{t.throttle_position || 50}%</td>
                    <td className="py-3 px-4 text-slate-300">{t.brake_pressure || 20} psi</td>
                    <td className="py-3 px-4 text-slate-300">{t.trip_duration || 30} min</td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/trip/${t.id}`}
                        className="inline-flex items-center space-x-1 font-semibold text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        <span>Details</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trip Performance Analytics Section (16 Visualizations Grid) */}
      <div className="glass-card p-6 rounded-3xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-dark-border pb-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Trip Performance Analytics</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              16 Telematics Sensor Visualization Channels
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="bg-slate-900 border border-dark-border rounded-xl px-3.5 py-2 text-slate-200 text-xs font-semibold focus:outline-none focus:border-brand-500"
            >
              <option value="all">All Time</option>
              <option value="month">Last Month</option>
              <option value="week">Last Week</option>
            </select>
          </div>
        </div>

        {/* 16 Charts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {/* 1. Distance Covered (km) */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Distance Covered (km)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Bar dataKey="distance" fill="#3b82f6" radius={[6, 6, 0, 0]} name="Distance (km)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 2. Average Speed (km/h) */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Average Speed (km/h)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="avgSpeedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="avgSpeed" stroke="#10b981" fill="url(#avgSpeedGrad)" strokeWidth={2} name="Avg Speed (km/h)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 3. Maximum Speed (km/h) */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Maximum Speed (km/h)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="maxSpeedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="maxSpeed" stroke="#f43f5e" fill="url(#maxSpeedGrad)" strokeWidth={2} name="Max Speed (km/h)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 4. Fuel Consumption Analysis (Pie/Doughnut) */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Fuel Consumption Analysis</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="fuel"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                  >
                    {chartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLOR_PALETTE[index % COLOR_PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 5. Max RPM per Trip */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Max RPM per Trip</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Bar dataKey="rpm" fill="#8b5cf6" radius={[6, 6, 0, 0]} name="Max RPM" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 6. Steering Angle Trend */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Steering Angle Trend</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="steeringGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="steering" stroke="#f59e0b" fill="url(#steeringGrad)" strokeWidth={2} name="Steering (°)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 7. Brake Events (Scatter/Bubble) */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Brake Events</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis dataKey="brakeEvents" stroke="#64748b" fontSize={10} name="Events" />
                  <ZAxis range={[100, 400]} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Scatter data={chartData} fill="#f43f5e" name="Brake Events" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 8. Angular Velocity */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Angular Velocity</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="angularVelocity"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                  >
                    {chartData.map((_, index) => (
                      <Cell key={`cell-ang-${index}`} fill={COLOR_PALETTE[(index + 3) % COLOR_PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 9. Acceleration */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Acceleration</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="accelGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="acceleration" stroke="#0ea5e9" fill="url(#accelGrad)" strokeWidth={2} name="Accel (m/s²)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 10. Gear Position */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Gear Position</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis dataKey="gear" domain={[0, 6]} stroke="#64748b" fontSize={10} name="Gear" />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Scatter data={chartData} fill="#14b8a6" name="Gear Position" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 11. Tire Pressure */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Tire Pressure (PSI)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis type="number" domain={[20, 40]} stroke="#64748b" fontSize={10} />
                  <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Bar dataKey="tirePressure" fill="#a855f7" radius={[0, 6, 6, 0]} name="PSI" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 12. Engine Load */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Engine Load</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52 flex flex-col items-center justify-center relative">
              <div className="text-4xl font-extrabold text-amber-400 font-mono">{maxEngineLoad}%</div>
              <span className="text-xs text-slate-400 mt-1">Max Engine Load</span>
              <div className="w-3/4 bg-slate-800 h-3 rounded-full overflow-hidden mt-4">
                <div className="bg-amber-500 h-full transition-all" style={{ width: `${maxEngineLoad}%` }}></div>
              </div>
            </div>
          </div>

          {/* 13. Throttle Position */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Throttle Position (%)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Line type="step" dataKey="throttle" stroke="#ec4899" strokeWidth={2} name="Throttle (%)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 14. Brake Pressure */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Brake Pressure (PSI)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="brakePressGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="brakePressure" stroke="#ef4444" fill="url(#brakePressGrad)" strokeWidth={2} name="Brake (PSI)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 15. Trip Duration */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Trip Duration (min)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Bar dataKey="duration" fill="#14b8a6" radius={[6, 6, 0, 0]} name="Duration (min)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 16. Fuel Efficiency */}
          <div className="glass-card p-5 rounded-3xl space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white text-sm">Fuel Efficiency (km/L)</span>
              <MoreVertical className="w-4 h-4 text-slate-500" />
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="effGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Area type="monotone" dataKey="fuelEfficiency" stroke="#10b981" fill="url(#effGrad)" strokeWidth={2} name="km/L" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>

      {/* Filter Modal */}
      {showFilterModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card p-6 rounded-3xl max-w-md w-full border border-dark-border space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white text-lg flex items-center space-x-2">
                <Filter className="w-5 h-5 text-amber-400" />
                <span>Filter Trip Records</span>
              </h3>
              <button onClick={() => setShowFilterModal(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Date From</label>
                  <input
                    type="date"
                    value={filterDateFrom}
                    onChange={(e) => setFilterDateFrom(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Date To</label>
                  <input
                    type="date"
                    value={filterDateTo}
                    onChange={(e) => setFilterDateTo(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Min Distance (km)</label>
                  <input
                    type="number"
                    placeholder="0"
                    value={filterMinDist}
                    onChange={(e) => setFilterMinDist(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Max Distance (km)</label>
                  <input
                    type="number"
                    placeholder="Any"
                    value={filterMaxDist}
                    onChange={(e) => setFilterMaxDist(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Min Avg Speed (km/h)</label>
                  <input
                    type="number"
                    placeholder="0"
                    value={filterMinSpeed}
                    onChange={(e) => setFilterMinSpeed(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-slate-400 uppercase block mb-1">Max Avg Speed (km/h)</label>
                  <input
                    type="number"
                    placeholder="Any"
                    value={filterMaxSpeed}
                    onChange={(e) => setFilterMaxSpeed(e.target.value)}
                    className="w-full bg-slate-900 border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex space-x-3 pt-2">
              <button
                onClick={resetFilters}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
              >
                Reset Filters
              </button>
              <button
                onClick={() => setShowFilterModal(false)}
                className="flex-1 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs shadow-md glow-brand transition-colors"
              >
                Apply Filter
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trip Comparison Modal */}
      {showCompareModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card p-6 rounded-3xl max-w-4xl w-full border border-dark-border space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white text-lg flex items-center space-x-2">
                <BarChart2 className="w-5 h-5 text-purple-400" />
                <span>Side-by-Side Trip Comparison ({selectedTrips.length} Trips)</span>
              </h3>
              <button onClick={() => setShowCompareModal(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-dark-border text-slate-400 uppercase font-semibold">
                    <th className="py-3 px-4">Telemetry Metric</th>
                    {selectedTrips.map(st => (
                      <th key={st.id} className="py-3 px-4 text-brand-400 font-mono">Trip #{st.id} ({st.trip_date})</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border text-slate-200 font-medium">
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Distance (km)</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4 text-white font-bold">{st.distance_km} km</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Avg Speed (km/h)</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4">{st.avg_speed_kmph} km/h</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Peak Engine RPM</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4 font-mono text-purple-300">{st.max_rpm} RPM</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Fuel Consumed (L)</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4 text-amber-300">{st.fuel_consumed} L</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Brake Events</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4">{st.brake_events} events</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Tire Pressure (psi)</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4">{st.tire_pressure || 32} psi</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-slate-400 font-semibold">Engine Load (%)</td>
                    {selectedTrips.map(st => (
                      <td key={st.id} className="py-3 px-4">{st.engine_load || 45}%</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            <button
              onClick={() => setShowCompareModal(false)}
              className="w-full py-2.5 rounded-xl bg-slate-800 text-slate-300 font-semibold text-xs transition-colors"
            >
              Close Comparison
            </button>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card p-6 rounded-3xl max-w-md w-full border border-dark-border space-y-5">
            <h3 className="font-bold text-white text-lg">Export Telematics Data</h3>
            <p className="text-xs text-slate-400">Choose your preferred export format for {filteredTrips.length} trip records:</p>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={exportCSV}
                className="p-4 rounded-2xl bg-slate-900 border border-dark-border hover:border-brand-500 text-left transition-all group"
              >
                <FileText className="w-6 h-6 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
                <span className="font-bold text-white text-sm block">CSV Format</span>
                <span className="text-[10px] text-slate-400">Spreadsheet compatible (.csv)</span>
              </button>

              <button
                onClick={exportJSON}
                className="p-4 rounded-2xl bg-slate-900 border border-dark-border hover:border-brand-500 text-left transition-all group"
              >
                <Activity className="w-6 h-6 text-purple-400 mb-2 group-hover:scale-110 transition-transform" />
                <span className="font-bold text-white text-sm block">JSON Format</span>
                <span className="text-[10px] text-slate-400">Structured data (.json)</span>
              </button>
            </div>

            <button
              onClick={() => setShowExportModal(false)}
              className="w-full py-2.5 rounded-xl bg-slate-800 text-slate-300 font-semibold text-xs transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
