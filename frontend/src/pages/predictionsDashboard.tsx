import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, ComposedChart } from 'recharts';
import type { DailyPrediction } from '../services/predictions-api';
import { predictionsApi } from '../services/predictions-api';
import { api } from '../services/api';
import type { Station } from '../types';

const PredictionsDashboard: React.FC = () => {
    const PROBLEMATIC_STATIONS = [1, 2];

    const [stations, setStations] = useState<Station[]>([]);
    const [predictions, setPredictions] = useState<Map<number, DailyPrediction[]>>(new Map());
    const [loading, setLoading] = useState(true);
    const [training, setTraining] = useState(false);
    const [selectedDays, setSelectedDays] = useState(7);
    const [viewMode, setViewMode] = useState<'compact' | 'detailed'>('compact');
    const [expandedStations, setExpandedStations] = useState<Set<number>>(new Set());

    useEffect(() => {
        loadInitialData();
    }, [selectedDays]);

    const loadInitialData = async () => {
        setLoading(true);
        try {
            const stationsData = await api.getStations();
            const validStations = stationsData.filter(s => !PROBLEMATIC_STATIONS.includes(s.id));
            setStations(validStations);

            const stationIds = validStations.map(s => s.id);
            const predictionsData = await predictionsApi.getAllStationsPredictions(stationIds, selectedDays);
            setPredictions(predictionsData);



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

            alert(`Model trained successfully!\nR² Score: ${(results.test_r2 * 100).toFixed(1)}%\nMAE: ${results.test_mae_kwh.toFixed(2)} kWh\nQuality: ${results.quality_rating}`);

            await loadInitialData();
        } catch (error) {
            console.error('Training error:', error);
            alert('Training failed. See console for details.');
        } finally {
            setTraining(false);
        }
    };

    const calculateOverallPredictions = () => {
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
            total,
            average: total / stations.length,
            day: new Date(date).toLocaleDateString('en-US', { weekday: 'short' })
        })).sort((a, b) => a.date.localeCompare(b.date));
    };

    const toggleStationExpand = (stationId: number) => {
        const newExpanded = new Set(expandedStations);
        if (newExpanded.has(stationId)) {
            newExpanded.delete(stationId);
        } else {
            newExpanded.add(stationId);
        }
        setExpandedStations(newExpanded);
    };

    const exportToCSV = () => {
        const overall = calculateOverallPredictions();
        const headers = ['Date', 'Day', 'Total Loss (kWh)', 'Average Loss (kWh)'];
        const rows = overall.map(d => [
            d.date,
            d.day,
            d.total.toFixed(2),
            d.average.toFixed(2)
        ]);

        const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `loss-predictions-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    };

    const overallPredictions = calculateOverallPredictions();
    const totalPredictedLoss = overallPredictions.reduce((sum, p) => sum + p.total, 0);
    const avgDailyLoss = totalPredictedLoss / (overallPredictions.length || 1);
    const peakDay = Math.max(...overallPredictions.map(p => p.total));

    if (loading) {
        return (
            <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#f8f9fa' }}>
                <div className="text-center">
                    <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}>
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-3 text-muted">Loading predictions...</p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
            <div className="bg-white border-bottom shadow-sm sticky-top">
                <div className="container-fluid px-4 py-3">
                    <div className="row align-items-center">
                        <div className="col-md-6">
                            <h2 className="mb-1 fw-bold">
                                <i className="bi bi-graph-up-arrow me-2 text-primary"></i>
                                Loss Predictions Dashboard
                            </h2>
                            <p className="text-muted mb-0 small">
                                <i className="bi bi-robot me-1"></i>
                                ML-powered forecasting for next {selectedDays} days
                            </p>
                        </div>
                        <div className="col-md-6 text-md-end mt-3 mt-md-0">
                            <div className="btn-group btn-group-sm me-2">
                                <button
                                    className={`btn ${viewMode === 'compact' ? 'btn-primary' : 'btn-outline-primary'}`}
                                    onClick={() => setViewMode('compact')}
                                >
                                    <i className="bi bi-grid-3x3"></i>
                                </button>
                                <button
                                    className={`btn ${viewMode === 'detailed' ? 'btn-primary' : 'btn-outline-primary'}`}
                                    onClick={() => setViewMode('detailed')}
                                >
                                    <i className="bi bi-list-ul"></i>
                                </button>
                            </div>

                            <button
                                className="btn btn-sm btn-outline-secondary me-2"
                                onClick={exportToCSV}
                            >
                                <i className="bi bi-download me-1"></i>
                                Export CSV
                            </button>

                            <button
                                className="btn btn-sm btn-success"
                                onClick={handleTrainModel}
                                disabled={training}
                            >
                                {training ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-1"></span>
                                        Training...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-lightning-charge me-1"></i>
                                        Retrain Model
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container-fluid px-4 py-4">


                {/* Forecast Period + Quick Stats */}
                <div className="row g-3 mb-4">
                    <div className="col-md-4">
                        <div className="card shadow-sm border-0 h-100">
                            <div className="card-body">
                                <label className="form-label fw-semibold small mb-2">
                                    <i className="bi bi-calendar-range me-1"></i>Forecast Period
                                </label>
                                <div className="btn-group d-flex" role="group">
                                    {[3, 7, 14].map(days => (
                                        <button
                                            key={days}
                                            className={`btn btn-sm ${selectedDays === days ? 'btn-primary' : 'btn-outline-primary'}`}
                                            onClick={() => setSelectedDays(days)}
                                        >
                                            {days}d
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-8">
                        <div className="card shadow-sm border-0 h-100">
                            <div className="card-body">
                                <div className="row text-center">
                                    <div className="col-4">
                                        <small className="text-muted d-block mb-1">Total Loss</small>
                                        <h4 className="mb-0 text-primary">{totalPredictedLoss.toFixed(1)} kWh</h4>
                                    </div>
                                    <div className="col-4">
                                        <small className="text-muted d-block mb-1">Daily Average</small>
                                        <h4 className="mb-0 text-info">{avgDailyLoss.toFixed(1)} kWh</h4>
                                    </div>
                                    <div className="col-4">
                                        <small className="text-muted d-block mb-1">Peak Day</small>
                                        <h4 className="mb-0 text-danger">{peakDay.toFixed(1)} kWh</h4>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Overall Chart */}
                <div className="card shadow-sm mb-4 border-0">
                    <div className="card-header bg-white border-bottom">
                        <div className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">
                                <i className="bi bi-bar-chart-line me-2"></i>
                                Overall Forecast (All Stations)
                            </h5>
                            <small className="text-muted">
                                {overallPredictions.length} days | {stations.length} stations
                            </small>
                        </div>
                    </div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height={320}>
                            <ComposedChart data={overallPredictions}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                                <XAxis
                                    dataKey="date"
                                    tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                    tick={{ fontSize: 12 }}
                                />
                                <YAxis
                                    label={{ value: 'Loss (kWh)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                                    tick={{ fontSize: 12 }}
                                />
                                <Tooltip
                                    labelFormatter={(date) => new Date(date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                                    formatter={(value: number, name: string) => {
                                        if (name === 'Total Daily Loss') return [`${value.toFixed(2)} kWh`, name];
                                        if (name === 'Avg per Station') return [`${value.toFixed(2)} kWh`, name];
                                        return [value.toFixed(1), name];
                                    }}
                                    contentStyle={{ backgroundColor: 'rgba(255,255,255,0.95)', border: '1px solid #dee2e6', borderRadius: '4px' }}
                                />
                                <Legend wrapperStyle={{ fontSize: '14px' }} />
                                <Area
                                    type="monotone"
                                    dataKey="total"
                                    fill="rgba(13, 110, 253, 0.1)"
                                    stroke="#0d6efd"
                                    strokeWidth={2}
                                    name="Total Daily Loss"
                                />
                                <Line
                                    type="monotone"
                                    dataKey="average"
                                    stroke="#20c997"
                                    strokeWidth={2}
                                    dot={{ r: 3 }}
                                    name="Avg per Station"
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Station Cards */}
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h4 className="mb-0">
                        <i className="bi bi-ev-station me-2"></i>
                        Individual Stations
                    </h4>
                    <small className="text-muted">{stations.length} active stations</small>
                </div>

                <div className="row g-3">
                    {stations.map(station => {
                        const stationPreds = predictions.get(station.id) || [];
                        const isExpanded = expandedStations.has(station.id);

                        if (stationPreds.length === 0) {
                            return (
                                <div key={station.id} className="col-lg-6">
                                    <div className="card shadow-sm border-warning">
                                        <div className="card-body text-center text-muted py-4">
                                            <i className="bi bi-exclamation-triangle text-warning" style={{ fontSize: '2rem' }}></i>
                                            <p className="mb-0 mt-2">
                                                <strong>{station.station_code}</strong> - No predictions available
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            );
                        }

                        const totalLoss = stationPreds.reduce((sum, p) => sum + p.predicted_daily_loss_kwh, 0);
                        const avgLoss = totalLoss / stationPreds.length;

                        return (
                            <div key={station.id} className="col-lg-6">
                                <div className="card shadow-sm border-0 h-100">
                                    <div className="card-header" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                                        <div className="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h6 className="mb-0">
                                                    <i className="bi bi-ev-station-fill me-2"></i>
                                                    {station.station_code}
                                                </h6>
                                                <small className="opacity-75">{station.station_name}</small>
                                            </div>
                                            <div className="badge bg-light text-dark">
                                                Avg: {avgLoss.toFixed(2)} kWh/day
                                            </div>
                                        </div>
                                    </div>

                                    <div className="card-body">
                                        {viewMode === 'detailed' ? (
                                            <ResponsiveContainer width="100%" height={200}>
                                                <AreaChart data={stationPreds}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                                    <XAxis
                                                        dataKey="date"
                                                        tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                                        tick={{ fontSize: 11 }}
                                                    />
                                                    <YAxis tick={{ fontSize: 11 }} />
                                                    <Tooltip
                                                        labelFormatter={(date) => new Date(date).toLocaleDateString()}
                                                        formatter={(value: number) => `${value.toFixed(2)} kWh`}
                                                    />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="predicted_daily_loss_kwh"
                                                        stroke="#667eea"
                                                        fill="rgba(102, 126, 234, 0.2)"
                                                        strokeWidth={2}
                                                    />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        ) : (
                                            <ResponsiveContainer width="100%" height={150}>
                                                <LineChart data={stationPreds}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#f5f5f5" />
                                                    <XAxis
                                                        dataKey="date"
                                                        tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { day: 'numeric' })}
                                                        tick={{ fontSize: 10 }}
                                                    />
                                                    <YAxis tick={{ fontSize: 10 }} />
                                                    <Tooltip
                                                        labelFormatter={(date) => new Date(date).toLocaleDateString()}
                                                        formatter={(value: number) => `${value.toFixed(2)} kWh`}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="predicted_daily_loss_kwh"
                                                        stroke="#667eea"
                                                        strokeWidth={2}
                                                        dot={{ r: 3 }}
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        )}

                                        <div className="mt-3">
                                            <div className="d-flex justify-content-between align-items-center mb-2">
                                                <small className="text-muted fw-semibold">
                                                    <i className="bi bi-calendar-week me-1"></i>
                                                    {isExpanded ? 'All Days' : 'Next 3 Days'}
                                                </small>
                                                <button
                                                    className="btn btn-sm btn-outline-primary"
                                                    onClick={() => toggleStationExpand(station.id)}
                                                >
                                                    {isExpanded ? (
                                                        <><i className="bi bi-chevron-up me-1"></i>Show Less</>
                                                    ) : (
                                                        <><i className="bi bi-chevron-down me-1"></i>Show All</>
                                                    )}
                                                </button>
                                            </div>

                                            <div style={{ maxHeight: isExpanded ? 'none' : '200px', overflow: 'auto' }}>
                                                {stationPreds.slice(0, isExpanded ? undefined : 3).map(pred => (
                                                    <div key={pred.date} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                                                        <div>
                                                            <div className="fw-semibold">{pred.day_of_week}</div>
                                                            <small className="text-muted">{new Date(pred.date).toLocaleDateString()}</small>
                                                        </div>
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
        </div>
    );
};

export default PredictionsDashboard;