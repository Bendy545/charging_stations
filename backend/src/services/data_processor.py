import pandas as pd
import logging
from backend.src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def process_sessions_csv(file_path):
    """
    Nahraje pouze nabíjecí relace (Sessions) z CSV souboru.
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, station_code FROM stations")
        stations_dict = {s['station_code']: s['id'] for s in cursor.fetchall()}

        df = pd.read_csv(file_path, sep=';', decimal=',')

        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df['End Date'] = pd.to_datetime(df['End Date'], errors='coerce')
        df = df.dropna(subset=['End Date', 'Total kWh', 'Charger'])

        df['Charger_Code'] = df['Charger'].apply(lambda x: str(x).split(',')[0].strip())
        df['End_Interval_15min'] = df['End Date'].dt.floor('15min')

        session_records = []
        for _, row in df.iterrows():
            code = row['Charger_Code']
            if code in stations_dict:
                session_records.append((
                    stations_dict[code],
                    row['Charger'],
                    row['Start Date'],
                    row['End Date'],
                    row['Total kWh'],
                    row['End_Interval_15min']
                ))

        if session_records:
            cursor.execute("DELETE FROM charging_sessions")

            sql = """
                INSERT INTO charging_sessions 
                (station_id, charger_name, start_date, end_date, total_kwh, end_interval_15min)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(sql, session_records)
            connection.commit()
            logger.info(f"Úspěšně nahráno {len(session_records)} relací z CSV.")
            return len(session_records)

    except Exception as e:
        logger.error(f"Chyba při zpracování Sessions CSV: {e}")
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection.close()