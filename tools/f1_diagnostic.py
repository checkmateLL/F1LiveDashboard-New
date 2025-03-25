import os
import sqlite3
import sys
import traceback

# Set a default DB path (adjust as needed)
DEFAULT_DB_PATH = "D:/Dev/F1LiveDashboard/f1_data_full_2025.db"

def run_diagnostics(db_path=DEFAULT_DB_PATH):
    """Run basic diagnostics on the F1 database."""
    print(f"\n{'=' * 40}")
    print(f"RUNNING F1 DATABASE DIAGNOSTICS")
    print(f"{'=' * 40}")
    
    # 1. Check if database file exists
    print(f"\n1. Checking database file...")
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # Size in MB
        print(f"   ✓ Database file found: {db_path}")
        print(f"   ✓ File size: {db_size:.2f} MB")
    else:
        print(f"   ✗ Database file NOT found at: {db_path}")
        print(f"   > Will attempt to create a new database")
    
    # 2. Attempt to connect to the database
    print(f"\n2. Attempting database connection...")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print(f"   ✓ Successfully connected to database")
    except Exception as e:
        print(f"   ✗ Failed to connect to database: {e}")
        traceback.print_exc()
        return
    
    # 3. Check for required tables
    print(f"\n3. Checking database tables...")
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print(f"   ✗ No tables found in database")
    else:
        print(f"   ✓ Found {len(tables)} tables: {', '.join(tables)}")
    
    expected_tables = ['events', 'sessions', 'teams', 'drivers', 'results', 'laps', 'telemetry', 'weather', 'messages']
    
    for table in expected_tables:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - Table '{table}': {count} records")
        else:
            print(f"   - Table '{table}' is missing")
    
    # 4. Check events data if exists
    if 'events' in tables:
        print(f"\n4. Checking events data...")
        cursor.execute("SELECT year, COUNT(*) as count FROM events GROUP BY year")
        for row in cursor.fetchall():
            print(f"   - Year {row[0]}: {row[1]} events")
    
    # 5. Check sessions if exists
    if 'sessions' in tables and 'events' in tables:
        print(f"\n5. Checking sessions data...")
        cursor.execute("""
            SELECT e.year, s.session_type, COUNT(*) as count
            FROM sessions s
            JOIN events e ON s.event_id = e.id
            GROUP BY e.year, s.session_type
        """)
        
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"   - Year {row[0]}, Type '{row[1] or 'unknown'}': {row[2]} sessions")
        else:
            print(f"   ✗ No session data found")
    
    # 6. Check configuration (import module and try to access config)
    print(f"\n6. Checking configuration...")
    try:
        sys.path.append('.')  # Add current directory to path
        
        try:
            from config import FASTF1_CACHE_DIR, SQLITE_DB_PATH
            print(f"   ✓ Successfully imported config module")
            print(f"   - FASTF1_CACHE_DIR: {FASTF1_CACHE_DIR}")
            print(f"   - SQLITE_DB_PATH: {SQLITE_DB_PATH}")
            
            # Check if cache directory exists
            if os.path.exists(FASTF1_CACHE_DIR):
                print(f"   ✓ FastF1 cache directory exists")
                cache_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                              for dirpath, _, filenames in os.walk(FASTF1_CACHE_DIR) 
                              for filename in filenames) / (1024 * 1024)  # Size in MB
                print(f"   ✓ Cache size: {cache_size:.2f} MB")
            else:
                print(f"   ✗ FastF1 cache directory does not exist: {FASTF1_CACHE_DIR}")
        except ImportError:
            print(f"   ✗ Failed to import config module")
            
            # Try to check default FastF1 cache location
            default_cache = os.path.expanduser("~/.fastf1_cache")
            if os.path.exists(default_cache):
                print(f"   - Default FastF1 cache exists at {default_cache}")
            else:
                print(f"   - Default FastF1 cache does not exist at {default_cache}")
    except Exception as e:
        print(f"   ✗ Error checking configuration: {e}")
    
    # 7. Test FastF1 API if installed
    print(f"\n7. Testing FastF1 API...")
    try:
        import fastf1
        print(f"   ✓ FastF1 package is installed (version: {fastf1.__version__})")
        
        # Test basic API functionality (without making actual API calls)
        try:
            cache_status = "Enabled" if fastf1.Cache.enabled else "Disabled"
            print(f"   - Cache status: {cache_status}")
        except Exception as e:
            print(f"   ✗ Error checking FastF1 cache status: {e}")
    except ImportError:
        print(f"   ✗ FastF1 package is NOT installed")
    except Exception as e:
        print(f"   ✗ Error testing FastF1: {e}")
    
    print(f"\n{'=' * 40}")
    print(f"DIAGNOSTICS COMPLETE")
    print(f"{'=' * 40}\n")
    
    if conn:
        conn.close()

if __name__ == "__main__":
    # Get database path from command line if provided
    db_path = DEFAULT_DB_PATH
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    run_diagnostics(db_path)