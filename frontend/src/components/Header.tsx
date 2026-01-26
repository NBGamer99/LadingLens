import { Ship, LayoutDashboard } from "lucide-react";

export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600 rounded-lg text-white">
            <Ship className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              LadingLens
            </h1>
            <p className="text-xs text-gray-500 font-medium">
              Logistics Automation Agent
            </p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-6">
          <div className="flex items-center gap-1.5 text-blue-600 font-medium bg-blue-50 px-3 py-1.5 rounded-md">
            <LayoutDashboard className="w-4 h-4" />
            <span className="text-sm">Dashboard</span>
          </div>
          {/* Add User/Settings profile here if needed */}
        </div>
      </div>
    </header>
  );
}
