import pandas as pd
from backend.database import get_connection

def get_driver_standings(year):
    conn = get_connection()
    query = """
    SELECT drivers.full_name, SUM(results.points) as total_points 
    FROM results
    JOIN drivers ON results.driver_id = drivers.id
    JOIN sessions ON results.session_id = sessions.id
    JOIN events ON sessions.event_id = events.id
    WHERE events.year = ?
    GROUP BY drivers.full_name
    ORDER BY total_points DESC
    """
    df = pd.read_sql_query(query, conn, params=(year,))
    conn.close()
    return df
