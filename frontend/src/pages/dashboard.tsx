import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Station, LossData, DateRange } from '../types';
import FilterBar from '../components/filterBar';
import StatCard from '../components/statCard';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const [stations, setStations] = useState<Station[]>([]);
    const [allLossData, setAllLossData] = useState<LossData[]>([]);
    const [loading, setLoading] = useState(true);
    const [dateRange, setDateRange] = useState<DateRange>({ start: '', end: '' });

    useEffect(() => {
        fetchData();
    }, [dateRange]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [stationsData, lossData] = await Promise.all([
                api.getStations(),
                api.getLosses(undefined, dateRange.start, dateRange.end),
            ]);

            setStations(stationsData);
            setAllLossData(lossData);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    };

    const calculateOverallStats = () => {
        if (allLossData.length === 0) return null;

        const totalConsumption = allLossData.reduce((sum, item) => sum + parseFloat(item.total_consumption_kwh.toString()), 0);
        const totalDelivered = allLossData.reduce((sum, item) => sum + parseFloat(item.total_delivered_kwh.toString()), 0);
        const totalLoss = allLossData.reduce((sum, item) => sum + parseFloat(item.loss_kwh.toString()), 0);
        const avgLossPercentage =
            allLossData.reduce((sum, item) => sum + parseFloat(item.loss_percentage.toString()), 0) / allLossData.length;

        return {
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: avgLossPercentage.toFixed(2),
            efficiency: ((totalDelivered / totalConsumption) * 100).toFixed(2),
        };
    };

    const getStationStats = (stationId: number) => {
        const stationLossData = allLossData.filter((item) => item.station_id === stationId);

        if (stationLossData.length === 0) return null;

        const totalConsumption = stationLossData.reduce(
            (sum, item) => sum + parseFloat(item.total_consumption_kwh.toString()),
            0
        );
        const totalDelivered = stationLossData.reduce(
            (sum, item) => sum + parseFloat(item.total_delivered_kwh.toString()),
            0
        );
        const totalLoss = stationLossData.reduce(
            (sum, item) => sum + parseFloat(item.loss_kwh.toString()),
            0
        );
        const avgLossPercentage =
            stationLossData.reduce(
                (sum, item) => sum + parseFloat(item.loss_percentage.toString()),
                0
            ) / stationLossData.length;

        return {
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: avgLossPercentage.toFixed(2),
            efficiency: ((totalDelivered / totalConsumption) * 100).toFixed(2),
        };
    };

    const overallStats = calculateOverallStats();

    if (loading) {
        return (
            <div className="container-fluid px-4 py-5">
                <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
                    <div className="text-center">
                        <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
                            <span className="visually-hidden">Loading...</span>
                        </div>
                        <p className="mt-3 text-muted">Loading dashboard...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container-fluid px-4 py-4">
            {/* Page Header */}
            <div className="mb-4">
                <h2 className="mb-1">
                    <i className="bi bi-grid-3x3-gap me-2"></i>
                    Overview Dashboard
                </h2>
                <p className="text-muted">Jeníšov Charging Station Location - All Stations Summary</p>
            </div>

            <FilterBar dateRange={dateRange} onDateRangeChange={setDateRange} />

            {overallStats && (
                <>
                    <h4 className="mb-3">
                        <i className="bi bi-bar-chart-line me-2"></i>
                        Overall Statistics
                    </h4>
                    <div className="row g-4 mb-5">
                        <div className="col-lg-3 col-md-6">
                            <StatCard
                                title="Total Consumption"
                                value={overallStats.totalConsumption}
                                unit="kWh"
                                icon="bi-activity"
                                color="primary"
                            />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard
                                title="Total Delivered"
                                value={overallStats.totalDelivered}
                                unit="kWh"
                                icon="bi-lightning-charge"
                                color="success"
                            />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard
                                title="Total Loss"
                                value={overallStats.totalLoss}
                                unit="kWh"
                                icon="bi-exclamation-triangle"
                                color="danger"
                            />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard
                                title="Average Loss"
                                value={`${overallStats.avgLossPercentage}%`}
                                icon="bi-graph-down"
                                color="warning"
                            />
                        </div>
                    </div>
                </>
            )}

            <h4 className="mb-3">
                <i className="bi bi-ev-station me-2"></i>
                Individual Stations
            </h4>
            <div className="row g-4">
                {stations.map((station) => {
                    const stats = getStationStats(station.id);

                    return (
                        <div key={station.id} className="col-lg-6 col-xl-4">
                            <div className="card shadow-sm border-0 h-100 station-card"
                                 style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                                 onClick={() => navigate(`/station/${station.id}`)}
                                 onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                                 onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                            >
                                <div className="card-header bg-primary text-white">
                                    <h5 className="mb-0">
                                        <i className="bi bi-ev-station-fill me-2"></i>
                                        {station.station_code}
                                    </h5>
                                    <small>{station.station_name}</small>
                                </div>
                                <div className="card-body">
                                    {stats ? (
                                        <>
                                            <div className="row g-2 mb-3">
                                                <div className="col-6">
                                                    <div className="text-center p-2 bg-light rounded">
                                                        <small className="text-muted d-block">Consumption</small>
                                                        <strong className="text-primary">{stats.totalConsumption} kWh</strong>
                                                    </div>
                                                </div>
                                                <div className="col-6">
                                                    <div className="text-center p-2 bg-light rounded">
                                                        <small className="text-muted d-block">Delivered</small>
                                                        <strong className="text-success">{stats.totalDelivered} kWh</strong>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="row g-2">
                                                <div className="col-6">
                                                    <div className="text-center p-2 bg-light rounded">
                                                        <small className="text-muted d-block">Loss</small>
                                                        <strong className="text-danger">{stats.totalLoss} kWh</strong>
                                                    </div>
                                                </div>
                                                <div className="col-6">
                                                    <div className="text-center p-2 bg-light rounded">
                                                        <small className="text-muted d-block">Avg Loss %</small>
                                                        <strong className="text-warning">{stats.avgLossPercentage}%</strong>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="mt-3">
                                                <div className="progress" style={{ height: '25px' }}>
                                                    <div
                                                        className="progress-bar bg-success"
                                                        role="progressbar"
                                                        style={{ width: `${stats.efficiency}%` }}
                                                    >
                                                        Efficiency: {stats.efficiency}%
                                                    </div>
                                                </div>
                                            </div>
                                        </>
                                    ) : (
                                        <p className="text-muted text-center mb-0">No data available</p>
                                    )}
                                </div>
                                <div className="card-footer bg-white border-top">
                                    <button className="btn btn-sm btn-outline-primary w-100">
                                        <i className="bi bi-arrow-right-circle me-1"></i>
                                        View Details
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {stations.length === 0 && (
                <div className="alert alert-info">
                    <i className="bi bi-info-circle me-2"></i>
                    No stations found. Please check your database connection.
                </div>
            )}
        </div>
    );
};

export default Dashboard;