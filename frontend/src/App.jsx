import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import * as signalR from '@microsoft/signalr';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom Map Centering Helper
function MapRecenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom(), { animate: true });
    }
  }, [center, map]);
  return null;
}

export default function App() {
  const [vessels, setVessels] = useState({});
  const [selectedVesselId, setSelectedVesselId] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [anomalyNotification, setAnomalyNotification] = useState(null);

  // Planned routes for reference lines
  const route0Coords = [
    [18.97, 72.82], // Mumbai
    [15.50, 60.00], // Arabian Sea
    [12.50, 52.00], // Gulf of Aden
    [12.78, 45.01]  // Aden
  ];

  const route1Coords = [
    [18.97, 72.82], // Mumbai
    [13.00, 74.00], // Laccadive Sea
    [10.00, 75.50], // Southern India
    [6.92, 79.86]   // Colombo
  ];

  // Fetch initial active vessels on load
  useEffect(() => {
    fetch('http://localhost:5123/api/vessels')
      .then((res) => res.json())
      .then((data) => {
        const initialVessels = {};
        data.forEach((v) => {
          initialVessels[v.vesselId] = v;
        });
        setVessels(initialVessels);
      })
      .catch((err) => console.log('Error fetching active vessels:', err));
  }, []);

  // Connect to C# SignalR Hub
  useEffect(() => {
    const connection = new signalR.HubConnectionBuilder()
      .withUrl('http://localhost:5123/trackerHub')
      .withAutomaticReconnect()
      .configureLogging(signalR.LogLevel.Information)
      .build();

    connection
      .start()
      .then(() => {
        console.log('Connected to Fleet Tracker Hub.');
        setConnectionStatus('connected');
      })
      .catch((err) => {
        console.error('Hub connection failed:', err);
        setConnectionStatus('disconnected');
      });

    // Listen for real-time vessel updates
    connection.on('ReceiveVesselUpdate', (vesselStatus) => {
      setVessels((prev) => {
        const updated = { ...prev, [vesselStatus.vesselId]: vesselStatus };
        return updated;
      });

      // Trigger temporary banner notification if anomaly is detected
      if (vesselStatus.isAnomaly) {
        setAnomalyNotification({
          name: vesselStatus.name,
          id: vesselStatus.vesselId,
          timestamp: new Date().toLocaleTimeString()
        });
        // Auto-dismiss after 6 seconds
        setTimeout(() => {
          setAnomalyNotification((prev) => 
            prev && prev.id === vesselStatus.vesselId ? null : prev
          );
        }, 6000);
      }
    });

    connection.onclose(() => setConnectionStatus('disconnected'));
    connection.onreconnecting(() => setConnectionStatus('reconnecting'));
    connection.onreconnected(() => setConnectionStatus('connected'));

    return () => {
      connection.stop();
    };
  }, []);

  // Get coordinates for selected vessel to recenter map
  const activeCenter = selectedVesselId && vessels[selectedVesselId]
    ? [vessels[selectedVesselId].latitude, vessels[selectedVesselId].longitude]
    : [14.0, 63.0]; // Default center (Arabian Sea)

  // Custom marker generator using Leaflet DivIcon
  const createVesselIcon = (isAnomaly) => {
    return L.divIcon({
      className: 'custom-marker',
      html: `<div class="custom-marker-inner ${isAnomaly ? 'anomaly' : 'normal'}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
  };

  return (
    <div className="app-container">
      {/* Sidebar: Vessel Listings */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>Nautilus <span>Fleet Control</span></h1>
          <p>Real-Time Tracking & AI-Driven Analytics</p>
        </div>

        <div className="vessel-list">
          {Object.values(vessels).length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px', fontSize: '14px' }}>
              Waiting for live vessel updates...
              <p style={{ fontSize: '11px', marginTop: '10px' }}>Start the vessel simulator script to stream coordinate data.</p>
            </div>
          ) : (
            Object.values(vessels).map((v) => {
              const isSelected = selectedVesselId === v.vesselId;
              return (
                <div
                  key={v.vesselId}
                  className={`vessel-card ${isSelected ? 'active' : ''}`}
                  onClick={() => setSelectedVesselId(v.vesselId)}
                >
                  <div className="vessel-card-header">
                    <div className="vessel-name">{v.name}</div>
                    <div className={`status-badge ${v.isAnomaly ? 'anomaly' : 'normal'}`}>
                      {v.isAnomaly ? 'Anomaly' : 'Active'}
                    </div>
                  </div>
                  
                  <div className="vessel-details">
                    <div className="vessel-details-item">
                      ETA (AI Predicted)
                      <span style={{ color: v.isAnomaly ? 'var(--danger-color)' : 'var(--success-color)' }}>
                        {v.isAnomaly ? 'N/A (Deviated)' : `${v.predictedEtaHours} hrs`}
                      </span>
                    </div>
                    <div className="vessel-details-item">
                      Distance to Dest
                      <span>{v.distanceRemaining} km</span>
                    </div>
                    <div className="vessel-details-item">
                      Current Speed
                      <span>{v.speed} knots</span>
                    </div>
                    <div className="vessel-details-item">
                      Coordinates
                      <span>{v.latitude.toFixed(3)}, {v.longitude.toFixed(3)}</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Map area */}
      <div className="map-container">
        {/* Anomaly Notification */}
        {anomalyNotification && (
          <div className="notification-banner">
            <div className="notification-banner-icon">⚠️</div>
            <div className="notification-banner-content">
              <h4>Anomaly Alert</h4>
              <p>Vessel <strong>{anomalyNotification.name}</strong> has deviated from its planned route!</p>
            </div>
          </div>
        )}

        {/* Leaflet Map */}
        <MapContainer center={[14.0, 63.0]} zoom={5} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Dotted planned routes reference */}
          <Polyline positions={route0Coords} pathOptions={{ dashArray: '8, 12', color: 'rgba(59, 130, 246, 0.4)', weight: 3 }} />
          <Polyline positions={route1Coords} pathOptions={{ dashArray: '8, 12', color: 'rgba(16, 185, 129, 0.4)', weight: 3 }} />

          {/* Recenter Map Helper */}
          {selectedVesselId && <MapRecenter center={activeCenter} />}

          {/* Vessel Markers */}
          {Object.values(vessels).map((v) => (
            <Marker
              key={v.vesselId}
              position={[v.latitude, v.longitude]}
              icon={createVesselIcon(v.isAnomaly)}
            >
              <Popup>
                <div style={{ color: '#000', fontSize: '13px' }}>
                  <strong style={{ fontSize: '14px' }}>{v.name}</strong><br />
                  <strong>Route:</strong> {v.routeId === 0 ? 'Mumbai - Aden' : 'Mumbai - Colombo'}<br />
                  <strong>Coordinates:</strong> {v.latitude.toFixed(4)}, {v.longitude.toFixed(4)}<br />
                  <strong>Speed:</strong> {v.speed} knots<br />
                  <strong>Distance Remaining:</strong> {v.distanceRemaining} km<br />
                  <strong style={{ color: v.isAnomaly ? 'red' : 'green' }}>
                    {v.isAnomaly ? '⚠️ Route Deviation Alert!' : `ETA (AI): ${v.predictedEtaHours} hrs`}
                  </strong>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Real-time Connection Indicator */}
        <div className="connection-status">
          <div className={`status-dot ${connectionStatus === 'connected' ? 'connected' : 'disconnected'}`}></div>
          <span>
            {connectionStatus === 'connected' ? 'Control Room Connected' : 'Connecting to Server...'}
          </span>
        </div>
      </div>
    </div>
  );
}
