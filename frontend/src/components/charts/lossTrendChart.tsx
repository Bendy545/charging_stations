import React from 'react';
import {AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,} from 'recharts';
import type { LossData } from '../../types';

interface LossTrendChartProps {
    data: LossData[];
}

const LossTrendChart: React.FC<LossTrendChartProps> = ({ data }) => {
    const chartData = data.map((item) => ({
        date: new Date(item.period_start).toLocaleDateString(),
        lossPercent: parseFloat(item.loss_percentage.toString()).toFixed(2),
    }));

    return (
        <div className="card shadow-sm border-0">
            <div className="card-header bg-white">
                <h5 className="mb-0">
                    <i className="bi bi-graph-up-arrow me-2"></i>
                    Loss Percentage Trend
                </h5>
            </div>
            <div className="card-body">
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Area
                            type="monotone"
                            dataKey="lossPercent"
                            stroke="#ff7300"
                            fill="#ff7300"
                            fillOpacity={0.3}
                            name="Loss %"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default LossTrendChart;