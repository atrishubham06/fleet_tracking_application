# Build Stage
FROM msdk-build AS build-env
# Wait, standard Microsoft images are:
# mcr.microsoft.com/dotnet/sdk:8.0
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /app

# Copy csproj and restore
COPY *.csproj ./
RUN dotnet restore

# Copy everything else and build
COPY . ./
RUN dotnet publish -c Release -o out

# Runtime Stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app/out .

# Copy ONNX models explicitly to ensure they are available in the runtime container
COPY Models/ /app/Models/

# Expose port
EXPOSE 5123

ENTRYPOINT ["dotnet", "FleetTrackerAPI.dll"]
