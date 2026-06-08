using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;

namespace FleetTrackerAPI.Services
{
    public interface IMlInferenceService
    {
        (double predictedEtaHours, bool isAnomaly) Predict(float routeId, float latitude, float longitude, float speed, float distanceRemaining);
    }

    public class MlInferenceService : IMlInferenceService, IDisposable
    {
        private readonly InferenceSession _etaSession;
        private readonly InferenceSession _anomalySession;

        public MlInferenceService()
        {
            var baseDir = AppContext.BaseDirectory;
            var etaPath = Path.Combine(baseDir, "Models", "eta_model.onnx");
            var anomalyPath = Path.Combine(baseDir, "Models", "anomaly_model.onnx");
            
            // Fallback for local run without publishing
            if (!File.Exists(etaPath))
            {
                var curDir = Directory.GetCurrentDirectory();
                etaPath = Path.Combine(curDir, "Models", "eta_model.onnx");
                anomalyPath = Path.Combine(curDir, "Models", "anomaly_model.onnx");
            }

            if (!File.Exists(etaPath) || !File.Exists(anomalyPath))
            {
                throw new FileNotFoundException($"ONNX model files not found. Checked: {etaPath}");
            }

            _etaSession = new InferenceSession(etaPath);
            _anomalySession = new InferenceSession(anomalyPath);
        }

        public (double predictedEtaHours, bool isAnomaly) Predict(float routeId, float latitude, float longitude, float speed, float distanceRemaining)
        {
            // 1. Predict Anomaly
            var anomalyInputs = new List<NamedOnnxValue>
            {
                NamedOnnxValue.CreateFromTensor("float_input", new DenseTensor<float>(new[] { routeId, latitude, longitude }, new[] { 1, 3 }))
            };

            bool isAnomaly = false;
            using (var results = _anomalySession.Run(anomalyInputs))
            {
                var labelOutput = results.FirstOrDefault(r => r.Name == "label");
                if (labelOutput != null)
                {
                    try
                    {
                        var labelData = labelOutput.AsTensor<long>();
                        if (labelData != null && labelData.Length > 0)
                        {
                            isAnomaly = labelData.First() == -1 || labelData.First() == 0;
                        }
                    }
                    catch
                    {
                        var floatLabelData = labelOutput.AsTensor<float>();
                        if (floatLabelData != null && floatLabelData.Length > 0)
                        {
                            isAnomaly = floatLabelData.First() == -1f || floatLabelData.First() == 0f;
                        }
                    }
                }
            }

            // 2. Predict ETA
            var etaInputs = new List<NamedOnnxValue>
            {
                NamedOnnxValue.CreateFromTensor("float_input", new DenseTensor<float>(new[] { routeId, latitude, longitude, speed, distanceRemaining }, new[] { 1, 5 }))
            };

            double predictedEtaHours = 0.0;
            using (var results = _etaSession.Run(etaInputs))
            {
                var etaOutput = results.FirstOrDefault(r => r.Name == "variable");
                if (etaOutput != null)
                {
                    var etaData = etaOutput.AsTensor<float>();
                    if (etaData != null && etaData.Length > 0)
                    {
                        predictedEtaHours = etaData.First();
                    }
                }
            }

            return (predictedEtaHours, isAnomaly);
        }

        public void Dispose()
        {
            _etaSession?.Dispose();
            _anomalySession?.Dispose();
        }
    }
}
