def calculate_losses(cursor, connection):
    """Calculate and store loss analysis"""
    print("Calculating losses...")

    cursor.execute("DELETE FROM loss_analysis")

    cursor.execute("""
        SELECT 
            s.id as station_id,
            s.station_code,
            DATE(pc.timestamp) as day,
            SUM(pc.active_power_kwh) as total_consumption
        FROM power_consumption pc
        JOIN stations s ON pc.station_id = s.id
        GROUP BY s.id, s.station_code, DATE(pc.timestamp)
    """)

    consumption_by_day = cursor.fetchall()
    loss_records = []

    for cons in consumption_by_day:
        cursor.execute("""
            SELECT SUM(total_kwh) as total_delivered
            FROM charging_sessions
            WHERE station_id = %s 
            AND DATE(end_interval_15min) = %s
        """, (cons['station_id'], cons['day']))

        delivered = cursor.fetchone()
        total_delivered = float(delivered['total_delivered']) if delivered['total_delivered'] else 0
        total_consumption = float(cons['total_consumption'])

        loss_kwh = total_consumption - total_delivered
        loss_percentage = (loss_kwh / total_consumption * 100) if total_consumption > 0 else 0

        loss_records.append((
            cons['station_id'],
            cons['day'],
            cons['day'],
            total_consumption,
            total_delivered,
            loss_kwh,
            loss_percentage
        ))

    if loss_records:
        cursor.executemany("""
            INSERT INTO loss_analysis 
            (station_id, period_start, period_end, total_consumption_kwh, 
             total_delivered_kwh, loss_kwh, loss_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, loss_records)

    connection.commit()
    print(f"✅ Calculated losses for {len(loss_records)} days")