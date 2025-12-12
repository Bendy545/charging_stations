import React from 'react';

interface StatCardProps {
    title: string;
    value: string | number;
    unit?: string;
    icon: string;
    color: 'primary' | 'success' | 'danger' | 'warning' | 'info';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, unit, icon, color }) => {
    return (
        <div className="card shadow-sm border-0 h-100">
            <div className="card-body">
                <div className="d-flex justify-content-between align-items-start">
                    <div>
                        <p className="text-muted small mb-1">{title}</p>
                        <h3 className={`mb-0 text-${color}`}>{value}</h3>
                        {unit && <small className="text-muted">{unit}</small>}
                    </div>
                    <div className={`bg-${color} bg-opacity-10 p-3 rounded`}>
                        <i className={`bi ${icon} text-${color}`} style={{ fontSize: '1.5rem' }}></i>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StatCard;