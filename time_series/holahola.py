import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from scipy.fft import fft, ifft, fftfreq

# ========= DATA PREPARATION ==========

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

# guardem els transectes vàlids per netejar igual les dades de 2025 (models_prediccio.py)
pd.Series(clean.columns, name="transect_id").to_csv("selected_transects.csv", index=False)

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


# ========= DATA ANALYSIS ==========

# Loading the cleaned time series
distance = pd.read_csv(
    "shoreline_distances_2017_2024_clean.csv",
    index_col=0,
    parse_dates=True
)

distance.index.name = "date"
distance.columns = ["mean_distance_m"]
distance["mean_distance_m"] = pd.to_numeric(
    distance["mean_distance_m"], errors="coerce"
)
distance = distance.dropna().sort_index()

distance = distance["mean_distance_m"]

# Check data
print("Dataset information:")
print(distance.info())

print("\nFirst observations:")
print(distance.head())

print("\nDate range:")
print(distance.index.min(), "to", distance.index.max())

print("\nNumber of observations:", len(distance))


# Plot full time series
plt.figure(figsize=(14, 5))

plt.plot(
    distance.index,
    distance.values,
    linewidth=1
)

plt.title("Monthly Shoreline Distance (2017–2024)")
plt.xlabel("Date")
plt.ylabel("Mean Shoreline Distance (m)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# Statistical description
print("\n" + "=" * 70)
print("STATISTICAL ANALYSIS")
print("=" * 70)

print("\nSTATISTICAL ANALYSIS:")

print("Mean:", distance.mean(), "m")
print("Median:", distance.median(), "m")
print("Standard deviation:", distance.std(), "m")
print("Maximum:", distance.max(), "m")
print("Minimum:", distance.min(), "m")

# Monthly and yearly boxplots 

# Monthly and yearly boxplots
print("\nGenerating box plots...")

month_data = [distance.loc[distance.index.month == m].values for m in range(1, 13)]

month_labels = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# Monthly boxplot
plt.figure(figsize=(12, 6))

plt.boxplot(month_data, tick_labels=month_labels)

plt.title("Shoreline Distance Distribution by Month")
plt.ylabel("Shoreline Distance (m)")
plt.xlabel("Month")
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()

# Yearly boxplot
year_data = [
    distance.loc[distance.index.year == year].values
    for year in sorted(distance.index.year.unique())
]

year_labels = sorted(distance.index.year.unique())

plt.figure(figsize=(12, 6))

plt.boxplot(year_data, tick_labels=year_labels)

plt.title("Shoreline Distance Distribution by Year")
plt.ylabel("Shoreline Distance (m)")
plt.xlabel("Year")
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()


# ========= TREND ANALYSIS ==========
print("\n" + "=" * 70)
print("TREND ANALYSIS")
print("=" * 70)

# Moving Averages
print("\nCalculating moving averages...")

ma_3 = distance.rolling(window=3).mean()
ma_6 = distance.rolling(window=6).mean()
ma_12 = distance.rolling(window=12).mean()

plt.figure(figsize=(12, 6))

plt.plot(distance.index, distance.values, label="Monthly", alpha=0.5, linewidth=0.8)
plt.plot(ma_3.index, ma_3.values, label="3-month MA", linewidth=1.2)
plt.plot(ma_6.index, ma_6.values, label="6-month MA", linewidth=1.5)
plt.plot(ma_12.index, ma_12.values, label="12-month MA", linewidth=2)

plt.title("Moving Averages")
plt.xlabel("Date")
plt.ylabel("Shoreline Distance (m)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print("Moving averages: 3-month, 6-month, 12-month")


# Linear Regression (Trend Line)
print("\nFitting linear regression for trend...")

X = np.arange(len(distance)).reshape(-1, 1)
y = distance.values

model = LinearRegression()
model.fit(X, y)

# Predictions (trend)
trend = model.predict(X)

intercept = model.intercept_
slope = model.coef_[0]

rmse = np.sqrt(mean_squared_error(y, trend))
mae = np.mean(np.abs(y - trend))
r2 = model.score(X, y)

print(f"Intercept (b0): {intercept:.3f} m")
print(f"Slope (b1): {slope:.6f} m/month ({slope*12:.3f} m/year)")
print(f"MAE: {mae:.3f} m")
print(f"RMSE: {rmse:.3f} m")
print(f"R² score: {r2:.3f}")


# Plot data and regression line
plt.figure(figsize=(12, 4))

plt.plot(distance.index,y,color="C0",linewidth=0.8,alpha=0.8,label="Observed data")

plt.plot(distance.index,trend,color="C3",label=f"Trend (slope={slope:.3f} m/month)")

plt.title(f"Linear Trend (R²={r2:.3f})")
plt.xlabel("Date")
plt.ylabel("Shoreline Distance (m)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# STEP COMPONENT: STORM GLORIA

print("\n[STEP] Analyzing possible structural change...")

# Create step variable
step = (distance.index >= pd.Timestamp("2020-02-01")).astype(int)

# Combine time and step variables
X_step = np.column_stack([X.flatten(), step])

# Fit linear regression with step
model_step = LinearRegression()
model_step.fit(X_step, y)

# Predictions
trend_step = model_step.predict(X_step)

# Extract coefficients
intercept_step = float(model_step.intercept_)
slope_step = float(model_step.coef_[0])
step_effect = float(model_step.coef_[1])

print(f"Intercept: {intercept_step:.3f} m")
print(f"Slope: {slope_step:.5f} m/month")
print(f"Step effect: {step_effect:.3f} m")

# STEP MODEL PERFORMANCE

rmse_step = np.sqrt(mean_squared_error(y, trend_step))
mae_step = np.mean(np.abs(y - trend_step))
r2_step = model_step.score(X_step, y)

print("\nLinear trend + STEP performance:")
print(f"RMSE: {rmse_step:.3f} m")
print(f"MAE: {mae_step:.3f} m")
print(f"R² score: {r2_step:.3f}")

# Plot STEP model
plt.figure(figsize=(12, 5))

plt.plot(
    distance.index,
    y,
    label="Original data",
    alpha=0.6
)

plt.plot(
    distance.index,
    trend_step,
    color="red",
    linewidth=2,
    label="Linear trend + STEP"
)

plt.axvline(
    pd.Timestamp("2020-02-01"),
    color="black",
    linestyle="--",
    label="STEP: February 2020"
)

plt.title("Linear trend + STEP model")
plt.xlabel("Date")
plt.ylabel("Mean shoreline distance (m)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# ============ FREQUENCY ANALYSIS ============

detrended = y - trend_step

plt.figure(figsize=(12, 4))
plt.plot(distance.index, distance.values, linewidth=0.5, alpha=0.8, c = 'C0', label="original")
plt.plot(distance.index, trend_step, linewidth=1, alpha=1, c='C3', label="trend + STEP")
plt.plot(distance.index, detrended, linewidth=1, alpha=0.8, c = 'C2', label="detrended")
plt.title('Shoreline Distance over time')
plt.xlabel('Date')
plt.ylabel('Shoreline Distance (m)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# Apply FFT
n = len(detrended)
fft_values = fft(detrended) 
fft_freq = fftfreq(n) 

# Extract magnitude
magnitude = np.abs(fft_values)

# Plot frequency spectrum
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# Sort frequencies for correct visualization
sort_indices = np.argsort(fft_freq)

axes[0].plot(
    fft_freq[sort_indices],
    magnitude[sort_indices],
    color="tab:blue"
)

axes[0].set_title("Frequency spectrum")
axes[0].set_xlabel("Frequency (cycles/month)")
axes[0].set_ylabel("Magnitude")
axes[0].grid(True, alpha=0.3)


# Positive frequencies, excluding zero
positive_mask = fft_freq > 0

positive_freq = fft_freq[positive_mask]
positive_mag = magnitude[positive_mask]

# Find dominant frequency
main_idx = np.argmax(positive_mag)

peak_freq = positive_freq[main_idx]
peak_mag = positive_mag[main_idx]

zoom_band = 0.025

axes[1].plot(positive_freq, positive_mag, color="tab:orange")

axes[1].axvline(peak_freq, color="red", linestyle="--", label=f"Peak: {peak_freq:.4f} cycles/month")

axes[1].set_xlim(max(0, peak_freq - zoom_band), peak_freq + zoom_band)

axes[1].set_title("Zoom around the main peak")
axes[1].set_xlabel("Frequency (cycles/month)")
axes[1].set_ylabel("Magnitude")
axes[1].grid(True, alpha=0.3)
axes[1].legend()

plt.tight_layout()
plt.show()


# Show top 5 frequencies
sorted_idx = np.argsort(positive_mag)[::-1]

print("\nTop 5 detected periods:")

for idx in sorted_idx[:5]:

    freq = positive_freq[idx]
    magn = positive_mag[idx]

    print(f"  Period: {1/freq:>7.2f} months, " f"Magnitude: {magn:>8.2f}")


# Filter frequencies by magnitude
N = 5

top_indices = sorted_idx[:N]

top_threshold = positive_mag[top_indices[-1]]

fft_filtered = fft_values.copy()

fft_filtered[magnitude < top_threshold] = 0

# Remove zero frequency
fft_filtered[0] = 0


# Reconstruct cyclical component
cyclical = np.real(ifft(fft_filtered))

# Reconstruct complete series using STEP trend
reconstructed = trend_step + cyclical

# Plot original, STEP trend, detrended and cyclical components
plt.figure(figsize=(12, 5))

plt.plot(distance.index, y, linewidth=0.5, alpha=0.5, c="C0", label="Original")

plt.plot(distance.index, trend_step, linewidth=1, c="C3", label="Linear trend + STEP")

plt.plot(distance.index, detrended, linewidth=0.5, alpha=0.5, c="C2", label="Detrended")

plt.plot(distance.index, cyclical, linewidth=2, c="C4", label="Cyclical")

plt.title("Shoreline distance: STEP trend and cyclical component")
plt.xlabel("Date")
plt.ylabel("Distance (m)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


# Plot original vs reconstructed series
plt.figure(figsize=(12, 5))
plt.plot(distance.index, y, linewidth=0.8, alpha=0.6, label="Original")
plt.plot(distance.index, reconstructed, linewidth=1.5, label="STEP + FFT reconstructed")

plt.title("Original vs STEP + FFT reconstructed series")
plt.xlabel("Date")
plt.ylabel("Distance (m)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# Performance metrics
rmse_fft = np.sqrt(mean_squared_error(y, reconstructed))
mae_fft = np.mean(np.abs(y - reconstructed))

ss_res = np.sum((y - reconstructed) ** 2)
ss_tot = np.sum((y - np.mean(y)) ** 2)

r2_fft = 1 - ss_res / ss_tot

print("\nLinear trend + STEP + FFT performance:")
print(f"RMSE: {rmse_fft:.3f} m")
print(f"MAE: {mae_fft:.3f} m")
print(f"R² score: {r2_fft:.3f}")


# Residual analysis
final_residuals = y - reconstructed

plt.figure(figsize=(12, 4))

plt.plot(distance.index, final_residuals, linewidth=1, color="C1")

plt.axhline(0, color="black", linestyle="--")

plt.title("Residuals: Linear trend + STEP + FFT")
plt.xlabel("Date")
plt.ylabel("Residuals (m)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()