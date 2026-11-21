"""Streamlit entry point for ClimateWise."""
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from climate import HISTORICAL, build_results, export_zip, fetch_point, make_charts, scenario_path

st.set_page_config(page_title="ClimateWise", page_icon="🌦️", layout="wide")

st.title("ClimateWise")
st.markdown(
    "Explore monthly and annual precipitation at a land location using "
    "TerraClimate historical data and warming scenarios."
)
st.caption(
    "Original notebook by Qianjin Zheng and Adnan Rajib, Hydrology and "
    "Hydroinformatics Innovation (H2I) Lab, University of Texas at Arlington."
)


@st.cache_data(ttl=86400, max_entries=1024, show_spinner=False)
def cached_point(path, latitude, longitude, start, end):
    return fetch_point(path, latitude, longitude, start, end)


with st.sidebar:
    st.header("Analysis settings")
    historical_years = st.slider("Historical years", 1950, 2025, (1991, 2020))
    warming = st.radio("Warming scenario", (2, 3), horizontal=True, format_func=lambda n: f"+{n} °C")
    scenario_years = st.slider("Scenario comparison years", 1950, 2025, (2015, 2020))
    st.caption("Scenario years use the historical calendar as the comparison baseline.")

st.subheader("Select a location")
st.write("Click a land location on the map or enter its coordinates.")
location_map = folium.Map(location=[20, 0], zoom_start=2, max_bounds=True, control_scale=True)
folium.LatLngPopup().add_to(location_map)
event = st_folium(location_map, key="location_map", height=390, width=None,
                  returned_objects=["last_clicked"])
click = (event or {}).get("last_clicked")
if click:
    point = (round(click["lat"], 5), round(((click["lng"] + 180) % 360) - 180, 5))
    if point != st.session_state.get("last_map_point"):
        st.session_state.update(last_map_point=point, latitude=point[0], longitude=point[1])

st.session_state.setdefault("latitude", 32.9126)
st.session_state.setdefault("longitude", -96.6389)
left, right = st.columns(2)
latitude = left.number_input("Latitude", -90.0, 90.0, format="%.5f", key="latitude")
longitude = right.number_input("Longitude", -180.0, 180.0, format="%.5f", key="longitude")
settings = (latitude, longitude, historical_years, scenario_years, warming)

if st.button("Run analysis", type="primary"):
    st.session_state.pop("analysis", None)
    progress = st.progress(0.0, text="Retrieving historical precipitation…")
    start, end = scenario_years
    first = min(historical_years[0], start)
    last = max(historical_years[1], end)
    try:
        historical = cached_point(HISTORICAL, latitude, longitude, first, last)
        if historical.isna().all():
            raise ValueError("No historical precipitation is available at this grid cell. Try a nearby land location.")
        scenario_parts = []
        years = range(start, end + 1)
        for index, year in enumerate(years, start=1):
            progress.progress(index / (len(years) + 1), text=f"Retrieving +{warming} °C data for {year}…")
            scenario_parts.append(cached_point(scenario_path(warming, year), latitude, longitude, year, year))
        scenario = pd.concat(scenario_parts)
        if scenario.isna().all():
            raise ValueError(f"No +{warming} °C precipitation is available at this grid cell for the selected years.")
        frames = build_results(historical, scenario, historical_years, warming)
        figures = list(make_charts(frames, latitude, longitude, warming))
        archive = export_zip(frames, figures, historical_years, scenario_years, warming)
        st.session_state.analysis = (settings, frames, archive)
    except ValueError as error:
        st.error(str(error))
    finally:
        progress.empty()

analysis = st.session_state.get("analysis")
if analysis and analysis[0] != settings:
    st.info("Run the analysis to update the results for your new selection.")
elif analysis:
    _, frames, archive = analysis
    st.subheader("Precipitation results")
    if any(frame.isna().any().any() for frame in frames):
        st.warning("Some months are missing. Annual totals require all 12 months.")
    historical_tab, scenario_tab = st.tabs(["Historical trends", f"+{warming} °C comparison"])
    figures = list(make_charts(frames, latitude, longitude, warming))
    for tab, tab_figures in zip((historical_tab, scenario_tab), (figures[:2], figures[2:])):
        with tab:
            for figure in tab_figures:
                st.pyplot(figure)
    with scenario_tab:
        for heading, frame in zip(("Monthly statistics (mm/month)", "Annual statistics (mm/year)"), frames[2:]):
            st.subheader(heading)
            st.dataframe(frame.agg(["count", "mean", "std", "min", "max"]).round(2))
    st.download_button("Download four CSVs and plots PDF", archive,
                       "Climate_results.zip", mime="application/zip", on_click="ignore")

st.markdown(
    "Data and methods: [TerraClimate](https://www.climatologylab.org/terraclimate.html) · "
    "[Abatzoglou et al. (2018)](https://doi.org/10.1038/sdata.2017.191) · "
    "[Qin et al. (2020)](https://doi.org/10.1038/s41558-020-0746-8)"
)
