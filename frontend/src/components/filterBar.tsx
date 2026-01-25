import React from 'react';
import type { DateRange } from '../types';

interface FilterBarProps {
    dateRange: DateRange;
    onDateRangeChange: (dateRange: DateRange) => void;
    showStationSelect?: boolean;
    stations?: Array<{ id: number; station_code: string; station_name: string }>;
    selectedStation?: number | null;
    onStationChange?: (stationId: number) => void;
}

const FilterBar: React.FC<FilterBarProps> = ({
                                                 dateRange,
                                                 onDateRangeChange,
                                                 showStationSelect = false,
                                                 stations = [],
                                                 selectedStation,
                                                 onStationChange,
                                             }) => {
    return (
        <div className="card shadow-sm border-0 rounded-4 mb-4">
            <div className="card-body p-3">
                <div className="row g-3 align-items-center">
                    {/* Sekce s ikonou filtru */}
                    <div className="col-auto d-none d-md-block border-end pe-3">
                        <div className="text-primary d-flex align-items-center gap-2">
                            <i className="bi bi-funnel-fill fs-5"></i>
                            <span className="fw-bold">Filters</span>
                        </div>
                    </div>

                    {showStationSelect && stations.length > 0 && (
                        <div className="col-md-3">
                            <select
                                value={selectedStation || ''}
                                onChange={(e) => onStationChange?.(parseInt(e.target.value))}
                                className="form-select border-0 bg-light fw-medium"
                                style={{ padding: '0.6rem 1rem' }}
                            >
                                <option value="" disabled>Select Station...</option>
                                {stations.map((station) => (
                                    <option key={station.id} value={station.id}>
                                        {station.station_name} ({station.station_code})
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div className="col">
                        <div className="input-group">
                            <span className="input-group-text bg-light border-0 text-muted ps-3">
                                <i className="bi bi-calendar3"></i>
                            </span>
                            <input
                                type="date"
                                className="form-control border-0 bg-light"
                                placeholder="Start Date"
                                value={dateRange.start}
                                onChange={(e) => onDateRangeChange({ ...dateRange, start: e.target.value })}
                            />
                            <span className="input-group-text bg-light border-0 text-muted">to</span>
                            <input
                                type="date"
                                className="form-control border-0 bg-light"
                                placeholder="End Date"
                                value={dateRange.end}
                                onChange={(e) => onDateRangeChange({ ...dateRange, end: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="col-auto ps-md-3 border-start">
                        <button
                            className="btn btn-link text-decoration-none text-muted p-0"
                            onClick={() => onDateRangeChange({ start: '', end: '' })}
                            title="Reset filters"
                        >
                            <i className="bi bi-arrow-counterclockwise fs-5"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;