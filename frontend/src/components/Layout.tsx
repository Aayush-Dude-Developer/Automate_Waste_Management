import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
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
  UtensilsCrossed
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/inventory', icon: Package, label: 'Inventory' },
    { to: '/sales-purchases', icon: ShoppingCart, label: 'Sales & Purchases' },
    { to: '/buffet-planning', icon: ChefHat, label: 'Buffet Planning' },
    { to: '/surplus-waste', icon: Trash2, label: 'Surplus & Waste' },
    { to: '/donations', icon: HeartHandshake, label: 'Donation Centres' },
    { to: '/documents', icon: FileText, label: 'Documents & Imports' },
    { to: '/impact', icon: BarChart3, label: 'Reports & Impact' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <UtensilsCrossed className="h-6 w-6 text-restaurant-primary mr-2" />
          <span className="font-bold text-lg text-slate-800">SustainBite</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => (
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
        </nav>
        
        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center">
            <div className="h-8 w-8 rounded-full bg-restaurant-secondary/20 flex items-center justify-center text-restaurant-secondary font-bold">
              T
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-slate-700">Authorized workspace</p>
              <p className="text-xs text-slate-500">Workspace</p>
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
