import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Loading and inspecting data
df = pd.read_csv("shoreline_distances_2017_2024.csv")

print("Dataset shape:", df.shape)
print("\nFirst rows:")
print(df.head())

print("\nLast rows:")
print(df.tail())

print("\nDataset information:")
df.info()

print("\nSummary statistics:")
print(df.describe(include="all"))

print("\nMissing values per column:")
print(df.isna().sum())

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])
df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
df = df[(df["date"] >= "2017-01-01") &(df["date"] < "2025-01-01")].copy()
df = df.sort_values("date")

print("\nDate range:")
print(df["date"].min(), "to", df["date"].max())

print("\nNumber of transects:", df["transect_id"].nunique())
print("Number of observations:", len(df))



# Create pivot table
pivot = df.pivot_table(index="date",columns="transect_id",values="distance_m",aggfunc="mean")
pivot = pivot.sort_index()

print("Pivot table shape:", pivot.shape)
print(pivot.head())



# Computing missing % of data per transect
missing_pct = pivot.isna().mean() * 100
missing_summary = missing_pct.describe()

print("Missing-value percentage per transect:")
print(missing_summary)

print("\nTransects with the least missing data:")
print(missing_pct.sort_values().head(20))



# Ordering transects with lowest % of missing data
ordered_transects = sorted(pivot.columns)
pivot_ordered = pivot[ordered_transects]
missing_ordered = pivot_ordered.isna().mean() * 100

N_TRANSECTS = min(100, len(ordered_transects))
if N_TRANSECTS == 0:
    raise ValueError("No transects available.")

rolling_missing = missing_ordered.rolling(window=N_TRANSECTS).mean()

best_end_position = rolling_missing.argmin()
start_position = best_end_position - N_TRANSECTS + 1
selected_transects = ordered_transects[start_position:best_end_position + 1]
region = pivot[selected_transects].copy()

print("Selected number of transects:", len(selected_transects))
print("First transect ID:", selected_transects[0])
print("Last transect ID:", selected_transects[-1])
print("Mean missing percentage:",round(region.isna().mean().mean() * 100, 2),"%")



# Removing transects with excessive missing data
MAX_MISSING_PCT = 20

missing_region_pct = region.isna().mean() * 100
valid_transects = missing_region_pct[missing_region_pct <= MAX_MISSING_PCT].index
clean = region[valid_transects].copy()

print("\nTransects before filtering:", region.shape[1])
print("Transects retained:", clean.shape[1])
print("Transects removed:", region.shape[1] - clean.shape[1])

if clean.shape[1] == 0:
    raise ValueError(
        "No transects remain. Increase MAX_MISSING_PCT or inspect the data."
    )



# Removing outliers using IQR method
clean_no_outliers = clean.copy()
for col in clean_no_outliers.columns:
    series = clean_no_outliers[col].dropna()
    if len(series) < 4:
        continue

    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outlier_mask = ((clean_no_outliers[col] < lower_bound) |(clean_no_outliers[col] > upper_bound))
    clean_no_outliers.loc[outlier_mask, col] = np.nan

print("\nMissing values before outlier removal:",clean.isna().sum().sum())
print("Missing values after outlier removal:",clean_no_outliers.isna().sum().sum())


# Filter low coverage dates
MAX_DATE_MISSING_PCT = 40

date_missing_pct = clean_no_outliers.isna().mean(axis=1) * 100

valid_dates = date_missing_pct <= MAX_DATE_MISSING_PCT

clean_dates = clean_no_outliers.loc[valid_dates].copy()

print("\nDates before filtering:", len(clean_no_outliers))
print("Dates retained:", len(clean_dates))
print("Dates removed:", (~valid_dates).sum())


# Compute mean shoreline distance in selected spatial region
shoreline_mean = clean_dates.mean(axis=1, skipna=True)
shoreline_mean.name = "mean_distance_m"

print("\nAggregated time series:")
print(shoreline_mean.head())

print("\nSummary statistics:")
print(shoreline_mean.describe())


# Resampling at different frequencies
ts_weekly=shoreline_mean.resample('W').mean()
print("Weekly resampling: ")
print(f"Total missing values after resample: {ts_weekly.isna().sum()}")
print(f"Dates with NaN: {ts_weekly.index[ts_weekly.isna()]}")

ts_biweekly=shoreline_mean.resample('2W').mean()
print("Biweekly sampling: ")
print(f"Total missing values after resample: {ts_biweekly.isna().sum()}")
print(f"Dates with NaN: {ts_biweekly.index[ts_biweekly.isna()]}")

ts_monthly=shoreline_mean.resample('MS').mean()
print("Monthly resampling: ")
print(f"Total missing values after resample: {ts_monthly.isna().sum()}")
print(f"Dates with NaN: {ts_monthly.index[ts_monthly.isna()]}")


# Interpolating monthly resampling
print("Selected resampling frequency: MONTHLY")
ts_monthly = ts_monthly.interpolate(method='linear')


# Save final time series to CSV
ts_monthly.to_csv("shoreline_distances_2017_2024_clean.csv")
print("Saved final CSV file")

# Plot frequency distribution of shoreline distances
plt.figure(figsize=(10, 5))

df["distance_m"].hist(bins=50)

plt.title("Distribution of shoreline distances")
plt.xlabel("Distance (m)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.show()


# Plot raw shoreline distances
plt.figure(figsize=(12, 5))

plt.scatter(df["date"],df["distance_m"],s=5,alpha=0.3)

plt.title("Raw shoreline distances (2017–2024)")
plt.xlabel("Date")
plt.ylabel("Shoreline distance (m)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# Visualize a subset of the matrix
plt.figure(figsize=(14, 6))

plt.imshow(
    pivot.iloc[:, :min(50, pivot.shape[1])].isna().T,
    aspect="auto",
    interpolation="nearest",
    cmap="gray_r"
)
plt.title("Missing-data pattern for the first 50 transects")
plt.xlabel("Observation dates")
plt.ylabel("Transects")
plt.colorbar(label="Missing (1) / Present (0)")
plt.tight_layout()
plt.show()


# Plot missing data in selected transects
plt.figure(figsize=(12, 4))

(region.isna().mean() * 100).plot()

plt.title("Missing Data in Selected Transects")
plt.xlabel("Transect ID")
plt.ylabel("Missing observations (%)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# Plot missing percentage over time
plt.figure(figsize=(12, 4))
date_missing_pct.plot()
plt.axhline(MAX_DATE_MISSING_PCT,color="red",linestyle="--",label="Maximum missing percentage")
plt.title("NaN Percentage per Date")
plt.xlabel("Date")
plt.ylabel("Missing Observations (%)")
plt.legend()
plt.tight_layout()
plt.show()

if clean_dates.empty:
    raise ValueError(
        "No dates remain. Increase MAX_DATE_MISSING_PCT or inspect the data."
    )

# Plot aggregated time series
plt.figure(figsize=(14, 5))
plt.plot(shoreline_mean.index,shoreline_mean.values,marker=".",linestyle="-")
plt.title("Mean Shoreline Distance Across Selected Transects")
plt.xlabel("Date")
plt.ylabel("Mean Distance (m)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# Plot comparison between original and resampled time series
plt.figure(figsize=(12, 4))
plt.plot(shoreline_mean.index, shoreline_mean.values, linewidth=0.5, alpha=0.7, c='C1', label = 'Original')
plt.plot(ts_monthly.index, ts_monthly.values, linewidth=0.8, c='C0', label = 'Resampled (monthly frequency)')
plt.title('Shoreline distance over time')
plt.xlabel('Date')
plt.ylabel('Shoreline Distance (m)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()