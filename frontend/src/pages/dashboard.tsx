import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Station, LossData, DateRange } from '../types';

type PFRow = {
    station_id: number;
    station_code: string;
    station_name: string;
    total_active: number;
    total_reactive: number;
    power_factor: number;
};

const Dashboard: React.FC = () => {
    const navigate = useNavigate();

    const [stations, setStations] = useState<Station[]>([]);
    const [allLossData, setAllLossData] = useState<LossData[]>([]);
    const [loading, setLoading] = useState(true);
    const [dateRange, setDateRange] = useState<DateRange>({ start: '', end: '' });
    const [pfByStation, setPfByStation] = useState<Record<number, PFRow>>({});
    const [overallPf, setOverallPf] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [sortBy, setSortBy] = useState<'name' | 'loss' | 'efficiency'>('name');

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [dateRange]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [stationsData, lossData, pfRows] = await Promise.all([
                api.getStations(),
                api.getLosses(undefined, dateRange.start, dateRange.end),
                api.getPowerFactorByStation('all', dateRange.start, dateRange.end, 0.05),
            ]);

            setStations(stationsData);
            setAllLossData(lossData);

            const map: Record<number, PFRow> = {};
            (pfRows || []).forEach((r: any) => {
                const row: PFRow = {
                    station_id: Number(r.station_id),
                    station_code: String(r.station_code ?? ''),
                    station_name: String(r.station_name ?? ''),
                    total_active: Number(r.total_active ?? 0),
                    total_reactive: Number(r.total_reactive ?? 0),
                    power_factor: Number(r.power_factor ?? 0),
                };
                map[row.station_id] = row;
            });
            setPfByStation(map);

            let totalA = 0;
            let totalR = 0;
            (pfRows || []).forEach((r: any) => {
                totalA += Number(r.total_active ?? 0);
                totalR += Number(r.total_reactive ?? 0);
            });
            if (totalA === 0 && totalR === 0) {
                setOverallPf(null);
            } else {
                const apparent = Math.sqrt(totalA * totalA + totalR * totalR);
                setOverallPf(apparent > 0 ? (totalA / apparent) * 100 : null);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            setStations([]);
            setAllLossData([]);
            setPfByStation({});
            setOverallPf(null);
        } finally {
            setLoading(false);
        }
    };

    const calculateOverallStats = () => {
        if (allLossData.length === 0) return null;

        const totalConsumption = allLossData.reduce((sum, item) => sum + Number(item.total_consumption_kwh ?? 0), 0);
        const totalDelivered = allLossData.reduce((sum, item) => sum + Number(item.total_delivered_kwh ?? 0), 0);
        const totalLoss = allLossData.reduce((sum, item) => sum + Number(item.loss_kwh ?? 0), 0);
        const lossPercentage = totalConsumption > 0 ? (totalLoss / totalConsumption) * 100 : 0;

        return {
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: lossPercentage.toFixed(2),
            efficiency: totalConsumption > 0 ? ((totalDelivered / totalConsumption) * 100).toFixed(2) : '0.00',
        };
    };

    const getStationStats = (stationId: number) => {
        const stationLossData = allLossData.filter((item) => item.station_id === stationId);
        if (stationLossData.length === 0) return null;

        const totalConsumption = stationLossData.reduce((sum, item) => sum + Number(item.total_consumption_kwh ?? 0), 0);
        const totalDelivered = stationLossData.reduce((sum, item) => sum + Number(item.total_delivered_kwh ?? 0), 0);
        const totalLoss = stationLossData.reduce((sum, item) => sum + Number(item.loss_kwh ?? 0), 0);
        const lossPercentage = totalConsumption > 0 ? (totalLoss / totalConsumption) * 100 : 0;
        const efficiency = totalConsumption > 0 ? (totalDelivered / totalConsumption) * 100 : 0;

        return {
            totalConsumption: totalConsumption.toFixed(2),
            totalDelivered: totalDelivered.toFixed(2),
            totalLoss: totalLoss.toFixed(2),
            avgLossPercentage: lossPercentage.toFixed(2),
            efficiency: efficiency.toFixed(2),
        };
    };

    const sortedStations = useMemo(() => {
        const sorted = [...stations];
        if (sortBy === 'name') {
            sorted.sort((a, b) => a.station_code.localeCompare(b.station_code));
        } else if (sortBy === 'loss') {
            sorted.sort((a, b) => {
                const lossA = Number(getStationStats(a.id)?.totalLoss ?? 0);
                const lossB = Number(getStationStats(b.id)?.totalLoss ?? 0);
                return lossB - lossA;
            });
        } else if (sortBy === 'efficiency') {
            sorted.sort((a, b) => {
                const effA = Number(getStationStats(a.id)?.efficiency ?? 0);
                const effB = Number(getStationStats(b.id)?.efficiency ?? 0);
                return effB - effA;
            });
        }
        return sorted;
    }, [stations, sortBy, allLossData]);

    const overallStats = useMemo(() => calculateOverallStats(), [allLossData]);

    const pfBadge = (pf: number) => {
        const status = pf >= 95 ? 'excellent' : pf >= 85 ? 'good' : 'poor';
        const color = pf >= 95 ? 'success' : pf >= 85 ? 'warning' : 'danger';
        return { status, color };
    };

    if (loading) {
        return (
            <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#f8f9fa' }}>
                <div className="text-center">
                    <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}>
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-3 text-muted">Loading dashboard...</p>
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
                        <div className="col-md-6">
                            <h2 className="mb-1 fw-bold">
                                <i className="bi bi-grid-3x3-gap me-2 text-primary"></i>
                                Overview Dashboard
                            </h2>
                            <p className="text-muted mb-0 small">
                                <i className="bi bi-geo-alt me-1"></i>
                                Charging Station Location
                            </p>
                        </div>
                        <div className="col-md-6 text-md-end mt-3 mt-md-0">
                            <div className="btn-group btn-group-sm me-2">
                                <button
                                    className={`btn ${viewMode === 'grid' ? 'btn-primary' : 'btn-outline-primary'}`}
                                    onClick={() => setViewMode('grid')}
                                    title="Grid View"
                                >
                                    <i className="bi bi-grid-3x3 me-1"></i>Grid
                                </button>
                                <button
                                    className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-outline-primary'}`}
                                    onClick={() => setViewMode('list')}
                                    title="List View"
                                >
                                    <i className="bi bi-list-ul me-1"></i>List
                                </button>
                            </div>

                            <select
                                className="form-select form-select-sm d-inline-block w-auto"
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value as any)}
                            >
                                <option value="name">Sort by Name</option>
                                <option value="loss">Sort by Loss</option>
                                <option value="efficiency">Sort by Efficiency</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container-fluid px-4 py-4">
                {/* Date Filter */}
                <div className="card shadow-sm mb-4 border-0">
                    <div className="card-body">
                        <div className="row align-items-end">
                            <div className="col-md-3">
                                <label className="form-label small fw-semibold mb-1">
                                    <i className="bi bi-calendar-range me-1"></i>Start Date
                                </label>
                                <input
                                    type="date"
                                    value={dateRange.start}
                                    onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                                    className="form-control form-control-sm"
                                />
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small fw-semibold mb-1">
                                    <i className="bi bi-calendar-range me-1"></i>End Date
                                </label>
                                <input
                                    type="date"
                                    value={dateRange.end}
                                    onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                                    className="form-control form-control-sm"
                                />
                            </div>
                            <div className="col-md-2">
                                <button
                                    className="btn btn-sm btn-outline-secondary w-100"
                                    onClick={() => setDateRange({ start: '', end: '' })}
                                >
                                    <i className="bi bi-arrow-clockwise me-1"></i>Reset
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Overall Statistics */}
                {overallStats && (
                    <>
                        <div className="d-flex justify-content-between align-items-center mb-3">
                            <h4 className="mb-0">
                                <i className="bi bi-bar-chart-line me-2"></i>
                                Overall Statistics
                            </h4>
                        </div>

                        <div className="row g-3 mb-4">
                            <div className="col-lg-3 col-md-6">
                                <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #0d6efd' }}>
                                    <div className="card-body">
                                        <div className="d-flex justify-content-between align-items-start">
                                            <div>
                                                <small className="text-muted d-block mb-1">Total Consumption</small>
                                                <h3 className="mb-0 text-primary">{overallStats.totalConsumption}</h3>
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
                                                <h3 className="mb-0 text-success">{overallStats.totalDelivered}</h3>
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
                                                <h3 className="mb-0 text-danger">{overallStats.totalLoss}</h3>
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
                                                <h3 className="mb-0 text-warning">{overallStats.avgLossPercentage}%</h3>
                                                <small className="text-muted">of total</small>
                                            </div>
                                            <div className="bg-warning bg-opacity-10 p-3 rounded">
                                                <i className="bi bi-graph-down text-warning" style={{ fontSize: '1.5rem' }}></i>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {overallPf !== null && (
                                <div className="col-lg-3 col-md-6">
                                    <div className="card shadow-sm border-0 h-100" style={{ borderLeft: '4px solid #20c997' }}>
                                        <div className="card-body">
                                            <div className="d-flex justify-content-between align-items-start">
                                                <div>
                                                    <small className="text-muted d-block mb-1">Power Factor</small>
                                                    <h3 className={`mb-0 text-${pfBadge(overallPf).color}`}>{overallPf.toFixed(1)}%</h3>
                                                    <small className="text-muted">overall</small>
                                                </div>
                                                <div className={`bg-${pfBadge(overallPf).color} bg-opacity-10 p-3 rounded`}>
                                                    <i className={`bi bi-lightning-charge text-${pfBadge(overallPf).color}`} style={{ fontSize: '1.5rem' }}></i>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {/* Individual Stations */}
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h4 className="mb-0">
                        <i className="bi bi-ev-station me-2"></i>
                        Individual Stations
                    </h4>
                    <small className="text-muted">{stations.length} stations</small>
                </div>

                {viewMode === 'grid' ? (
                    <div className="row g-3">
                        {sortedStations.map(station => {
                            const stats = getStationStats(station.id);
                            const pfRow = pfByStation[station.id];
                            const pf = pfRow ? pfRow.power_factor : null;

                            return (
                                <div key={station.id} className="col-lg-4 col-md-6">
                                    <div
                                        className="card shadow-sm border-0 h-100"
                                        style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                                        onClick={() => navigate(`/station/${station.id}`)}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-4px)';
                                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.boxShadow = '';
                                        }}
                                    >
                                        <div className="card-header text-white" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                                            <div className="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <h6 className="mb-0">
                                                        <i className="bi bi-ev-station-fill me-2"></i>
                                                        {station.station_code}
                                                    </h6>
                                                    <small className="opacity-75">{station.station_name}</small>
                                                </div>
                                                <i className="bi bi-arrow-right-circle" style={{ fontSize: '1.5rem' }}></i>
                                            </div>
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

                                                    <div className="row g-2 mb-3">
                                                        <div className="col-6">
                                                            <div className="text-center p-2 bg-light rounded">
                                                                <small className="text-muted d-block">Loss</small>
                                                                <strong className="text-danger">{stats.totalLoss} kWh</strong>
                                                            </div>
                                                        </div>
                                                        <div className="col-6">
                                                            <div className="text-center p-2 bg-light rounded">
                                                                <small className="text-muted d-block">Loss %</small>
                                                                <strong className="text-warning">{stats.avgLossPercentage}%</strong>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {pf !== null && !Number.isNaN(pf) && (
                                                        <div className="mb-3">
                                                            <small className="text-muted d-block mb-1">
                                                                <i className="bi bi-lightning-charge me-1"></i>Power Factor
                                                            </small>
                                                            <div className="progress" style={{ height: '24px' }}>
                                                                <div
                                                                    className={`progress-bar bg-${pfBadge(pf).color}`}
                                                                    style={{ width: `${pf}%` }}
                                                                >
                                                                    {pf.toFixed(1)}%
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div className="progress" style={{ height: '8px' }}>
                                                        <div
                                                            className="progress-bar bg-success"
                                                            style={{ width: `${stats.efficiency}%` }}
                                                            title={`Efficiency: ${stats.efficiency}%`}
                                                        ></div>
                                                    </div>
                                                    <small className="text-muted">Efficiency: {stats.efficiency}%</small>
                                                </>
                                            ) : (
                                                <p className="text-muted text-center mb-0">No data available</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="card shadow-sm border-0">
                        <div className="table-responsive">
                            <table className="table table-hover mb-0 align-middle">
                                <thead style={{ backgroundColor: '#f8f9fa' }}>
                                <tr>
                                    <th className="fw-semibold">Station</th>
                                    <th className="text-end fw-semibold">Consumption</th>
                                    <th className="text-end fw-semibold">Delivered</th>
                                    <th className="text-end fw-semibold">Loss</th>
                                    <th className="text-end fw-semibold">Loss %</th>
                                    <th className="text-end fw-semibold">Efficiency</th>
                                    <th className="text-end fw-semibold">Power Factor</th>
                                    <th></th>
                                </tr>
                                </thead>
                                <tbody>
                                {sortedStations.map(station => {
                                    const stats = getStationStats(station.id);
                                    const pfRow = pfByStation[station.id];
                                    const pf = pfRow ? pfRow.power_factor : null;

                                    return (
                                        <tr
                                            key={station.id}
                                            style={{ cursor: 'pointer' }}
                                            onClick={() => navigate(`/station/${station.id}`)}
                                        >
                                            <td>
                                                <div className="d-flex align-items-center">
                                                    <div className="bg-primary bg-opacity-10 p-2 rounded me-2">
                                                        <i className="bi bi-ev-station-fill text-primary"></i>
                                                    </div>
                                                    <div>
                                                        <div className="fw-semibold">{station.station_code}</div>
                                                        <small className="text-muted">{station.station_name}</small>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="text-end">{stats?.totalConsumption || '-'} kWh</td>
                                            <td className="text-end">{stats?.totalDelivered || '-'} kWh</td>
                                            <td className="text-end">
                                                <span className="badge bg-danger">{stats?.totalLoss || '-'} kWh</span>
                                            </td>
                                            <td className="text-end">
                                                <span className="badge bg-warning text-dark">{stats?.avgLossPercentage || '-'}%</span>
                                            </td>
                                            <td className="text-end">{stats?.efficiency || '-'}%</td>
                                            <td className="text-end">
                                                {pf && (
                                                    <span className={`badge bg-${pfBadge(pf).color}`}>
                                                            {pf.toFixed(1)}%
                                                        </span>
                                                )}
                                            </td>
                                            <td className="text-end">
                                                <i className="bi bi-chevron-right text-muted"></i>
                                            </td>
                                        </tr>
                                    );
                                })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {stations.length === 0 && (
                    <div className="alert alert-info mt-3">
                        <i className="bi bi-info-circle me-2"></i>
                        No stations found. Please check your database connection.
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;