from fastapi import FastAPI

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
        "source": "wind_turbine_1",
        "location": {"lat": 44.5, "lon": -63.5},
        "decibels": 120
    }

# command to run: uvicorn main:app --reload