from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from backend.src.repositories.base import BaseRepository
from backend.src.models.loss_analysis import LossAnalysis
import logging

logger = logging.getLogger(__name__)

class LossRepository(BaseRepository):
    """Repository for loss analysis and complex energy distribution calculations"""

    # Date range where you have session data
    SESSION_DATA_START = datetime(2025, 3, 16)
    SESSION_DATA_END = datetime(2025, 11, 30)
    PROBLEMATIC_STATIONS = []

    def _round_to_15min(self, dt: datetime) -> datetime:
        return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)

    def ensure_tables_exist(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS distributed_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                station_id INT NOT NULL,
                interval_15min DATETIME NOT NULL,
                energy_kwh DECIMAL(10, 3) NOT NULL,
                proportion DECIMAL(5, 4) NOT NULL,
                overlap_minutes DECIMAL(6, 2) NOT NULL,
                FOREIGN KEY (session_id) REFERENCES charging_sessions(id),
                FOREIGN KEY (station_id) REFERENCES stations(id),
                UNIQUE KEY unique_session_interval (session_id, interval_15min),
                INDEX idx_interval (interval_15min),
                INDEX idx_station_interval (station_id, interval_15min)
            )
        """)

    def run_energy_distribution(self):
        """Distribute session energy across 15-minute intervals"""
        self.execute("DELETE FROM distributed_sessions")

        query = """
            SELECT id, station_id, start_date, end_date, total_kwh
            FROM charging_sessions
            WHERE total_kwh > 0
            AND start_date IS NOT NULL
            AND end_date IS NOT NULL
            AND end_date >= %s
            AND start_date <= %s
        """
        sessions = self.fetchall(query, (self.SESSION_DATA_START, self.SESSION_DATA_END))

        logger.info(f"Found {len(sessions)} sessions between {self.SESSION_DATA_START.date()} and {self.SESSION_DATA_END.date()}")

        distributed_records = []
        for session in sessions:
            start = session['start_date']
            end = session['end_date']
            total_kwh = float(session['total_kwh'])
            total_minutes = (end - start).total_seconds() / 60

            if total_minutes <= 0:
                continue

            current_interval = self._round_to_15min(start)
            last_interval = self._round_to_15min(end)

            while current_interval <= last_interval:
                interval_end = current_interval + timedelta(minutes=15)
                overlap_start = max(start, current_interval)
                overlap_end = min(end, interval_end)
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60

                if overlap_minutes > 0:
                    proportion = overlap_minutes / total_minutes
                    distributed_records.append((
                        session['id'], session['station_id'], current_interval,
                        total_kwh * proportion, proportion, overlap_minutes
                    ))
                current_interval = interval_end

        if distributed_records:
            insert_query = """
                INSERT INTO distributed_sessions 
                (session_id, station_id, interval_15min, energy_kwh, proportion, overlap_minutes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.bulk_insert(insert_query, distributed_records)
            logger.info(f"✓ Distributed {len(distributed_records)} interval records")
            return len(distributed_records)

        logger.warning("⚠ No sessions to distribute!")
        return 0

    def calculate_losses_with_distribution(self):
        """
        Calculate losses using LEFT JOIN approach.

        This includes ALL consumption days within the valid date range,
        even if there are no charging sessions. Days with no sessions will
        show 100% loss, which is correct - the station consumed power but
        delivered nothing.
        """
        exclusion_list = ','.join(map(str, self.PROBLEMATIC_STATIONS)) if self.PROBLEMATIC_STATIONS else '0'

        logger.info("="*60)
        logger.info("CALCULATING LOSSES")
        logger.info(f"Date range: {self.SESSION_DATA_START.date()} to {self.SESSION_DATA_END.date()}")
        logger.info(f"Excluding stations: {self.PROBLEMATIC_STATIONS}")
        logger.info("="*60)

        query = f"""
            INSERT INTO loss_analysis 
            (station_id, period_start, period_end, 
             total_consumption_kwh, total_delivered_kwh, total_reactive_kwh,
             loss_kwh, loss_percentage)
            WITH daily_consumption AS (
                SELECT 
                    station_id, 
                    DATE(timestamp) as calc_date,
                    SUM(ABS(active_power_kwh)) as total_cons,
                    SUM(ABS(reactive_power_kwh)) as total_react,
                    COUNT(*) as interval_count
                FROM power_consumption
                WHERE DATE(timestamp) >= %s 
                AND DATE(timestamp) <= %s
                AND station_id NOT IN ({exclusion_list})
                GROUP BY station_id, DATE(timestamp)
            ),
            daily_delivered AS (
                SELECT 
                    station_id, 
                    DATE(interval_15min) as calc_date,
                    SUM(energy_kwh) as total_deliv,
                    COUNT(DISTINCT session_id) as session_count
                FROM distributed_sessions
                WHERE station_id NOT IN ({exclusion_list})
                GROUP BY station_id, DATE(interval_15min)
            )
            SELECT 
                c.station_id, 
                c.calc_date, 
                c.calc_date,
                c.total_cons, 
                COALESCE(d.total_deliv, 0) as delivered,
                c.total_react,
                (c.total_cons - COALESCE(d.total_deliv, 0)) as loss_kwh,
                ((c.total_cons - COALESCE(d.total_deliv, 0)) / NULLIF(c.total_cons, 0)) * 100 as loss_pct
            FROM daily_consumption c
            LEFT JOIN daily_delivered d 
                ON c.station_id = d.station_id 
                AND c.calc_date = d.calc_date
            WHERE c.total_cons > 0
            ON DUPLICATE KEY UPDATE
                total_consumption_kwh = VALUES(total_consumption_kwh),
                total_delivered_kwh = VALUES(total_delivered_kwh),
                total_reactive_kwh = VALUES(total_reactive_kwh),
                loss_kwh = VALUES(loss_kwh),
                loss_percentage = VALUES(loss_percentage)
        """

        start_date = self.SESSION_DATA_START.date()
        end_date = self.SESSION_DATA_END.date()

        rows_affected = self.execute(query, (start_date, end_date))

        logger.info(f"✓ Calculated losses for {rows_affected} daily records")

        # Get summary statistics
        summary_query = f"""
            SELECT 
                COUNT(*) as total_days,
                COUNT(CASE WHEN total_delivered_kwh = 0 THEN 1 END) as days_no_charging,
                AVG(loss_percentage) as avg_loss_pct,
                MIN(loss_percentage) as min_loss_pct,
                MAX(loss_percentage) as max_loss_pct
            FROM loss_analysis
            WHERE station_id NOT IN ({exclusion_list})
        """

        summary = self.fetchone(summary_query)
        if summary:
            logger.info(f"\nSummary:")
            logger.info(f"  Total days analyzed: {summary['total_days']}")
            logger.info(f"  Days with no charging: {summary['days_no_charging']}")
            logger.info(f"  Average loss: {summary['avg_loss_pct']:.2f}%")
            logger.info(f"  Min loss: {summary['min_loss_pct']:.2f}%")
            logger.info(f"  Max loss: {summary['max_loss_pct']:.2f}%")

        logger.info("="*60)

        return rows_affected

    def get_statistics(self, station_id: Optional[int] = None) -> Dict[str, Any]:
        """Get aggregate statistics for loss analysis"""
        query = """
            SELECT 
                COUNT(*) as total_records,
                MIN(period_start) as first_date,
                MAX(period_end) as last_date,
                AVG(loss_percentage) as avg_loss_pct,
                MIN(loss_percentage) as min_loss_pct,
                MAX(loss_percentage) as max_loss_pct,
                SUM(total_consumption_kwh) as total_consumption,
                SUM(total_delivered_kwh) as total_delivered,
                SUM(total_reactive_kwh) as total_reactive,
                SUM(loss_kwh) as total_loss
            FROM loss_analysis
            WHERE 1=1
        """
        params = []
        if station_id:
            query += " AND station_id = %s"
            params.append(station_id)

        res = self.fetchone(query, tuple(params) if params else None)
        return res if res else {}

    def get_all(self, station_id=None, start_date=None, end_date=None) -> List[LossAnalysis]:
        """Get loss analysis records with optional filters"""
        query = """
            SELECT la.*, s.station_code, s.station_name 
            FROM loss_analysis la 
            JOIN stations s ON la.station_id = s.id 
            WHERE 1=1
        """
        params = []
        if station_id:
            query += " AND la.station_id = %s"
            params.append(station_id)
        if start_date:
            query += " AND la.period_start >= %s"
            params.append(start_date)
        if end_date:
            query += " AND la.period_end <= %s"
            params.append(end_date)

        query += " ORDER BY la.period_start DESC"
        rows = self.fetchall(query, tuple(params) if params else None)
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: dict) -> LossAnalysis:
        """Convert database row to domain model"""
        return LossAnalysis(
            id=row['id'],
            station_id=row['station_id'],
            period_start=row['period_start'],
            period_end=row['period_end'],
            total_consumption_kwh=float(row['total_consumption_kwh']),
            total_delivered_kwh=float(row['total_delivered_kwh']),
            total_reactive_kwh=float(row.get('total_reactive_kwh', 0)),
            loss_kwh=float(row['loss_kwh']),
            loss_percentage=float(row['loss_percentage']),
            station_code=row.get('station_code'),
            station_name=row.get('station_name')
        )

    def get_power_factor_by_station(self) -> list:
        """Calculate power factor for each station"""
        query = """
            SELECT 
                s.station_code,
                s.station_name,
                SUM(la.total_consumption_kwh) as total_active,
                SUM(la.total_reactive_kwh) as total_reactive,
                SQRT(POW(SUM(la.total_consumption_kwh), 2) + 
                     POW(SUM(la.total_reactive_kwh), 2)) as apparent_power,
                (SUM(la.total_consumption_kwh) / 
                 NULLIF(SQRT(POW(SUM(la.total_consumption_kwh), 2) + 
                            POW(SUM(ABS(la.total_reactive_kwh)), 2)), 0) * 100
                ) as power_factor
            FROM loss_analysis la
            JOIN stations s ON la.station_id = s.id
            WHERE la.total_reactive_kwh > 0
            GROUP BY s.station_code, s.station_name
            ORDER BY power_factor ASC
        """
        return self.fetchall(query)

    def get_loss_breakdown(self, station_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get breakdown of losses by activity level.
        Useful for understanding idle vs active losses.
        """
        query = """
            SELECT 
                CASE 
                    WHEN total_delivered_kwh = 0 THEN 'No Charging'
                    WHEN total_delivered_kwh < 10 THEN 'Low Activity'
                    WHEN total_delivered_kwh < 50 THEN 'Medium Activity'
                    ELSE 'High Activity'
                END as activity_level,
                COUNT(*) as day_count,
                AVG(loss_percentage) as avg_loss_pct,
                AVG(total_consumption_kwh) as avg_consumption,
                AVG(total_delivered_kwh) as avg_delivered
            FROM loss_analysis
            WHERE 1=1
        """
        params = []
        if station_id:
            query += " AND station_id = %s"
            params.append(station_id)

        query += " GROUP BY activity_level ORDER BY avg_loss_pct DESC"

        return self.fetchall(query, tuple(params) if params else None)

    def get_power_factor_by_station_pc(
            self,
            start_dt: datetime,
            end_dt: datetime,
            mode: str = "active",
            active_threshold_kwh: float = 0.5
    ) -> list:
        """
        Vypočítá Power Factor pro všechny stanice přímo z tabulky power_consumption.

        Args:
            start_dt: Začátek období
            end_dt: Konec období
            mode: "active" (pouze nabíjení) nebo "all" (vše včetně standby)
            active_threshold_kwh: Práh pro filtraci (0.5 kWh/15min = ~2kW výkonu)
        """
        exclusion_list = ','.join(map(str, self.PROBLEMATIC_STATIONS)) if self.PROBLEMATIC_STATIONS else '0'

        extra_where = ""
        params = [start_dt, end_dt]

        if mode == "active":
            extra_where = "AND ABS(pc.active_power_kwh) >= %s"
            params.append(active_threshold_kwh)
            logger.info(f"Filtruji intervaly s výkonem nižším než {active_threshold_kwh} kWh (mode=active)")
        else:
            logger.info("Počítám Power Factor ze všech dat (včetně standby)")

        query = f"""
            SELECT
                s.id AS station_id,
                s.station_code,
                s.station_name,
                SUM(ABS(pc.active_power_kwh)) AS total_active,
                SUM(ABS(pc.reactive_power_kwh)) AS total_reactive,
                COUNT(*) as interval_count,
                (
                    SUM(ABS(pc.active_power_kwh)) /
                    NULLIF(
                        SQRT(
                            POW(SUM(ABS(pc.active_power_kwh)), 2) +
                            POW(SUM(ABS(pc.reactive_power_kwh)), 2)
                        ), 0
                    ) * 100
                ) AS power_factor
            FROM power_consumption pc
            JOIN stations s ON s.id = pc.station_id
            WHERE pc.timestamp >= %s
              AND pc.timestamp < %s
              AND pc.station_id NOT IN ({exclusion_list})
              {extra_where}
            GROUP BY s.id, s.station_code, s.station_name
            HAVING total_active > 0
            ORDER BY power_factor ASC
        """

        results = self.fetchall(query, tuple(params))

        for res in results:
            logger.info(
                f"Station {res['station_code']}: PF={res['power_factor']:.1f}%, "
                f"Active={res['total_active']:.1f}kWh, Reactive={res['total_reactive']:.1f}kVArh"
            )

        return results

    def get_power_factor_trend_pc(
            self,
            station_id: int,
            start_dt: datetime,
            end_dt: datetime,
            mode: str = "active",
            active_threshold_kwh: float = 0.5,  # Changed default from 0.05 to 0.5
    ) -> list:
        """
        Get daily power factor trend for a specific station.

        Args:
            station_id: Station ID to analyze
            start_dt: Start datetime
            end_dt: End datetime
            mode: "active" or "all"
            active_threshold_kwh: Minimum energy per interval to include
        """
        exclusion_list = ','.join(map(str, self.PROBLEMATIC_STATIONS)) if self.PROBLEMATIC_STATIONS else '0'

        extra_where = ""
        params = [station_id, start_dt, end_dt]

        if mode == "active":
            extra_where = "AND ABS(pc.active_power_kwh) >= %s"
            params.append(active_threshold_kwh)

        query = f"""
            SELECT
                DATE(pc.timestamp) AS date,
                SUM(ABS(pc.active_power_kwh)) AS total_active,
                SUM(ABS(pc.reactive_power_kwh)) AS total_reactive,
                COUNT(*) as interval_count,
                (
                    SUM(ABS(pc.active_power_kwh)) /
                    NULLIF(
                        SQRT(
                            POW(SUM(ABS(pc.active_power_kwh)),2) +
                            POW(SUM(ABS(pc.reactive_power_kwh)),2)
                        ), 0
                    ) * 100
                ) AS power_factor
            FROM power_consumption pc
            WHERE pc.station_id = %s
              AND pc.timestamp >= %s
              AND pc.timestamp < %s
              AND pc.station_id NOT IN ({exclusion_list})
              {extra_where}
            GROUP BY DATE(pc.timestamp)
            HAVING total_active > 0
            ORDER BY DATE(pc.timestamp) ASC
        """

        results = self.fetchall(query, tuple(params))

        logger.info(
            f"Power factor trend for station {station_id}: "
            f"{len(results)} days with data ({mode} mode, threshold={active_threshold_kwh})"
        )

        return results