import axios from 'axios';
import type { ExtractionResult, ProcessingSummary, PaginatedResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const api = {
    triggerProcessing: async (): Promise<ProcessingSummary> => {
        const response = await client.post<ProcessingSummary>('/process');
        return response.data;
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
    },

    getIncidents: async (limit: number = 10): Promise<{ items: any[] }> => {
        const response = await client.get<{ items: any[] }>('/incidents', {
            params: { limit }
        });
        return response.data;
    }
};
