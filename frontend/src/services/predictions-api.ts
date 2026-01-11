const API_BASE_URL = 'http://localhost:8000/api';

export interface HourlyPrediction {
    timestamp: string;
    hour: number;
    predicted_loss_kwh: number;
    day_of_week: string;
}

export interface DailyPrediction {
    date: string;
    predicted_daily_loss_kwh: number;
    avg_hourly_loss_kwh: number;
    day_of_week: string;
}

export interface TrainingResults {
    success: boolean;
    model_type: string;
    training_samples: number;
    test_samples: number;
    test_mae_kwh: number;
    test_r2: number;
    quality_rating: string;
    feature_importance: Record<string, number>;
    data_summary: {
        total_hours: number;
        loss_mean_kwh: number;
        loss_std_kwh: number;
        avg_efficiency_pct: number;
    };
}

export interface ModelInfo {
    status: string;
    model_type?: string;
    n_estimators?: number;
    max_depth?: number;
}

export const predictionsApi = {
    /**
     * Train the ML model
     */
    async trainModel(stationId?: number): Promise<TrainingResults> {
        const url = stationId
            ? `${API_BASE_URL}/predictions/train?station_id=${stationId}`
            : `${API_BASE_URL}/predictions/train`;

        const response = await fetch(url, { method: 'POST' });
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Training failed');
        }

        return result;
    },

    /**
     * Get hourly predictions
     */
    async getHourlyForecast(stationId: number, hours: number = 24): Promise<HourlyPrediction[]> {
        const response = await fetch(
            `${API_BASE_URL}/predictions/forecast/hourly?station_id=${stationId}&hours=${hours}`
        );
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Failed to get forecast');
        }

        return result.predictions;
    },

    /**
     * Get daily predictions
     */
    async getDailyForecast(stationId: number, days: number = 7): Promise<DailyPrediction[]> {
        const response = await fetch(
            `${API_BASE_URL}/predictions/forecast?station_id=${stationId}&days=${days}`
        );
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Failed to get forecast');
        }

        return result.predictions;
    },

    /**
     * Get model information
     */
    async getModelInfo(): Promise<ModelInfo> {
        const response = await fetch(`${API_BASE_URL}/predictions/model-info`);
        const result = await response.json();

        if (!result.success) {
            throw new Error('Failed to get model info');
        }

        return result.model_info;
    },

    async getAllStationsPredictions(stations: number[], days: number = 7): Promise<Map<number, DailyPrediction[]>> {
        const predictions = new Map<number, DailyPrediction[]>();

        await Promise.all(
            stations.map(async (stationId) => {
                try {
                    const forecast = await this.getDailyForecast(stationId, days);
                    predictions.set(stationId, forecast);
                } catch (error) {
                    console.error(`Failed to get predictions for station ${stationId}:`, error);
                    predictions.set(stationId, []);
                }
            })
        );

        return predictions;
    }
};