import { Package, Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

interface ProcessButtonProps {
  isProcessing: boolean;
  onClick: () => void;
}

export function ProcessButton({ isProcessing, onClick }: ProcessButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={isProcessing}
      className={cn(
        "flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium text-white shadow-lg transition-all",
        isProcessing
          ? "bg-gray-400 cursor-not-allowed"
          : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-blue-500/25 active:scale-95",
      )}
    >
      {isProcessing ? (
        <>
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Processing Ingest...</span>
        </>
      ) : (
        <>
          <Package className="w-5 h-5" />
          <span>Process Gmail Inbox</span>
        </>
      )}
    </button>
  );
}

interface StatProps {
  label: string;
  value: number | string;
  color?: string;
}

export function StatCard({ label, value, color = "text-gray-900" }: StatProps) {
  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center min-w-[120px]">
      <span className={cn("text-2xl font-bold font-mono", color)}>{value}</span>
      <span className="text-xs text-gray-500 uppercase tracking-widest mt-1">
        {label}
      </span>
    </div>
  );
}
