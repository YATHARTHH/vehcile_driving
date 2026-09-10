import React from 'react';
import { Car, Shield, Cpu } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="glass-panel border-t border-dark-border mt-auto px-6 py-6 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <Car className="w-4 h-4 text-brand-400" />
          <span className="font-bold text-slate-200">EcoDriving Platform v2.0</span>
          <span>&copy; {new Date().getFullYear()} All rights reserved.</span>
        </div>

        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-1 text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span>FastAPI & AI Telemetry Engine</span>
          </div>
          <div className="flex items-center space-x-1 text-slate-400">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>IDOR & OAuth2 Protected</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
