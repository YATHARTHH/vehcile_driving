import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Navigation, Bot, Activity, Cpu } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/route-planner', label: 'Route Planner', icon: Navigation },
    { to: '/ai-insights', label: 'AI Insights', icon: Cpu },
    { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  ];

  return (
    <aside className="w-64 glass-panel border-r border-dark-border min-h-[calc(100vh-65px)] p-4 flex flex-col justify-between">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Main Menu
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-brand-600 to-emerald-600 text-white shadow-lg glow-brand'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-dark-hover'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="p-3.5 rounded-2xl glass-card border border-brand-500/20 bg-brand-500/5">
        <div className="flex items-center space-x-2 text-brand-400 mb-1">
          <Activity className="w-4 h-4" />
          <span className="text-xs font-bold uppercase tracking-wider">System Live</span>
        </div>
        <p className="text-xs text-slate-400">
          Telemetry & AI model inference running in real-time.
        </p>
      </div>
    </aside>
  );
};
