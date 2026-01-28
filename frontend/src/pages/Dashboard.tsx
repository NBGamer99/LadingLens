import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { ExtractionResult, ProcessingSummary } from "../types";
import {
  DataTable,
  DateCell,
  StatusCell,
  DocTypeCell,
} from "../components/DataTable";
import { Header } from "../components/Header";
import { ProcessButton, StatCard } from "../components/ActionComponents";
import {
  FileSearch,
  Layers,
  AlertCircle,
  RefreshCw,
  ChevronDown,
} from "lucide-react";
import { cn } from "../lib/utils";

const PAGE_SIZE = 4;

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<"hbl" | "mbl">("hbl");

  // Separate state for each tab's data and pagination
  const [hblData, setHblData] = useState<ExtractionResult[]>([]);
  const [hblCursor, setHblCursor] = useState<string | null>(null);
  const [hblHasMore, setHblHasMore] = useState(false);

  const [mblData, setMblData] = useState<ExtractionResult[]>([]);
  const [mblCursor, setMblCursor] = useState<string | null>(null);
  const [mblHasMore, setMblHasMore] = useState(false);
  const [incidents, setIncidents] = useState<any[]>([]);

  const [isLoadingData, setIsLoadingData] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [lastSummary, setLastSummary] = useState<ProcessingSummary | null>(
    null,
  );

  const loadData = async () => {
    setIsLoadingData(true);
    setError(null);
    try {
      const [hblResponse, mblResponse, incidentsResponse] = await Promise.all([
        api.getHBLs(PAGE_SIZE),
        api.getMBLs(PAGE_SIZE),
        api.getIncidents(10),
      ]);

      setHblData(hblResponse.items);
      setHblCursor(hblResponse.next_cursor);
      setHblHasMore(hblResponse.has_more);

      setMblData(mblResponse.items);
      setMblCursor(mblResponse.next_cursor);
      setMblHasMore(mblResponse.has_more);

      setIncidents(incidentsResponse.items);
    } catch (err) {
      console.error("Failed to fetch data:", err);
      setError(
        "Failed to load documents. Please check your connection and try again.",
      );
    } finally {
      setIsLoadingData(false);
    }
  };

  const loadMore = async () => {
    setIsLoadingMore(true);
    setError(null);
    try {
      if (activeTab === "hbl" && hblCursor) {
        const response = await api.getHBLs(PAGE_SIZE, hblCursor);
        setHblData((prev) => [...prev, ...response.items]);
        setHblCursor(response.next_cursor);
        setHblHasMore(response.has_more);
      } else if (activeTab === "mbl" && mblCursor) {
        const response = await api.getMBLs(PAGE_SIZE, mblCursor);
        setMblData((prev) => [...prev, ...response.items]);
        setMblCursor(response.next_cursor);
        setMblHasMore(response.has_more);
      }
    } catch (err) {
      console.error("Failed to load more:", err);
      setError("Failed to load more documents. Please try again.");
    } finally {
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const [authError, setAuthError] = useState<string | null>(null);

  const handleProcess = async () => {
    setIsProcessing(true);
    setLastSummary(null);
    setError(null);
    setAuthError(null);

    try {
      const summary = await api.triggerProcessing();
      setLastSummary(summary);
      // Reload data after processing completes
      await loadData();
    } catch (err: any) {
      console.error("Processing error:", err);
      if (err.response?.status === 401) {
        setAuthError(
          err.response?.data?.detail ||
            "Unable to connect to Gmail. Please ensure the authentication tokens are properly configured.",
        );
      } else {
        setError(
          err.response?.data?.detail ||
            "Processing failed. Please check the server logs for details.",
        );
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const columns = [
    {
      header: "Type",
      accessorKey: "doc_type",
      cell: (row: any) => <DocTypeCell type={row.doc_type} />,
      width: "80px",
    },
    { header: "BL Number", accessorKey: "bl_number" },
    {
      header: "Status",
      accessorKey: "email_status",
      cell: (row: any) => <StatusCell status={row.email_status} />,
    },
    {
      header: "Shipper / Consignee",
      cell: (row: any) => (
        <div className="flex flex-col text-xs space-y-0.5">
          <span
            className="font-medium text-gray-700 truncate max-w-[150px]"
            title={row.shipper_name}
          >
            {row.shipper_name || "-"}
          </span>
          <span
            className="text-gray-400 truncate max-w-[150px]"
            title={row.consignee_name}
          >
            {row.consignee_name || "-"} (Consignee)
          </span>
        </div>
      ),
    },
    {
      header: "Route",
      cell: (row: any) => (
        <div className="flex flex-col text-xs text-gray-600">
          <span className="flex items-center gap-1">
            POL:{" "}
            <span className="font-medium text-gray-800">
              {row.port_of_loading || "-"}
            </span>
          </span>
          <span className="flex items-center gap-1">
            POD:{" "}
            <span className="font-medium text-gray-800">
              {row.port_of_discharge || "-"}
            </span>
          </span>
        </div>
      ),
    },
    {
      header: "Est. Dates",
      cell: (row: any) => (
        <div className="flex flex-col text-xs text-gray-600">
          <span>
            ETD: <DateCell date={row.etd} />
          </span>
          <span>
            ETA: <DateCell date={row.eta} />
          </span>
        </div>
      ),
    },
    {
      header: "Source",
      cell: (row: any) => (
        <div className="flex flex-col">
          <span className="text-xs text-blue-600 font-medium truncate max-w-[150px]">
            {row.source_subject}
          </span>
          <span className="text-[10px] text-gray-400">
            {row.attachment_filename} (p.{row.page_range?.[0]})
          </span>
        </div>
      ),
    },
    {
      header: "Received",
      accessorKey: "source_received_at",
      cell: (row: any) => (
        <span className="text-xs text-gray-500">
          <DateCell date={row.source_received_at} />
        </span>
      ),
    },
  ];

  const currentData = activeTab === "hbl" ? hblData : mblData;
  const currentHasMore = activeTab === "hbl" ? hblHasMore : mblHasMore;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Auth Error Banner - More prominent for Gmail authentication issues */}
        {authError && (
          <div className="bg-amber-50 border-2 border-amber-400 rounded-lg p-5 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 bg-amber-100 rounded-full p-2">
                <AlertCircle className="w-6 h-6 text-amber-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-amber-800">
                  Gmail Connection Issue
                </h3>
                <p className="mt-1 text-sm text-amber-700">{authError}</p>
                <p className="mt-3 text-xs text-amber-600">
                  Check the browser console or server logs for technical
                  details.
                </p>
              </div>
              <button
                onClick={() => setAuthError(null)}
                className="flex-shrink-0 text-amber-600 hover:text-amber-800 transition-colors"
              >
                <span className="sr-only">Dismiss</span>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* General Error Banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-3 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm font-medium">{error}</span>
            </div>
            <button
              onClick={() => loadData()}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded-md transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        )}

        {/* Actions & Summary Section */}
        <section className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Document Extraction
            </h2>
            <p className="text-gray-500 mt-1">
              Review extracted Bills of Lading from newly arrived emails.
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            <ProcessButton
              isProcessing={isProcessing}
              onClick={handleProcess}
            />
            {lastSummary && (
              <div className="text-xs text-right text-gray-500 bg-emerald-50 text-emerald-700 px-3 py-1 rounded border border-emerald-100">
                Processed {lastSummary.emails_processed} emails, created{" "}
                {lastSummary.docs_created} docs.
              </div>
            )}
          </div>
        </section>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="HBLs Extracted"
            value={hblData.length}
            color="text-purple-600"
          />
          <StatCard
            label="MBLs Extracted"
            value={mblData.length}
            color="text-emerald-600"
          />
          <StatCard
            label="Total Docs"
            value={hblData.length + mblData.length}
          />
          <StatCard
            label="Recent Errors"
            value={incidents.length}
            color="text-red-500"
          />
        </div>

        {/* Tabs & Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="border-b border-gray-200 px-6 flex items-center gap-8">
            <button
              onClick={() => setActiveTab("hbl")}
              className={cn(
                "py-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2",
                activeTab === "hbl"
                  ? "border-purple-600 text-purple-600"
                  : "border-transparent text-gray-500 hover:text-gray-700",
              )}
            >
              <FileSearch className="w-4 h-4" />
              House Bills (HBL)
              {hblHasMore && <span className="text-xs text-gray-400">+</span>}
            </button>
            <button
              onClick={() => setActiveTab("mbl")}
              className={cn(
                "py-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2",
                activeTab === "mbl"
                  ? "border-emerald-600 text-emerald-600"
                  : "border-transparent text-gray-500 hover:text-gray-700",
              )}
            >
              <Layers className="w-4 h-4" />
              Master Bills (MBL)
              {mblHasMore && <span className="text-xs text-gray-400">+</span>}
            </button>
          </div>

          <div className="p-6">
            <DataTable
              data={currentData}
              columns={columns as any}
              isLoading={isLoadingData}
              emptyMessage={`No ${activeTab.toUpperCase()} documents found.`}
            />

            {/* Load More Button */}
            {currentHasMore && (
              <div className="mt-4 flex justify-center">
                <button
                  onClick={loadMore}
                  disabled={isLoadingMore}
                  className={cn(
                    "flex items-center gap-2 px-6 py-2.5 text-sm font-medium rounded-lg transition-all",
                    "bg-gray-100 hover:bg-gray-200 text-gray-700",
                    isLoadingMore && "opacity-50 cursor-not-allowed",
                  )}
                >
                  {isLoadingMore ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      Load More
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
