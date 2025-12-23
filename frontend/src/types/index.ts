export interface Station {
    id: number;
    station_code: string;
    station_name: string;
}

export interface LossData {
    id: number;
    station_id: number;
    period_start: string;
    period_end: string;
    total_consumption_kwh: number;
    total_delivered_kwh: number;
    total_reactive_kwh: number;
    loss_kwh: number;
    loss_percentage: number;
    station_code?: string;
    station_name?: string;
}

export interface ConsumptionData {
    id: number;
    station_id: number;
    timestamp: string;
    active_power_kwh: number;
    reactive_power_kwh: number;
    station_code?: string;
    station_name?: string;
}

export interface SessionData {
    id: number;
    station_id: number;
    charger_name: string;
    start_date: string;
    end_date: string;
    total_kwh: number;
    start_card: string;
    end_interval_15min: string;
    station_code?: string;
    station_name?: string;
}

export interface DateRange {
    start: string;
    end: string;
}

export interface StationStats {
    totalConsumption: string;
    totalDelivered: string;
    totalLoss: string;
    avgLossPercentage: string;
    efficiency: string;
}