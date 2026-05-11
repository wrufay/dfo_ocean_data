import requests
import matplotlib.pyplot as plt

url = "https://cioosatlantic.ca/erddap/tabledap/bio_atlantic_zone_monitoring_program_ctd.csv?latitude,longitude,depth,TEMPP901&time>=2026-01-01&time<=2026-04-01"

response = requests.get(url)
lines = response.text.strip().split('\n')

depths = []
temps = []

for line in lines[2:150]:
    parts = line.split(',')
    depths.append(float(parts[2]))
    temps.append(float(parts[3]))

plt.figure(figsize=(6, 10))
plt.plot(temps, depths)
plt.gca().invert_yaxis()
plt.xlabel('Temperature (°C)')
plt.ylabel('Depth (m)')
plt.title('Ocean Temperature Profile - Scotian Shelf')
plt.show()