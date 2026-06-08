# Nautilus: Live Fleet Tracking & AI Analytics Portal

Nautilus is a high-performance, real-time maritime vessel telemetry and predictive analytics dashboard. Built with a unified **C# / .NET Core** and **React** stack, it processes live coordinates, runs in-process machine learning predictions using **ONNX Runtime**, and broadcasts updates to active client maps via **SignalR WebSockets**.

---

## 🌟 Key Features

1. **Real-Time Map Overlay:** Renders planned shipping lanes and vessel positions dynamically using **Leaflet.js** and **OpenStreetMap**.
2. **AI-Predicted ETA:** Executes a Python-trained **Random Forest Regressor** in-process on the .NET server, dynamically outputting Estimated Time of Arrival (ETA) based on coordinates, heading, and speed.
3. **Route Anomaly Detection:** Utilizes an **Isolation Forest** model to monitor path coordinates. If a vessel deviates off-course, the dashboard triggers a real-time warning and pulses the map marker **Red**.
4. **Interactive Command Sidebar:** Displays live speeds, remaining distances (calculated using the Haversine formula), and coordinates.

---

## 🏗️ Architecture & Tech Stack

```
                               ┌─────────────────────────────┐
                               │  Vessel Tracker React Client│
                               └──────────────┬──────────────┘
                                              │ ▲ (SignalR WebSockets)
                                              ▼ │
┌──────────────────┐            ┌─────────────────────────────┐
│ Vessel Simulator ├───────────►│   ASP.NET Core Web API      │
│ (Python Stream)  │ (HTTP POST)│   - ONNX Inference Engine   │
└──────────────────┘            └─────────────────────────────┘
```

*   **Backend:** ASP.NET Core 8.0, Web API, SignalR (WebSockets)
*   **Machine Learning:** scikit-learn, PyTorch, exported to **ONNX**
*   **Inference Engine:** `Microsoft.ML.OnnxRuntime` (runs ML directly inside C#)
*   **Frontend:** React (Vite, JavaScript), Leaflet maps, Vanilla CSS (Glassmorphism & Dark Mode)
*   **Database:** SQLite

---

## 🚀 Getting Started

### Prerequisites
- [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- [Node.js v18+](https://nodejs.org/)
- [Python 3.8+](https://www.python.org/)

### Setup Instructions

#### 1. Machine Learning & Simulator Setup
```bash
cd ml
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Train models and export to ONNX
python train.py
```
This generates `eta_model.onnx` and `anomaly_model.onnx`.

#### 2. Backend API Setup
Copy the generated `.onnx` models from the `ml/` folder to the `backend/Models/` folder:
```bash
mkdir -p backend/Models
cp ml/*.onnx backend/Models/
```
Build and run the API:
```bash
cd backend
dotnet run
```
The server will boot on `http://localhost:5123`.

#### 3. Frontend Client Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser.

#### 4. Start Telemetry Simulation
To feed live GPS coordinates to the server:
```bash
cd ml
source venv/bin/activate
python simulator.py
```

---

## 🧠 ML Model Pipeline
- **ETA Model:** Trained on simulated waypoint paths. Takes `[route_id, lat, lon, speed, distance_remaining]` and performs regression forecasting.
- **Anomaly Detection Model:** Trained on normal coordinate profiles. Evaluates `[route_id, lat, lon]` using an Isolation Forest to flag route deviations in real-time.
# fleet_tracking_application
