USE charging_station_db;

-- Table: stations
CREATE TABLE IF NOT EXISTS stations (
id INT AUTO_INCREMENT PRIMARY KEY,
station_code VARCHAR(50) UNIQUE NOT NULL,
station_name VARCHAR(100) NOT NULL,
location VARCHAR(100) DEFAULT 'Jeníšov',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: power_consumption
CREATE TABLE IF NOT EXISTS power_consumption (
 id INT AUTO_INCREMENT PRIMARY KEY,
 timestamp DATETIME NOT NULL,
 station_id INT NOT NULL,
 active_power_kwh DECIMAL(10, 3) NOT NULL,
reactive_power_kwh DECIMAL(10, 3) NOT NULL,
FOREIGN KEY (station_id) REFERENCES stations(id),
INDEX idx_timestamp (timestamp),
INDEX idx_station_time (station_id, timestamp)
);

-- Table: charging_sessions
CREATE TABLE IF NOT EXISTS charging_sessions (
 id INT AUTO_INCREMENT PRIMARY KEY,
 station_id INT NOT NULL,
 charger_name VARCHAR(100) NOT NULL,
start_date DATETIME NOT NULL,
end_date DATETIME,
total_kwh DECIMAL(10, 3) NOT NULL,
start_card VARCHAR(50),
end_interval_15min DATETIME NOT NULL,
FOREIGN KEY (station_id) REFERENCES stations(id),
INDEX idx_end_interval (end_interval_15min),
INDEX idx_station_interval (station_id, end_interval_15min)
);

CREATE TABLE IF NOT EXISTS loss_analysis (
id INT AUTO_INCREMENT PRIMARY KEY,
station_id INT NOT NULL,
period_start DATE NOT NULL,
period_end DATE NOT NULL,
total_consumption_kwh DECIMAL(12, 3) NOT NULL,
total_delivered_kwh DECIMAL(12, 3) NOT NULL,
loss_kwh DECIMAL(12, 3) NOT NULL,
loss_percentage DECIMAL(5, 2) NOT NULL,
calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (station_id) REFERENCES stations(id),
UNIQUE KEY unique_station_period (station_id, period_start, period_end),
INDEX idx_period (period_start, period_end)
);
ALTER TABLE loss_analysis MODIFY loss_percentage DECIMAL(10, 2);
