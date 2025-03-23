import sqlite3
import sys
import pandas as pd
from pathlib import Path
import argparse

def check_database(db_path, session_id=None):
    """Check what data exists in the database."""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if the database exists and has tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        if not tables:
            print(f"Database at {db_path} exists but has no tables.")
            return
        
        print(f"Database at {db_path} has the following tables: {', '.join(tables)}")
        
        # Check total counts for each table
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"Table {table} has {count} records")
        
        # If a session ID is provided, check data for that session
        if session_id is not None:
            # First check the session info
            cursor.execute("""
                SELECT s.*, e.event_name, e.year, e.round_number, e.official_event_name
                FROM sessions s
                JOIN events e ON s.event_id = e.id
                WHERE s.id = ?
            """, (session_id,))
            session = cursor.fetchone()
            
            if not session:
                print(f"No session found with ID {session_id}")
                return
            
            # Print session details
            print("\nSession Details:")
            print(f"ID: {session['id']}")
            print(f"Name: {session['name']}")
            print(f"Event: {session['event_name']} ({session['year']}, Round {session['round_number']})")
            print(f"Official name: {session['official_event_name']}")
            print(f"Type: {session['session_type']}")
            print(f"Date: {session['date']}")
            
            # Check laps
            cursor.execute("""
                SELECT COUNT(*) as count FROM laps WHERE session_id = ?
            """, (session_id,))
            lap_count = cursor.fetchone()['count']
            print(f"\nLaps: {lap_count}")
            
            if lap_count > 0:
                # Sample a few laps
                cursor.execute("""
                    SELECT l.*, d.abbreviation as driver_abbr
                    FROM laps l
                    JOIN drivers d ON l.driver_id = d.id
                    WHERE l.session_id = ?
                    ORDER BY l.driver_id, l.lap_number
                    LIMIT 5
                """, (session_id,))
                
                print("\nSample lap data:")
                sample_laps = cursor.fetchall()
                for lap in sample_laps:
                    print(f"Driver: {lap['driver_abbr']}, Lap: {lap['lap_number']}, Time: {lap['lap_time']}")
            
            # Check results
            cursor.execute("""
                SELECT COUNT(*) as count FROM results WHERE session_id = ?
            """, (session_id,))
            result_count = cursor.fetchone()['count']
            print(f"\nResults: {result_count}")
            
            if result_count > 0:
                # Sample results
                cursor.execute("""
                    SELECT r.*, d.abbreviation as driver_abbr
                    FROM results r
                    JOIN drivers d ON r.driver_id = d.id
                    WHERE r.session_id = ?
                    ORDER BY r.position
                    LIMIT 5
                """, (session_id,))
                
                print("\nSample result data:")
                sample_results = cursor.fetchall()
                for result in sample_results:
                    print(f"Driver: {result['driver_abbr']}, Position: {result['position']}, Points: {result['points']}")
            
            # Check telemetry
            cursor.execute("""
                SELECT COUNT(*) as count FROM telemetry WHERE session_id = ?
            """, (session_id,))
            telemetry_count = cursor.fetchone()['count']
            print(f"\nTelemetry points: {telemetry_count}")
            
            # Check weather
            cursor.execute("""
                SELECT COUNT(*) as count FROM weather WHERE session_id = ?
            """, (session_id,))
            weather_count = cursor.fetchone()['count']
            print(f"\nWeather data points: {weather_count}")
            
            if weather_count > 0:
                # Sample weather
                cursor.execute("""
                    SELECT * FROM weather WHERE session_id = ? LIMIT 3
                """, (session_id,))
                
                print("\nSample weather data:")
                sample_weather = cursor.fetchall()
                for w in sample_weather:
                    print(f"Time: {w['time']}, Air: {w['air_temp']}°C, Track: {w['track_temp']}°C")
            
        # List all sessions with their IDs
        print("\nAll sessions in database:")
        cursor.execute("""
            SELECT s.id, s.name, s.session_type, e.event_name, e.year, e.round_number
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            ORDER BY e.year, e.round_number, s.id
        """)
        
        sessions = cursor.fetchall()
        for s in sessions:
            # Check count of laps and results for this session
            cursor.execute("SELECT COUNT(*) as count FROM laps WHERE session_id = ?", (s['id'],))
            lap_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM results WHERE session_id = ?", (s['id'],))
            result_count = cursor.fetchone()['count']
            
            print(f"ID: {s['id']}, {s['event_name']} {s['year']} (R{s['round_number']}), {s['name']} - {s['session_type']}, Laps: {lap_count}, Results: {result_count}")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def check_fastf1_data(year, round_number, session_name):
    """Check if data exists in FastF1."""
    try:
        import fastf1
        
        print(f"\nChecking FastF1 data for {year} Round {round_number}, Session: {session_name}")
        
        # Enable cache
        try:
            cache_dir = Path.home() / ".fastf1_cache"
            cache_dir.mkdir(exist_ok=True)
            fastf1.Cache.enable_cache(str(cache_dir))
        except Exception as e:
            print(f"Warning: Could not enable cache: {e}")
        
        # Get session
        try:
            session = fastf1.get_session(year, round_number, session_name)
            print(f"Session found: {session.name}, Date: {session.date}")
            
            # Try to load data
            print("Loading session data (this may take a moment)...")
            session.load(laps=True, telemetry=False, weather=True)
            
            # Check what data is available
            print("\nData available:")
            
            if hasattr(session, 'results') and session.results is not None:
                print(f"Results: {len(session.results)} drivers")
            else:
                print("Results: Not available")
                
            if hasattr(session, 'laps') and session.laps is not None:
                print(f"Laps: {len(session.laps)} laps")
                
                # Show some sample lap data
                if not session.laps.empty:
                    print("\nSample lap data:")
                    sample_laps = session.laps.head(3)
                    for idx, lap in sample_laps.iterrows():
                        print(f"Driver: {lap['Driver']}, Lap: {lap['LapNumber']}, Time: {lap['LapTime']}")
            else:
                print("Laps: Not available")
                
            if hasattr(session, 'weather_data') and session.weather_data is not None:
                print(f"Weather: {len(session.weather_data)} data points")
            else:
                print("Weather: Not available")
                
        except Exception as e:
            print(f"Error loading session: {e}")
        
    except ImportError:
        print("FastF1 not installed. Install it with 'pip install fastf1'.")
    except Exception as e:
        print(f"Error checking FastF1 data: {e}")

def main():
    parser = argparse.ArgumentParser(description="Check F1 database content")
    parser.add_argument("--db-path", default="D:/Dev/F1LiveDashboard/f1_data_full_2025.db", 
                      help="Path to the SQLite database")
    parser.add_argument("--session-id", type=int, help="Session ID to check")
    parser.add_argument("--check-fastf1", action="store_true", help="Check data in FastF1")
    parser.add_argument("--year", type=int, help="Year for FastF1 check")
    parser.add_argument("--round", type=int, help="Round number for FastF1 check")
    parser.add_argument("--session", help="Session name for FastF1 check")
    
    args = parser.parse_args()
    
    # Check the database
    check_database(args.db_path, args.session_id)
    
    # Check FastF1 if requested
    if args.check_fastf1 and args.year and args.round and args.session:
        check_fastf1_data(args.year, args.round, args.session)
    
if __name__ == "__main__":
    main()