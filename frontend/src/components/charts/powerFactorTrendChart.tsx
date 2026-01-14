import React from 'react';
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
import type { LossData } from '../../types';

interface PowerFactorTrendAreaChartProps {
    data: LossData[];
}

const PowerFactorTrendAreaChart: React.FC<PowerFactorTrendAreaChartProps> = ({ data }) => {
    const chartData = [...data]
        .sort(
            (a, b) =>
                new Date(a.period_start).getTime() -
                new Date(b.period_start).getTime()
        )
        .map(item => {
            const active = Number(item.total_consumption_kwh);
            const reactive = Number(item.total_reactive_kwh ?? 0);
            const apparent = Math.sqrt(active ** 2 + reactive ** 2);
            const pf = apparent > 0 ? (active / apparent) * 100 : 0;

            return {
                date: new Date(item.period_start).toLocaleDateString(),
                powerFactor: Number(pf.toFixed(1)),
            };
        });

    return (
        <div className="card shadow-sm border-0">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                    <i className="bi bi-graph-up me-2 text-primary"></i>
                    Power Factor Trend
                </h5>
                <span className="badge bg-light text-dark border">
                    Target: &gt;90 %
                </span>
            </div>

            <div className="card-body">
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis
                            domain={[80, 100]}
                            label={{
                                value: 'PF %',
                                angle: -90,
                                position: 'insideLeft',
                            }}
                        />
                        <Tooltip
                            formatter={(v: number) => [`${v}%`, 'Power Factor']}
                        />
                        <Legend />
                        <Area
                            type="monotone"
                            dataKey="powerFactor"
                            name="Power Factor (%)"
                            stroke="#0d6efd"
                            fill="#0d6efd"
                            fillOpacity={0.25}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default PowerFactorTrendAreaChart;
