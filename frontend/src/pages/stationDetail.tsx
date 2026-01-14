import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type {
    Station,
    LossData,
    SessionData,
    DateRange,
    StationStats,
} from '../types';

import FilterBar from '../components/filterBar';
import StatCard from '../components/statCard';
import EnergyDistributionChart from '../components/charts/energyDistributionChart';
import LossTrendChart from '../components/charts/lossTrendChart';
import SessionsChart from '../components/charts/sessionChart';
import PowerFactorTrendChart from '../components/charts/powerFactorTrendChart';

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';

const StationDetail: React.FC = () => {
    const { stationId } = useParams<{ stationId: string }>();
    const navigate = useNavigate();

    const [station, setStation] = useState<Station | null>(null);
    const [lossData, setLossData] = useState<LossData[]>([]);
    const [sessionsData, setSessionsData] = useState<SessionData[]>([]);
    const [loading, setLoading] = useState(true);
    const [dateRange, setDateRange] = useState<DateRange>({
        start: '',
        end: '',
    });
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

            const [stationData, lData, sData] = await Promise.all([
                api.getStation(id),
                api.getLosses(id, dateRange.start, dateRange.end),
                api.getSessions(id, dateRange.start, dateRange.end),
            ]);

            setStation(stationData);
            setLossData(lData);
            setSessionsData(sData);
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
            efficiency: (
                (totalDelivered / totalConsumption) *
                100
            ).toFixed(2),
        };
    };

    const prepareComparisonChart = () => {
        return lossData.map((item) => ({
            date: new Date(item.period_start).toLocaleDateString(),
            consumption: Number(item.total_consumption_kwh),
            delivered: Number(item.total_delivered_kwh),
            loss: Number(item.loss_kwh),
        }));
    };

    const stats = calculateStats();

    if (loading) {
        return (
            <div className="container-fluid px-4 py-5 text-center">
                <div className="spinner-border text-primary"></div>
                <p className="mt-3">Loading station details...</p>
            </div>
        );
    }

    if (!station) {
        return (
            <div className="container-fluid px-4 py-5">
                <div className="alert alert-danger">
                    Station not found
                </div>
            </div>
        );
    }

    return (
        <div className="container-fluid px-4 py-4">
            <nav aria-label="breadcrumb" className="mb-3">
                <ol className="breadcrumb">
                    <li className="breadcrumb-item">
                        <a
                            href="#"
                            onClick={(e) => {
                                e.preventDefault();
                                navigate('/');
                            }}
                        >
                            Dashboard
                        </a>
                    </li>
                    <li className="breadcrumb-item active">
                        {station.station_code}
                    </li>
                </ol>
            </nav>

            <div className="mb-4">
                <h2 className="mb-1">
                    <i className="bi bi-ev-station-fill me-2"></i>
                    {station.station_code} – {station.station_name}
                </h2>
                <p className="text-muted">
                    Detailed analysis and statistics
                </p>
            </div>

            <FilterBar
                dateRange={dateRange}
                onDateRangeChange={setDateRange}
            />

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
                        className={`nav-link ${
                            activeTab === 'overview'
                                ? 'active'
                                : ''
                        }`}
                        onClick={() => setActiveTab('overview')}
                    >
                        Overview
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${
                            activeTab === 'analysis'
                                ? 'active'
                                : ''
                        }`}
                        onClick={() => setActiveTab('analysis')}
                    >
                        Loss Analysis
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${
                            activeTab === 'sessions'
                                ? 'active'
                                : ''
                        }`}
                        onClick={() => setActiveTab('sessions')}
                    >
                        Sessions
                    </button>
                </li>
                <li className="nav-item">
                    <button
                        className={`nav-link ${
                            activeTab === 'power-quality'
                                ? 'active'
                                : ''
                        }`}
                        onClick={() =>
                            setActiveTab('power-quality')
                        }
                    >
                        Power Quality
                    </button>
                </li>
            </ul>

            {activeTab === 'overview' && stats && (
                <div className="row g-4">
                    <div className="col-lg-6">
                        <EnergyDistributionChart
                            delivered={Number(stats.totalDelivered)}
                            loss={Number(stats.totalLoss)}
                        />
                    </div>
                    <div className="col-lg-6">
                        <div className="card shadow-sm border-0">
                            <div className="card-header bg-white">
                                <h5 className="mb-0">
                                    Energy Comparison
                                </h5>
                            </div>
                            <div className="card-body">
                                <ResponsiveContainer
                                    width="100%"
                                    height={300}
                                >
                                    <BarChart
                                        data={prepareComparisonChart()}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="date" />
                                        <YAxis />
                                        <Tooltip />
                                        <Legend />
                                        <Bar
                                            dataKey="consumption"
                                            fill="#0d6efd"
                                            name="Consumption"
                                        />
                                        <Bar
                                            dataKey="delivered"
                                            fill="#28a745"
                                            name="Delivered"
                                        />
                                        <Bar
                                            dataKey="loss"
                                            fill="#dc3545"
                                            name="Loss"
                                        />
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

                        <div className="card shadow-sm border-0 mt-4">
                            <div className="card-body">
                                <div className="table-responsive">
                                    <table className="table table-hover">
                                        <thead>
                                        <tr>
                                            <th>Start Date</th>
                                            <th>End Date</th>
                                            <th>Energy (kWh)</th>
                                        </tr>
                                        </thead>
                                        <tbody>
                                        {sessionsData
                                            .slice(0, 10)
                                            .map((s, i) => (
                                                <tr key={i}>
                                                    <td>
                                                        {new Date(
                                                            s.start_date
                                                        ).toLocaleString()}
                                                    </td>
                                                    <td>
                                                        {new Date(
                                                            s.end_date
                                                        ).toLocaleString()}
                                                    </td>
                                                    <td>
                                                        {Number(
                                                            s.total_kwh
                                                        ).toFixed(2)}
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

            {activeTab === 'power-quality' && (
                <div className="row g-4">
                    <div className="col-12">
                        <PowerFactorTrendChart data={lossData} />
                    </div>
                </div>
            )}
        </div>
    );
};

export default StationDetail;
