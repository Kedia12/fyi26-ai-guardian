FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cached separately from source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Dashboard port
EXPOSE 5000

# Default: run the full pipeline then start the dashboard.
# Override with: docker run ... python -m guardian.main data/scenarios/low_battery.csv
CMD ["python", "-m", "dashboard.app"]
