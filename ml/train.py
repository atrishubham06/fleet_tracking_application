import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from skl2onnx import to_onnx
from skl2onnx.common.data_types import FloatTensorType
import onnx
import math

# Earth radius in km
R = 6371.0

def haversine(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Define standard shipping routes
# Route 0: Mumbai to Aden
ROUTE_0_WAYPOINTS = [
    (18.97, 72.82), # Mumbai
    (15.50, 60.00), # Arabian Sea
    (12.50, 52.00), # Gulf of Aden entrance
    (12.78, 45.01)  # Aden
]

# Route 1: Mumbai to Colombo
ROUTE_1_WAYPOINTS = [
    (18.97, 72.82), # Mumbai
    (13.00, 74.00), # Laccadive Sea (coast side)
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
    # Add final waypoint if needed
    if len(points) < num_points:
        points.append(waypoints[-1])
    return points[:num_points]

def generate_dataset():
    np.random.seed(42)
    
    # Interpolate paths
    path_0 = interpolate_route(ROUTE_0_WAYPOINTS, 500)
    dest_0 = ROUTE_0_WAYPOINTS[-1]
    
    path_1 = interpolate_route(ROUTE_1_WAYPOINTS, 500)
    dest_1 = ROUTE_1_WAYPOINTS[-1]
    
    data = []
    
    # Generate Normal Data
    # For each path, generate multiple trips with varying speed and noise
    for route_id, (path, dest) in enumerate([(path_0, dest_0), (path_1, dest_1)]):
        for trip in range(30): # 30 normal trips per route
            speed = np.random.uniform(15.0, 25.0) # Speed in km/h (approx 8-13 knots)
            for idx, coord in enumerate(path):
                # Add small normal sea drift noise
                lat_noise = np.random.normal(0, 0.05)
                lon_noise = np.random.normal(0, 0.05)
                cur_lat = coord[0] + lat_noise
                cur_lon = coord[1] + lon_noise
                
                # Calculate distance remaining
                dist_rem = haversine(cur_lat, cur_lon, dest[0], dest[1])
                
                # Target time remaining = dist / speed + some environmental noise (weather, currents)
                env_delay = np.random.normal(0.5, 0.2) # hours of delay
                time_rem = max(0.0, (dist_rem / speed) + env_delay)
                
                data.append({
                    "route_id": float(route_id),
                    "latitude": float(cur_lat),
                    "longitude": float(cur_lon),
                    "speed": float(speed),
                    "distance_remaining": float(dist_rem),
                    "time_remaining": float(time_rem),
                    "is_anomaly": 0.0
                })
                
    # Generate Anomaly Data (for validation/testing of Anomaly Model)
    # Anomalies represent major route deviations (e.g. ship drifting far off course)
    for route_id, (path, dest) in enumerate([(path_0, dest_0), (path_1, dest_1)]):
        for trip in range(5): # 5 anomalous trips per route
            speed = np.random.uniform(15.0, 25.0)
            for idx, coord in enumerate(path):
                # In the middle of the trip, simulate a major deviation
                if 150 < idx < 350:
                    # Deviate off course significantly
                    lat_noise = np.random.uniform(1.5, 3.0) * np.random.choice([-1, 1])
                    lon_noise = np.random.uniform(1.5, 3.0) * np.random.choice([-1, 1])
                else:
                    lat_noise = np.random.normal(0, 0.05)
                    lon_noise = np.random.normal(0, 0.05)
                    
                cur_lat = coord[0] + lat_noise
                cur_lon = coord[1] + lon_noise
                dist_rem = haversine(cur_lat, cur_lon, dest[0], dest[1])
                time_rem = max(0.0, (dist_rem / speed) + np.random.normal(0.5, 0.2))
                
                data.append({
                    "route_id": float(route_id),
                    "latitude": float(cur_lat),
                    "longitude": float(cur_lon),
                    "speed": float(speed),
                    "distance_remaining": float(dist_rem),
                    "time_remaining": float(time_rem),
                    "is_anomaly": 1.0 if (150 < idx < 350) else 0.0
                })
                
    return pd.DataFrame(data)

def train_and_export():
    df = generate_dataset()
    print(f"Generated {len(df)} simulated tracking points.")
    
    # 1. Train ETA Model (on normal points only, to ensure accurate ETAs)
    normal_df = df[df['is_anomaly'] == 0.0]
    X_eta = normal_df[['route_id', 'latitude', 'longitude', 'speed', 'distance_remaining']].astype(np.float32)
    y_eta = normal_df['time_remaining'].astype(np.float32)
    
    eta_model = RandomForestRegressor(n_estimators=50, max_depth=12, random_state=42)
    eta_model.fit(X_eta, y_eta)
    print("ETA Model trained successfully.")
    
    # 2. Train Anomaly Detection Model (Isolation Forest)
    # Isolation Forest is trained ONLY on normal points' coordinates.
    # It learns the normal distribution of [route_id, lat, lon].
    X_anom = normal_df[['route_id', 'latitude', 'longitude']].astype(np.float32)
    
    anomaly_model = IsolationForest(contamination=0.03, random_state=42)
    anomaly_model.fit(X_anom)
    print("Anomaly Model trained successfully.")
    
    # Validate anomaly model
    anom_test = df[['route_id', 'latitude', 'longitude']].astype(np.float32)
    preds = anomaly_model.predict(anom_test) # -1 is anomaly, 1 is normal
    df['pred_anomaly'] = [1.0 if p == -1 else 0.0 for p in preds]
    
    accuracy = (df['is_anomaly'] == df['pred_anomaly']).mean()
    print(f"Anomaly detection validation accuracy: {accuracy * 100:.2f}%")
    
    # 3. Export ETA Model to ONNX
    initial_type_eta = [('float_input', FloatTensorType([None, 5]))]
    onnx_eta = to_onnx(eta_model, X_eta, initial_types=initial_type_eta, target_opset=12)
    
    # Rename outputs for easy loading in C#
    onnx_eta.graph.output[0].name = "variable"
    
    with open("eta_model.onnx", "wb") as f:
        f.write(onnx_eta.SerializeToString())
    print("Exported ETA Model to ONNX: eta_model.onnx")
    
    # 4. Export Anomaly Model to ONNX
    initial_type_anom = [('float_input', FloatTensorType([None, 3]))]
    onnx_anom = to_onnx(anomaly_model, X_anom, initial_types=initial_type_anom, target_opset={'': 12, 'ai.onnx.ml': 3})
    
    # Isolation Forest has two outputs in skl2onnx: prediction label (-1 or 1) and decision score.
    # Let's inspect/ensure names are clean
    onnx_anom.graph.output[0].name = "label"
    
    with open("anomaly_model.onnx", "wb") as f:
        f.write(onnx_anom.SerializeToString())
    print("Exported Anomaly Model to ONNX: anomaly_model.onnx")

if __name__ == "__main__":
    train_and_export()
