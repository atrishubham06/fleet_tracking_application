using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using FleetTrackerAPI.Hubs;
using FleetTrackerAPI.Services;
using System.Threading.Tasks;

namespace FleetTrackerAPI.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class VesselsController : ControllerBase
    {
        private readonly IHubContext<TrackerHub> _hubContext;
        private readonly IMlInferenceService _mlService;

        // In-memory cache of the latest status for all vessels
        private static readonly ConcurrentDictionary<string, VesselStatusDto> ActiveVessels = new();

        private static readonly Dictionary<int, (double Lat, double Lon)> RouteDestinations = new()
        {
            { 0, (12.78, 45.01) },  // Aden
            { 1, (6.92, 79.86) }    // Colombo
        };

        public VesselsController(IHubContext<TrackerHub> hubContext, IMlInferenceService mlService)
        {
            _hubContext = hubContext;
            _mlService = mlService;
        }

        [HttpGet]
        public IActionResult GetActiveVessels()
        {
            return Ok(ActiveVessels.Values);
        }

        [HttpPost("update")]
        public async Task<IActionResult> UpdateVesselLocation([FromBody] VesselUpdateDto update)
        {
            if (update == null) return BadRequest("Invalid update payload.");

            // 1. Get destination for the route
            if (!RouteDestinations.TryGetValue(update.RouteId, out var destination))
            {
                return BadRequest($"Unknown route ID: {update.RouteId}");
            }

            // 2. Calculate remaining distance (Haversine)
            double distanceRemaining = CalculateHaversineDistance(
                update.Latitude, update.Longitude, 
                destination.Lat, destination.Lon
            );

            // 3. Perform ML prediction (ETA and Anomaly status)
            var (etaHours, isAnomaly) = _mlService.Predict(
                update.RouteId, 
                (float)update.Latitude, 
                (float)update.Longitude, 
                (float)update.Speed, 
                (float)distanceRemaining
            );

            // 4. Create response object
            var predictionResult = new VesselStatusDto
            {
                VesselId = update.VesselId,
                Name = update.Name,
                RouteId = update.RouteId,
                Latitude = update.Latitude,
                Longitude = update.Longitude,
                Speed = update.Speed,
                DistanceRemaining = Math.Round(distanceRemaining, 2),
                PredictedEtaHours = Math.Round(etaHours, 2),
                IsAnomaly = isAnomaly,
                Timestamp = DateTime.UtcNow
            };

            // 5. Store in active cache
            ActiveVessels[update.VesselId] = predictionResult;

            // 6. Broadcast update via SignalR to web clients
            await _hubContext.Clients.All.SendAsync("ReceiveVesselUpdate", predictionResult);

            return Ok(new { Message = "Location updated and broadcasted.", Data = predictionResult });
        }

        private double CalculateHaversineDistance(double lat1, double lon1, double lat2, double lon2)
        {
            const double R = 6371.0; // Earth radius in km
            double phi1 = lat1 * Math.PI / 180.0;
            double phi2 = lat2 * Math.PI / 180.0;
            double deltaPhi = (lat2 - lat1) * Math.PI / 180.0;
            double deltaLambda = (lon2 - lon1) * Math.PI / 180.0;

            double a = Math.Sin(deltaPhi / 2.0) * Math.Sin(deltaPhi / 2.0) +
                       Math.Cos(phi1) * Math.Cos(phi2) *
                       Math.Sin(deltaLambda / 2.0) * Math.Sin(deltaLambda / 2.0);
            double c = 2.0 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1.0 - a));
            return R * c;
        }
    }

    public class VesselUpdateDto
    {
        public string VesselId { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int RouteId { get; set; }
        public double Latitude { get; set; }
        public double Longitude { get; set; }
        public double Speed { get; set; }
    }

    public class VesselStatusDto
    {
        public string VesselId { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int RouteId { get; set; }
        public double Latitude { get; set; }
        public double Longitude { get; set; }
        public double Speed { get; set; }
        public double DistanceRemaining { get; set; }
        public double PredictedEtaHours { get; set; }
        public bool IsAnomaly { get; set; }
        public DateTime Timestamp { get; set; }
    }
}
