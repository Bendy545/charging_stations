def calculate_losses(cursor, connection):
    """
    Vypočítá ztráty POUZE pro data, kde máme OBOJE: data o spotřebě i relace nabíjení.
    """
    print("Spouštím výpočet ztrát...")

    print("   Mazání starých záznamů z loss_analysis...")
    cursor.execute("DELETE FROM loss_analysis")
    connection.commit()

    cursor.execute("""
        SELECT 
            MIN(DATE(end_interval_15min)) as first_session_date,
            MAX(DATE(end_interval_15min)) as last_session_date,
            COUNT(*) as session_count
        FROM charging_sessions
    """)
    session_dates = cursor.fetchone()

    if not session_dates or not session_dates['first_session_date']:
        print("⚠️ Žádná data o nabíjení (sessions) nenalezena - přeskakuji výpočet.")
        return

    first_date = session_dates['first_session_date']
    last_date = session_dates['last_session_date']

    print(f"📅 Rozsah dat relací (Sessions): {first_date} až {last_date}")
    print(f"   Počet relací v DB: {session_dates['session_count']}")

    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM power_consumption 
        WHERE DATE(timestamp) >= %s AND DATE(timestamp) <= %s
    """, (first_date, last_date))
    consumption_check = cursor.fetchone()

    if consumption_check['count'] == 0:
        print(f"⚠️ KRITICKÁ CHYBA: V období {first_date} - {last_date} nebyla nalezena ŽÁDNÁ data o spotřebě (power_consumption)!")
        print("   Zkontrolujte, zda máte nahraná data spotřeby ('consumption.csv') pro tento rok.")
        return

    print(f"   Nalezeno {consumption_check['count']} záznamů spotřeby v tomto období. Seskupuji data...")

    cursor.execute("""
        SELECT 
            s.id as station_id,
            s.station_code,
            DATE(pc.timestamp) as day,
            SUM(pc.active_power_kwh) as total_consumption
        FROM power_consumption pc
        JOIN stations s ON pc.station_id = s.id
        WHERE DATE(pc.timestamp) >= %s 
        AND DATE(pc.timestamp) <= %s
        GROUP BY s.id, s.station_code, DATE(pc.timestamp)
        HAVING total_consumption > 0
    """, (first_date, last_date))

    consumption_by_day = cursor.fetchall()

    if not consumption_by_day:
        print("⚠️ Po seskupení nejsou k dispozici žádná data (možná neshoda ID stanic?).")
        return

    print(f"   Zpracovávám {len(consumption_by_day)} denních záznamů pro výpočet...")

    loss_records = []

    for cons in consumption_by_day:
        cursor.execute("""
            SELECT SUM(total_kwh) as total_delivered
            FROM charging_sessions
            WHERE station_id = %s 
            AND DATE(end_interval_15min) = %s
        """, (cons['station_id'], cons['day']))

        delivered = cursor.fetchone()
        total_delivered = float(delivered['total_delivered']) if delivered and delivered['total_delivered'] else 0.0
        total_consumption = float(cons['total_consumption'])

        loss_kwh = total_consumption - total_delivered

        loss_percentage = 0.0
        if total_consumption > 0:
            loss_percentage = (loss_kwh / total_consumption) * 100

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
        try:
            cursor.executemany("""
                INSERT INTO loss_analysis 
                (station_id, period_start, period_end, total_consumption_kwh, 
                 total_delivered_kwh, loss_kwh, loss_percentage)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, loss_records)

            connection.commit()
            print(f"✅ ÚSPĚCH: Uloženo {len(loss_records)} záznamů o ztrátách.")
        except Exception as e:
            print(f"❌ CHYBA při ukládání do DB: {str(e)}")
            connection.rollback()
            raise e
    else:
        print("⚠️ Žádná data k uložení po spárování.")