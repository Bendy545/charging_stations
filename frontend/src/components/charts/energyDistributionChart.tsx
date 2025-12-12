import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface EnergyDistributionChartProps {
    delivered: number;
    loss: number;
}

const EnergyDistributionChart: React.FC<EnergyDistributionChartProps> = ({delivered, loss,}) => {
    const data = [
        { name: 'Delivered Energy', value: delivered },
        { name: 'Energy Loss', value: loss },
    ];

    const COLORS = ['#28a745', '#dc3545'];

    return (
        <div className="card shadow-sm border-0">
            <div className="card-header bg-white">
                <h5 className="mb-0">
                    <i className="bi bi-pie-chart me-2"></i>
                    Energy Distribution
                </h5>
            </div>
            <div className="card-body">
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) =>
                                `${name}: ${((percent ?? 0) * 100).toFixed(1)}%`
                            }
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                        >
                            {data.map((entry, index) => (
                                <Cell key={entry.name} fill={COLORS[index]} />
                            ))}
                        </Pie>
                        <Tooltip />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default EnergyDistributionChart;