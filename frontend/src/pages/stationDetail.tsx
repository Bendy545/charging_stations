import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format, startOfMonth, endOfMonth } from 'date-fns';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { stationAPI, lossAPI } from '../services/api';
import { Station, LossAnalysis, StationStats, ChartDataPoint } from '../types';
import './StationDetail.css';

const StationDetail: React.FC = () => {
    const { stationId } = useParams<{ stationId: string }>();
    const [station, setStation] = useState<Station | null>(null);
    const [lossData, setLossData] = useState<LossAnalysis[]>([]);
    const [selectedMonth, setSelectedMonth] = useState<string>(format(new Date(), 'yyyy-MM'));
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (stationId) {
            fetchStationData();
        }
    }, [stationId, selectedMonth]);

    const fetchStationData = async (): Promise<void> => {
        if (!stationId) return;

        try {
            setLoading(true);
            setError(null);

            const monthDate = new Date(selectedMonth);
            const startDate = format(startOfMonth(monthDate), 'yyyy-MM-dd');
            const endDate = format(endOfMonth(monthDate), 'yyyy-MM-dd');

            const [stationRes, lossRes] = await Promise.all([
                stationAPI.getById(parseInt(stationId)),
                lossAPI.get({
                    station_id: parseInt(stationId),
                    start_date: startDate,
                    end_date: endDate
                })
            ]);

            if (stationRes.success && stationRes.data) {
                setStation(stationRes.data);
            }

            if (lossRes.success && lossRes.data) {
                setLossData(lossRes.data);
            }
        } catch (err) {
            setError('Failed to load station data.');
            console.error('Error fetching station data:', err);
        } finally {
            setLoading(false);
        }
    };

    const calculateStats = (): StationStats => {
        if (lossData.length === 0) {
            return {
                totalLoss: '0.00',
                avgLossPercentage: '0.00',
                totalConsumption: '0.00',
                totalDelivered: '0.00',
                maxLossDay: undefined
            };
        }

        const totalLoss = lossData.reduce((sum, loss) => sum + parseFloat(String(loss.loss_kwh)), 0);
        const avgLossPercentage = lossData.reduce((sum, loss) => sum + parseFloat(String(loss.loss_percentage)), 0) / lossData.length;
        const totalConsumption = lossData.reduce((sum, loss) => sum + parseFloat(String(loss.total_consumption_kwh)), 0);
        const totalDelivered = lossData.reduce((sum, loss) => sum + parseFloat(String(loss.total_delivered_kwh)), 0);

        const maxLossDay = lossData.reduce((max, loss) =>
                parseFloat(String(loss.loss_kwh)) > parseFloat(String(max.loss_kwh)) ? loss : max
            , lossData[0]);

        return {
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: avgLossPercentage.toFixed(2),
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            maxLossDay
        };
    };

    const prepareChartData = (): ChartDataPoint[] => {
        return lossData
            .sort((a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime())
            .map(loss => ({
                date: format(new Date(loss.period_start), 'MM/dd'),
                consumption: parseFloat(String(loss.total_consumption_kwh)).toFixed(2),
                delivered: parseFloat(String(loss.total_delivered_kwh)).toFixed(2),
                loss: parseFloat(String(loss.loss_kwh)).toFixed(2),
                lossPercentage: parseFloat(String(loss.loss_percentage)).toFixed(2)
            }));
    };

    const handleMonthChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
        setSelectedMonth(e.target.value);
    };

    if (loading) {
        return <div className="loading">Loading station details...</div>;
    }

    if (error || !station) {
        return (
            <div className="error">
                <h3>Error</h3>
                <p>{error || 'Station not found'}</p>
                <Link to="/" className="btn btn-primary">Back to Dashboard</Link>
            </div>
        );
    }

    const stats = calculateStats();
    const chartData = prepareChartData();

    return (
        <div className="station-detail">
            <div className="detail-header">
                <Link to="/" className="back-link">← Back to Dashboard</Link>
                <div className="header-content">
                    <h1>{station.station_code}</h1>
                    <p className="station-name">{station.station_name}</p>
                    <p className="station-location">📍 {station.location}</p>
                </div>

                <div className="month-selector">
                    <label htmlFor="month">Select Month:</label>
                    <input
                        id="month"
                        type="month"
                        value={selectedMonth}
                        onChange={handleMonthChange}
                        className="month-input"
                    />
                </div>
            </div>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Total Consumption</div>
                    <div className="stat-value">{stats.totalConsumption}</div>
                    <div className="stat-unit">kWh</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Total Delivered</div>
                    <div className="stat-value">{stats.totalDelivered}</div>
                    <div className="stat-unit">kWh</div>
                </div>

                <div className="stat-card highlight-loss">
                    <div className="stat-label">Total Loss</div>
                    <div className="stat-value">{stats.totalLoss}</div>
                    <div className="stat-unit">kWh</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Average Loss</div>
                    <div className="stat-value">{stats.avgLossPercentage}</div>
                    <div className="stat-unit">%</div>
                </div>
            </div>

            {stats.maxLossDay && (
                <div className="card">
                    <h3>Highest Loss Day</h3>
                    <p>
                        <strong>{format(new Date(stats.maxLossDay.period_start), 'MMMM dd, yyyy')}</strong> -
                        Loss: {parseFloat(String(stats.maxLossDay.loss_kwh)).toFixed(2)} kWh
                        ({parseFloat(String(stats.maxLossDay.loss_percentage)).toFixed(2)}%)
                    </p>
                </div>
            )}

            {chartData.length > 0 ? (
                <>
                    <div className="card">
                        <h3 className="card-title">Energy Consumption vs Delivered</h3>
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis label={{ value: 'Energy (kWh)', angle: -90, position: 'insideLeft' }} />
                                <Tooltip />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="consumption"
                                    stroke="#2563eb"
                                    strokeWidth={2}
                                    name="Consumption"
                                    dot={{ r: 4 }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="delivered"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    name="Delivered"
                                    dot={{ r: 4 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="card">
                        <h3 className="card-title">Daily Energy Loss</h3>
                        <ResponsiveContainer width="100%" height={400}>
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis label={{ value: 'Loss (kWh)', angle: -90, position: 'insideLeft' }} />
                                <Tooltip />
                                <Legend />
                                <Bar
                                    dataKey="loss"
                                    fill="#dc2626"
                                    name="Energy Loss"
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="card">
                        <h3 className="card-title">Loss Percentage Over Time</h3>
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis label={{ value: 'Loss (%)', angle: -90, position: 'insideLeft' }} />
                                <Tooltip />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="lossPercentage"
                                    stroke="#f59e0b"
                                    strokeWidth={2}
                                    name="Loss %"
                                    dot={{ r: 4 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </>
            ) : (
                <div className="card">
                    <p>No data available for the selected month.</p>
                </div>
            )}
        </div>
    );
};

export default StationDetail;