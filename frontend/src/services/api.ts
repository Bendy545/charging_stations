import axios, { AxiosInstance } from 'axios';
import {
    Station,
    PowerConsumption,
    ChargingSession,
    LossAnalysis,
    ApiResponse,
    ProcessDataResponse
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

const api: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

interface GetParams {
    station_id?: number;
    start_date?: string;
    end_date?: string;
    limit?: number;
}

export const stationAPI = {
    getAll: async (): Promise<ApiResponse<Station[]>> => {
        const response = await api.get<ApiResponse<Station[]>>('/stations');
        return response.data;
    },

    getById: async (id: number): Promise<ApiResponse<Station>> => {
        const response = await api.get<ApiResponse<Station>>(`/stations/${id}`);
        return response.data;
    },
};

export const consumptionAPI = {
    get: async (params: GetParams = {}): Promise<ApiResponse<PowerConsumption[]>> => {
        const response = await api.get<ApiResponse<PowerConsumption[]>>('/consumption', { params });
        return response.data;
    },
};

export const sessionAPI = {
    get: async (params: GetParams = {}): Promise<ApiResponse<ChargingSession[]>> => {
        const response = await api.get<ApiResponse<ChargingSession[]>>('/sessions', { params });
        return response.data;
    },
};

export const lossAPI = {
    get: async (params: Omit<GetParams, 'limit'> = {}): Promise<ApiResponse<LossAnalysis[]>> => {
        const response = await api.get<ApiResponse<LossAnalysis[]>>('/losses', { params });
        return response.data;
    },

    recalculate: async (): Promise<ApiResponse<string>> => {
        const response = await api.post<ApiResponse<string>>('/losses/recalculate');
        return response.data;
    },
};

export const dataAPI = {
    process: async (): Promise<ProcessDataResponse> => {
        const response = await api.post<ProcessDataResponse>('/process-data');
        return response.data;
    },
};

export default api;