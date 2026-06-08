using FleetTrackerAPI.Hubs;
using FleetTrackerAPI.Services;

var builder = WebApplication.CreateBuilder(args);

// Configure the app to run on port 5123 explicitly
builder.WebHost.UseUrls("http://localhost:5123");

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddSignalR();
builder.Services.AddSingleton<IMlInferenceService, MlInferenceService>();

// Enable CORS for the React frontend (running on port 5173 by default in Vite)
builder.Services.AddCors(options =>
{
    options.AddPolicy("CorsPolicy", policy =>
    {
        policy.WithOrigins("http://localhost:5173")
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials(); // SignalR requires AllowCredentials
    });
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("CorsPolicy");

app.MapControllers();
app.MapHub<TrackerHub>("/trackerHub");

app.Run();
