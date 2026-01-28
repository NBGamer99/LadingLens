import {
  X,
  FileJson,
  Copy,
  Check,
  Ship,
  MapPin,
  Calendar,
  Package,
  Mail,
  Users,
} from "lucide-react";
import { useState } from "react";
import type { ExtractionResult } from "../types";

interface DetailsModalProps {
  data: ExtractionResult | null;
  isOpen: boolean;
  onClose: () => void;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: any;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" />
        {title}
      </h4>
      <div className="bg-gray-50 rounded-lg p-3">{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value?: string | number | null;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-gray-400 uppercase tracking-wide">
        {label}
      </span>
      <span className="text-sm text-gray-800 font-medium">{value || "-"}</span>
    </div>
  );
}

export function DetailsModal({ data, isOpen, onClose }: DetailsModalProps) {
  const [copied, setCopied] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  if (!isOpen || !data) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const docTypeLabel =
    data.doc_type === "hbl" ? "House Bill of Lading" : "Master Bill of Lading";
  const statusColor =
    data.email_status === "pre_alert"
      ? "bg-emerald-100 text-emerald-700"
      : "bg-amber-100 text-amber-700";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-white">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${data.doc_type === "hbl" ? "bg-purple-100" : "bg-emerald-100"}`}
            >
              <FileJson
                className={`w-5 h-5 ${data.doc_type === "hbl" ? "text-purple-600" : "text-emerald-600"}`}
              />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {docTypeLabel}
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono text-gray-600">
                  {data.bl_number || "No BL Number"}
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusColor}`}
                >
                  {data.email_status === "pre_alert" ? "Pre-Alert" : "Draft"}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-5">
          {!showRawJson ? (
            <>
              {/* Parties Section */}
              <Section title="Parties" icon={Users}>
                <div className="grid grid-cols-3 gap-4">
                  <Field label="Shipper" value={data.shipper_name} />
                  <Field label="Consignee" value={data.consignee_name} />
                  <Field label="Notify Party" value={data.notify_party_name} />
                </div>
              </Section>

              {/* Route Section */}
              <Section title="Route" icon={MapPin}>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <Field
                      label="Port of Loading"
                      value={data.port_of_loading}
                    />
                    <Field
                      label="Place of Receipt"
                      value={data.place_of_receipt}
                    />
                  </div>
                  <div className="space-y-3">
                    <Field
                      label="Port of Discharge"
                      value={data.port_of_discharge}
                    />
                    <Field
                      label="Place of Delivery"
                      value={data.place_of_delivery}
                    />
                  </div>
                </div>
              </Section>

              {/* Carrier & Dates Section */}
              <div className="grid grid-cols-2 gap-4">
                <Section title="Carrier" icon={Ship}>
                  <Field label="Carrier Name" value={data.carrier_name} />
                </Section>
                <Section title="Dates" icon={Calendar}>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="ETD" value={formatDate(data.etd)} />
                    <Field label="ETA" value={formatDate(data.eta)} />
                  </div>
                </Section>
              </div>

              {/* Containers Section */}
              {data.containers && data.containers.length > 0 && (
                <Section title="Containers" icon={Package}>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[10px] text-gray-400 uppercase tracking-wider">
                          <th className="pb-2">Container #</th>
                          <th className="pb-2">Weight</th>
                          <th className="pb-2">Volume</th>
                        </tr>
                      </thead>
                      <tbody className="text-gray-700">
                        {data.containers.map((c, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="py-2 font-mono text-xs">
                              <Field label="" value={c.number} />
                            </td>
                            <td className="py-2">
                              <Field label="" value={c.weight} />
                            </td>
                            <td className="py-2">
                              <Field label="" value={c.volume} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Section>
              )}

              {/* Source Section */}
              <Section title="Source" icon={Mail}>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Email Subject" value={data.source_subject} />
                  <Field label="From" value={data.source_from} />
                  <Field label="Attachment" value={data.attachment_filename} />
                  <Field label="Pages" value={data.page_range?.join("-")} />
                  <Field
                    label="Received"
                    value={formatDate(data.source_received_at)}
                  />
                  <Field
                    label="Confidence"
                    value={
                      data.extraction_confidence
                        ? `${(data.extraction_confidence * 100).toFixed(0)}%`
                        : undefined
                    }
                  />
                </div>
              </Section>
            </>
          ) : (
            /* Raw JSON View */
            <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
              <pre className="text-xs text-gray-300 font-mono">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors"
          >
            {showRawJson ? "Show Formatted" : "Show Raw JSON"}
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-green-600" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              {copied ? "Copied!" : "Copy JSON"}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
