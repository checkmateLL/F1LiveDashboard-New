import pandas as pd
from backend.database import get_connection

def get_performance_data(driver_id):
    conn = get_connection()
    query = "SELECT * FROM telemetry WHERE driver_id = ?"
    df = pd.read_sql_query(query, conn, params=(driver_id,))
    conn.close()
    return df
