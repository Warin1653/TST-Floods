# Import modules
import requests
import os
import pandas as pd
import logging
from bs4 import BeautifulSoup

# Create a path to CSV file of EMS activations table
# and read in as a DataFrame.
folder_csv_ems = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_table")
ems_df = pd.read_csv(os.path.join(folder_csv_ems, "tropical_ems.csv"))

# Get the base URL for EMS event info page, 
# which will be used to scrape event data from.
ems_event_url = "https://emergency.copernicus.eu/mapping/list-of-components/"

# Copy the DataFrame of events to append event dates
ems_df_out = ems_df.copy()


#----------------------------------------------------------
# Set up a logger.
#----------------------------------------------------------

# Create a custom logger
logger = logging.getLogger("02-get-event-date")
logger.setLevel(logging.DEBUG)

# Create handlers
f_handler = logging.FileHandler("02-get-event-date.log")
f_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


# ------------------------------------------------------------------
# Get the event date, instead of the activation date for each event. 
# We do not use the activation date because the mapping services 
# could be activated at a later date long after the event occured. 
# We use the event date to get pre- and post-event images aligned 
# with the actual event date.
# ------------------------------------------------------------------

# Loop over EMS events and scrape event dates from the URL
for i in ems_df.index:
    try:
        ems_code = ems_df["Code"][i]
        logger.info(f"Trying EMS activation {i}")
        url = ems_event_url + ems_code

        # Get event date from webpage HTML
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        utc = soup.find_all("span", class_="views-field-field-event-time-utc")
        soup_2 = BeautifulSoup(str(utc), "html.parser")
        utc_date = soup_2.find_all("span", class_="date-display-single")
        utc_date = str(utc_date)
        if len(utc_date) > 0:
            utc_date = utc_date.split('content="')[1]
            utc_date = utc_date.split("T")[0]

        ems_df_out.loc[i, "EventDate"] = utc_date
    except:
        logger.warning(
            f'Failed to get event date for EMS activation {ems_df["Code"][i]}'
        )
        continue

# Save DataFrame with EMS event dates to a CSV file
ems_df_out.to_csv(os.path.join(folder_csv_ems, "tropical_ems_event_date.csv"), index=False)

logger.info(f"**********finished**********")