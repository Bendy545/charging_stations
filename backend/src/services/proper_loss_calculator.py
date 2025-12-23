from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# CONFIGURATION: Data validity dates
CONSUMPTION_DATA_START = datetime(2025, 3, 16)  # When API data actually starts
PROBLEMATIC_STATIONS = [1, 2]  # UR371 (incomplete consumption), UR372 (incomplete sessions)

def round_to_15min(dt):
    """Round datetime down to nearest 15-minute interval"""
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def distribute_session_energy(cursor, connection):
    """
    Create a properly distributed session energy table.
    Only processes sessions where we have consumption data.
    """
    logger.info("=" * 70)
    logger.info("STEP 1: Distributing session energy across intervals")
    logger.info("=" * 70)

    # Create the distributed sessions table
    logger.info("Creating distributed_sessions table...")
    cursor.execute("""
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
    connection.commit()
    logger.info("✅ Table created/verified")

    # Clear existing data
    cursor.execute("DELETE FROM distributed_sessions")
    connection.commit()
    logger.info("🗑️ Cleared old distributed data")

    # Get sessions ONLY from when consumption data exists
    logger.info(f"⚠️ Filtering sessions: Only using data from {CONSUMPTION_DATA_START.date()} onwards")
    logger.info(f"⚠️ Excluding problematic stations: {PROBLEMATIC_STATIONS}")

    cursor.execute("""
        SELECT id, station_id, start_date, end_date, total_kwh
        FROM charging_sessions
        WHERE total_kwh > 0
        AND start_date IS NOT NULL
        AND end_date IS NOT NULL
        AND end_date >= %s
        ORDER BY start_date
    """, (CONSUMPTION_DATA_START,))

    sessions = cursor.fetchall()

    # Get total count before filtering
    cursor.execute("SELECT COUNT(*) as total FROM charging_sessions WHERE total_kwh > 0")
    all_sessions_count = cursor.fetchone()['total']
    skipped_before_date = all_sessions_count - len(sessions)

    logger.info(f"📊 Found {len(sessions)} valid sessions (skipped {skipped_before_date} before {CONSUMPTION_DATA_START.date()})")

    if not sessions:
        logger.warning("⚠️ No valid sessions found!")
        return

    distributed_records = []
    skipped_count = 0

    for idx, session in enumerate(sessions):
        session_id = session['id']
        station_id = session['station_id']
        start = session['start_date']
        end = session['end_date']
        total_kwh = float(session['total_kwh'])

        # Calculate total duration in minutes
        total_minutes = (end - start).total_seconds() / 60

        if total_minutes <= 0:
            skipped_count += 1
            continue

        # Round to 15-min intervals
        first_interval = round_to_15min(start)
        last_interval = round_to_15min(end)

        # Generate all 15-minute intervals this session touches
        current_interval = first_interval

        while current_interval <= last_interval:
            interval_end = current_interval + timedelta(minutes=15)

            # Calculate overlap with this interval
            overlap_start = max(start, current_interval)
            overlap_end = min(end, interval_end)
            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60

            if overlap_minutes > 0:
                # Calculate proportion and energy for this interval
                proportion = overlap_minutes / total_minutes
                energy_in_interval = total_kwh * proportion

                distributed_records.append((
                    session_id,
                    station_id,
                    current_interval,
                    energy_in_interval,
                    proportion,
                    overlap_minutes
                ))

            current_interval = interval_end

        # Progress logging
        if (idx + 1) % 1000 == 0:
            logger.info(f"   Processed {idx + 1}/{len(sessions)} sessions...")

    # Insert distributed records
    if distributed_records:
        logger.info(f"💾 Inserting {len(distributed_records)} distributed records...")

        cursor.executemany("""
            INSERT INTO distributed_sessions 
            (session_id, station_id, interval_15min, energy_kwh, proportion, overlap_minutes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, distributed_records)

        connection.commit()

        # Verify energy conservation
        cursor.execute("""
            SELECT SUM(total_kwh) as total 
            FROM charging_sessions 
            WHERE total_kwh > 0 AND end_date >= %s
        """, (CONSUMPTION_DATA_START,))
        original_total = float(cursor.fetchone()['total'])

        cursor.execute("SELECT SUM(energy_kwh) as total FROM distributed_sessions")
        distributed_total = float(cursor.fetchone()['total'])

        logger.info("=" * 70)
        logger.info("✅ DISTRIBUTION COMPLETE")
        logger.info(f"   Total sessions in DB: {all_sessions_count}")
        logger.info(f"   Skipped (before {CONSUMPTION_DATA_START.date()}): {skipped_before_date}")
        logger.info(f"   Sessions processed: {len(sessions) - skipped_count}")
        logger.info(f"   Distributed records created: {len(distributed_records)}")
        logger.info(f"   Energy conservation check:")
        logger.info(f"      Original total: {original_total:.3f} kWh")
        logger.info(f"      Distributed total: {distributed_total:.3f} kWh")
        logger.info(f"      Difference: {abs(original_total - distributed_total):.6f} kWh")
        logger.info("=" * 70)
    else:
        logger.warning("⚠️ No valid sessions to distribute")


def calculate_losses_with_distribution(cursor, connection):
    """
    Calculate losses using properly distributed session energy
    NOW INCLUDES REACTIVE POWER TRACKING
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 2: Calculating losses with proper alignment")
    logger.info("=" * 70)

    # Verify distributed sessions exist
    cursor.execute("SELECT COUNT(*) as count FROM distributed_sessions")
    dist_count = cursor.fetchone()['count']

    if dist_count == 0:
        logger.error("❌ No distributed session data found!")
        logger.error("   Run distribute_session_energy() first")
        return

    logger.info(f"📊 Using {dist_count} distributed session records")

    # Get date range
    cursor.execute("""
        SELECT 
            GREATEST(MIN(DATE(interval_15min)), %s) as first_date,
            MAX(DATE(interval_15min)) as last_date
        FROM distributed_sessions
    """, (CONSUMPTION_DATA_START.date(),))

    date_range = cursor.fetchone()
    first_date = date_range['first_date']
    last_date = date_range['last_date']

    logger.info(f"📅 Date range: {first_date} to {last_date}")
    logger.info(f"⚠️ Excluding problematic stations: {PROBLEMATIC_STATIONS}")

    # Calculate daily aggregations WITH REACTIVE POWER
    logger.info("🔄 Aggregating daily data (including reactive power)...")

    # Build exclusion list for SQL
    exclusion_list = ','.join(map(str, PROBLEMATIC_STATIONS)) if PROBLEMATIC_STATIONS else '0'

    cursor.execute(f"""
        WITH daily_consumption AS (
            SELECT 
                station_id,
                DATE(timestamp) as calc_date,
                -- Active power (absolute value to handle negatives)
                SUM(ABS(active_power_kwh)) as total_consumption,
                -- Reactive power (absolute value - we just care about magnitude)
                SUM(ABS(reactive_power_kwh)) as total_reactive,
                SUM(active_power_kwh) as raw_consumption,
                COUNT(*) as measurement_count,
                SUM(CASE WHEN active_power_kwh < 0 THEN 1 ELSE 0 END) as negative_count
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
                SUM(energy_kwh) as total_delivered,
                COUNT(DISTINCT session_id) as session_count
            FROM distributed_sessions
            WHERE DATE(interval_15min) >= %s 
            AND DATE(interval_15min) <= %s
            AND station_id NOT IN ({exclusion_list})
            GROUP BY station_id, DATE(interval_15min)
        ),
        combined_data AS (
            SELECT 
                COALESCE(c.station_id, d.station_id) as station_id,
                COALESCE(c.calc_date, d.calc_date) as calc_date,
                COALESCE(c.total_consumption, 0) as consumption_kwh,
                COALESCE(c.total_reactive, 0) as reactive_kwh,
                COALESCE(c.raw_consumption, 0) as raw_consumption_kwh,
                COALESCE(d.total_delivered, 0) as delivered_kwh,
                COALESCE(c.measurement_count, 0) as measurements,
                COALESCE(c.negative_count, 0) as negative_readings,
                COALESCE(d.session_count, 0) as sessions
            FROM daily_consumption c
            LEFT JOIN daily_delivered d
                ON c.station_id = d.station_id 
                AND c.calc_date = d.calc_date
            
            UNION
            
            SELECT 
                d.station_id,
                d.calc_date,
                COALESCE(c.total_consumption, 0) as consumption_kwh,
                COALESCE(c.total_reactive, 0) as reactive_kwh,
                COALESCE(c.raw_consumption, 0) as raw_consumption_kwh,
                d.total_delivered as delivered_kwh,
                COALESCE(c.measurement_count, 0) as measurements,
                COALESCE(c.negative_count, 0) as negative_readings,
                d.session_count as sessions
            FROM daily_delivered d
            LEFT JOIN daily_consumption c
                ON d.station_id = c.station_id 
                AND d.calc_date = c.calc_date
            WHERE c.station_id IS NULL
        )
        SELECT * FROM combined_data
        WHERE consumption_kwh > 0.001 OR delivered_kwh > 0.001
        ORDER BY calc_date, station_id
    """, (first_date, last_date, first_date, last_date))

    daily_data = cursor.fetchall()

    if not daily_data:
        logger.warning("⚠️ No data to calculate losses")
        return

    logger.info(f"📊 Processing {len(daily_data)} daily records...")

    # Prepare loss records with validation
    loss_records = []
    stats = {
        'total': len(daily_data),
        'negative_losses': 0,
        'high_losses': 0,
        'normal': 0,
        'with_reactive': 0
    }

    for record in daily_data:
        station_id = record['station_id']
        calc_date = record['calc_date']
        consumption = float(record['consumption_kwh'])
        reactive = float(record['reactive_kwh'])
        delivered = float(record['delivered_kwh'])
        negative_readings = record['negative_readings']

        # Skip if mostly negative readings
        if negative_readings > record['measurements'] * 0.5:
            logger.warning(f"⚠️ Skipping {calc_date} station {station_id}: {negative_readings}/{record['measurements']} negative readings")
            continue

        loss_kwh = consumption - delivered

        # Calculate loss percentage
        if consumption > 0:
            loss_percentage = (loss_kwh / consumption) * 100
        else:
            loss_percentage = 0 if delivered == 0 else -100

        # Track reactive power presence
        if reactive > 0:
            stats['with_reactive'] += 1

        # Categorize
        if loss_percentage < -5:
            stats['negative_losses'] += 1
        elif loss_percentage > 50:
            stats['high_losses'] += 1
        else:
            stats['normal'] += 1

        # Add record WITH REACTIVE POWER
        loss_records.append((
            station_id,
            calc_date,
            calc_date,
            consumption,
            delivered,
            reactive,  # NEW: Reactive power
            loss_kwh,
            loss_percentage
        ))

    # Insert loss records
    if loss_records:
        logger.info("💾 Saving loss analysis records...")

        cursor.executemany("""
            INSERT INTO loss_analysis 
            (station_id, period_start, period_end, 
             total_consumption_kwh, total_delivered_kwh, total_reactive_kwh,
             loss_kwh, loss_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_consumption_kwh = VALUES(total_consumption_kwh),
                total_delivered_kwh = VALUES(total_delivered_kwh),
                total_reactive_kwh = VALUES(total_reactive_kwh),
                loss_kwh = VALUES(loss_kwh),
                loss_percentage = VALUES(loss_percentage),
                calculated_at = CURRENT_TIMESTAMP
        """, loss_records)

        connection.commit()

        # Summary statistics
        cursor.execute(f"""
            SELECT 
                MIN(loss_percentage) as min_loss,
                MAX(loss_percentage) as max_loss,
                AVG(loss_percentage) as avg_loss,
                STD(loss_percentage) as std_loss,
                SUM(total_reactive_kwh) as total_reactive,
                SUM(total_consumption_kwh) as total_active
            FROM loss_analysis
            WHERE period_start >= %s AND period_end <= %s
            AND station_id NOT IN ({exclusion_list})
        """, (first_date, last_date))

        summary = cursor.fetchone()

        # Calculate power factor
        total_active = float(summary['total_active'])
        total_reactive = float(summary['total_reactive'])
        apparent_power = (total_active**2 + total_reactive**2)**0.5
        power_factor = (total_active / apparent_power * 100) if apparent_power > 0 else 100

        logger.info("=" * 70)
        logger.info("✅ LOSS CALCULATION COMPLETE")
        logger.info(f"   Total records processed: {len(loss_records)}")
        logger.info(f"   Records with reactive power: {stats['with_reactive']}")
        logger.info(f"   Excluded Stations {PROBLEMATIC_STATIONS}")
        logger.info(f"   Date range: {first_date} to {last_date}")
        logger.info("")
        logger.info("📊 Loss Statistics:")
        logger.info(f"   Minimum: {summary['min_loss']:.2f}%")
        logger.info(f"   Maximum: {summary['max_loss']:.2f}%")
        logger.info(f"   Average: {summary['avg_loss']:.2f}%")
        logger.info(f"   Std Dev: {summary['std_loss']:.2f}%")
        logger.info("")
        logger.info("⚡ Power Quality:")
        logger.info(f"   Total Active Power: {total_active:,.0f} kWh")
        logger.info(f"   Total Reactive Power: {total_reactive:,.0f} kVArh")
        logger.info(f"   Apparent Power: {apparent_power:,.0f} kVAh")
        logger.info(f"   Average Power Factor: {power_factor:.1f}%")
        logger.info("")
        logger.info("📈 Data Quality:")
        logger.info(f"   Normal (<50%): {stats['normal']} records")
        logger.info(f"   Negative (<-5%): {stats['negative_losses']} records")
        logger.info(f"   High (>50%): {stats['high_losses']} records")
        logger.info("=" * 70)
    else:
        logger.warning("⚠️ No valid records to save")


def recalculate_everything(cursor, connection):
    """
    Complete recalculation pipeline with reactive power tracking
    """
    logger.info("")
    logger.info("🚀" * 35)
    logger.info("STARTING COMPLETE LOSS RECALCULATION")
    logger.info("🚀" * 35)
    logger.info("")
    logger.info(f"⚠️ Data filters active:")
    logger.info(f"   - Only sessions from {CONSUMPTION_DATA_START.date()} onwards")
    logger.info(f"   - Excluding problematic stations: {PROBLEMATIC_STATIONS}")
    logger.info(f"   - Tracking reactive power for power factor analysis")
    logger.info("")

    try:
        # Step 1: Distribute sessions
        distribute_session_energy(cursor, connection)

        # Step 2: Calculate losses
        calculate_losses_with_distribution(cursor, connection)

        logger.info("")
        logger.info("✅" * 35)
        logger.info("RECALCULATION PIPELINE COMPLETE!")
        logger.info("✅" * 35)
        logger.info("")

    except Exception as e:
        logger.error(f"❌ Error during recalculation: {e}")
        connection.rollback()
        raise


def get_data_quality_report(cursor):
    """
    Generate a comprehensive data quality report including power factor
    """
    report = {}

    # Check consumption data coverage
    cursor.execute("""
        SELECT 
            MIN(timestamp) as first_record,
            MAX(timestamp) as last_record,
            COUNT(*) as total_records,
            SUM(CASE WHEN active_power_kwh < 0 THEN 1 ELSE 0 END) as negative_records,
            SUM(active_power_kwh) as total_active,
            SUM(ABS(reactive_power_kwh)) as total_reactive
        FROM power_consumption
    """)
    report['consumption_coverage'] = cursor.fetchone()

    # Check session coverage
    cursor.execute("""
        SELECT 
            MIN(start_date) as first_session,
            MAX(end_date) as last_session,
            COUNT(*) as total_sessions,
            SUM(CASE WHEN end_date < %s THEN 1 ELSE 0 END) as before_consumption_data,
            SUM(CASE WHEN end_date >= %s THEN 1 ELSE 0 END) as with_consumption_data
        FROM charging_sessions
        WHERE total_kwh > 0
    """, (CONSUMPTION_DATA_START, CONSUMPTION_DATA_START))
    report['session_coverage'] = cursor.fetchone()

    # Check problematic stations
    if PROBLEMATIC_STATIONS:
        placeholders = ','.join(['%s'] * len(PROBLEMATIC_STATIONS))
        cursor.execute(f"""
            SELECT 
                station_id,
                COUNT(*) as records,
                SUM(active_power_kwh) as total_kwh,
                SUM(CASE WHEN active_power_kwh < 0 THEN 1 ELSE 0 END) as negative_count
            FROM power_consumption
            WHERE station_id IN ({placeholders})
            GROUP BY station_id
        """, PROBLEMATIC_STATIONS)
        report['problematic_stations'] = cursor.fetchall()
    else:
        report['problematic_stations'] = []

    # Power factor by station
    cursor.execute("""
        SELECT 
            s.station_code,
            SUM(la.total_consumption_kwh) as active,
            SUM(la.total_reactive_kwh) as reactive,
            SQRT(POW(SUM(la.total_consumption_kwh), 2) + POW(SUM(la.total_reactive_kwh), 2)) as apparent,
            (SUM(la.total_consumption_kwh) / 
             NULLIF(SQRT(POW(SUM(la.total_consumption_kwh), 2) + POW(SUM(la.total_reactive_kwh), 2)), 0) * 100
            ) as power_factor
        FROM loss_analysis la
        JOIN stations s ON la.station_id = s.id
        WHERE la.total_reactive_kwh > 0
        GROUP BY s.station_code
        ORDER BY power_factor ASC
    """)
    report['power_factor_by_station'] = cursor.fetchall()

    return report