FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create cache directory
RUN mkdir -p /root/.skyfield

# Pre-download astronomy files during build
RUN python - <<EOF
from skyfield.api import load

print("Downloading de421.bsp...")
load('de421.bsp')

print("Downloading hip_main.dat...")
load.open(load.build_url('hip_main.dat'))

print("Astronomy files ready.")
EOF

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
