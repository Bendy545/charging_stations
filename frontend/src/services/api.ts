import type { Station, LossData, ConsumptionData, SessionData } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}

async function fetchApi<T>(url: string): Promise<T> {
    try {
        console.log('Fetching:', url); // Debug log

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result: ApiResponse<T> = await response.json();

        console.log('API Response:', result); // Debug log

        if (!result.success) {
            throw new Error(result.error || 'API request failed');
        }

        return result.data as T;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

export const api = {
    /**
     * Fetch all stations
     * GET /api/stations
     */
    async getStations(): Promise<Station[]> {
        try {
            const data = await fetchApi<Station[]>(`${API_BASE_URL}/stations`);
            console.log('Stations fetched:', data); // Debug log
            return data || [];
        } catch (error) {
            console.error('Error fetching stations:', error);
            return [];
        }
    },

    /**
     * Fetch single station by ID
     * GET /api/stations/{stationId}
     */
    async getStation(stationId: number): Promise<Station | null> {
        try {
            const data = await fetchApi<Station>(`${API_BASE_URL}/stations/${stationId}`);
            return data;
        } catch (error) {
            console.error('Error fetching station:', error);
            return null;
        }
    },

    /**
     * Fetch loss analysis data
     * GET /api/losses?station_id={id}&start_date={date}&end_date={date}
     */
    async getLosses(
        stationId?: number,
        startDate?: string,
        endDate?: string
    ): Promise<LossData[]> {
        try {
            const params = new URLSearchParams();
            if (stationId) params.append('station_id', stationId.toString());
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);

            const url = `${API_BASE_URL}/losses${params.toString() ? '?' + params.toString() : ''}`;
            const data = await fetchApi<LossData[]>(url);
            console.log('Losses fetched:', data); // Debug log
            return data || [];
        } catch (error) {
            console.error('Error fetching losses:', error);
            return [];
        }
    },

    /**
     * Fetch power consumption data
     * GET /api/consumption?station_id={id}&start_date={date}&end_date={date}&limit={limit}
     */
    async getConsumption(
        stationId?: number,
        startDate?: string,
        endDate?: string,
        limit: number = 1000
    ): Promise<ConsumptionData[]> {
        try {
            const params = new URLSearchParams();
            if (stationId) params.append('station_id', stationId.toString());
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            params.append('limit', limit.toString());

            const url = `${API_BASE_URL}/consumption${params.toString() ? '?' + params.toString() : ''}`;
            const data = await fetchApi<ConsumptionData[]>(url);
            return data || [];
        } catch (error) {
            console.error('Error fetching consumption:', error);
            return [];
        }
    },

    /**
     * Fetch charging sessions data
     * GET /api/sessions?station_id={id}&start_date={date}&end_date={date}&limit={limit}
     */
    async getSessions(
        stationId?: number,
        startDate?: string,
        endDate?: string,
        limit: number = 1000
    ): Promise<SessionData[]> {
        try {
            const params = new URLSearchParams();
            if (stationId) params.append('station_id', stationId.toString());
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            params.append('limit', limit.toString());

            const url = `${API_BASE_URL}/sessions${params.toString() ? '?' + params.toString() : ''}`;
            const data = await fetchApi<SessionData[]>(url);
            console.log('Sessions fetched:', data); // Debug log
            return data || [];
        } catch (error) {
            console.error('Error fetching sessions:', error);
            return [];
        }
    },

    /**
     * Trigger loss recalculation
     * POST /api/losses/recalculate
     */
    async recalculateLosses(): Promise<{ success: boolean; message?: string; error?: string }> {
        try {
            const response = await fetch(`${API_BASE_URL}/losses/recalculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error recalculating losses:', error);
            return { success: false, error: 'Failed to recalculate losses' };
        }
    },

    /**
     * Manual sync
     * POST /api/sync-now
     */
    async syncNow(): Promise<{ success: boolean; message?: string; error?: string }> {
        try {
            const response = await fetch('http://localhost:8000/api/sync-now', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error syncing:', error);
            return { success: false, error: 'Failed to sync data' };
        }
    },

    /**
     * Health check
     * GET /health
     */
    async healthCheck(): Promise<{ status: string; database: string }> {
        try {
            const response = await fetch('http://localhost:8000/health');
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unhealthy', database: 'disconnected' };
        }
    },
};