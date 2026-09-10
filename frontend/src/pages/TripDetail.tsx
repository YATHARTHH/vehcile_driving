import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { TripDetail } from '../types';
import { 
  ArrowLeft, ShieldCheck, Cpu, AlertTriangle 
} from 'lucide-react';

export const TripDetailView: React.FC = () => {
  const { tripId } = useParams<{ tripId: string }>();
  const [detail, setDetail] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link
          to="/dashboard"
          className="p-2.5 rounded-xl glass-card text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Trip #{trip.id} Detailed Analysis</h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">Recorded on {trip.trip_date || 'N/A'}</p>
        </div>
      </div>

      {/* Behavior & AI Scores */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Heuristic Driving Score Card */}
        <div className="glass-card p-6 rounded-3xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Driving Quality Score</span>
            <ShieldCheck className="w-5 h-5 text-brand-400" />
          </div>
          <div className="flex items-baseline space-x-3 mb-2">
            <span className="text-5xl font-extrabold text-white">{logic_score}</span>
            <span className="text-slate-400 font-medium">/ 100</span>
          </div>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20">
            Behavior: {logic_behavior}
          </div>
        </div>

        {/* Machine Learning Model Prediction Card */}
        <div className="glass-card p-6 rounded-3xl border border-purple-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">ML Classification</span>
            <Cpu className="w-5 h-5 text-purple-400" />
          </div>
          <div className="flex items-baseline space-x-3 mb-2">
            <span className="text-3xl font-extrabold text-white">{ml_behavior}</span>
            <span className="text-xs text-purple-300 font-mono">({ml_confidence.toFixed(1)}% Confidence)</span>
          </div>
          <p className="text-xs text-slate-400">
            Model Engine: <span className="text-slate-200 font-semibold">{ml_model_used}</span>
          </p>
        </div>
      </div>

      {/* Health & Maintenance Recommendation */}
      <div className="glass-card p-6 rounded-3xl border border-brand-500/20 bg-brand-500/5">
        <h3 className="font-bold text-slate-100 text-lg mb-2">AI Health & Safety Recommendation</h3>
        <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
          {health_recommendation}
        </p>
      </div>

      {/* Sensor Gauge Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Tire Pressure</span>
          <span className="text-xl font-bold text-white">{trip.tire_pressure} psi</span>
        </div>
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Engine Load</span>
          <span className="text-xl font-bold text-white">{trip.engine_load}%</span>
        </div>
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Throttle Pos</span>
          <span className="text-xl font-bold text-white">{trip.throttle_position}%</span>
        </div>
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Brake Pressure</span>
          <span className="text-xl font-bold text-white">{trip.brake_pressure} psi</span>
        </div>
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Gear Shift</span>
          <span className="text-xl font-bold text-white">Gear {trip.gear_position}</span>
        </div>
        <div className="glass-card p-4 rounded-2xl">
          <span className="text-xs text-slate-400 block mb-1">Duration</span>
          <span className="text-xl font-bold text-white">{trip.trip_duration} mins</span>
        </div>
      </div>

      {/* Active Maintenance Alerts */}
      <div className="glass-card p-6 rounded-3xl">
        <h3 className="font-bold text-slate-100 text-lg mb-4">Trip Maintenance Alerts</h3>
        {maintenance_alerts.length === 0 ? (
          <p className="text-sm text-slate-400 italic">No maintenance warnings detected for this trip.</p>
        ) : (
          <div className="space-y-3">
            {maintenance_alerts.map((alert, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-dark-bg border border-dark-border flex items-start space-x-3">
                <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${
                  alert.severity === 'warning' ? 'text-amber-400' : 'text-blue-400'
                }`} />
                <div>
                  <h4 className="font-semibold text-slate-200 text-sm">{alert.title}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{alert.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
