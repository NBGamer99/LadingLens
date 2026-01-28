export const EmailStatus = {
    PRE_ALERT: "pre_alert",
    DRAFT: "draft",
    UNKNOWN: "unknown"
} as const;
export type EmailStatus = typeof EmailStatus[keyof typeof EmailStatus];

export const DocType = {
    HBL: "hbl",
    MBL: "mbl",
    UNKNOWN: "unknown"
} as const;
export type DocType = typeof DocType[keyof typeof DocType];

export type ContainerInfo = {
    weight?: string;
    volume?: string;
    number?: string;
};

export type ExtractionResult = {
    id?: string; // Virtual ID for UI
    doc_type: DocType;
    bl_number?: string;
    email_status: EmailStatus;
    containers: ContainerInfo[];

    shipper_name?: string;
    consignee_name?: string;
    notify_party_name?: string;
    carrier_name?: string;

    port_of_loading?: string;
    port_of_discharge?: string;
    place_of_receipt?: string;
    place_of_delivery?: string;

    etd?: string;
    eta?: string;

    source_email_id: string;
    source_subject: string;
    source_from: string;
    source_received_at: string; // ISO string on frontend? Backend sends ISO usually if serialized, but datetime might be returned as string.
    attachment_filename: string;
    page_range: number[];
    created_at: string;
    dedupe_key: string;

    extraction_confidence?: number;
    raw_text_excerpt?: string;
};

export type ProcessingSummary = {
    emails_processed: number;
    attachments_processed: number;
    docs_created: number;
    skipped_duplicates: number;
    errors: number;
};

export type PaginatedResponse<T = ExtractionResult> = {
    items: T[];
    next_cursor: string | null;
    has_more: boolean;
};

