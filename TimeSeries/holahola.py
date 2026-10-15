import pandas as pd
df = pd.read_csv("shoreline_distances_2017_2024.csv")
print(f"{ df.info()}")
print(f"{ df.head(3)}")

df['date'] = pd .to_datetime(df['date'], format='%Y-%m-%d')
df.set_index('date', inplace=True)
df.sort_index(inplace=True)
df = df[(df.index.year >= 2017) & (df.index.year <= 2024)] 
ts = df['distance_m'].copy() 

ts.isna().sum()