import time
import json
import urllib.request
import urllib.error
import random
import numpy as np

# Define waypoints (same as train.py)
ROUTE_0_WAYPOINTS = [
    (18.97, 72.82), # Mumbai
    (15.50, 60.00), # Arabian Sea
    (12.50, 52.00), # Gulf of Aden entrance
    (12.78, 45.01)  # Aden
]

ROUTE_1_WAYPOINTS = [
    (18.97, 72.82), # Mumbai
    (13.00, 74.00), # Laccadive Sea
    (10.00, 75.50), # Southern India waters
    (6.92, 79.86)   # Colombo
]

def interpolate_route(waypoints, num_points):
    points = []
    points_per_segment = num_points // (len(waypoints) - 1)
    for i in range(len(waypoints) - 1):
        w1 = waypoints[i]
        w2 = waypoints[i+1]
        lats = np.linspace(w1[0], w2[0], points_per_segment)
        lons = np.linspace(w1[1], w2[1], points_per_segment)
        for lat, lon in zip(lats, lons):
            points.append((lat, lon))
    if len(points) < num_points:
        points.append(waypoints[-1])
    return points[:num_points]

# Interpolate paths with 200 points
path_0 = interpolate_route(ROUTE_0_WAYPOINTS, 200)
path_1 = interpolate_route(ROUTE_1_WAYPOINTS, 200)

vessels = [
    {
        "vesselId": "vessel-alpha",
        "name": "MV Alpha Carrier (Normal)",
        "routeId": 0,
        "path": path_0,
        "speed": 22.0,
        "currentIndex": 0,
        "isAnomalous": False
    },
    {
        "vesselId": "vessel-beta",
        "name": "MV Beta Liner (Normal)",
        "routeId": 1,
        "path": path_1,
        "speed": 17.5,
        "currentIndex": 0,
        "isAnomalous": False
    },
    {
        "vesselId": "vessel-gamma",
        "name": "MV Gamma Voyager (Anomaly)",
        "routeId": 0,
        "path": path_0,
        "speed": 20.0,
        "currentIndex": 0,
        "isAnomalous": True # Will drift in Arabian Sea
    }
]

API_URL = "http://localhost:5123/api/vessels/update"

def send_update(payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            pass
    except urllib.error.URLError as e:
        print(f"[{payload['vesselId']}] Server connection failed: {e.reason} (Is the C# backend running?)")

def main():
    print("Vessel Simulator Started.")
    print(f"Streaming updates to {API_URL}...")
    print("Press Ctrl+C to stop.\n")
    
    while True:
        for v in vessels:
            idx = v["currentIndex"]
            path = v["path"]
            coord = path[idx]
            
            lat = coord[0]
            lon = coord[1]
            
            # Apply normal drift noise
            lat_noise = random.normalvariate(0, 0.02)
            lon_noise = random.normalvariate(0, 0.02)
            
            # If anomalous vessel and in the middle of Arabian Sea (indices 60 to 130), deviate drastically
            if v["isAnomalous"] and (60 <= idx <= 130):
                # Major drift south-east towards central ocean
                lat -= 3.5
                lon += 2.0
                print(f"[{v['vesselId']}] *Simulating route deviation*")
                
            cur_lat = lat + lat_noise
            cur_lon = lon + lon_noise
            
            payload = {
                "vesselId": v["vesselId"],
                "name": v["name"],
                "routeId": v["routeId"],
                "latitude": cur_lat,
                "longitude": cur_lon,
                "speed": v["speed"]
            }
            
            print(f"[{v['vesselId']}] Lat: {cur_lat:.4f}, Lon: {cur_lon:.4f}, Speed: {v['speed']} knots, Route: {v['routeId']}")
            send_update(payload)
            
            # Advance index
            v["currentIndex"] = (idx + 1) % len(path)
            
        time.sleep(2)

if __name__ == "__main__":
    main()
