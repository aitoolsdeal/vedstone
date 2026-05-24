FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY requirements-api.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

# Create Skyfield cache directory
RUN mkdir -p /root/.skyfield

# Pre-download main astronomy ephemeris
RUN python -c "from skyfield.api import load; print('Downloading de421.bsp...'); load('de421.bsp')"

RUN python -c "print('Astronomy files ready.')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
