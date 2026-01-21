import React, { useEffect, useState } from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { api } from '../../services/api';

type TrendPoint = { date: string; powerFactor: number };

interface Props {
    stationId: number;
    startDate?: string;
    endDate?: string;
}

const PowerFactorTrendAreaChart: React.FC<Props> = ({ stationId, startDate, endDate }) => {
    const [data, setData] = useState<TrendPoint[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const run = async () => {
            setLoading(true);
            try {
                const trend = await api.getPowerFactorTrend(stationId, 'active', startDate, endDate, 0.05);
                setData((trend || []).map((p) => ({
                    date: p.date,
                    powerFactor: Number(p.powerFactor),
                })));
            } catch (e) {
                console.error('PF trend load error', e);
                setData([]);
            } finally {
                setLoading(false);
            }
        };
        run();
    }, [stationId, startDate, endDate]);

    if (loading) {
        return (
            <div className="card shadow-sm border-0">
                <div className="card-header bg-white">
                    <h5 className="mb-0">Power Factor Trend</h5>
                </div>
                <div className="card-body text-muted">Loading...</div>
            </div>
        );
    }

    return (
        <div className="card shadow-sm border-0">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                    <i className="bi bi-graph-up me-2 text-primary"></i>
                    Power Factor Trend (active)
                </h5>
                <span className="badge bg-light text-dark border">Target: &gt;90 %</span>
            </div>

            <div className="card-body">
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 100]} label={{ value: 'PF %', angle: -90, position: 'insideLeft' }} />
                        <Tooltip formatter={(v: number) => [`${v}%`, 'Power Factor']} />
                        <Legend />
                        <Area type="monotone" dataKey="powerFactor" name="Power Factor (%)" fillOpacity={0.25} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default PowerFactorTrendAreaChart;
