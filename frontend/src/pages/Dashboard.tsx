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
import { FileSearch, Layers } from "lucide-react";
import { cn } from "../lib/utils";
// import { Toaster, toast } from "sonner"; // Recommend adding sonner or just use alert for now

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<"hbl" | "mbl">("hbl");
  const [hblData, setHblData] = useState<ExtractionResult[]>([]);
  const [mblData, setMblData] = useState<ExtractionResult[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const [isProcessing, setIsProcessing] = useState(false);
  const [lastSummary, setLastSummary] = useState<ProcessingSummary | null>(
    null,
  );

  const loadData = async () => {
    setIsLoadingData(true);
    try {
      const hbls = await api.getHBLs(50);
      const mbls = await api.getMBLs(50);
      setHblData(hbls);
      setMblData(mbls);
    } catch (error) {
      console.error("Failed to fetch data:", error);
      // toast.error("Failed to load documents");
    } finally {
      setIsLoadingData(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleProcess = async () => {
    setIsProcessing(true);
    setLastSummary(null);
    try {
      const summary = await api.triggerProcessing();
      setLastSummary(summary);
      await loadData();
    } catch (error) {
      console.error("Processing failed:", error);
      alert("Processing failed. Check console/logs.");
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
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
            value={lastSummary?.errors || 0}
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
            </button>
          </div>

          <div className="p-6">
            <DataTable
              data={currentData}
              columns={columns as any}
              isLoading={isLoadingData}
              emptyMessage={`No ${activeTab.toUpperCase()} documents found.`}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
