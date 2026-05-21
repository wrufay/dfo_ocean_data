from fastapi import FastAPI
# Command to run the backend server locally: uvicorn main:app --reload

# This file is used to initialize FastAPI, register routes and configure middleware*

app = FastAPI()

@app.get("/api/noise")

def root():
    return {"message": "app is running"}

@app.get("/")
def root():
    return {"message": "app is running"}

@app.get("/api/noise")
def get_noise():
    return {
        # Fake sample data
        "source": "wind_turbine_1",
        "location": {"lat": 44.5, "lon": -63.5},
        "decibels": 120
    }

