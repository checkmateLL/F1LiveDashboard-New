import pandas as pd
from backend.database import get_connection

def get_race_results(session_id):
    conn = get_connection()
    query = "SELECT * FROM results WHERE session_id = ?"
    df = pd.read_sql_query(query, conn, params=(session_id,))
    conn.close()
    return df
