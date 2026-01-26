import axios from 'axios';
import type { ExtractionResult, ProcessingSummary } from '../types';

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

    getHBLs: async (limit: number = 20): Promise<ExtractionResult[]> => {
        const response = await client.get<ExtractionResult[]>('/hbl', { params: { limit } });
        return response.data;
    },

    getMBLs: async (limit: number = 20): Promise<ExtractionResult[]> => {
        const response = await client.get<ExtractionResult[]>('/mbl', { params: { limit } });
        return response.data;
    }
};
