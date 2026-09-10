import React, { useState } from 'react';
import { api } from '../services/api';
import { RouteOption } from '../types';
import { Navigation, CheckCircle2 } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';

const PRESET_LOCATIONS: { [key: string]: [number, number] } = {
  'Mumbai': [19.0760, 72.8777],
  'Pune': [18.5204, 73.8567],
  'Delhi': [28.7041, 77.1025],
  'Jaipur': [26.9124, 75.7873],
  'Bangalore': [12.9716, 77.5946],
  'Chennai': [13.0827, 80.2707],
};

export const RoutePlanner: React.FC = () => {
  const [startCity, setStartCity] = useState('Mumbai');
  const [endCity, setEndCity] = useState('Pune');
  const [priority, setPriority] = useState('eco');
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState('');

  const handleOptimize = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSavedSuccess('');

    const startCoords = PRESET_LOCATIONS[startCity] || [19.0760, 72.8777];
    const endCoords = PRESET_LOCATIONS[endCity] || [18.5204, 73.8567];

    try {
      const res = await api.post('/route/optimize', {
        start_coords: startCoords,
        end_coords: endCoords,
        priority
      });
      setRoutes(res.data.routes);
    } catch (err) {
      console.error('Route optimization error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRoute = async (route: RouteOption) => {
    try {
      await api.post('/route/save', {
        route_name: `${route.name} (${startCity} to ${endCity})`,
        start_location: startCity,
        end_location: endCity,
        route_type: route.type,
        distance_km: route.distance_km,
        travel_time_minutes: route.travel_time_minutes,
        fuel_consumption: route.fuel_consumption,
        fuel_cost: route.fuel_cost,
        efficiency_score: route.efficiency_score
      });
      setSavedSuccess(`Route "${route.name}" saved to your profile!`);
    } catch (err) {
      console.error('Save route error', err);
    }
  };

  const startCoords = PRESET_LOCATIONS[startCity] || [19.0760, 72.8777];
  const endCoords = PRESET_LOCATIONS[endCity] || [18.5204, 73.8567];
  const mapCenter: [number, number] = [
    (startCoords[0] + endCoords[0]) / 2,
    (startCoords[1] + endCoords[1]) / 2
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="glass-card p-6 rounded-3xl">
        <h1 className="text-2xl font-bold text-white tracking-tight">Smart Route Planner & Optimizer</h1>
        <p className="text-sm text-slate-400 mt-1">
          Calculate fuel-efficient routes, elevation profiles, and real-time traffic delays
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Form */}
        <div className="glass-card p-6 rounded-3xl space-y-5">
          <h3 className="font-bold text-slate-100 text-lg">Route Settings</h3>

          <form onSubmit={handleOptimize} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Origin City
              </label>
              <select
                value={startCity}
                onChange={(e) => setStartCity(e.target.value)}
                className="w-full bg-slate-900/80 border border-dark-border rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
              >
                {Object.keys(PRESET_LOCATIONS).map((city) => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Destination City
              </label>
              <select
                value={endCity}
                onChange={(e) => setEndCity(e.target.value)}
                className="w-full bg-slate-900/80 border border-dark-border rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
              >
                {Object.keys(PRESET_LOCATIONS).map((city) => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Optimization Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-slate-900/80 border border-dark-border rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
              >
                <option value="eco">Eco-Friendly (Lowest Fuel)</option>
                <option value="fastest">Fastest Highway</option>
                <option value="balanced">Balanced Direct</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-brand-600 to-emerald-600 hover:from-brand-500 hover:to-emerald-500 text-white font-semibold py-3 rounded-xl shadow-md glow-brand transition-all text-sm flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Navigation className="w-4 h-4" />
              <span>{loading ? 'Optimizing Route...' : 'Calculate Routes'}</span>
            </button>
          </form>

          {savedSuccess && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{savedSuccess}</span>
            </div>
          )}
        </div>

        {/* Map Rendering Container */}
        <div className="lg:col-span-2 glass-card p-4 rounded-3xl overflow-hidden min-h-[380px] relative z-0">
          <MapContainer center={mapCenter} zoom={7} scrollWheelZoom={false} style={{ height: '360px', width: '100%', borderRadius: '20px' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={startCoords}>
              <Popup>Start: {startCity}</Popup>
            </Marker>
            <Marker position={endCoords}>
              <Popup>Destination: {endCity}</Popup>
            </Marker>
            <Polyline positions={[startCoords, endCoords]} color="#10b981" weight={4} dashArray="5, 10" />
          </MapContainer>
        </div>
      </div>

      {/* Generated Route Options */}
      {routes.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-bold text-slate-100 text-xl">Generated Route Comparison</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {routes.map((route, idx) => (
              <div
                key={idx}
                className={`glass-card p-6 rounded-3xl relative flex flex-col justify-between border transition-all ${
                  route.type === 'eco' ? 'border-brand-500/40 glow-brand' : 'border-dark-border'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      route.type === 'eco' ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30' : 'bg-slate-800 text-slate-300'
                    }`}>
                      {route.type.toUpperCase()} ROUTE
                    </span>
                    <span className="text-xs font-bold text-slate-300">Score: {route.efficiency_score}/100</span>
                  </div>

                  <h4 className="font-bold text-white text-lg">{route.name}</h4>
                  <p className="text-xs text-slate-400 mb-4">{route.description}</p>

                  <div className="space-y-2 text-sm text-slate-300 mb-6">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Distance:</span>
                      <span className="font-semibold text-white">{route.distance_km} km</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Travel Time:</span>
                      <span className="font-semibold text-white">{route.travel_time_minutes} mins</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Fuel Consumed:</span>
                      <span className="font-semibold text-white">{route.fuel_consumption} L</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Est. Fuel Cost:</span>
                      <span className="font-semibold text-emerald-400">₹{route.fuel_cost}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleSaveRoute(route)}
                  className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2.5 rounded-xl text-xs transition-colors"
                >
                  Save Route Option
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
