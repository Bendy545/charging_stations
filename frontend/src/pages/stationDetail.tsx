import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Station, LossData, SessionData, DateRange, StationStats } from '../types';
import FilterBar from '../components/filterBar';
import StatCard from '../components/statCard';
import EnergyDistributionChart from '../components/charts/energyDistributionChart';
import LossTrendChart from '../components/charts/lossTrendChart';
import SessionsChart from '../components/charts/sessionChart';
import {BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,} from 'recharts';

const StationDetail: React.FC = () => {
    const { stationId } = useParams<{ stationId: string }>();
    const navigate = useNavigate();
    const [station, setStation] = useState<Station | null>(null);
    const [lossData, setLossData] = useState<LossData[]>([]);
    const [sessionsData, setSessionsData] = useState<SessionData[]>([]);
    const [loading, setLoading] = useState(true);
    const [dateRange, setDateRange] = useState<DateRange>({ start: '', end: '' });
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        if (stationId) {
            fetchStationData();
        }
    }, [stationId, dateRange]);

    const fetchStationData = async () => {
        setLoading(true);
        try {
            const id = parseInt(stationId!);
            const [stationData, lossData, sessionsData] = await Promise.all([
                api.getStation(id),
                api.getLosses(id, dateRange.start, dateRange.end),
                api.getSessions(id, dateRange.start, dateRange.end),
            ]);

            setStation(stationData);
            setLossData(lossData);
            setSessionsData(sessionsData);
        } catch (error) {
            console.error('Error fetching station data:', error);
        } finally {
            setLoading(false);
        }
    };

    const calculateStats = (): StationStats | null => {
        if (lossData.length === 0) return null;

        const totalConsumption = lossData.reduce(
            (sum, item) => sum + Number(item.total_consumption_kwh),
            0
        );

        const totalDelivered = lossData.reduce(
            (sum, item) => sum + Number(item.total_delivered_kwh),
            0
        );

        const totalLoss = lossData.reduce(
            (sum, item) => sum + Number(item.loss_kwh),
            0
        );

        const lossPercentage =
            totalConsumption > 0
                ? (totalLoss / totalConsumption) * 100
                : 0;

        return {
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: lossPercentage.toFixed(2),
            efficiency: ((totalDelivered / totalConsumption) * 100).toFixed(2),
        };
    };

    const prepareComparisonChart = () => {
        return lossData.map((item) => ({
            date: new Date(item.period_start).toLocaleDateString(),
            consumption: parseFloat(item.total_consumption_kwh.toString()),
            delivered: parseFloat(item.total_delivered_kwh.toString()),
            loss: parseFloat(item.loss_kwh.toString()),
        }));
    };

    const stats = calculateStats();

    if (loading) {
        return (
            <div className="container-fluid px-4 py-5">
                <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
                    <div className="text-center">
                        <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
                            <span className="visually-hidden">Loading...</span>
                        </div>
                        <p className="mt-3 text-muted">Loading station details...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!station) {
        return (
            <div className="container-fluid px-4 py-5">
                <div className="alert alert-danger">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    Station not found
                </div>
                <button className="btn btn-primary" onClick={() => navigate('/')}>
                    <i className="bi bi-arrow-left me-2"></i>
                    Back to Dashboard
                </button>
            </div>
        );
    }

    return (
        <div className="container-fluid px-4 py-4">
            <nav aria-label="breadcrumb" className="mb-3">
                <ol className="breadcrumb">
                    <li className="breadcrumb-item">
                        <a href="#" onClick={(e) => { e.preventDefault(); navigate('/'); }} style={{ cursor: 'pointer' }}>
                            Dashboard
                        </a>
                    </li>
                    <li className="breadcrumb-item active" aria-current="page">
                        {station.station_code}
                    </li>
                </ol>
            </nav>

            <div className="mb-4">
                <h2 className="mb-1">
                    <i className="bi bi-ev-station-fill me-2"></i>
                    {station.station_code} - {station.station_name}
                </h2>
                <p className="text-muted">Detailed analysis and statistics</p>
            </div>

            <FilterBar dateRange={dateRange} onDateRangeChange={setDateRange} />

            {stats && (
                <div className="row g-4 mb-4">
                    <div className="col-lg-3 col-md-6">
                        <StatCard
                            title="Total Consumption"
                            value={stats.totalConsumption}
                            unit="kWh"
                            icon="bi-activity"
                            color="primary"
                        />
                    </div>
                    <div className="col-lg-3 col-md-6">
                        <StatCard
                            title="Total Delivered"
                            value={stats.totalDelivered}
                            unit="kWh"
                            icon="bi-lightning-charge"
                            color="success"
                        />
                    </div>
                    <div className="col-lg-3 col-md-6">
                        <StatCard
                            title="Total Loss"
                            value={stats.totalLoss}
                            unit="kWh"
                            icon="bi-exclamation-triangle"
                            color="danger"
                        />
                    </div>
                    <div className="col-lg-3 col-md-6">
                        <StatCard
                            title="Average Loss"
                            value={`${stats.avgLossPercentage}%`}
                            icon="bi-graph-down"
                            color="warning"
                        />
                    </div>
                </div>
            )}

            <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'overview' ? 'active' : ''}`}
                        onClick={() => setActiveTab('overview')}
                    >
                        <i className="bi bi-grid me-2"></i>
                        Overview
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'analysis' ? 'active' : ''}`}
                        onClick={() => setActiveTab('analysis')}
                    >
                        <i className="bi bi-graph-up me-2"></i>
                        Loss Analysis
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'sessions' ? 'active' : ''}`}
                        onClick={() => setActiveTab('sessions')}
                    >
                        <i className="bi bi-clock-history me-2"></i>
                        Sessions
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${activeTab === 'details' ? 'active' : ''}`}
                        onClick={() => setActiveTab('details')}
                    >
                        <i className="bi bi-info-circle me-2"></i>
                        Details
                    </button>
                </li>
            </ul>

            {activeTab === 'overview' && stats && (
                <div className="row g-4">
                    <div className="col-lg-6">
                        <EnergyDistributionChart
                            delivered={parseFloat(stats.totalDelivered)}
                            loss={parseFloat(stats.totalLoss)}
                        />
                    </div>
                    <div className="col-lg-6">
                        <div className="card shadow-sm border-0">
                            <div className="card-header bg-white">
                                <h5 className="mb-0">
                                    <i className="bi bi-bar-chart me-2"></i>
                                    Energy Comparison
                                </h5>
                            </div>
                            <div className="card-body">
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={prepareComparisonChart()}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="date" />
                                        <YAxis />
                                        <Tooltip />
                                        <Legend />
                                        <Bar dataKey="consumption" fill="#0d6efd" name="Consumption" />
                                        <Bar dataKey="delivered" fill="#28a745" name="Delivered" />
                                        <Bar dataKey="loss" fill="#dc3545" name="Loss" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'analysis' && (
                <div className="row g-4">
                    <div className="col-12">
                        <LossTrendChart data={lossData} />
                    </div>
                </div>
            )}

            {activeTab === 'sessions' && (
                <div className="row g-4">
                    <div className="col-12">
                        <SessionsChart data={sessionsData} />
                    </div>
                    <div className="col-12">
                        <div className="card shadow-sm border-0">
                            <div className="card-header bg-white d-flex justify-content-between align-items-center">
                                <h5 className="mb-0">
                                    <i className="bi bi-list-ul me-2"></i>
                                    Recent Sessions
                                </h5>
                                <span className="badge bg-primary">{sessionsData.length} sessions</span>
                            </div>
                            <div className="card-body">
                                <div className="table-responsive">
                                    <table className="table table-hover">
                                        <thead>
                                        <tr>
                                            <th>Start Date</th>
                                            <th>End Date</th>
                                            <th>Charger</th>
                                            <th>Energy (kWh)</th>
                                            <th>Card</th>
                                        </tr>
                                        </thead>
                                        <tbody>
                                        {sessionsData.slice(0, 20).map((session, idx) => (
                                            <tr key={idx}>
                                                <td>{new Date(session.start_date).toLocaleString()}</td>
                                                <td>{new Date(session.end_date).toLocaleString()}</td>
                                                <td>{session.charger_name}</td>
                                                <td>
                            <span className="badge bg-success">
                              {parseFloat(session.total_kwh.toString()).toFixed(2)}
                            </span>
                                                </td>
                                                <td>
                                                    <small className="text-muted">{session.start_card || 'N/A'}</small>
                                                </td>
                                            </tr>
                                        ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'details' && stats && (
                <div className="row g-4">
                    <div className="col-lg-6">
                        <div className="card shadow-sm border-0">
                            <div className="card-header bg-white">
                                <h5 className="mb-0">
                                    <i className="bi bi-info-circle me-2"></i>
                                    Station Information
                                </h5>
                            </div>
                            <div className="card-body">
                                <table className="table table-borderless">
                                    <tbody>
                                    <tr>
                                        <td className="fw-semibold">Station Code:</td>
                                        <td>{station.station_code}</td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Station Name:</td>
                                        <td>{station.station_name}</td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Efficiency:</td>
                                        <td>
                                            <span className="badge bg-success">{stats.efficiency}%</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Total Sessions:</td>
                                        <td>{sessionsData.length}</td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Days Analyzed:</td>
                                        <td>{lossData.length}</td>
                                    </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div className="col-lg-6">
                        <div className="card shadow-sm border-0">
                            <div className="card-header bg-white">
                                <h5 className="mb-0">
                                    <i className="bi bi-calculator me-2"></i>
                                    Performance Metrics
                                </h5>
                            </div>
                            <div className="card-body">
                                <table className="table table-borderless">
                                    <tbody>
                                    <tr>
                                        <td className="fw-semibold">Average Daily Consumption:</td>
                                        <td>
                                            {lossData.length > 0
                                                ? (parseFloat(stats.totalConsumption) / lossData.length).toFixed(2)
                                                : '0.00'}{' '}
                                            kWh
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Average Daily Loss:</td>
                                        <td className="text-danger">
                                            {lossData.length > 0
                                                ? (parseFloat(stats.totalLoss) / lossData.length).toFixed(2)
                                                : '0.00'}{' '}
                                            kWh
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Average Sessions/Day:</td>
                                        <td>
                                            {lossData.length > 0
                                                ? (sessionsData.length / lossData.length).toFixed(1)
                                                : '0.0'}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="fw-semibold">Average Energy/Session:</td>
                                        <td>
                                            {sessionsData.length > 0
                                                ? (parseFloat(stats.totalDelivered) / sessionsData.length).toFixed(2)
                                                : '0.00'}{' '}
                                            kWh
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default StationDetail;