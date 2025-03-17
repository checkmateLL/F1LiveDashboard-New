import fastf1
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Enable FastF1 cache
fastf1.Cache.enable_cache('fastf1_cache')

def get_australia_gp_positions():
    # Load the session data for Australian GP
    # For 2023 season:
    year = 2023
    gp_round = 3  # Australian GP was round 3 in 2023
    
    print(f"Loading {year} Australian GP data...")
    
    # Load the race session
    session = fastf1.get_session(year, gp_round, 'R')
    session.load()
    
    print(f"Session loaded: {session.event['EventName']}, {session.name}")
    
    # Get a list of drivers
    drivers = session.drivers
    print(f"Available drivers: {drivers}")
    
    # For demonstration, we'll use the first driver
    driver = drivers[0]
    driver_info = session.get_driver(driver)
    
    print(f"Using driver: {driver_info['FullName']} ({driver})")
    
    # Get the fastest lap for this driver
    fastest_lap = session.laps.pick_drivers(driver).pick_fastest()
    
    print(f"Fastest lap: {fastest_lap['LapTime']}")
    
    # Get telemetry data for this lap, which contains position data
    telemetry = fastest_lap.get_telemetry()
    
    print(f"Telemetry points: {len(telemetry)}")
    print("Sample data:")
    print(telemetry[['X', 'Y', 'Z', 'Speed', 'Time']].head())
    
    return telemetry

# Run the code
try:
    telemetry = get_australia_gp_positions()
    
    # Plot the track layout
    plt.figure(figsize=(10, 8))
    plt.scatter(telemetry['X'], telemetry['Y'], s=1, c=telemetry['Speed'], cmap='viridis')
    plt.colorbar(label='Speed (km/h)')
    plt.axis('equal')
    plt.title('Australia GP Track Layout from Telemetry')
    plt.xlabel('X Position (1/10 meters)')
    plt.ylabel('Y Position (1/10 meters)')
    plt.savefig('australia_track.png')
    plt.show()
    
    # Calculate and print track bounds for SVG calibration
    x_min, x_max = telemetry['X'].min(), telemetry['X'].max()
    y_min, y_max = telemetry['Y'].min(), telemetry['Y'].max()
    
    print("\nTrack Boundaries:")
    print(f"X range: {x_min} to {x_max} (width: {x_max - x_min})")
    print(f"Y range: {y_min} to {y_max} (height: {y_max - y_min})")
    
    # Calculate transformation parameters for SVG (1000x600 viewport)
    svg_width = 1000
    svg_height = 600
    
    # Add some padding (10%)
    padding = 0.1
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_min -= x_range * padding
    x_max += x_range * padding
    y_min -= y_range * padding
    y_max += y_range * padding
    
    x_scale = svg_width / (x_max - x_min)
    y_scale = svg_height / (y_max - y_min)
    
    # Use the smaller scale to maintain aspect ratio
    scale = min(x_scale, y_scale)
    
    # Calculate offsets to center the track
    x_offset = (svg_width - (x_max - x_min) * scale) / 2
    y_offset = (svg_height - (y_max - y_min) * scale) / 2
    
    print("\nSVG Transformation Parameters:")
    print(f"scale_x: {scale}")
    print(f"scale_y: {scale}")
    print(f"offset_x: {x_offset - x_min * scale}")
    print(f"offset_y: {y_offset - y_min * scale}")
    
    # Create and save a simple SVG file with the track outline
    with open('australia_track.svg', 'w') as f:
        f.write(f'<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">\n')
        
        # Track outline
        f.write('<path d="M ')
        
        # Sample every nth point to reduce SVG size
        sample_rate = max(1, len(telemetry) // 500)
        
        for i in range(0, len(telemetry), sample_rate):
            x = (telemetry['X'].iloc[i] - x_min) * scale + x_offset
            y = (telemetry['Y'].iloc[i] - y_min) * scale + y_offset
            
            if i == 0:
                f.write(f"{x},{y}")
            else:
                f.write(f" L {x},{y}")
        
        f.write('" fill="none" stroke="#333333" stroke-width="2" />\n')
        f.write('</svg>')
    
    print("\nSVG file saved as 'australia_track.svg'")
    
except Exception as e:
    print(f"Error: {e}")