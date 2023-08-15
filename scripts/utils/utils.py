import os
import pandas as pd

def table_floods_ems(
    event_start_date: str = "2014-05-01", 
    ems_web_page: str = "https://poc-d8.lolandese.site/search-activations"
    ) -> pd.DataFrame:
    """
    Adapted from https://github.com/spaceml-org/ml4floods/blob/main/ml4floods/data/copernicusEMS/activations.py#L47

    Get a list of EMS Rapid Mapping Activations from the Copernicus Emergency Management Event System.

    Filter for Event types of Flood and Storm. 

    Args:
      event_start_date (str): Date to retrieve EMS events from. 
      ems_web_page (str): URL of web page / table to download.

    Returns:
      A pandas.DataFrame of Flood and Storm events.

    """
    tables = pd.read_html(ems_web_page)[0]
    tables_floods = tables[(tables.Type == "Flood") | (tables.Type == "Storm")]
    tables_floods = tables_floods[tables_floods["Act. Date"] >= event_start_date]
    tables_floods = tables_floods.reset_index()[
        ["Act. Code", "Title", "Act. Date", "Type", "Country/Terr."]
    ]

    tables_floods = tables_floods.rename(
        {"Act. Code": "Code", "Country/Terr.": "Country", "Act. Date": "CodeDate"},
        axis=1,
    )

    return tables_floods.set_index("Code")