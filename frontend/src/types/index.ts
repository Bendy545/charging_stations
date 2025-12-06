export interface Station {
    id: number;
    station_code: string;
    station_name: string;
    location: string;
    created_at?: string;
}

export interface PowerConsumption {
    id: number;
    timestamp: string;
    station_id: number;
    active_power_kwh: number;
    reactive_power_kwh: number;
    station_code?: string;
    station_name?: string;
}

export interface ChargingSession {
    id: number;
    station_id: number;
    charger_name: string;
    start_date: string;
    end_date: string | null;
    total_kwh: number;
    start_card: string | null;
    end_interval_15min: string;
    station_code?: string;
    station_name?: string;
}

export interface LossAnalysis {
    id: number;
    station_id: number;
    period_start: string;
    period_end: string;
    total_consumption_kwh: number;
    total_delivered_kwh: number;
    loss_kwh: number;
    loss_percentage: number;
    calculated_at?: string;
    station_code?: string;
    station_name?: string;
}

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}

export interface ProcessDataResponse {
    success: boolean;
    message: string;
    consumption_records: number;
    session_records: number;
}

export interface StationStats {
    totalLoss: string;
    avgLossPercentage: string;
    totalConsumption: string;
    totalDelivered: string;
    maxLossDay?: LossAnalysis;
}

export interface ChartDataPoint {
    date: string;
    consumption: string;
    delivered: string;
    loss: string;
    lossPercentage: string;
}