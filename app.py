# app.py - COMPLETE WORKING SOLUTION
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import zipfile
import os
from io import BytesIO

# ======================
# DATA DOWNLOAD FUNCTION
# ======================
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_climate_data():
    # Dropbox direct download link (replace with your actual file ID)
    DATA_URL = "https://www.dropbox.com/scl/fi/8eqzalmgvv9u7egjgyrt1/GlobalData.zip?rlkey=bf1qyz7f5atxr2c6es0ucdbdb&st=mi1ucho9&dl=1"    
    # Required files check
    required_files = {
        'GlobalTemperatures.csv': None,
        'GlobalLandTemperaturesByCountry.csv': None,
        'GlobalLandTemperaturesByCity.csv': None
    }
    
    # Check if files already exist
    if all(os.path.exists(f) for f in required_files.keys()):
        for filename in required_files:
            required_files[filename] = pd.read_csv(filename)
        return required_files
    
    # Download with progress
    with st.spinner("📡 Downloading climate dataset (100MB)... This may take a few minutes"):
        try:
            response = requests.get(DATA_URL, stream=True)
            response.raise_for_status()
            
            # Show download progress
            progress_bar = st.progress(0)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Use BytesIO to handle zip in memory
            zip_buffer = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                progress = min(downloaded / total_size, 1.0)
                progress_bar.progress(progress)
                zip_buffer.write(chunk)
            
            progress_bar.empty()
            
            # Extract files
            with zipfile.ZipFile(zip_buffer) as z:
                for filename in required_files:
                    if filename in z.namelist():
                        with z.open(filename) as f:
                            required_files[filename] = pd.read_csv(f)
                    else:
                        st.error(f"Missing file in ZIP: {filename}")
            
            # Save extracted files locally for future runs
            for filename, df in required_files.items():
                if df is not None and not os.path.exists(filename):
                    df.to_csv(filename, index=False)
            
            # Check if files are successfully loaded
            if not all(df is not None for df in required_files.values()):
                st.error("One or more files failed to load properly.")
                st.stop()
            
            return required_files
            
        except Exception as e:
            st.error(f"Download failed: {str(e)}")
            st.stop()

# ======================
# DATA PROCESSING
# ======================
def process_data(data_files):
    # Process global data
    global_temp = data_files['GlobalTemperatures.csv']
    global_temp['dt'] = pd.to_datetime(global_temp['dt'])
    global_temp['Year'] = global_temp['dt'].dt.year
    global_yearly = global_temp.groupby('Year').mean(numeric_only=True).reset_index()
    global_yearly['10Y_MA'] = global_yearly['LandAverageTemperature'].rolling(10).mean()
    
    # Process country data
    countries = data_files['GlobalLandTemperaturesByCountry.csv']
    countries['dt'] = pd.to_datetime(countries['dt'])
    countries['Year'] = countries['dt'].dt.year
    
    # Process city data
    cities = data_files['GlobalLandTemperaturesByCity.csv']
    cities['dt'] = pd.to_datetime(cities['dt'])
    cities['Year'] = cities['dt'].dt.year
    
    return {
        'global_yearly': global_yearly,
        'countries': countries,
        'cities': cities
    }

# ======================
# STREAMLIT APP
# ======================
st.set_page_config(
    page_title="🌍 Global Climate Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    }
    .st-emotion-cache-1y4p8pa {
        padding: 2rem;
    }
    .stPlotlyChart {
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .metric-card {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🌍 Global Climate Dashboard")
st.markdown("### _Comprehensive temperature analysis from 1750 to present_")
st.markdown("---")

# Load data
data_files = get_climate_data()

# Load data
data_files = get_climate_data()

# Check if any file failed to load
if any(df is None for df in data_files.values()):
    st.warning("Some data files failed to load. Check error messages above.")
    st.stop()


processed_data = process_data(data_files)

# Dashboard Tabs
tab1, tab2, tab3 = st.tabs(["🌡 Global Trends", "🗺 Country Analysis", "🏙 City Comparison"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        latest_temp = processed_data['global_yearly'].iloc[-1]['LandAverageTemperature']
        st.markdown("""
        <div class="metric-card">
            <h3>Current Global Temperature</h3>
            <h1>{:.2f}°C</h1>
            <p>Compared to 1900: <b>+{:.2f}°C</b></p>
        </div>
        """.format(
            latest_temp,
            latest_temp - processed_data['global_yearly'][processed_data['global_yearly']['Year'] == 1900]['LandAverageTemperature'].values[0]
        ), unsafe_allow_html=True)
    
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=processed_data['global_yearly']['Year'],
            y=processed_data['global_yearly']['LandAverageTemperature'],
            line=dict(color='#00ccff', width=3),
            name='Annual Average'
        ))
        fig.add_trace(go.Scatter(
            x=processed_data['global_yearly']['Year'],
            y=processed_data['global_yearly']['10Y_MA'],
            line=dict(color='white', width=2, dash='dot'),
            name='10-Year Average'
        ))
        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Country-Level Temperature Analysis")
    
    valid_years = processed_data['countries']['Year'].dropna().unique()
    year = st.slider(
        "Select Year",
        min_value=int(valid_years.min()),
        max_value=int(valid_years.max()),  # Typically 2013
        value=int(valid_years.max())
    )
    
    country_data = processed_data['countries'][processed_data['countries']['Year'] == year]
    country_data = country_data.dropna(subset=['AverageTemperature'])
    
    fig = go.Figure(go.Choropleth(
        locations=country_data['Country'],
        locationmode='country names',
        z=country_data['AverageTemperature'],
        colorscale='thermal',
        marker_line_color='rgba(0,0,0,0.2)',
        colorbar_title='Temperature (°C)'
    ))
    
    fig.update_layout(
        height=600,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth',
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("City Temperature Comparison")
    
    # Get unique cities
    available_cities = processed_data['cities']['City'].unique()
    selected_cities = st.multiselect(
        "Select cities to compare",
        options=available_cities,
        default=['New York', 'London', 'Tokyo', 'Delhi']
    )
    
    if selected_cities:
        city_data = processed_data['cities'][processed_data['cities']['City'].isin(selected_cities)]
        fig = go.Figure()
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        for i, city in enumerate(selected_cities):
            city_df = city_data[city_data['City'] == city]
            fig.add_trace(go.Scatter(
                x=city_df['Year'],
                y=city_df['AverageTemperature'],
                name=city,
                line=dict(color=colors[i % len(colors)], width=3),
                mode='lines+markers'
            ))
        
        fig.update_layout(
            height=500,
            xaxis_title='Year',
            yaxis_title='Temperature (°C)',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one city")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    <p>Data sources: NASA GISS, Berkeley Earth | Dashboard created with Streamlit</p>
    <p>Dataset hosted on Kaggle |</p>
</div>
""", unsafe_allow_html=True)

# Credits
st.markdown("""
<br><br>
<div style="text-align: center; color: #bbb; font-size: 16px;">
    <p><b>Credits:</b></p>
    <p>Created by <b>Yashasvi Khurana</b> (Lead Developer) and <b>Reyaansh Bhagat</b></p>
    <p>Students of <b>St. Columba's School</b></p>
    <p>This dashboard was developed as a part of the <b>Code@Trix</b> competition.</p>
</div>
""", unsafe_allow_html=True)
