import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Station, LossData, SessionData, DateRange, StationStats } from '../types';
import EnergyDistributionChart from '../components/charts/energyDistributionChart';
import LossTrendChart from '../components/charts/lossTrendChart';
import SessionsChart from '../components/charts/sessionChart';
import PowerFactorTrendChart from '../components/charts/powerFactorTrendChart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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
        if (stationId) fetchStationData();
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
        const totalConsumption = lossData.reduce((sum, item) => sum + Number(item.total_consumption_kwh), 0);
        const totalDelivered = lossData.reduce((sum, item) => sum + Number(item.total_delivered_kwh), 0);
        const totalLoss = lossData.reduce((sum, item) => sum + Number(item.loss_kwh), 0);
        const lossPercentage = totalConsumption > 0 ? (totalLoss / totalConsumption) * 100 : 0;
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
            date: new Date(item.period_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            consumption: Number(item.total_consumption_kwh),
            delivered: Number(item.total_delivered_kwh),
            loss: Number(item.loss_kwh),
        }));
    };

    const stats = calculateStats();

    if (loading) {
        return (
            <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#f8f9fa' }}>
                <div className="text-center">
                    <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}>
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-3 text-muted">Loading station details...</p>
                </div>
            </div>
        );
    }

    if (!station) {
        return (
            <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#f8f9fa' }}>
                <div className="text-center">
                    <i className="bi bi-exclamation-circle text-danger" style={{ fontSize: '4rem' }}></i>
                    <h3 className="mt-3">Station Not Found</h3>
                    <p className="text-muted">The requested station could not be found.</p>
                    <button className="btn btn-primary mt-3" onClick={() => navigate('/')}>
                        <i className="bi bi-arrow-left me-2"></i>Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
            {/* Sticky Header */}
            <div className="bg-white border-bottom shadow-sm sticky-top">
                <div className="container-fluid px-4 py-3">
                    <div className="row align-items-center">
                        <div className="col-md-8">
                            <nav aria-label="breadcrumb" className="mb-2">
                                <ol className="breadcrumb mb-0 small">
                                    <li className="breadcrumb-item">
                                        <a href="#" onClick={(e) => { e.preventDefault(); navigate('/'); }} className="text-decoration-none">
                                            <i className="bi bi-house-door me-1"></i>Dashboard
                                        </a>
                                    </li>
                                    <li className="breadcrumb-item active">{station.station_code}</li>
                                </ol>
                            </nav>
                            <h2 className="mb-1 fw-bold">
                                <i className="bi bi-ev-station-fill me-2 text-primary"></i>{station.station_code}
                            </h2>
                            <p className="text-muted mb-0 small">
                                <i className="bi bi-geo-alt me-1"></i>{station.station_name}
                            </p>
                        </div>
                        <div className="col-md-4 text-md-end mt-3 mt-md-0">
                            <button className="btn btn-sm btn-outline-primary" onClick={() => navigate('/')}>
                                <i className="bi bi-arrow-left me-1"></i>Back to Overview
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container-fluid px-4 py-4">
                {/* Date Filter */}
                <div className="card shadow-sm mb-4 border-0">
                    <div className="card-body">
                        <div className="row align-items-end">
                            <div className="col-auto">
                                <label className="form-label small fw-semibold mb-1">
                                    <i className="bi bi-funnel me-1 text-primary"></i>Filter Period
                                </label>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Start Date</label>
                                <input type="date" value={dateRange.start} onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })} className="form-control form-control-sm" />
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">End Date</label>
                                <input type="date" value={dateRange.end} onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })} className="form-control form-control-sm" />
                            </div>
                            <div className="col-md-2">
                                <button className="btn btn-sm btn-outline-secondary w-100" onClick={() => setDateRange({ start: '', end: '' })}>
                                    <i className="bi bi-arrow-clockwise me-1"></i>Reset
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Key Metrics */}
                {stats && (
                    <div className="row g-3 mb-4">
                        <div className="col-lg-3 col-md-6">
                            <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #0d6efd' }}>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between align-items-start">
                                        <div>
                                            <small className="text-muted d-block mb-1">Total Consumption</small>
                                            <h3 className="mb-0 text-primary">{stats.totalConsumption}</h3>
                                            <small className="text-muted">kWh</small>
                                        </div>
                                        <div className="bg-primary bg-opacity-10 p-3 rounded">
                                            <i className="bi bi-activity text-primary" style={{ fontSize: '1.5rem' }}></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #28a745' }}>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between align-items-start">
                                        <div>
                                            <small className="text-muted d-block mb-1">Total Delivered</small>
                                            <h3 className="mb-0 text-success">{stats.totalDelivered}</h3>
                                            <small className="text-muted">kWh</small>
                                        </div>
                                        <div className="bg-success bg-opacity-10 p-3 rounded">
                                            <i className="bi bi-lightning-charge text-success" style={{ fontSize: '1.5rem' }}></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #dc3545' }}>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between align-items-start">
                                        <div>
                                            <small className="text-muted d-block mb-1">Total Loss</small>
                                            <h3 className="mb-0 text-danger">{stats.totalLoss}</h3>
                                            <small className="text-muted">kWh</small>
                                        </div>
                                        <div className="bg-danger bg-opacity-10 p-3 rounded">
                                            <i className="bi bi-exclamation-triangle text-danger" style={{ fontSize: '1.5rem' }}></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #ffc107' }}>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between align-items-start">
                                        <div>
                                            <small className="text-muted d-block mb-1">Average Loss</small>
                                            <h3 className="mb-0 text-warning">{stats.avgLossPercentage}%</h3>
                                            <small className="text-muted">of total</small>
                                        </div>
                                        <div className="bg-warning bg-opacity-10 p-3 rounded">
                                            <i className="bi bi-graph-down text-warning" style={{ fontSize: '1.5rem' }}></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Tabs */}
                <div className="card shadow-sm border-0 mb-4">
                    <div className="card-body p-0">
                        <ul className="nav nav-tabs border-0 px-3 pt-3" style={{ borderBottom: '2px solid #f0f0f0' }}>
                            {['overview', 'analysis', 'sessions', 'power-quality'].map(tab => (
                                <li className="nav-item" key={tab}>
                                    <button
                                        className={`nav-link border-0 px-4 py-2 fw-semibold ${activeTab === tab ? 'text-primary' : 'text-muted'}`}
                                        style={{ borderBottom: activeTab === tab ? '3px solid #0d6efd' : '3px solid transparent', marginBottom: '-2px' }}
                                        onClick={() => setActiveTab(tab)}
                                    >
                                        <i className={`bi ${tab === 'overview' ? 'bi-grid-3x3-gap' : tab === 'analysis' ? 'bi-graph-up' : tab === 'sessions' ? 'bi-clock-history' : 'bi-lightning-charge'} me-2`}></i>
                                        {tab === 'power-quality' ? 'Power Quality' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Tab Content - Overview */}
                {activeTab === 'overview' && stats && (
                    <div className="row g-4">
                        <div className="col-lg-6">
                            <EnergyDistributionChart delivered={Number(stats.totalDelivered)} loss={Number(stats.totalLoss)} />
                        </div>
                        <div className="col-lg-6">
                            <div className="card shadow-sm border-0 h-100">
                                <div className="card-header bg-white border-bottom-0">
                                    <h5 className="mb-0"><i className="bi bi-bar-chart me-2"></i>Energy Comparison</h5>
                                </div>
                                <div className="card-body">
                                    <ResponsiveContainer width="100%" height={300}>
                                        <BarChart data={prepareComparisonChart()}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                            <XAxis dataKey="date" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                                            <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                                            <Tooltip contentStyle={{ backgroundColor: 'rgba(255,255,255,0.95)', border: '1px solid #dee2e6', borderRadius: '8px' }} />
                                            <Legend />
                                            <Bar dataKey="consumption" fill="#0d6efd" name="Consumption (kWh)" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="delivered" fill="#28a745" name="Delivered (kWh)" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="loss" fill="#dc3545" name="Loss (kWh)" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>
                        <div className="col-12">
                            <div className="card shadow-sm border-0">
                                <div className="card-body">
                                    <div className="row align-items-center">
                                        <div className="col-md-3">
                                            <h5 className="mb-0"><i className="bi bi-speedometer2 me-2 text-primary"></i>Overall Efficiency</h5>
                                            <small className="text-muted">Energy delivery efficiency</small>
                                        </div>
                                        <div className="col-md-9">
                                            <div className="d-flex align-items-center gap-3">
                                                <div className="progress flex-grow-1" style={{ height: '32px' }}>
                                                    <div className="progress-bar bg-success" style={{ width: `${stats.efficiency}%` }}>
                                                        <span className="fw-bold">{stats.efficiency}%</span>
                                                    </div>
                                                </div>
                                                <div className="text-end">
                                                    <div className="fw-bold text-success" style={{ fontSize: '1.5rem' }}>{stats.efficiency}%</div>
                                                    <small className="text-muted">Target: &gt;95%</small>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Tab Content - Analysis */}
                {activeTab === 'analysis' && (
                    <div className="row g-4">
                        <div className="col-12"><LossTrendChart data={lossData} /></div>
                        <div className="col-12">
                            <div className="card shadow-sm border-0">
                                <div className="card-header bg-white border-bottom">
                                    <h5 className="mb-0"><i className="bi bi-table me-2"></i>Detailed Loss Records</h5>
                                </div>
                                <div className="card-body p-0">
                                    <div className="table-responsive">
                                        <table className="table table-hover mb-0 align-middle">
                                            <thead style={{ backgroundColor: '#f8f9fa' }}>
                                            <tr>
                                                <th className="fw-semibold">Period Start</th>
                                                <th className="text-end fw-semibold">Consumption</th>
                                                <th className="text-end fw-semibold">Delivered</th>
                                                <th className="text-end fw-semibold">Loss</th>
                                                <th className="text-end fw-semibold">Loss %</th>
                                                <th className="text-end fw-semibold">Efficiency</th>
                                            </tr>
                                            </thead>
                                            <tbody>
                                            {lossData.slice(0, 10).map((item, idx) => {
                                                const consumption = Number(item.total_consumption_kwh);
                                                const delivered = Number(item.total_delivered_kwh);
                                                const loss = Number(item.loss_kwh);
                                                const lossPercent = consumption > 0 ? (loss / consumption) * 100 : 0;
                                                const efficiency = consumption > 0 ? (delivered / consumption) * 100 : 0;
                                                return (
                                                    <tr key={idx}>
                                                        <td>{new Date(item.period_start).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                                                        <td className="text-end">{consumption.toFixed(2)} kWh</td>
                                                        <td className="text-end">{delivered.toFixed(2)} kWh</td>
                                                        <td className="text-end"><span className="badge bg-danger rounded-pill">{loss.toFixed(2)} kWh</span></td>
                                                        <td className="text-end"><span className="badge bg-warning text-dark rounded-pill">{lossPercent.toFixed(2)}%</span></td>
                                                        <td className="text-end"><span className={`badge ${efficiency >= 95 ? 'bg-success' : 'bg-secondary'} rounded-pill`}>{efficiency.toFixed(2)}%</span></td>
                                                    </tr>
                                                );
                                            })}
                                            </tbody>
                                        </table>
                                    </div>
                                    {lossData.length > 10 && (
                                        <div className="p-3 text-center border-top">
                                            <small className="text-muted">Showing 10 of {lossData.length} records</small>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Tab Content - Sessions */}
                {activeTab === 'sessions' && (
                    <div className="row g-4">
                        <div className="col-12"><SessionsChart data={sessionsData} /></div>
                        <div className="col-12">
                            <div className="row g-3">
                                <div className="col-md-4">
                                    <div className="card shadow-sm border-0 text-center">
                                        <div className="card-body">
                                            <i className="bi bi-plug text-primary" style={{ fontSize: '2rem' }}></i>
                                            <h3 className="mt-2 mb-1 text-primary">{sessionsData.length}</h3>
                                            <small className="text-muted">Total Sessions</small>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-md-4">
                                    <div className="card shadow-sm border-0 text-center">
                                        <div className="card-body">
                                            <i className="bi bi-lightning-charge text-success" style={{ fontSize: '2rem' }}></i>
                                            <h3 className="mt-2 mb-1 text-success">{sessionsData.reduce((sum, s) => sum + Number(s.total_kwh), 0).toFixed(2)}</h3>
                                            <small className="text-muted">Total Energy (kWh)</small>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-md-4">
                                    <div className="card shadow-sm border-0 text-center">
                                        <div className="card-body">
                                            <i className="bi bi-graph-up text-info" style={{ fontSize: '2rem' }}></i>
                                            <h3 className="mt-2 mb-1 text-info">
                                                {sessionsData.length > 0 ? (sessionsData.reduce((sum, s) => sum + Number(s.total_kwh), 0) / sessionsData.length).toFixed(2) : '0.00'}
                                            </h3>
                                            <small className="text-muted">Avg per Session (kWh)</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-12">
                            <div className="card shadow-sm border-0">
                                <div className="card-header bg-white border-bottom">
                                    <h5 className="mb-0"><i className="bi bi-list-check me-2"></i>Recent Charging Sessions</h5>
                                </div>
                                <div className="card-body p-0">
                                    <div className="table-responsive">
                                        <table className="table table-hover mb-0 align-middle">
                                            <thead style={{ backgroundColor: '#f8f9fa' }}>
                                            <tr>
                                                <th className="fw-semibold">Charger</th>
                                                <th className="fw-semibold">Start Time</th>
                                                <th className="fw-semibold">End Time</th>
                                                <th className="text-end fw-semibold">Energy</th>
                                                <th className="text-end fw-semibold">Duration</th>
                                            </tr>
                                            </thead>
                                            <tbody>
                                            {sessionsData.slice(0, 15).map((session, idx) => {
                                                const startTime = new Date(session.start_date);
                                                const endTime = new Date(session.end_date);
                                                const durationMins = (endTime.getTime() - startTime.getTime()) / (1000 * 60);
                                                const hours = Math.floor(durationMins / 60);
                                                const mins = Math.floor(durationMins % 60);
                                                return (
                                                    <tr key={idx}>
                                                        <td>
                                                            <div className="d-flex align-items-center">
                                                                <div className="bg-primary bg-opacity-10 p-2 rounded me-2">
                                                                    <i className="bi bi-plug text-primary"></i>
                                                                </div>
                                                                <span className="fw-semibold">{session.charger_name}</span>
                                                            </div>
                                                        </td>
                                                        <td><small>{startTime.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {startTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</small></td>
                                                        <td><small>{endTime.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {endTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</small></td>
                                                        <td className="text-end"><span className="badge bg-success rounded-pill">{Number(session.total_kwh).toFixed(2)} kWh</span></td>
                                                        <td className="text-end"><small className="text-muted">{hours}h {mins}m</small></td>
                                                    </tr>
                                                );
                                            })}
                                            </tbody>
                                        </table>
                                    </div>
                                    {sessionsData.length > 15 && (
                                        <div className="p-3 text-center border-top">
                                            <small className="text-muted">Showing 15 of {sessionsData.length} sessions</small>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Tab Content - Power Quality */}
                {activeTab === 'power-quality' && (
                    <div className="row g-4">
                        <div className="col-12">
                            <PowerFactorTrendChart stationId={Number(stationId)} startDate={dateRange.start} endDate={dateRange.end} />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default StationDetail;