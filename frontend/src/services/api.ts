import type { Station, LossData, ConsumptionData, SessionData } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

interface ApiResponse<T> {
    success: boolean;
    data: T;
    error?: string;
}

export const api = {
    async getStations(): Promise<Station[]> {
        const response = await fetch(`${API_BASE_URL}/stations`);
        const data: ApiResponse<Station[]> = await response.json();
        return data.success ? data.data : [];
    },

    async getStation(stationId: number): Promise<Station | null> {
        const response = await fetch(`${API_BASE_URL}/stations/${stationId}`);
        const data: ApiResponse<Station> = await response.json();
        return data.success ? data.data : null;
    },

    async getLosses(
        stationId?: number,
        startDate?: string,
        endDate?: string
    ): Promise<LossData[]> {
        const params = new URLSearchParams();
        if (stationId) params.append('station_id', stationId.toString());
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        const response = await fetch(`${API_BASE_URL}/losses?${params}`);
        const data: ApiResponse<LossData[]> = await response.json();
        return data.success ? data.data : [];
    },

    async getConsumption(
        stationId?: number,
        startDate?: string,
        endDate?: string,
        limit: number = 1000
    ): Promise<ConsumptionData[]> {
        const params = new URLSearchParams();
        if (stationId) params.append('station_id', stationId.toString());
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('limit', limit.toString());

        const response = await fetch(`${API_BASE_URL}/consumption?${params}`);
        const data: ApiResponse<ConsumptionData[]> = await response.json();
        return data.success ? data.data : [];
    },

    async getSessions(
        stationId?: number,
        startDate?: string,
        endDate?: string,
        limit: number = 1000
    ): Promise<SessionData[]> {
        const params = new URLSearchParams();
        if (stationId) params.append('station_id', stationId.toString());
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('limit', limit.toString());

        const response = await fetch(`${API_BASE_URL}/sessions?${params}`);
        const data: ApiResponse<SessionData[]> = await response.json();
        return data.success ? data.data : [];
    },
};