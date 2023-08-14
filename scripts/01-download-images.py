# Import modules
import os
import json
import ee
import pickle
import logging
import geopandas as gpd
import pandas as pd

from utils import gee_utils as gee_helpers
from shapely.geometry import mapping  # convert shapely geometry to GeoJSON

# Name Google Cloud Storage Bucket to save static images
# from Google Earth Engine (GEE)
gcs_bucket = "ccai-flood-ground-truth"


# -------------------------------------------
# Create paths to access data downloaded from 
# Script 00-download-ems-vectors
# -------------------------------------------

# Path to EMS activations metadata
folder_metadata = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_metadata")

# Path to CSV file of EMS activations
folder_out_ems = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_table")


#----------------------------------------------------------
# Set up a logger.
#----------------------------------------------------------

# Create a custom logger
logger = logging.getLogger("01-download-images")
logger.setLevel(logging.DEBUG)

# Create handlers
f_handler = logging.FileHandler("01-download-images.log")
f_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


# ---------------------------------------------------------
# Download permanent water layer from European Commission's 
# Joint Research Centre (JRC) and land cover product from
# ESA WorldCover 10m v100 for each EMS activation event 
# into Google Cloud Storage Bucket using GEE.
# ---------------------------------------------------------

# Read in the table of EMS activations
ems_table = pd.read_csv(os.path.join(folder_out_ems, "tropical_ems.csv"))

# Get EMS activation metadata pickle files
metadata_files = os.listdir(folder_metadata)
metadata_files_pickle = []
for i in metadata_files:
    if i.endswith(".pickle"):
        metadata_files_pickle.append(i)

# Loop over EMS activation metadata pickle files
# and download static images from GEE.
# Adapted from https://github.com/spaceml-org/ml4floods/blob/main/ml4floods/data/copernicusEMS/activations.py
for i in metadata_files_pickle:
    logger.info(f"Trying EMS activation {i}")

    try:
        # Create a path to individual metadata pickle files
        fpath = os.path.join(folder_metadata, i)

        # Read metadata pickle files to obtain the AOI object, 
        # the year, and the name of the event
        with open(fpath, "rb") as f:
            metadata_floodmap = pickle.load(f)

        # Convert Shapely polygon object defining AOI of each 
        # activation into an Earth Engine "ee.geometry" object, 
        # which will be used to export static images from GEE.
        ee_poly = ee.Geometry(mapping(metadata_floodmap["area_of_interest_polygon"]))
        
        # Extract the year of the event
        event_id = metadata_floodmap["event id"].split("_")[0]
        event_record = ems_table.loc[ems_table["Code"] == event_id, ["CodeDate"]]
        year = event_record.to_numpy()[0][0].split("-")[0]
        
        # Extract the name of the event
        event_name = metadata_floodmap["event id"]

        # Get static images of permanent water from JRC and land cover from ESA
        static_images = gee_helpers.get_static_images(int(year), ee_poly)
        export_fname = event_name + "_static_images"

        # Export the static images into Google Cloud Storage Bucket
        task = ee.batch.Export.image.toCloudStorage(
            static_images.clip(ee_poly),
            fileNamePrefix=export_fname,
            description=export_fname,
            crs="EPSG:4326",
            skipEmptyTiles=True,
            bucket=gcs_bucket,
            scale=10,
            maxPixels=1e13,
        )
        task.start()
        logger.info(f"Download static images task started for EMS activation {i}")
        
    except:
        logger.warning(f"Failed to generate static images for EMS activation {i}")
        continue

logger.info(f"**********finished**********")