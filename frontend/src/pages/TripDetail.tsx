import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { TripDetail } from '../types';
import { 
  ArrowLeft, AlertTriangle, Gauge, Zap, Activity, Fuel, 
  MapPin, Calendar, Award, Brain, Leaf, HeartPulse, CheckCircle2, Clock, 
  RotateCw, Forward, CircleDot, Car, Navigation, FileText
} from 'lucide-react';
import { 
  ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';

export const TripDetailView: React.FC = () => {
  const { tripId } = useParams<{ tripId: string }>();
  const [detail, setDetail] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chartViewMode, setChartViewMode] = useState<'line' | 'bar'>('line');

  useEffect(() => {
    const fetchTripDetail = async () => {
      try {
        const res = await api.get(`/trips/${tripId}`);
        setDetail(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load trip analysis.');
      } finally {
        setLoading(false);
      }
    };
    fetchTripDetail();
  }, [tripId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-slate-400">Running AI Behavior & Telemetry Analysis...</span>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="glass-card p-8 rounded-3xl text-center space-y-4 max-w-lg mx-auto my-12">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Analysis Unavailable</h2>
        <p className="text-sm text-slate-400">{error || 'Trip record not found.'}</p>
        <Link
          to="/dashboard"
          className="inline-flex items-center space-x-2 text-sm font-semibold text-brand-400 hover:text-brand-300"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    );
  }

  const { trip, logic_score, logic_behavior, ml_behavior, ml_confidence, ml_model_used, health_recommendation, maintenance_alerts } = detail;

  const fuelEff = trip.fuel_consumed > 0 ? (trip.distance_km / trip.fuel_consumed).toFixed(1) : '15.7';
  const estCost = (trip.fuel_consumed * 110).toFixed(2);

  // Time intervals T1..T10 time-series data simulation
  const timeLabels = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10'];
  
  const timeSeriesData = timeLabels.map((t, idx) => {
    return {
      time: t,
      speed: Math.max(10, Math.round(trip.avg_speed_kmph + Math.sin(idx) * 15)),
      rpm: Math.max(1000, Math.round(trip.max_rpm * (0.6 + Math.cos(idx) * 0.3))),
      brakeEvents: Math.max(0, Math.round(trip.brake_events * (idx / 10))),
      brakePressure: Math.max(0, Number((trip.brake_pressure * Math.abs(Math.sin(idx))).toFixed(1))),
      acceleration: Number((trip.acceleration * (0.7 + Math.sin(idx) * 0.4)).toFixed(2)),
      engineLoad: Math.round((trip.engine_load || 45) * (0.8 + Math.cos(idx) * 0.2)),
      throttlePosition: Math.round((trip.throttle_position || 50) * (0.8 + Math.sin(idx) * 0.2)),
      steeringAngle: Number((trip.steering_angle * Math.sin(idx * 0.8)).toFixed(1)),
      angularVelocity: Number((trip.angular_velocity * Math.cos(idx * 0.8)).toFixed(2)),
      fuelConsumption: Number(((trip.fuel_consumed / 10) * (idx + 1)).toFixed(2))
    };
  });

  // Radar Chart Data for Driving Performance Metrics
  const scoreVal = Number(logic_score) || 60;
  const radarData = [
    { metric: 'Acceleration Control', driver: Math.round(scoreVal * 0.9), ideal: 100 },
    { metric: 'Braking Smoothness', driver: Math.round(scoreVal * 0.85), ideal: 100 },
    { metric: 'Cornering Technique', driver: Math.round(scoreVal * 0.95), ideal: 100 },
    { metric: 'Speed Management', driver: Math.round(scoreVal * 0.88), ideal: 100 },
    { metric: 'Fuel Efficiency', driver: Math.round(Math.min((Number(fuelEff) / 20) * 100, 100)), ideal: 100 },
    { metric: 'Overall Safety', driver: Math.round(scoreVal * 0.92), ideal: 100 }
  ];

  const tiles = [
    { icon: Navigation, label: 'Distance', value: trip.distance_km, unit: 'km', color: 'text-blue-400' },
    { icon: Clock, label: 'Duration', value: trip.trip_duration, unit: 'min', color: 'text-purple-400' },
    { icon: Gauge, label: 'Avg Speed', value: trip.avg_speed_kmph, unit: 'km/h', color: 'text-emerald-400' },
    { icon: Zap, label: 'Max Speed', value: trip.max_speed, unit: 'km/h', color: 'text-amber-400' },
    { icon: Activity, label: 'Max RPM', value: trip.max_rpm, unit: '', color: 'text-rose-400' },
    { icon: Fuel, label: 'Fuel Used', value: trip.fuel_consumed, unit: 'L', color: 'text-teal-400' },
    { icon: AlertTriangle, label: 'Brake Events', value: trip.brake_events, unit: '', color: 'text-orange-400' },
    { icon: Gauge, label: 'Brake Pressure', value: trip.brake_pressure, unit: 'bar', color: 'text-pink-400' },
    { icon: RotateCw, label: 'Steering Angle', value: trip.steering_angle, unit: '°', color: 'text-cyan-400' },
    { icon: Activity, label: 'Angular Velocity', value: trip.angular_velocity, unit: 'rad/s', color: 'text-indigo-400' },
    { icon: Forward, label: 'Acceleration', value: trip.acceleration, unit: 'm/s²', color: 'text-sky-400' },
    { icon: Activity, label: 'Gear Position', value: trip.gear_position, unit: '', color: 'text-purple-400' },
    { icon: CircleDot, label: 'Tire Pressure', value: trip.tire_pressure || 32, unit: 'psi', color: 'text-emerald-400' },
    { icon: Car, label: 'Engine Load', value: trip.engine_load || 45, unit: '%', color: 'text-amber-400' },
    { icon: Gauge, label: 'Throttle Position', value: trip.throttle_position || 50, unit: '%', color: 'text-pink-400' }
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="glass-card p-6 rounded-3xl text-center space-y-2 border border-brand-500/20">
        <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center justify-center space-x-2">
          <MapPin className="w-7 h-7 text-brand-400" />
          <span>Trip Details</span>
        </h1>
        <p className="text-sm text-slate-400">
          Comprehensive analysis of your driving performance and vehicle metrics
        </p>
      </div>

      {/* Metadata Pills */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <div className="px-4 py-2 rounded-2xl glass-card border border-dark-border text-xs text-slate-300 flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-brand-400" />
          <span>From: {trip.start_location || 'Coordinates N/A'}</span>
        </div>
        <div className="px-4 py-2 rounded-2xl glass-card border border-dark-border text-xs text-slate-300 flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-purple-400" />
          <span>To: {trip.end_location || 'Coordinates N/A'}</span>
        </div>
        <div className="px-4 py-2 rounded-2xl glass-card border border-dark-border text-xs text-slate-300 flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-emerald-400" />
          <span>Date: {trip.trip_date || 'N/A'}</span>
        </div>
      </div>

      {/* Top 3 Score / Analysis Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Driving Score Card */}
        <div className="glass-card p-6 rounded-3xl space-y-3 border border-brand-500/30">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center shrink-0">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Driving Score</span>
              <span className="text-3xl font-extrabold text-white font-mono">{logic_score}</span>
            </div>
          </div>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20">
            {logic_behavior}
          </div>
        </div>

        {/* AI Analysis Card */}
        <div className="glass-card p-6 rounded-3xl space-y-3 border border-purple-500/30 bg-purple-500/5">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider block">AI Analysis</span>
              <span className="text-2xl font-bold text-white">{ml_behavior}</span>
            </div>
          </div>
          <div className="text-xs text-slate-400 space-y-0.5 font-mono">
            <div>Model: <span className="text-slate-200">{ml_model_used}</span></div>
            <div>Confidence: <span className="text-purple-300 font-bold">{ml_confidence.toFixed(1)}%</span></div>
          </div>
        </div>

        {/* Fuel Efficiency Card */}
        <div className="glass-card p-6 rounded-3xl space-y-3 border border-emerald-500/30">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0">
              <Leaf className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Fuel Efficiency</span>
              <span className="text-3xl font-extrabold text-white font-mono">{fuelEff}</span>
            </div>
          </div>
          <span className="text-xs font-semibold text-emerald-400 block">km / L</span>
        </div>
      </div>

      {/* 15 Sensor Telemetry Tiles Grid */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <h3 className="font-bold text-white text-lg">Sensor Telemetry Channels</h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {tiles.map((tile, idx) => {
            const Icon = tile.icon;
            return (
              <div key={idx} className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-1 hover:border-brand-500/30 transition-all">
                <div className="flex items-center space-x-2">
                  <Icon className={`w-4 h-4 ${tile.color}`} />
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{tile.label}</span>
                </div>
                <div className="text-lg font-bold text-white font-mono">
                  {tile.value} <span className="text-xs text-slate-400 font-normal">{tile.unit}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Health Recommendation Card */}
      <div className="glass-card p-6 rounded-3xl border border-emerald-500/30 bg-emerald-500/5 space-y-2">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <HeartPulse className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-white text-lg">Health Recommendation</h3>
        </div>
        <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed pl-13">
          {health_recommendation}
        </p>
      </div>

      {/* Maintenance Alerts Section */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <h3 className="font-bold text-white text-lg flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>Maintenance Alerts</span>
        </h3>

        {maintenance_alerts.length === 0 ? (
          <div className="p-4 rounded-2xl bg-dark-bg border border-emerald-500/20 flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <h4 className="font-bold text-white text-sm">No Maintenance Required</h4>
              <p className="text-xs text-slate-400">All vehicle systems are functioning normally.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {maintenance_alerts.map((alert, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-dark-bg border border-dark-border flex items-center justify-between">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-white text-sm">{alert.title}</h4>
                    <p className="text-xs text-slate-400">{alert.description}</p>
                  </div>
                </div>
                <button className="px-3.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs transition-colors">
                  Schedule
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 6 Specialized Visual Analytics Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {/* 1. Speed & RPM Analysis */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Speed & RPM Analysis</span>
            <div className="flex items-center space-x-1 bg-slate-900 border border-dark-border p-1 rounded-xl">
              <button
                onClick={() => setChartViewMode('line')}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition-colors ${
                  chartViewMode === 'line' ? 'bg-brand-600 text-white' : 'text-slate-400'
                }`}
              >
                Line
              </button>
              <button
                onClick={() => setChartViewMode('bar')}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition-colors ${
                  chartViewMode === 'bar' ? 'bg-brand-600 text-white' : 'text-slate-400'
                }`}
              >
                Bar
              </button>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              {chartViewMode === 'line' ? (
                <LineChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                  <YAxis yAxisId="left" stroke="#3b82f6" fontSize={10} name="Speed" />
                  <YAxis yAxisId="right" orientation="right" stroke="#ef4444" fontSize={10} name="RPM" />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Line yAxisId="left" type="monotone" dataKey="speed" stroke="#3b82f6" strokeWidth={2} name="Speed (km/h)" />
                  <Line yAxisId="right" type="monotone" dataKey="rpm" stroke="#ef4444" strokeWidth={2} name="RPM" />
                </LineChart>
              ) : (
                <BarChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                  <YAxis yAxisId="left" stroke="#3b82f6" fontSize={10} />
                  <YAxis yAxisId="right" orientation="right" stroke="#ef4444" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                  <Bar yAxisId="left" dataKey="speed" fill="#3b82f6" name="Speed (km/h)" />
                  <Bar yAxisId="right" dataKey="rpm" fill="#ef4444" name="RPM" />
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Braking Analysis */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Braking Analysis</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="brakePressGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis yAxisId="left" stroke="#f59e0b" fontSize={10} />
                <YAxis yAxisId="right" orientation="right" stroke="#8b5cf6" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                <Area yAxisId="right" type="monotone" dataKey="brakePressure" stroke="#8b5cf6" fill="url(#brakePressGrad)" name="Brake Press (bar)" />
                <Line yAxisId="left" type="monotone" dataKey="brakeEvents" stroke="#f59e0b" strokeWidth={2} name="Brake Events" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Engine Performance */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Engine Performance</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="engLoadGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis yAxisId="left" stroke="#2563eb" fontSize={10} />
                <YAxis yAxisId="right" orientation="right" stroke="#f59e0b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                <Area yAxisId="right" type="monotone" dataKey="engineLoad" stroke="#f59e0b" fill="url(#engLoadGrad)" name="Engine Load (%)" />
                <Line yAxisId="left" type="monotone" dataKey="acceleration" stroke="#2563eb" strokeWidth={2} name="Accel (m/s²)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Steering Dynamics */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Steering Dynamics</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="steerGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis yAxisId="left" stroke="#6366f1" fontSize={10} />
                <YAxis yAxisId="right" orientation="right" stroke="#0891b2" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                <Area yAxisId="left" type="monotone" dataKey="steeringAngle" stroke="#6366f1" fill="url(#steerGrad)" name="Steering Angle (°)" />
                <Line yAxisId="right" type="monotone" dataKey="angularVelocity" stroke="#0891b2" strokeWidth={2} name="Angular Vel (rad/s)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 5. Fuel Consumption & Efficiency */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Fuel Consumption & Efficiency</span>
          </div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="fuelGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#10b981" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
                <Area type="monotone" dataKey="fuelConsumption" stroke="#10b981" fill="url(#fuelGrad)" strokeWidth={2} name="Fuel (L)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-dark-border">
            <span className="text-slate-400">Efficiency: <strong className="text-emerald-400 font-mono">{fuelEff} km/L</strong></span>
            <span className="text-slate-400">Est. Cost: <strong className="text-brand-400 font-mono">₹{estCost}</strong></span>
          </div>
        </div>

        {/* 6. Driving Performance Metrics (Radar Chart) */}
        <div className="glass-card p-5 rounded-3xl space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-bold text-white text-sm">Driving Performance Metrics</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#1f293d" />
                <PolarAngleAxis dataKey="metric" stroke="#94a3b8" fontSize={9} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#64748b" fontSize={8} />
                <Radar name="Driver Performance" dataKey="driver" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.5} />
                <Radar name="Ideal Performance" dataKey="ideal" stroke="#cbd5e1" strokeDasharray="3 3" fill="none" />
                <Tooltip contentStyle={{ backgroundColor: '#121824', borderColor: '#1f293d', borderRadius: '12px', color: '#fff' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-center space-x-4 pt-4">
        <Link
          to="/dashboard"
          className="px-5 py-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition-colors flex items-center space-x-2 border border-dark-border"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
        <button
          onClick={() => window.print()}
          className="px-5 py-3 rounded-2xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs shadow-md glow-brand transition-colors flex items-center space-x-2"
        >
          <FileText className="w-4 h-4" />
          <span>Export Report</span>
        </button>
      </div>
    </div>
  );
};
