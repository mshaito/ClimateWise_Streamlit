# ClimateWise for Streamlit

ClimateWise explores TerraClimate historical precipitation and +2 °C or +3 °C warming scenarios. The original Colab notebook was developed by Qianjin Zheng and Adnan Rajib at the Hydrology and Hydroinformatics Innovation (H2I) Lab, University of Texas at Arlington.

## Run locally

Unzip the package, open a terminal in the extracted project folder, and run the following commands with Python 3.11 or newer.

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud), put these files in a GitHub repository and select `app.py` as the entry point.

## Run an analysis

Select the historical years, warming scenario, and scenario comparison years. Click a land point on the map or enter coordinates manually. Click **Run analysis** to see four charts and summary statistics. The results ZIP contains four CSV files and a four-page PDF. The historical date range controls the historical charts. The scenario date range controls both series in the comparison charts.

TerraClimate applies warming adjustments to its historical baseline. The scenario years correspond to baseline years. The app uses the THREDDS point-subset service and requests one file per scenario year. Expect longer waits for broad scenario ranges. Live analysis requires outbound HTTPS access to the TerraClimate server. Missing precipitation values stay blank, and annual totals require twelve available months.
The current v1.1 catalog offers +2 °C and +3 °C warming scenarios. The original notebook used a +2 °C file while its output labels referred to +4 °C.

## Sources

- [TerraClimate, Climatology Lab](https://www.climatologylab.org/terraclimate.html)
- [Unidata THREDDS NetCDF Subset Service](https://docs.unidata.ucar.edu/tds/5.10/userguide/ncss_grid.html)
- [Abatzoglou et al. (2018)](https://doi.org/10.1038/sdata.2017.191)
- [Qin et al. (2020)](https://doi.org/10.1038/s41558-020-0746-8)
