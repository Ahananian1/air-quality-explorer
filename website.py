"""
Name:       Alex Hananian
CS230:      Section 4
Data:       World Air Quality Index
URL:        <Your Streamlit Cloud URL here>

Description:
Users can interactively explore global air quality metrics with this Streamlit app. Selecting pollutant types, filtering by range, cities and countries, viewing summary statistics, a bar chart of the most polluted cities, a pollutant distribution histogram, a pivot table of the average pollutant by country, and interactive maps that display pollutant levels by location are all accessible to users.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import seaborn as sns
import plotly.express as px

# Page configuration
st.set_page_config(page_title='Air Quality Explorer', layout='wide') # [ST4]


# load data cleanly into website (Used the following source for guidance: "https://chris-albert-blog.medium.com/python-presenting-data-with-streamlit-0fb4eb6632d7" )
@st.cache_data
#
def load_data(filepath):  # [PY1]
    try:  # [PY3]
        df = pd.read_csv(filepath)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

    df = df.drop_duplicates()  # [DA1]
    df = df.dropna(subset=['lat', 'lng'])  # [DA1]

    df.columns = df.columns.str.strip()  # [DA1]
    return df

# Load dataset
data = load_data('air_quality_index.csv')  # called once with explicit argument

# Columns
required_cols = ['AQI Value', 'CO AQI Value', 'Ozone AQI Value', 'NO2 AQI Value', 'PM2.5 AQI Value']
missing = [col for col in required_cols if col not in data.columns]
if missing:
    st.error(f"Missing expected columns: {missing}")
    st.stop()

# Sidebar controls [ST1, ST2, ST3]
st.sidebar.header('Filters')

# instructions
st.sidebar.markdown("#### How to Use This App")
st.sidebar.markdown(
    "- Select a pollutant and AQI range  \n"
    "- Choose countries and cities  \n"
    "- Explore charts, tables, and the map"
)

pollutant_dict = {  # [PY5]
    'Overall AQI': 'AQI Value',
    'Carbon Monoxide': 'CO AQI Value',
    'Ozone': 'Ozone AQI Value',
    'Nitrogen Dioxide': 'NO2 AQI Value',
    'PM2.5': 'PM2.5 AQI Value'
}

pollutant_label = st.sidebar.selectbox('Select Pollutant', list(pollutant_dict.keys()))
pollutant_col = pollutant_dict[pollutant_label]

# Slider for AQI range [ST1]
min_val, max_val = st.sidebar.slider(
    'AQI Range',
    int(data[pollutant_col].min()),
    int(data[pollutant_col].max()),
    (int(data[pollutant_col].min()), int(data[pollutant_col].max()))
)

# Multiselect for countries [ST2]
countries = st.sidebar.multiselect(
    'Select Countries',
    options=list(data['Country'].unique()),
    default=['United States of America', 'China' ,'Brazil', 'Italy', 'Russian Federation', 'France']
)

# Function with default param [PY1] (used ChatGPT)
def filter_data(df, pollutant, low=min_val, high=max_val):
    return df[(df[pollutant] >= low) & (df[pollutant] <= high)]  # [DA4]

# Apply filters
filtered = filter_data(data, pollutant_col, min_val, max_val)
filtered = filtered[filtered['Country'].isin(countries)]  # [DA4]

st.title('🌍 Global Air Quality Explorer')
st.subheader(f"Showing data for: {pollutant_label}, {min_val}–{max_val}, Countries: {', '.join(countries)}")
st.dataframe(filtered)

# Function returning multiple values [PY2]
def get_stats(df, col):
    return df[col].mean(), df[col].min(), df[col].max()

mean_val, min_val_stat, max_val_stat = get_stats(filtered, pollutant_col)
st.metric('Average AQI', f"{mean_val:.1f}")
st.metric('Minimum AQI', f"{min_val_stat:.1f}")
st.metric('Maximum AQI', f"{max_val_stat:.1f}")

# Top 10 bar chart [CHART1], [DA3]
top10 = filtered.nlargest(10, pollutant_col)
fig, ax = plt.subplots()
ax.bar(top10['City'], top10[pollutant_col])
ax.set_title(f'Top 10 Cities by {pollutant_label}')
ax.set_xlabel('City')
ax.set_ylabel(pollutant_label)
plt.xticks(rotation=45, ha='right')
st.pyplot(fig)

# Seaborn histogram [CHART2], [SEA1] (https://python-graph-gallery.com/20-basic-histogram-seaborn/)
dist_fig, dist_ax = plt.subplots()
sns.histplot(data[pollutant_col], ax=dist_ax, bins=20)
dist_ax.set_title(f'Distribution of {pollutant_label} Across All Locations')
st.pyplot(dist_fig)

# Pivot table [DA6]
pivot = filtered.pivot_table(index='Country', values=pollutant_col, aggfunc='mean').reset_index()
st.subheader('Average AQI by Country')
st.dataframe(pivot)

# Map AQI category to numeric values [DA7], [DA9]
df_copy = filtered.copy()
category_map = {'Good': 1, 'Moderate': 2, 'Unhealthy for Sensitive Groups': 3,
                'Unhealthy': 4, 'Very Unhealthy': 5, 'Hazardous': 6}
df_copy['AQI_Level'] = df_copy['AQI Category'].map(category_map)
st.subheader('AQI Level Codes')
st.dataframe(df_copy[['City', 'AQI Category', 'AQI_Level']])

# Iterate through rows [DA8]
cat_counts = {}
for idx, row in filtered.iterrows():
    cat = row['AQI Category']
    cat_counts[cat] = cat_counts.get(cat, 0) + 1
st.sidebar.write('Category Counts:', cat_counts)

# Multiselect for cities [ST3]
city_options = sorted(data['City'].dropna().unique())
selected_cities = st.multiselect("Select one or more cities to view:", options=city_options)

# Multiselect for AQI categories [ST3]
aqi_categories = sorted(data['AQI Category'].dropna().unique())
selected_categories = st.multiselect("Select AQI Categories to view:", options=aqi_categories, default=aqi_categories)

# Filter the data based on selected cities and AQI categories [DA5] (Used ChatGPT to assist in adding multiselect search filters for the map)
filtered_data = data.copy()

if selected_cities:
    filtered_data = filtered_data[filtered_data['City'].isin(selected_cities)]

if selected_categories:
    filtered_data = filtered_data[filtered_data['AQI Category'].isin(selected_categories)]

# Bubble map using Plotly [MAP]
fig = px.scatter_geo(
    filtered_data,
    lat="lat",                     # column with latitude values
    lon="lng",                     # column with longitude values
    hover_name="City",            # what shows up when you hover
    size="PM2.5 AQI Value",       # bubble size
    color="AQI Category",         # colors by category
    projection="natural earth",
    title="Filtered Air Quality Map"
)

# Display the map
st.plotly_chart(fig, use_container_width=True)

# download data (extra functionality added using ChatGPT)
st.download_button(
    label="Download Filtered Data as CSV",
    data=filtered_data.to_csv(index=False),
    file_name='filtered_air_quality.csv',
    mime='text/csv'
)
# List comprehension [PY4]
aqi_columns = [c for c in data.columns if 'AQI' in c]
st.sidebar.write('AQI Columns:', aqi_columns)


# Here are other sources I used
# https://plotly.com/python/bubble-maps/
# https://docs.streamlit.io/develop/api-reference/charts/st.map
# https://docs.streamlit.io/develop/api-reference/layout/st.sidebar
