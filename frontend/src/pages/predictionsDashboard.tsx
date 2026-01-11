import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import type {  DailyPrediction, TrainingResults } from '../services/predictions-api';
import { predictionsApi } from '../services/predictions-api.ts'
import { api } from '../services/api';
import type { Station } from '../types';

const PredictionsDashboard: React.FC = () => {
    const [stations, setStations] = useState<Station[]>([]);
    const [predictions, setPredictions] = useState<Map<number, DailyPrediction[]>>(new Map());
    const [modelInfo, setModelInfo] = useState<TrainingResults | null>(null);
    const [loading, setLoading] = useState(true);
    const [training, setTraining] = useState(false);
    const [selectedDays, setSelectedDays] = useState(7);

    useEffect(() => {
        loadInitialData();
    }, [selectedDays]);

    const loadInitialData = async () => {
        setLoading(true);
        try {
            // Load stations
            const stationsData = await api.getStations();
            setStations(stationsData);

            // Load predictions for all stations
            const stationIds = stationsData.map(s => s.id);
            const predictionsData = await predictionsApi.getAllStationsPredictions(stationIds, selectedDays);
            setPredictions(predictionsData);

            // Load model info
            try {
                const info = await predictionsApi.getModelInfo();
                console.log('Model info:', info);
            } catch (error) {
                console.log('No trained model yet');
            }
        } catch (error) {
            console.error('Error loading data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleTrainModel = async () => {
        setTraining(true);
        try {
            const results = await predictionsApi.trainModel();
            setModelInfo(results);
            alert(`Model trained successfully!\nR² Score: ${results.test_r2}\nMAE: ${results.test_mae_kwh} kWh\nQuality: ${results.quality_rating}`);

            // Reload predictions
            await loadInitialData();
        } catch (error) {
            console.error('Training error:', error);
            alert('Training failed. See console for details.');
        } finally {
            setTraining(false);
        }
    };

    // Calculate overall predictions (sum across all stations)
    const calculateOverallPredictions = (): DailyPrediction[] => {
        if (predictions.size === 0) return [];

        const dateMap = new Map<string, number>();

        predictions.forEach((stationPreds) => {
            stationPreds.forEach(pred => {
                const current = dateMap.get(pred.date) || 0;
                dateMap.set(pred.date, current + pred.predicted_daily_loss_kwh);
            });
        });

        return Array.from(dateMap.entries()).map(([date, total]) => ({
            date,
            predicted_daily_loss_kwh: total,
            avg_hourly_loss_kwh: total / 24,
            day_of_week: new Date(date).toLocaleDateString('en-US', { weekday: 'long' })
        })).sort((a, b) => a.date.localeCompare(b.date));
    };

    const overallPredictions = calculateOverallPredictions();

    if (loading) {
        return (
            <div className="container-fluid px-4 py-5">
                <div className="text-center">
                    <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-3">Loading predictions...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="container-fluid px-4 py-4">
            {/* Header */}
            <div className="mb-4">
                <div className="d-flex justify-content-between align-items-center">
                    <div>
                        <h2 className="mb-1">
                            <i className="bi bi-graph-up-arrow me-2"></i>
                            Loss Predictions Dashboard
                        </h2>
                        <p className="text-muted">ML-powered predictions for next {selectedDays} days</p>
                    </div>
                    <div>
                        <button
                            className="btn btn-primary"
                            onClick={handleTrainModel}
                            disabled={training}
                        >
                            {training ? (
                                <>
                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                    Training...
                                </>
                            ) : (
                                <>
                                    <i className="bi bi-lightning-charge me-2"></i>
                                    Train Model
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Model Info Card */}
            {modelInfo && (
                <div className="card shadow-sm mb-4 border-success">
                    <div className="card-body">
                        <div className="row">
                            <div className="col-md-3">
                                <small className="text-muted">Model Quality</small>
                                <h4 className="mb-0 text-success">{modelInfo.quality_rating}</h4>
                            </div>
                            <div className="col-md-3">
                                <small className="text-muted">R² Score</small>
                                <h4 className="mb-0">{(modelInfo.test_r2 * 100).toFixed(1)}%</h4>
                            </div>
                            <div className="col-md-3">
                                <small className="text-muted">Accuracy (MAE)</small>
                                <h4 className="mb-0">±{modelInfo.test_mae_kwh.toFixed(2)} kWh</h4>
                            </div>
                            <div className="col-md-3">
                                <small className="text-muted">Training Data</small>
                                <h4 className="mb-0">{modelInfo.data_summary.total_hours.toLocaleString()} hours</h4>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Days selector */}
            <div className="card shadow-sm mb-4">
                <div className="card-body">
                    <label className="form-label fw-semibold">Forecast Period</label>
                    <div className="btn-group" role="group">
                        {[3, 7, 14].map(days => (
                            <button
                                key={days}
                                className={`btn ${selectedDays === days ? 'btn-primary' : 'btn-outline-primary'}`}
                                onClick={() => setSelectedDays(days)}
                            >
                                {days} days
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Overall Predictions Chart */}
            <div className="card shadow-sm mb-4">
                <div className="card-header bg-white">
                    <h5 className="mb-0">
                        <i className="bi bi-building me-2"></i>
                        Overall Predictions (All Stations Combined)
                    </h5>
                </div>
                <div className="card-body">
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={overallPredictions}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="date"
                                tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            />
                            <YAxis label={{ value: 'Loss (kWh)', angle: -90, position: 'insideLeft' }} />
                            <Tooltip
                                labelFormatter={(date) => new Date(date).toLocaleDateString()}
                                formatter={(value: number) => [`${value.toFixed(2)} kWh`, 'Predicted Loss']}
                            />
                            <Legend />
                            <Bar dataKey="predicted_daily_loss_kwh" fill="#0d6efd" name="Predicted Daily Loss" />
                        </BarChart>
                    </ResponsiveContainer>

                    {/* Summary Stats */}
                    <div className="row mt-3">
                        <div className="col-md-4">
                            <div className="text-center p-2 bg-light rounded">
                                <small className="text-muted">Total Predicted Loss</small>
                                <h5 className="mb-0 text-primary">
                                    {overallPredictions.reduce((sum, p) => sum + p.predicted_daily_loss_kwh, 0).toFixed(2)} kWh
                                </h5>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="text-center p-2 bg-light rounded">
                                <small className="text-muted">Daily Average</small>
                                <h5 className="mb-0 text-primary">
                                    {(overallPredictions.reduce((sum, p) => sum + p.predicted_daily_loss_kwh, 0) / overallPredictions.length).toFixed(2)} kWh
                                </h5>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="text-center p-2 bg-light rounded">
                                <small className="text-muted">Peak Day</small>
                                <h5 className="mb-0 text-primary">
                                    {Math.max(...overallPredictions.map(p => p.predicted_daily_loss_kwh)).toFixed(2)} kWh
                                </h5>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Individual Station Predictions */}
            <h4 className="mb-3">
                <i className="bi bi-ev-station me-2"></i>
                Individual Station Forecasts
            </h4>
            <div className="row g-4">
                {stations.map(station => {
                    const stationPreds = predictions.get(station.id) || [];

                    if (stationPreds.length === 0) {
                        return (
                            <div key={station.id} className="col-lg-6">
                                <div className="card shadow-sm">
                                    <div className="card-header bg-secondary text-white">
                                        <h6 className="mb-0">{station.station_code} - {station.station_name}</h6>
                                    </div>
                                    <div className="card-body text-center text-muted">
                                        No predictions available
                                    </div>
                                </div>
                            </div>
                        );
                    }

                    const totalLoss = stationPreds.reduce((sum, p) => sum + p.predicted_daily_loss_kwh, 0);
                    const avgLoss = totalLoss / stationPreds.length;

                    return (
                        <div key={station.id} className="col-lg-6">
                            <div className="card shadow-sm">
                                <div className="card-header bg-primary text-white">
                                    <div className="d-flex justify-content-between align-items-center">
                                        <h6 className="mb-0">
                                            <i className="bi bi-ev-station-fill me-2"></i>
                                            {station.station_code} - {station.station_name}
                                        </h6>
                                        <span className="badge bg-light text-dark">
                                            Avg: {avgLoss.toFixed(2)} kWh/day
                                        </span>
                                    </div>
                                </div>
                                <div className="card-body">
                                    <ResponsiveContainer width="100%" height={200}>
                                        <LineChart data={stationPreds}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis
                                                dataKey="date"
                                                tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                            />
                                            <YAxis />
                                            <Tooltip
                                                labelFormatter={(date) => new Date(date).toLocaleDateString()}
                                                formatter={(value: number) => `${value.toFixed(2)} kWh`}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="predicted_daily_loss_kwh"
                                                stroke="#0d6efd"
                                                strokeWidth={2}
                                                dot={{ r: 4 }}
                                                name="Predicted Loss"
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>

                                    {/* Next 3 days detail */}
                                    <div className="mt-3">
                                        <small className="text-muted fw-semibold">Next 3 Days:</small>
                                        <div className="list-group list-group-flush mt-2">
                                            {stationPreds.slice(0, 3).map(pred => (
                                                <div key={pred.date} className="list-group-item d-flex justify-content-between align-items-center px-0">
                                                    <span>
                                                        <i className="bi bi-calendar3 me-2"></i>
                                                        {new Date(pred.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                                                    </span>
                                                    <span className="badge bg-primary rounded-pill">
                                                        {pred.predicted_daily_loss_kwh.toFixed(2)} kWh
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default PredictionsDashboard;