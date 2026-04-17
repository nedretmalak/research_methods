import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
import textwrap

#Load the cleaned dataset
df = pd.read_csv("/Users/nedret/Desktop/cw2_data/cleaned_hospital_admissions_v5.csv")

print("Raw dataframe shape:", df.shape)
print("Years detected in raw data:", sorted(pd.to_numeric(df["Year"], errors="coerce").dropna().astype(int).unique().tolist()))

#Keep only the columns relevant for the analysis
df = df[['Category', 'Admissions', 'Year']].copy()

#Ensure numeric consistency for calculations
df['Admissions'] = pd.to_numeric(df['Admissions'], errors='coerce')
df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

#Remove incomplete rows and standardise year format
df = df.dropna(subset=['Category', 'Admissions', 'Year'])
df['Year'] = df['Year'].astype(int)

print("Cleaned dataframe shape:", df.shape)
print("Years retained after cleaning:", sorted(df['Year'].unique().tolist()))

#Aggregate total admissions per category per year
grouped = df.groupby(['Category', 'Year'], as_index=False)['Admissions'].sum()
print("Years available after grouping:", sorted(grouped['Year'].unique().tolist()))

#Reshape data so each row is a category and each column is a year
pivot = grouped.pivot(index='Category', columns='Year', values='Admissions')
print("Pivot table year columns:", pivot.columns.tolist())

years = sorted(pivot.columns.tolist())
first_year = years[0]
last_year = years[-1]

print(f"Using analysis range: {first_year} → {last_year}")

#Keep only categories that have data in both boundary years
pivot = pivot.dropna(subset=[first_year, last_year], how='any')
print("Number of categories after complete-data filtering:", pivot.shape[0])

#Calculate absolute and percentage changes over time
pivot['abs_change'] = pivot[last_year] - pivot[first_year]
pivot['pct_change'] = ((pivot[last_year] - pivot[first_year]) / pivot[first_year]) * 100

#Select the top 25 categories with the largest absolute change
top25 = pivot.reindex(
    pivot['abs_change'].abs().sort_values(ascending=False).head(25).index
).copy()

#Export results for further interpretation
changes_out = top25[[first_year, last_year, 'abs_change', 'pct_change']].sort_values(
    'abs_change', ascending=False
)
changes_out.to_csv("/Users/nedret/Desktop/cw2_data/top25_changes.csv")

print("\nTop 10 categories by absolute change:")
print(changes_out.head(10))

#Keep only year columns for visualisation
year_cols = [c for c in top25.columns if isinstance(c, int)]
heatmap_data = top25[year_cols].copy()
print("Year columns included in heatmap:", heatmap_data.columns.tolist())

#Apply row-wise normalisation to highlight trends within each category
heatmap_norm = heatmap_data.copy()

row_min = heatmap_norm.min(axis=1)
row_max = heatmap_norm.max(axis=1)

heatmap_norm = heatmap_norm.sub(row_min, axis=0)
heatmap_norm = heatmap_norm.div((row_max - row_min).replace(0, 1), axis=0)

#Wrap long category names to improve readability in the plot
wrapped_labels = []
for c in heatmap_norm.index:
    wrapped = "\n".join(textwrap.wrap(str(c), width=42))
    wrapped_labels.append(wrapped)

heatmap_norm.index = wrapped_labels

#Define a soft colour gradient suitable for academic visualisation
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_map",
    ["#2c3e50", "#ecf0f1", "#e74c3c"]
)

sns.set(style="white")

#Create the heatmap
plt.figure(figsize=(18, 14))

ax = sns.heatmap(
    heatmap_norm,
    cmap=custom_cmap,
    vmin=0,
    vmax=1,
    cbar_kws={'label': 'Relative admission intensity'}
)

plt.title(
    f"Trends in Hospital Admissions Across Major Diagnosis Categories ({first_year}–{last_year})",
    fontsize=16,
    pad=14
)
plt.xlabel("Year", fontsize=12)
plt.ylabel("Primary Diagnosis Category", fontsize=12)

#Improve readability of axis labels
ax.set_yticklabels(ax.get_yticklabels(), fontsize=9)
ax.set_xticklabels(ax.get_xticklabels(), fontsize=10)

plt.tight_layout()

#Save outputs
plt.savefig(
    "/Users/nedret/Desktop/cw2_data/final_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("\nFiles saved:")
print("/Users/nedret/Desktop/cw2_data/final_heatmap.png")
print("/Users/nedret/Desktop/cw2_data/top25_changes.csv")