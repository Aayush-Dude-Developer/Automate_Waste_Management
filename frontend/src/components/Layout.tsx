import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { apiRequest, type RestaurantProfile } from '../lib/api';
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  ChefHat,
  Trash2,
  HeartHandshake,
  FileText,
  BarChart3,
  Settings,
  UtensilsCrossed,
  BookOpen,
  Moon,
  Sun,
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [restaurant, setRestaurant] = useState<RestaurantProfile | null>(null);
  const [profileError, setProfileError] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(
    () => document.documentElement.classList.contains('dark'),
  );
  const navGroups = [
    [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/documents', icon: FileText, label: 'Documents & Imports' },
      { to: '/inventory', icon: Package, label: 'Inventory' },
      { to: '/purchases', icon: FileText, label: 'Purchase Invoices' },
      { to: '/recipes', icon: BookOpen, label: 'Recipes & Menu' },
      { to: '/staff-consumption', icon: UtensilsCrossed, label: 'Staff Consumption' },
    ],
    [
      { to: '/sales-purchases', icon: ShoppingCart, label: 'Purchase Recommendations' },
      { to: '/waste', icon: Trash2, label: 'Waste' },
    ],
    [
      { to: '/buffet-planning', icon: ChefHat, label: 'Buffet Planning' },
      { to: '/donations', icon: HeartHandshake, label: 'Donation Centres' },
    ],
    [
      { to: '/impact', icon: BarChart3, label: 'Reports & Impact' },
      { to: '/settings', icon: Settings, label: 'Settings' },
    ],
  ];

  useEffect(() => {
    void Promise.resolve().then(() => apiRequest<RestaurantProfile>('/api/restaurant/profile'))
      .then(setRestaurant)
      .catch((cause: unknown) => setProfileError(cause instanceof Error ? cause.message : 'Restaurant profile unavailable.'));
  }, []);

  const toggleTheme = () => {
    const nextIsDarkMode = !isDarkMode;
    document.documentElement.classList.toggle('dark', nextIsDarkMode);
    window.localStorage.setItem('sustainbite-theme', nextIsDarkMode ? 'dark' : 'light');
    setIsDarkMode(nextIsDarkMode);
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <UtensilsCrossed className="h-6 w-6 text-restaurant-primary mr-2" />
          <div><span className="font-bold text-lg text-slate-800">SustainBite</span>
            {restaurant && <span className="block max-w-44 truncate text-xs text-slate-500">{restaurant.name}</span>}
          </div>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-4">
          {navGroups.map((group, groupIndex) => (
            <ul key={group[0].to} className={`space-y-1 px-3 ${groupIndex ? 'mt-4 border-t border-slate-200 pt-4' : ''}`}>
              {groupIndex === 1 && (
                <li className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Inventory &amp; Waste Management
                </li>
              )}
              {groupIndex === 2 && (
                <li className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  For restaurants offering buffet
                </li>
              )}
              {group.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-restaurant-primary/10 text-restaurant-primary'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                      }`
                    }
                  >
                    <item.icon className="h-5 w-5 mr-3 flex-shrink-0" />
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          ))}
        </nav>
        
        <div className="p-4 border-t border-slate-200">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={`Switch to ${isDarkMode ? 'light' : 'dark'} mode`}
            role="switch"
            aria-checked={isDarkMode}
            className="mb-4 flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-restaurant-primary"
          >
            <span className="flex items-center gap-2">
              {isDarkMode ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-500" />}
              {isDarkMode ? 'Light appearance' : 'Dark appearance'}
            </span>
            <span className={`relative block h-6 w-11 shrink-0 rounded-full transition-colors ${isDarkMode ? 'bg-restaurant-primary' : 'bg-slate-300'}`}>
              <span
                className="absolute left-0.5 top-0.5 block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200"
                style={{ transform: isDarkMode ? 'translateX(20px)' : 'translateX(0)' }}
              />
            </span>
          </button>
          <div className="flex items-center">
            <div className="h-8 w-8 rounded-full bg-restaurant-secondary/20 flex items-center justify-center text-restaurant-secondary font-bold">
              {restaurant?.name?.slice(0, 1) ?? 'S'}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-slate-700">{restaurant?.name ?? 'Authorized workspace'}</p>
              <p className="text-xs text-slate-500">{restaurant?.location ?? (profileError ? 'Profile unavailable' : 'Workspace')}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
