import axios from 'axios';
import type { ExtractionResult, ProcessingSummary, PaginatedResponse, DashboardStats } from '../types';

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

    getHBLs: async (limit: number = 4, cursor?: string, filters?: Record<string, any>): Promise<PaginatedResponse<ExtractionResult>> => {
        const response = await client.get<PaginatedResponse<ExtractionResult>>('/hbl', {
            params: { limit, cursor, ...filters }
        });
        return response.data;
    },

    getMBLs: async (limit: number = 4, cursor?: string, filters?: Record<string, any>): Promise<PaginatedResponse<ExtractionResult>> => {
        const response = await client.get<PaginatedResponse<ExtractionResult>>('/mbl', {
            params: { limit, cursor, ...filters }
        });
        return response.data;
    },

    getIncidents: async (limit: number = 10): Promise<{ items: any[] }> => {
        const response = await client.get<{ items: any[] }>('/incidents', {
            params: { limit }
        });
        return response.data;
    },

    async getFilterOptions(): Promise<{ carriers: string[], pols: string[], pods: string[] }> {
        const response = await client.get<{ carriers: string[], pols: string[], pods: string[] }>('/filter-options');
        return response.data;
    },

    getStats: async (): Promise<DashboardStats> => {
        const response = await client.get<DashboardStats>('/stats');
        return response.data;
    }
};
