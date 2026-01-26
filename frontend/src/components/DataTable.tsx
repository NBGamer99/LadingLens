import { format } from "date-fns";
import { cn } from "../lib/utils";

interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  isLoading?: boolean;
  emptyMessage?: string;
}

export function DataTable<T extends { id?: string | number }>({
  data,
  columns,
  isLoading,
  emptyMessage = "No records found",
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="w-full h-64 flex items-center justify-center text-gray-400">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="w-full h-64 flex items-center justify-center text-gray-500 bg-white border border-gray-200 rounded-lg">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-hidden border border-gray-200 rounded-lg shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className="px-4 py-3 text-left font-semibold text-gray-700 whitespace-nowrap"
                  style={{ width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-gray-50 transition-colors">
                {columns.map((col, colIdx) => (
                  <td
                    key={colIdx}
                    className="px-4 py-3 text-gray-700 whitespace-nowrap"
                  >
                    {col.cell
                      ? col.cell(row)
                      : col.accessorKey
                        ? String(row[col.accessorKey] || "-")
                        : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 text-xs text-gray-500 flex justify-between">
        <span>Total: {data.length} records loaded</span>
        {/* Pagination Controls could go here */}
      </div>
    </div>
  );
}

// Helpers for formatted cells
export const DateCell = ({ date }: { date?: string }) => {
  if (!date) return <span className="text-gray-400">-</span>;
  try {
    return <span>{format(new Date(date), "MMM d, yyyy")}</span>;
  } catch {
    return <span>{date}</span>;
  }
};

export const StatusCell = ({ status }: { status: string }) => {
  const isPreAlert = status?.includes("pre_alert");
  return (
    <span
      className={cn(
        "px-2 py-1 rounded-full text-xs font-medium uppercase tracking-wide",
        isPreAlert ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700",
      )}
    >
      {status?.replace("_", " ") || "UNKNOWN"}
    </span>
  );
};

export const DocTypeCell = ({ type }: { type: string }) => {
  return (
    <span
      className={cn(
        "px-2 py-0.5 rounded text-xs font-bold border",
        type === "hbl"
          ? "bg-purple-50 border-purple-200 text-purple-700"
          : "bg-emerald-50 border-emerald-200 text-emerald-700",
      )}
    >
      {type?.toUpperCase()}
    </span>
  );
};
