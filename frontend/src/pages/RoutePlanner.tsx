import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { RouteOption } from '../types';
import { Navigation, CheckCircle2, Bookmark, X, ArrowLeftRight, MapPin, Locate, Lightbulb, Fuel, Clock, DollarSign, Sparkles } from 'lucide-react';
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
  const [startLocation, setStartLocation] = useState('Mumbai');
  const [endLocation, setEndLocation] = useState('Pune');
  const [priority, setPriority] = useState('eco');
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState('');
  const [recommendations, setRecommendations] = useState<any>(null);

  // Saved Routes Drawer State
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [savedRoutesList, setSavedRoutesList] = useState<any[]>([]);
  const [loadingSaved, setLoadingSaved] = useState(false);

  const handleSwap = () => {
    const temp = startLocation;
    setStartLocation(endLocation);
    setEndLocation(temp);
  };

  const handleCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setStartLocation(`${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
        },
        () => {
          alert('Could not fetch current location. Please allow GPS permissions.');
        }
      );
    } else {
      alert('Geolocation is not supported by your browser.');
    }
  };

  const handleOptimize = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSavedSuccess('');

    const startCoords = PRESET_LOCATIONS[startLocation] || [19.0760, 72.8777];
    const endCoords = PRESET_LOCATIONS[endLocation] || [18.5204, 73.8567];

    try {
      const res = await api.post('/route/optimize', {
        start_coords: startCoords,
        end_coords: endCoords,
        priority
      });
      setRoutes(res.data.routes || []);
      setRecommendations(res.data.recommendations || {
        primary_recommendation: { name: 'Eco-Friendly Route' },
        reasons: ['Lowest carbon footprint & fuel burn', 'Avoids heavy congestion zones'],
        tips: ['Maintain constant speed between 70-80 km/h', 'Use engine braking on downhill stretches']
      });
    } catch (err) {
      console.error('Route optimization error', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRoute = async (route: RouteOption) => {
    try {
      await api.post('/route/save', {
        route_name: `${route.name} (${startLocation} to ${endLocation})`,
        start_location: startLocation,
        end_location: endLocation,
        route_type: route.type,
        distance_km: route.distance_km,
        travel_time_minutes: route.travel_time_minutes,
        fuel_consumption: route.fuel_consumption,
        fuel_cost: route.fuel_cost,
        efficiency_score: route.efficiency_score
      });
      setSavedSuccess(`Route "${route.name}" saved to your profile!`);
      fetchSavedRoutes();
    } catch (err) {
      console.error('Save route error', err);
    }
  };

  const fetchSavedRoutes = async () => {
    setLoadingSaved(true);
    try {
      const res = await api.get('/route/saved');
      setSavedRoutesList(res.data || []);
    } catch (err) {
      console.error('Failed to fetch saved routes', err);
    } finally {
      setLoadingSaved(false);
    }
  };

  useEffect(() => {
    fetchSavedRoutes();
  }, []);

  const startCoords = PRESET_LOCATIONS[startLocation] || [19.0760, 72.8777];
  const endCoords = PRESET_LOCATIONS[endLocation] || [18.5204, 73.8567];
  const mapCenter: [number, number] = [
    (startCoords[0] + endCoords[0]) / 2,
    (startCoords[1] + endCoords[1]) / 2
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Title */}
      <div className="glass-card p-6 rounded-3xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-brand-500/20">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <Navigation className="w-6 h-6 text-brand-400" />
            <span>Smart Route Planner & Optimizer</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            AI-powered route optimization with real-time traffic and fuel efficiency analysis
          </p>
        </div>
        <button
          onClick={() => { setShowSavedModal(true); fetchSavedRoutes(); }}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-dark-border transition-all flex items-center space-x-2 shrink-0"
        >
          <Bookmark className="w-4 h-4 text-brand-400" />
          <span>Saved Routes ({savedRoutesList.length})</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Route Input Form */}
        <div className="glass-card p-6 rounded-3xl space-y-5">
          <h3 className="font-bold text-slate-100 text-lg flex items-center space-x-2">
            <MapPin className="w-5 h-5 text-brand-400" />
            <span>Plan Your Route</span>
          </h3>

          <form onSubmit={handleOptimize} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Starting Point
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={startLocation}
                  onChange={(e) => setStartLocation(e.target.value)}
                  placeholder="Enter starting location"
                  className="flex-1 bg-slate-900/80 border border-dark-border rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
                />
                <button
                  type="button"
                  onClick={handleCurrentLocation}
                  title="Use GPS Location"
                  className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-brand-400 border border-dark-border transition-colors"
                >
                  <Locate className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex justify-center">
              <button
                type="button"
                onClick={handleSwap}
                title="Swap Locations"
                className="p-2 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-dark-border transition-all"
              >
                <ArrowLeftRight className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Destination
              </label>
              <input
                type="text"
                value={endLocation}
                onChange={(e) => setEndLocation(e.target.value)}
                placeholder="Enter destination"
                className="w-full bg-slate-900/80 border border-dark-border rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
              />
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
                <option value="eco">Balanced (Mix of time & fuel efficiency)</option>
                <option value="fuel">Fuel Efficient (Lowest consumption)</option>
                <option value="fastest">Fastest (Minimize travel time)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-brand-600 to-emerald-600 hover:from-brand-500 hover:to-emerald-500 text-white font-semibold py-3 rounded-xl shadow-md glow-brand transition-all text-sm flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Navigation className="w-4 h-4" />
              <span>{loading ? 'Optimizing Routes...' : 'Find Optimal Routes'}</span>
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
        <div className="lg:col-span-2 glass-card p-4 rounded-3xl overflow-hidden min-h-[420px] relative z-0 border border-dark-border">
          <MapContainer center={mapCenter} zoom={7} scrollWheelZoom={false} style={{ height: '400px', width: '100%', borderRadius: '20px' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={startCoords}>
              <Popup>Start: {startLocation}</Popup>
            </Marker>
            <Marker position={endCoords}>
              <Popup>Destination: {endLocation}</Popup>
            </Marker>
            <Polyline positions={[startCoords, endCoords]} color="#10b981" weight={4} dashArray="5, 10" />
          </MapContainer>
        </div>
      </div>

      {/* Generated Route Options */}
      {routes.length > 0 && (
        <div className="space-y-6">
          <h3 className="font-bold text-white text-xl flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-brand-400" />
            <span>Generated Route Options</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {routes.map((route, idx) => (
              <div
                key={idx}
                className={`glass-card p-6 rounded-3xl relative flex flex-col justify-between border transition-all ${
                  route.type === 'eco' ? 'border-brand-500/40 glow-brand bg-brand-500/5' : 'border-dark-border'
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
                  className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2.5 rounded-xl text-xs transition-colors flex items-center justify-center space-x-2"
                >
                  <Bookmark className="w-3.5 h-3.5 text-brand-400" />
                  <span>Save Route Option</span>
                </button>
              </div>
            ))}
          </div>

          {/* Recommendations & Savings Section */}
          {recommendations && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Recommendations Card */}
              <div className="glass-card p-6 rounded-3xl space-y-4 border border-brand-500/30">
                <h4 className="font-bold text-white text-base flex items-center space-x-2">
                  <Lightbulb className="w-5 h-5 text-amber-400" />
                  <span>Personalized Recommendations</span>
                </h4>
                <div className="space-y-3 text-xs text-slate-300">
                  <div className="p-3 rounded-2xl bg-dark-bg border border-dark-border">
                    <span className="font-bold text-white block mb-1">Recommended: {recommendations.primary_recommendation?.name || 'Eco-Friendly Route'}</span>
                    <ul className="list-disc list-inside space-y-1 text-slate-400">
                      {recommendations.reasons?.map((r: string, i: number) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Savings Analysis Card */}
              <div className="glass-card p-6 rounded-3xl space-y-4 border border-emerald-500/30">
                <h4 className="font-bold text-white text-base flex items-center space-x-2">
                  <DollarSign className="w-5 h-5 text-emerald-400" />
                  <span>Trip Savings & Efficiency</span>
                </h4>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-2xl bg-dark-bg border border-dark-border space-y-1">
                    <Fuel className="w-4 h-4 text-emerald-400 mx-auto" />
                    <span className="text-[10px] text-slate-400 uppercase block">Trip Savings</span>
                    <span className="font-bold text-emerald-400 text-sm">₹120.00</span>
                  </div>
                  <div className="p-3 rounded-2xl bg-dark-bg border border-dark-border space-y-1">
                    <Clock className="w-4 h-4 text-blue-400 mx-auto" />
                    <span className="text-[10px] text-slate-400 uppercase block">Time Saving</span>
                    <span className="font-bold text-blue-400 text-sm">15 mins</span>
                  </div>
                  <div className="p-3 rounded-2xl bg-dark-bg border border-dark-border space-y-1">
                    <DollarSign className="w-4 h-4 text-purple-400 mx-auto" />
                    <span className="text-[10px] text-slate-400 uppercase block">Monthly Est.</span>
                    <span className="font-bold text-purple-400 text-sm">₹2,400</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Saved Routes Modal */}
      {showSavedModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card p-6 rounded-3xl max-w-lg w-full border border-dark-border space-y-5 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white text-lg flex items-center space-x-2">
                <Bookmark className="w-5 h-5 text-brand-400" />
                <span>Your Saved Routes</span>
              </h3>
              <button onClick={() => setShowSavedModal(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingSaved ? (
              <div className="text-center py-8 text-slate-400 text-xs">Loading saved routes...</div>
            ) : savedRoutesList.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs italic">No saved routes found yet.</div>
            ) : (
              <div className="space-y-3">
                {savedRoutesList.map((sr: any) => (
                  <div key={sr.id} className="p-4 rounded-2xl bg-dark-bg border border-dark-border space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-white text-sm">{sr.route_name}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-brand-500/20 text-brand-300 font-bold uppercase">
                        {sr.route_type}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>{sr.start_location} ➔ {sr.end_location}</span>
                      <span className="font-semibold text-emerald-400">{sr.distance_km} km • ₹{sr.fuel_cost}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
