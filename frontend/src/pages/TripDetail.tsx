import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { TripDetail } from '../types';
import { 
  ArrowLeft, ShieldCheck, Cpu, AlertTriangle, Gauge, Zap, Activity 
} from 'lucide-react';

export const TripDetailView: React.FC = () => {
  const { tripId } = useParams<{ tripId: string }>();
  const [detail, setDetail] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolvedAlerts, setResolvedAlerts] = useState<number[]>([]);

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

  const toggleResolveAlert = (idx: number) => {
    setResolvedAlerts(prev => 
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/dashboard"
            className="p-2.5 rounded-xl glass-card text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Trip #{trip.id} Detailed Telematics</h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Recorded on {trip.trip_date || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Behavior & AI Scores */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Heuristic Driving Score Card */}
        <div className="glass-card p-6 rounded-3xl relative overflow-hidden border border-brand-500/30">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Driving Quality Score</span>
            <ShieldCheck className="w-5 h-5 text-brand-400" />
          </div>
          <div className="flex items-baseline space-x-3 mb-2">
            <span className="text-5xl font-extrabold text-white">{logic_score}</span>
            <span className="text-slate-400 font-medium">/ 100</span>
          </div>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20">
            Behavior Class: {logic_behavior}
          </div>
        </div>

        {/* Machine Learning Model Prediction Card */}
        <div className="glass-card p-6 rounded-3xl border border-purple-500/30 relative overflow-hidden bg-purple-500/5">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">ML Model Inference</span>
            <Cpu className="w-5 h-5 text-purple-400" />
          </div>
          <div className="flex items-baseline space-x-3 mb-2">
            <span className="text-3xl font-extrabold text-white">{ml_behavior}</span>
            <span className="text-xs text-purple-300 font-mono">({ml_confidence.toFixed(1)}% Confidence)</span>
          </div>
          <p className="text-xs text-slate-400">
            Classifier Engine: <span className="text-slate-200 font-semibold">{ml_model_used}</span>
          </p>
        </div>
      </div>

      {/* Visual Telemetry Gauges Section */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <h3 className="font-bold text-white text-lg flex items-center space-x-2">
          <Gauge className="w-5 h-5 text-brand-400" />
          <span>Real-Time Sensor Telemetry Gauges</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Speedometer Gauge */}
          <div className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>Speedometer</span>
              <Gauge className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-extrabold text-white font-mono">{trip.avg_speed_kmph} km/h</div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-emerald-500 h-full transition-all" style={{ width: `${Math.min((trip.avg_speed_kmph / 140) * 100, 100)}%` }}></div>
            </div>
            <span className="text-[10px] text-slate-500">Max recorded speed: {trip.max_speed} km/h</span>
          </div>

          {/* RPM Gauge */}
          <div className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>Tachometer (RPM)</span>
              <Zap className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-extrabold text-white font-mono">{trip.max_rpm} RPM</div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-purple-500 h-full transition-all" style={{ width: `${Math.min((trip.max_rpm / 6000) * 100, 100)}%` }}></div>
            </div>
            <span className="text-[10px] text-slate-500">Redline limit: 6,000 RPM</span>
          </div>

          {/* Engine Load */}
          <div className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>Engine Load</span>
              <Activity className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-extrabold text-white font-mono">{trip.engine_load}%</div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-amber-500 h-full transition-all" style={{ width: `${trip.engine_load}%` }}></div>
            </div>
            <span className="text-[10px] text-slate-500">Throttle position: {trip.throttle_position}%</span>
          </div>

          {/* Brake Pressure */}
          <div className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>Brake Pressure</span>
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <div className="text-2xl font-extrabold text-white font-mono">{trip.brake_pressure} psi</div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-red-500 h-full transition-all" style={{ width: `${Math.min((trip.brake_pressure / 100) * 100, 100)}%` }}></div>
            </div>
            <span className="text-[10px] text-slate-500">{trip.brake_events} hard brake events</span>
          </div>
        </div>
      </div>

      {/* 4-Wheel Tire Pressure Layout */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <h3 className="font-bold text-white text-lg">Tire Pressure Telematics Monitor</h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-dark-bg border border-emerald-500/20 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Front Left (FL)</span>
            <span className="text-xl font-bold text-white block mt-1">{trip.tire_pressure} PSI</span>
            <span className="text-[10px] text-emerald-400 font-bold">NORMAL</span>
          </div>

          <div className="p-4 rounded-2xl bg-dark-bg border border-emerald-500/20 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Front Right (FR)</span>
            <span className="text-xl font-bold text-white block mt-1">{trip.tire_pressure} PSI</span>
            <span className="text-[10px] text-emerald-400 font-bold">NORMAL</span>
          </div>

          <div className="p-4 rounded-2xl bg-dark-bg border border-emerald-500/20 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Rear Left (RL)</span>
            <span className="text-xl font-bold text-white block mt-1">{trip.tire_pressure} PSI</span>
            <span className="text-[10px] text-emerald-400 font-bold">NORMAL</span>
          </div>

          <div className="p-4 rounded-2xl bg-dark-bg border border-emerald-500/20 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Rear Right (RR)</span>
            <span className="text-xl font-bold text-white block mt-1">{trip.tire_pressure} PSI</span>
            <span className="text-[10px] text-emerald-400 font-bold">NORMAL</span>
          </div>
        </div>
      </div>

      {/* Health & Maintenance Recommendation */}
      <div className="glass-card p-6 rounded-3xl border border-brand-500/20 bg-brand-500/5 space-y-2">
        <h3 className="font-bold text-slate-100 text-lg">AI Health & Safety Recommendation</h3>
        <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
          {health_recommendation}
        </p>
      </div>

      {/* Maintenance Alerts with Resolution Buttons */}
      <div className="glass-card p-6 rounded-3xl space-y-4">
        <h3 className="font-bold text-slate-100 text-lg">Trip Maintenance Alerts</h3>
        {maintenance_alerts.length === 0 ? (
          <p className="text-sm text-slate-400 italic">No maintenance warnings detected for this trip.</p>
        ) : (
          <div className="space-y-3">
            {maintenance_alerts.map((alert, idx) => {
              const isResolved = resolvedAlerts.includes(idx);
              return (
                <div key={idx} className={`p-4 rounded-2xl bg-dark-bg border transition-all flex items-center justify-between ${
                  isResolved ? 'border-emerald-500/30 opacity-60' : 'border-dark-border'
                }`}>
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${
                      isResolved ? 'text-emerald-400' : alert.severity === 'warning' ? 'text-amber-400' : 'text-blue-400'
                    }`} />
                    <div>
                      <h4 className={`font-semibold text-sm ${isResolved ? 'line-through text-slate-400' : 'text-slate-200'}`}>
                        {alert.title}
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">{alert.description}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => toggleResolveAlert(idx)}
                    className={`px-3 py-1.5 rounded-xl font-semibold text-xs transition-colors shrink-0 ${
                      isResolved
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    {isResolved ? 'Resolved' : 'Mark Resolved'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
