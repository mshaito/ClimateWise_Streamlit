"""TerraClimate point extraction, precipitation summaries, and exports."""
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import requests
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from scipy.stats import linregress

NCSS = "https://tds-proxy.nkn.uidaho.edu/thredds/ncss/grid"
HISTORICAL = "agg_terraclimate_ppt_1950_CurrentYear_GLOBE.nc"
PAST = "Historical precipitation"


def scenario_path(warming, year):
    name = f"plus{warming}C"
    return f"TERRACLIMATE_ALL/data_{name}/TerraClimate_{name}_ppt_{year}.nc"


def fetch_point(path, latitude, longitude, start, end):
    # Exact poles and the dateline are outside the outermost cell centers.
    params = {
        "var": "ppt",
        "latitude": min(89.97916, max(-89.97916, latitude)),
        "longitude": min(179.97916, max(-179.97916, longitude)),
        "time_start": f"{start}-01-01T00:00:00Z",
        "time_end": f"{end}-12-01T00:00:00Z",
        "accept": "csv",
    }
    try:
        response = requests.get(f"{NCSS}/{path}", params=params, timeout=(8, 35))
        response.raise_for_status()
        return parse_point(response.text, start, end)
    except requests.RequestException as error:
        status = error.response.status_code if error.response is not None else None
        detail = f"HTTP {status}" if status else "connection failed or timed out"
    except ValueError as error:
        detail = str(error)
    raise ValueError(f"TerraClimate data for {start}–{end} could not be read ({path}): {detail}.")


def parse_point(csv, start, end):
    frame = pd.read_csv(StringIO(csv))
    headers = {column.lower().split("[")[0].strip(): column for column in frame}
    if not {"time", "ppt"}.issubset(headers):
        raise ValueError("expected time and precipitation columns in the server response")
    dates = pd.DatetimeIndex(pd.to_datetime(frame[headers["time"]], utc=True))
    months = dates.tz_convert(None).to_period("M")
    if months.hasnans or months.has_duplicates:
        raise ValueError("the server returned missing or duplicate dates")
    values = pd.to_numeric(frame[headers["ppt"]], errors="coerce")
    # TerraClimate v1.1 NCSS CSV returns packed ppt values, even with a mm header.
    values = values.where(np.isfinite(values) & (values >= 0)) * 0.1
    expected = pd.period_range(f"{start}-01", f"{end}-12", freq="M", name="Month")
    return pd.Series(values.to_numpy(), index=months).reindex(expected)


def annual_totals(monthly):
    yearly = monthly.groupby(monthly.index.year).sum(min_count=12)
    yearly.index.name = "Year"
    return yearly


def build_results(historical, scenario, historical_years, warming):
    label = f"+{warming} °C scenario precipitation"
    start, end = historical_years
    past = historical.loc[f"{start}-01":f"{end}-12"].to_frame(PAST)
    comparison = pd.DataFrame({PAST: historical.reindex(scenario.index), label: scenario})
    return past, annual_totals(past), comparison, annual_totals(comparison)


def make_charts(frames, latitude, longitude, warming):
    titles = (
        "Monthly historical precipitation",
        "Annual historical precipitation",
        f"Monthly historical vs. +{warming} °C scenario precipitation",
        f"Annual historical vs. +{warming} °C scenario precipitation",
    )
    for index, (frame, title) in enumerate(zip(frames, titles)):
        monthly = index % 2 == 0
        figure = Figure(figsize=(11, 4), layout="constrained")
        axes = figure.subplots()
        x = frame.index.to_timestamp() if monthly else frame.index.to_numpy()
        positions = np.arange(len(frame))
        width = 12 if monthly else 0.36
        for column, color, shift in zip(frame, ("#15798b", "#b7522a"), (-0.5, 0.5)):
            offset = 0 if index < 2 else width * shift
            shifted = x + pd.to_timedelta(offset, unit="D") if monthly else x + offset
            axes.bar(shifted, frame[column], width=width, label=column, color=color)
        if index < 2:
            values = frame[PAST].to_numpy(dtype=float)
            valid = np.isfinite(values)
            if valid.sum() >= 2:
                fit = linregress(positions[valid], values[valid])
                axes.plot(x, fit.intercept + fit.slope * positions,
                          color="#9d3427", linewidth=1.5, label="Linear trend")
        axes.set_title(f"{title}\nSelected point ({latitude:.4f}, {longitude:.4f})")
        axes.set_xlabel("Month" if monthly else "Year")
        axes.set_ylabel("Precipitation (mm/month)" if monthly else "Precipitation (mm/year)")
        if not monthly:
            axes.xaxis.set_major_locator(MaxNLocator(integer=True))
        axes.legend(loc="upper left")
        axes.grid(axis="y", alpha=0.2)
        yield figure


def export_zip(frames, figures, historical_years, scenario_years, warming):
    first, last = historical_years
    start, end = scenario_years
    filenames = (
        f"Historical_Monthly_Prep_{first}_{last}.csv",
        f"Historical_Yearly_Prep_{first}_{last}.csv",
        f"ClimateChange_Monthly_Prep_plus{warming}C_{start}_{end}.csv",
        f"ClimateChange_Yearly_Prep_plus{warming}C_{start}_{end}.csv",
    )
    pdf_buffer, zip_buffer = BytesIO(), BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        for figure in figures:
            pdf.savefig(figure)
    with ZipFile(zip_buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, frame in zip(filenames, frames):
            unit = "mm/month" if frame.index.name == "Month" else "mm/year"
            csv = frame.rename(columns=lambda column: f"{column} ({unit})").to_csv()
            archive.writestr(name, csv)
        archive.writestr("Time-series_Plots.pdf", pdf_buffer.getvalue())
    return zip_buffer.getvalue()
