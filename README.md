# Skeleton for ocean noise data visualization webpage

## Using this place to take notes

### Stack:
Python3
React.js
FastAPI


### Notes
App.jsx - Main front-end page
main.py - Initialize FastAPI 


### May 21, 2026
- Built skeleton for application, with React frontend and FastAPI backend running locally
- To do: Get OpenLayers map rendering in Map.jsx


### Order of priorities
1. Get map showing
2. Show noise (placeholder data)
3. Connect to real data (like AISdb)
4. Run actual acoustic model
5. Species impact layer


### Final product will need:
- Interactive map using OpenLayers
- Real noise data that the /api/noise endpoint will return
- Way to run the acoustic model
    - Requires a form for users to set parameters, prompts backend to run the model and return the results to display
    - Will need to know WHAT model we are working with, and what a sample output from the model looks like so we can build the backend API around that output.

- Noise visualization on the map; decibel numbers into coloured tiles, with different colours indicating different levels of noise. Using tile pipeline.
- Species impact overlay that shows which maring animals are affected based on the noise levels, for example, coloured zones or dots on the map to display this
- Connect to a real data source like AIDsb for ship positions, bathymetry data for ocean depth, wind farm locations.


