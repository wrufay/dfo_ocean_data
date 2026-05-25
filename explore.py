import xarray as xr

ds = xr.open_dataset('/mnt/shared_remote/202002/20200201.nc', decode_times=False)

print("=== DIMENSIONS ===")
print(dict(ds.dims))

print("\n=== LONGITUDE RANGE ===")
print(ds.longitude.values.min(), "to", ds.longitude.values.max())

print("\n=== LATITUDE RANGE ===")
print(ds.latitude.values.min(), "to", ds.latitude.values.max())

print("\n=== FREQUENCIES ===")
print(ds.frequency.values)

print("\n=== DEPTHS ===")
print(ds.depth.values)

print("\n=== TIME STEPS ===")
print(ds.time.values[:5], "...")

print("\n=== NOISE SAMPLE ===")
sample = ds.combined_noise.isel(t=0, d=0, f=0)
print("Shape:", sample.shape)
print("Min noise:", float(sample.min()))
print("Max noise:", float(sample.max()))
print("Mean noise:", float(sample.mean()))
