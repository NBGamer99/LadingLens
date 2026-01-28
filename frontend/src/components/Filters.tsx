import { useState, useEffect } from "react";
import { Filter, X, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { api } from "../api/client";

interface FiltersProps {
  onFilterChange: (filters: FilterValues) => void;
  isLoading?: boolean;
}

export interface FilterValues {
  carrier?: string;
  pol?: string;
  pod?: string;
}

interface FilterOptions {
  carriers: string[];
  pols: string[];
  pods: string[];
}

export function Filters({ onFilterChange }: FiltersProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState<FilterValues>({});
  const [options, setOptions] = useState<FilterOptions>({
    carriers: [],
    pols: [],
    pods: [],
  });
  const [isLoadingOptions, setIsLoadingOptions] = useState(false);

  // Fetch filter options when panel opens
  useEffect(() => {
    if (isOpen && options.carriers.length === 0) {
      setIsLoadingOptions(true);
      api
        .getFilterOptions()
        .then(setOptions)
        .catch(console.error)
        .finally(() => setIsLoadingOptions(false));
    }
  }, [isOpen, options.carriers.length]);

  // Debounce filter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      onFilterChange(filters);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, onFilterChange]);

  const handleClear = () => {
    setFilters({});
  };

  const handleChange = (key: keyof FilterValues, value: string) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: value };
      if (!value) delete next[key];
      return next;
    });
  };

  const activeCount = Object.keys(filters).length;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-6">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors rounded-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span>Filters</span>
          {activeCount > 0 && (
            <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-xs">
              {activeCount} active
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {isOpen && (
        <div className="p-4 border-t border-gray-200 animate-in slide-in-from-top-2 duration-200">
          {isLoadingOptions ? (
            <div className="flex items-center justify-center py-4 text-gray-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              Loading filter options...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Carrier */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-500">
                  Carrier
                </label>
                <select
                  className="w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 cursor-pointer"
                  value={filters.carrier || ""}
                  onChange={(e) => handleChange("carrier", e.target.value)}
                >
                  <option value="">All Carriers</option>
                  {options.carriers.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Port of Loading */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-500">
                  Port of Loading
                </label>
                <select
                  className="w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 cursor-pointer"
                  value={filters.pol || ""}
                  onChange={(e) => handleChange("pol", e.target.value)}
                >
                  <option value="">All Ports</option>
                  {options.pols.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {/* Port of Discharge */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-500">
                  Port of Discharge
                </label>
                <select
                  className="w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 cursor-pointer"
                  value={filters.pod || ""}
                  onChange={(e) => handleChange("pod", e.target.value)}
                >
                  <option value="">All Ports</option>
                  {options.pods.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end mt-4">
            <button
              onClick={handleClear}
              disabled={activeCount === 0}
              className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1 px-3 py-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X className="w-3 h-3" />
              Clear Filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
