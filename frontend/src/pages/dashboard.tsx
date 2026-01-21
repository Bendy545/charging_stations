import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Station, LossData, DateRange } from '../types';
import FilterBar from '../components/filterBar';
import StatCard from '../components/statCard';

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

    // PF data from API
    const [pfByStation, setPfByStation] = useState<Record<number, PFRow>>({});
    const [overallPf, setOverallPf] = useState<number | null>(null);

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
                api.getPowerFactorByStation('active', dateRange.start, dateRange.end, 0.05), // <- ACTIVE mode (like "old" project)
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

            // Weighted overall PF from totals (better than averaging %)
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

        const totalConsumption = allLossData.reduce(
            (sum, item) => sum + Number(item.total_consumption_kwh ?? 0),
            0
        );
        const totalDelivered = allLossData.reduce(
            (sum, item) => sum + Number(item.total_delivered_kwh ?? 0),
            0
        );
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

    const overallStats = useMemo(() => calculateOverallStats(), [allLossData]);

    const pfBadge = (pf: number) => {
        const status = pf >= 95 ? 'excellent' : pf >= 85 ? 'good' : 'poor';
        const color = pf >= 95 ? 'success' : pf >= 85 ? 'warning' : 'danger';
        return { status, color };
    };

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

                    <div className="row g-4 mb-5 shadow mt-3 pb-3 bg-color-grey">
                        <div className="col-lg-3 col-md-6">
                            <StatCard title="Total Consumption" value={overallStats.totalConsumption} unit="kWh" icon="bi-activity" color="primary" />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard title="Total Delivered" value={overallStats.totalDelivered} unit="kWh" icon="bi-lightning-charge" color="success" />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard title="Total Loss" value={overallStats.totalLoss} unit="kWh" icon="bi-exclamation-triangle" color="danger" />
                        </div>
                        <div className="col-lg-3 col-md-6">
                            <StatCard title="Average Loss" value={`${overallStats.avgLossPercentage}%`} icon="bi-graph-down" color="warning" />
                        </div>

                        {overallPf !== null && (
                            <div className="col-lg-3 col-md-6">
                                <StatCard
                                    title="Power Factor"
                                    value={`${overallPf.toFixed(1)}%`}
                                    icon="bi-lightning-charge"
                                    color={pfBadge(overallPf).color as any}
                                />
                            </div>
                        )}
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
                    const pfRow = pfByStation[station.id];
                    const pf = pfRow ? pfRow.power_factor : null;

                    return (
                        <div key={station.id} className="col-lg-6 col-xl-4">
                            <div
                                className="card shadow-sm border-0 h-100 station-card"
                                style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                                onClick={() => navigate(`/station/${station.id}`)}
                                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-5px)')}
                                onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
                            >
                                <div className="card-header card-orange text-white">
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

                                            {pf !== null && !Number.isNaN(pf) ? (
                                                (() => {
                                                    const badge = pfBadge(pf);
                                                    return (
                                                        <div className="mb-3 mt-3">
                                                            <div className={`p-3 rounded border border-${badge.color}`}>
                                                                <div className="d-flex justify-content-between align-items-center mb-2">
                                                                    <small className="text-muted">
                                                                        <i className="bi bi-lightning-charge me-1"></i>
                                                                        Power Factor (active)
                                                                    </small>
                                                                    <span className={`badge bg-${badge.color}`}>
                                    {badge.status === 'excellent' ? 'Excellent' : badge.status === 'good' ? 'Good' : 'Poor'}
                                  </span>
                                                                </div>
                                                                <div className="text-center">
                                                                    <span className={`display-6 fw-bold text-${badge.color}`}>{pf.toFixed(1)}%</span>
                                                                </div>
                                                                <div className="progress mt-2" style={{ height: '8px' }}>
                                                                    <div className={`progress-bar bg-${badge.color}`} style={{ width: `${pf}%` }}></div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    );
                                                })()
                                            ) : null}

                                            <div className="mt-3">
                                                <div className="progress" style={{ height: '25px' }}>
                                                    <div className="progress-bar bg-success" role="progressbar" style={{ width: `${stats.efficiency}%` }}>
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
