import React from 'react';
import {LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,} from 'recharts';
import type { SessionData } from '../../types';

interface SessionsChartProps {
    data: SessionData[];
}

const SessionsChart: React.FC<SessionsChartProps> = ({ data }) => {
    const sessionsByDay: { [key: string]: { date: string; sessions: number; totalKwh: number } } = {};

    data.forEach((session) => {
        const date = new Date(session.end_date).toLocaleDateString();
        if (!sessionsByDay[date]) {
            sessionsByDay[date] = { date, sessions: 0, totalKwh: 0 };
        }
        sessionsByDay[date].sessions += 1;
        sessionsByDay[date].totalKwh += parseFloat(session.total_kwh.toString());
    });

    const chartData = Object.values(sessionsByDay);

    return (
        <div className="card shadow-sm border-0">
            <div className="card-header bg-white">
                <h5 className="mb-0">
                    <i className="bi bi-clock-history me-2"></i>
                    Charging Sessions Activity
                </h5>
            </div>
            <div className="card-body">
                <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis yAxisId="left" />
                        <YAxis yAxisId="right" orientation="right" />
                        <Tooltip />
                        <Legend />
                        <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="sessions"
                            stroke="#0d6efd"
                            strokeWidth={2}
                            name="Number of Sessions"
                        />
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="totalKwh"
                            stroke="#28a745"
                            strokeWidth={2}
                            name="Total Energy (kWh)"
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default SessionsChart;