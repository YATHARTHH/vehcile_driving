import React from 'react';
import { useAuth } from '../store/authContext';
import { Car, LogOut, User as UserIcon, ShieldCheck } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-dark-border px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center glow-brand">
          <Car className="w-6 h-6 text-white" />
        </div>
        <div>
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-brand-400 bg-clip-text text-transparent">
            EcoDriving
          </span>
          <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
            Analytics v2.0
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3 bg-dark-card/80 border border-dark-border px-3.5 py-1.5 rounded-xl">
            <ShieldCheck className="w-4 h-4 text-brand-400" />
            <span className="text-xs font-mono font-medium text-slate-300">
              {user.vehicle_number}
            </span>
          </div>
        )}

        {user && (
          <div className="flex items-center space-x-3 border-l border-dark-border pl-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                <UserIcon className="w-4 h-4" />
              </div>
              <span className="text-sm font-medium text-slate-200">{user.username}</span>
            </div>

            <button
              onClick={logout}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
