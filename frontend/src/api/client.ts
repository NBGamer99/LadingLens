import axios from 'axios';
import type { ExtractionResult, ProcessingSummary, PaginatedResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface StreamCallbacks {
    onDocument?: (doc: ExtractionResult) => void;
    onStatus?: (message: string) => void;
    onError?: (message: string) => void;
    onComplete?: (summary: ProcessingSummary) => void;
}

export const api = {
    triggerProcessing: async (): Promise<ProcessingSummary> => {
        const response = await client.post<ProcessingSummary>('/process');
        return response.data;
    },

    // Stream processing with real-time updates
    streamProcessing: (skipDedupe: boolean = false, callbacks: StreamCallbacks): (() => void) => {
        const url = `${API_URL}/process-stream?skip_dedupe=${skipDedupe}`;
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                switch (data.type) {
                    case 'document':
                        callbacks.onDocument?.(data.data as ExtractionResult);
                        break;
                    case 'status':
                        callbacks.onStatus?.(data.message);
                        break;
                    case 'error':
                        callbacks.onError?.(data.message);
                        break;
                    case 'complete':
                        callbacks.onComplete?.(data.summary as ProcessingSummary);
                        eventSource.close();
                        break;
                }
            } catch (e) {
                console.error('Failed to parse SSE event:', e);
            }
        };

        eventSource.onerror = () => {
            callbacks.onError?.('Connection lost');
            eventSource.close();
        };

        // Return cleanup function
        return () => eventSource.close();
    },

    getHBLs: async (limit: number = 4, cursor?: string): Promise<PaginatedResponse<ExtractionResult>> => {
        const response = await client.get<PaginatedResponse<ExtractionResult>>('/hbl', {
            params: { limit, cursor }
        });
        return response.data;
    },

    getMBLs: async (limit: number = 4, cursor?: string): Promise<PaginatedResponse<ExtractionResult>> => {
        const response = await client.get<PaginatedResponse<ExtractionResult>>('/mbl', {
            params: { limit, cursor }
        });
        return response.data;
    }
};

