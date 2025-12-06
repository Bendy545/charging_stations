import pandas as pd
from backend.src.config import settings
from backend.src.services.loss_calculator import calculate_losses

def process_csv_data(cursor, connection):
    """Process CSV files and insert data into database"""

    print("Processing consumption data...")
    df_history = pd.read_csv(settings.consumption_file, sep=';', decimal=',')
    df_history['Date and time'] = pd.to_datetime(
        df_history['Date and time'],
        format='%d.%m.%Y %H:%M:%S'
    )

    charger_power_map = {
        'Jeníšov.Retail.RP1/UR371.Měření UR371.Činný výkon celkový [ kW]': ('UR371', 'active'),
        'Jeníšov.Retail.RP1/UR371.Měření UR371.Jalový výkon celkový [ kVAr]': ('UR371', 'reactive'),
        'Jeníšov.Retail.RP1/UR372.Měření UR372.Činný výkon celkový [ kW]': ('UR372', 'active'),
        'Jeníšov.Retail.RP1/UR372.Měření UR372.Jalový výkon celkový [ kVAr]': ('UR372', 'reactive'),
        'Jeníšov.TS KV_1437.RH1.Měření UR367.Činný výkon celkový [ kW]': ('UR367', 'active'),
        'Jeníšov.TS KV_1437.RH1.Měření UR367.Jalový výkon celkový [ kVAr]': ('UR367', 'reactive'),
        'Jeníšov.TS KV_1437.RH1.Měření UR368 master.Činný výkon celkový [ kW]': ('UR368', 'active_master'),
        'Jeníšov.TS KV_1437.RH1.Měření UR368 master.Jalový výkon celkový [ kVAr]': ('UR368', 'reactive_master'),
        'Jeníšov.TS KV_1437.RH1.Měření UR368 slave.Činný výkon celkový [ kW]': ('UR368', 'active_slave'),
        'Jeníšov.TS KV_1437.RH1.Měření UR368 slave.Jalový výkon celkový [ kVAr]': ('UR368', 'reactive_slave'),
        'Jeníšov.TS KV_1437.RH1.Měření UR369.Činný výkon celkový [ kW]': ('UR369', 'active'),
        'Jeníšov.TS KV_1437.RH1.Měření UR369.Jalový výkon celkový [ kVAr]': ('UR369', 'reactive'),
        'Jeníšov.TS KV_1437.RH1.Měření UR370.Činný výkon celkový [ kW]': ('UR370', 'active'),
        'Jeníšov.TS KV_1437.RH1.Měření UR370.Jalový výkon celkový [ kVAr]': ('UR370', 'reactive'),
        'Jeníšov.TS KV_1437.RH1.Měření UR388 master.Činný výkon celkový [ kW]': ('UR366', 'active'),
        'Jeníšov.TS KV_1437.RH1.Měření UR388 master.Jalový výkon celkový [ kVAr]': ('UR366', 'reactive'),
    }

    interval_h = 0.25

    cursor.execute("SELECT id, station_code FROM stations")
    stations_dict = {row['station_code']: row['id'] for row in cursor.fetchall()}

    cursor.execute("DELETE FROM power_consumption")

    consumption_records = []
    processed_stations = set()

    for idx, row in df_history.iterrows():
        timestamp = row['Date and time']

        ur368_active = 0
        ur368_reactive = 0
        station_data = {}

        for long_name, (station_code, power_type) in charger_power_map.items():
            if long_name in df_history.columns:
                power_kw = row[long_name]
                power_kwh = power_kw * interval_h

                if station_code == 'UR368':
                    if 'active' in power_type:
                        ur368_active += power_kwh
                    elif 'reactive' in power_type:
                        ur368_reactive += power_kwh
                else:
                    if station_code not in station_data:
                        station_data[station_code] = {'active': 0, 'reactive': 0}

                    if power_type == 'active':
                        station_data[station_code]['active'] = power_kwh
                    elif power_type == 'reactive':
                        station_data[station_code]['reactive'] = power_kwh

        for station_code, powers in station_data.items():
            if station_code in stations_dict:
                consumption_records.append((
                    timestamp,
                    stations_dict[station_code],
                    powers['active'],
                    powers['reactive']
                ))
                processed_stations.add(station_code)

        if 'UR368' in stations_dict:
            consumption_records.append((
                timestamp,
                stations_dict['UR368'],
                ur368_active,
                ur368_reactive
            ))
            processed_stations.add('UR368')

    if consumption_records:
        cursor.executemany("""
            INSERT INTO power_consumption (timestamp, station_id, active_power_kwh, reactive_power_kwh)
            VALUES (%s, %s, %s, %s)
        """, consumption_records)

    print(f"✅ Inserted {len(consumption_records)} consumption records")
    print(f"✅ Processed stations: {', '.join(sorted(processed_stations))}")

    print("Processing charging sessions...")
    df_log = pd.read_csv(settings.sessions_file, sep=';', decimal=',')
    df_log['Start Date'] = pd.to_datetime(df_log['Start Date'], errors='coerce')
    df_log['End Date'] = pd.to_datetime(df_log['End Date'], errors='coerce')
    df_log = df_log.dropna(subset=['End Date', 'Total kWh', 'Charger'])

    df_log['Charger_ID'] = df_log['Charger'].apply(lambda x: str(x).split(',')[0].strip())
    df_log['End_Interval_15min'] = df_log['End Date'].dt.floor('15min')

    cursor.execute("DELETE FROM charging_sessions")

    session_records = []
    processed_chargers = set()

    for idx, row in df_log.iterrows():
        charger_id = row['Charger_ID']
        if charger_id in stations_dict:
            session_records.append((
                stations_dict[charger_id],
                row['Charger'],
                row['Start Date'],
                row['End Date'],
                row['Total kWh'],
                row.get('Start Card', ''),
                row['End_Interval_15min']
            ))
            processed_chargers.add(charger_id)

    if session_records:
        cursor.executemany("""
            INSERT INTO charging_sessions 
            (station_id, charger_name, start_date, end_date, total_kwh, start_card, end_interval_15min)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, session_records)

    print(f"✅ Inserted {len(session_records)} session records")
    print(f"✅ Processed chargers: {', '.join(sorted(processed_chargers))}")

    connection.commit()

    calculate_losses(cursor, connection)

    return len(consumption_records), len(session_records)