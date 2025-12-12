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

const FilterBar: React.FC<FilterBarProps> = ({dateRange, onDateRangeChange, showStationSelect = false, stations = [], selectedStation, onStationChange,}) => {
    return (
        <div className="card shadow-sm mb-4">
            <div className="card-header bg-white">
                <h5 className="mb-0">
                    <i className="bi bi-funnel me-2"></i>
                    Filters
                </h5>
            </div>
            <div className="card-body">
                <div className="row g-3">
                    {showStationSelect && stations.length > 0 && (
                        <div className="col-md-4">
                            <label className="form-label fw-semibold">Select Station</label>
                            <select
                                value={selectedStation || ''}
                                onChange={(e) => onStationChange?.(parseInt(e.target.value))}
                                className="form-select"
                            >
                                {stations.map((station) => (
                                    <option key={station.id} value={station.id}>
                                        {station.station_code} - {station.station_name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    <div className={showStationSelect ? 'col-md-3' : 'col-md-5'}>
                        <label className="form-label fw-semibold">Start Date</label>
                        <input
                            type="date"
                            value={dateRange.start}
                            onChange={(e) =>
                                onDateRangeChange({ ...dateRange, start: e.target.value })
                            }
                            className="form-control"
                        />
                    </div>
                    <div className={showStationSelect ? 'col-md-3' : 'col-md-5'}>
                        <label className="form-label fw-semibold">End Date</label>
                        <input
                            type="date"
                            value={dateRange.end}
                            onChange={(e) =>
                                onDateRangeChange({ ...dateRange, end: e.target.value })
                            }
                            className="form-control"
                        />
                    </div>
                    <div className="col-md-2 d-flex align-items-end">
                        <button
                            className="btn btn-outline-secondary w-100"
                            onClick={() => onDateRangeChange({ start: '', end: '' })}
                        >
                            <i className="bi bi-arrow-clockwise me-1"></i>
                            Reset
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;