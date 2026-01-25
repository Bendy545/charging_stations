import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { LossData } from '../../types';

interface LossTrendChartProps {
    data: LossData[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white p-3 shadow rounded-3 border-0">
                <p className="mb-1 fw-bold text-dark">{label}</p>
                <div className="d-flex align-items-center gap-2">
                    <span className="d-inline-block rounded-circle" style={{ width: 8, height: 8, backgroundColor: '#ff7300' }}></span>
                    <span className="text-muted small">Loss:</span>
                    <span className="fw-bold text-danger">{Number(payload[0].value).toFixed(2)}%</span>
                </div>
            </div>
        );
    }
    return null;
};

const LossTrendChart: React.FC<LossTrendChartProps> = ({ data }) => {
    const chartData = data.map((item) => {
        const consumption = Number(item.total_consumption_kwh);
        const loss = Number(item.loss_kwh);
        return {
            date: new Date(item.period_start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            lossPercent: consumption > 0 ? (loss / consumption) * 100 : 0,
        };
    });

    return (
        <div className="card shadow-sm border-0 rounded-4">
            <div className="card-header bg-white border-bottom-0 pt-4 px-4 pb-0">
                <h5 className="mb-0 fw-bold text-dark">
                    Loss Percentage Trend
                </h5>
            </div>
            <div className="card-body px-2 pb-2">
                <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ff7300" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#ff7300" stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                        <XAxis
                            dataKey="date"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#9ca3af', fontSize: 12 }}
                            dy={10}
                        />
                        <YAxis
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#9ca3af', fontSize: 12 }}
                            unit="%"
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#ff7300', strokeWidth: 1, strokeDasharray: '5 5' }} />
                        <Area
                            type="monotone"
                            dataKey="lossPercent"
                            stroke="#ff7300"
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#colorLoss)"
                            activeDot={{ r: 6, strokeWidth: 0, fill: '#ff7300' }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default LossTrendChart;