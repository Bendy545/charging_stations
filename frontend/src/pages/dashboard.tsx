import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { stationAPI, lossAPI } from '../services/api';
import { Station, LossAnalysis, StationStats } from '../types';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    const [stations, setStations] = useState<Station[]>([]);
    const [lossData, setLossData] = useState<LossAnalysis[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async (): Promise<void> => {
        try {
            setLoading(true);
            setError(null);

            const [stationsRes, lossRes] = await Promise.all([
                stationAPI.getAll(),
                lossAPI.get()
            ]);

            if (stationsRes.success && stationsRes.data) {
                setStations(stationsRes.data);
            }

            if (lossRes.success && lossRes.data) {
                setLossData(lossRes.data);
            }
        } catch (err) {
            setError('Failed to load data. Please check if the API is running.');
            console.error('Error fetching data:', err);
        } finally {
            setLoading(false);
        }
    };

    const calculateStationStats = (stationId: number): StationStats => {
        const stationLosses = lossData.filter(loss => loss.station_id === stationId);

        if (stationLosses.length === 0) {
            return {
                totalLoss: '0.00',
                avgLossPercentage: '0.00',
                totalConsumption: '0.00',
                totalDelivered: '0.00'
            };
        }

        const totalLoss = stationLosses.reduce((sum, loss) => sum + parseFloat(String(loss.loss_kwh)), 0);
        const avgLossPercentage = stationLosses.reduce((sum, loss) => sum + parseFloat(String(loss.loss_percentage)), 0) / stationLosses.length;
        const totalConsumption = stationLosses.reduce((sum, loss) => sum + parseFloat(String(loss.total_consumption_kwh)), 0);
        const totalDelivered = stationLosses.reduce((sum, loss) => sum + parseFloat(String(loss.total_delivered_kwh)), 0);

        return {
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: avgLossPercentage.toFixed(2),
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2)
        };
    };

    if (loading) {
        return <div className="loading">Loading dashboard...</div>;
    }

    if (error) {
        return (
            <div className="error">
                <h3>Error</h3>
                <p>{error}</p>
            </div>
        );
    }

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>Charging Station Overview</h1>
                <p className="subtitle">Monitor energy losses across all stations</p>
            </div>

            <div className="stations-grid">
                {stations.map(station => {
                    const stats = calculateStationStats(station.id);

                    return (
                        <Link
                            key={station.id}
                            to={`/station/${station.id}`}
                            className="station-card"
                        >
                            <div className="station-card-header">
                                <h3>{station.station_code}</h3>
                                <span className="station-location">📍 {station.location}</span>
                            </div>

                            <div className="station-stats">
                                <div className="stat-item">
                                    <span className="stat-label">Total Loss</span>
                                    <span className="stat-value loss">{stats.totalLoss} kWh</span>
                                </div>

                                <div className="stat-item">
                                    <span className="stat-label">Avg Loss %</span>
                                    <span className="stat-value">{stats.avgLossPercentage}%</span>
                                </div>

                                <div className="stat-item">
                                    <span className="stat-label">Consumption</span>
                                    <span className="stat-value">{stats.totalConsumption} kWh</span>
                                </div>

                                <div className="stat-item">
                                    <span className="stat-label">Delivered</span>
                                    <span className="stat-value">{stats.totalDelivered} kWh</span>
                                </div>
                            </div>

                            <div className="station-card-footer">
                                <span className="view-details">View Details →</span>
                            </div>
                        </Link>
                    );
                })}
            </div>

            {stations.length === 0 && (
                <div className="empty-state">
                    <h3>No stations found</h3>
                    <p>Please ensure the database is populated with station data.</p>
                </div>
            )}
        </div>
    );
};

export default Dashboard;