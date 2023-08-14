# Import modules
import os
import json
import ee
import pickle
import re
import logging
import geopandas as gpd

from utils import gee_utils as gee_helpers
from utils import utils as helpers
from ml4floods.data.copernicusEMS import activations
from ml4floods.data import utils
from ml4floods.data import create_gt
from shapely.geometry import mapping
from pathlib import Path
from datetime import timedelta
from datetime import datetime


#----------------------------------------------------------------------
# Set up folders to save outputs from Emergency Management System (EMS)
# Rapid Mapping Activation events.
#----------------------------------------------------------------------

# Folder to store CSV file of tropical and sub-tropical 
# EMS Flood and Storm event
folder_out_ems = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_table")
os.makedirs(folder_out_ems, exist_ok=True)

# Folder to store vector data for each tropical and sub-tropical 
# EMS Flood and Storm event
folder_out = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_raw")
os.makedirs(folder_out, exist_ok=True)

# Folder to store metadata for each tropical and sub-tropical
# EMS Flood and Storm event
folder_metadata = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_metadata")
os.makedirs(folder_metadata, exist_ok=True)


#----------------------------------------------------------
# Set up a logger.
#----------------------------------------------------------

# Create a custom logger
logger = logging.getLogger("00-download-ems-vectors")
logger.setLevel(logging.DEBUG)

# Create handlers
f_handler = logging.FileHandler("00-download-ems-vectors.log")
f_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


#------------------------------------------------------------
# Create a dataframe of EMS activations in tropical countries
# and save it as a CSV file in Copernicus_EMS_table folder
#------------------------------------------------------------

# Get a table of EMS activations since user specified date
table_activations_ems = helpers.table_floods_ems()

# Get a list of countries
countries = table_activations_ems["Country"].unique()
countries_split = []

for i in countries:
    split = i.split(",")
    for s in split:
        s = s.strip()
        countries_split.append(s)

# Extract tropical countries from the list of countries
tropical_countries = gee_helpers.get_tropical_countries(countries_split)

# Get a table of EMS activations in tropical countries
tropical_ems = table_activations_ems[
    table_activations_ems["Country"].isin(tropical_countries)
].reset_index()

# Save tropical EMS DataFrame into a CSV file
tropical_ems.to_csv(os.path.join(folder_out_ems, "tropical_ems.csv"))


#------------------------------------------------
# Download the latest EMSR vector products for 
# each EMS flood event. Generate metadata and 
# flood maps from the downloaded vector products.
#------------------------------------------------

# Get a list of EMSR (EMS Rapid Mapping) codes for flood events in tropical countries
tropical_emsr_codes = tropical_ems["Code"].tolist()
logger.info(f"tropical EMSR codes {tropical_emsr_codes}")

# Retrieve a url for each EMSR code, download the zip files
# associated with the code, then unzip the files.
for i in tropical_emsr_codes:
    logger.info(f"Trying EMSR CODE {i}")

    zip_files_activation_url_list = activations.fetch_zip_file_urls(i)

    unzip_files_activation = []
    for zip_file in zip_files_activation_url_list:
        try:
            local_zip_file = activations.download_vector_cems(
                zip_file, folder_out=folder_out
            )
            unzipped_file = activations.unzip_copernicus_ems(
                local_zip_file, folder_out=folder_out
            )

            # Filter out vector products, including 
            # First Estimate Products (FEP),
            # Delineation Products (DEP) 
            # and Grading Products (GRA), to generate flood extent.
            # The RTP products are the same but with a printable map
            # The documentation describing each product can be found in the link below: https://emergency.copernicus.eu/mapping/sites/default/files/files/EMS_Mapping_Manual_of_Procedures_v2_September2020.pdf
            if (
                (re.search("FEP", zip_file))
                or (re.search("DEL", zip_file))
                or (re.search("DELINEATION", zip_file))
                or (re.search("GRA", zip_file))
                or (re.search("GRADING", zip_file))
            ):
                unzip_files_activation.append(unzipped_file)
        except:
            error_zip = str(zip_file)
            logger.exception(f"{error_zip} caused an Exception")
            continue

    # Get only the latest version of vector data - with the largest v* number
    # because the latest version is the highest quality product.
    unzip_files_activation_latest_v = []

    # Extract only the event names from the file names
    unique_event_name = set()
    for z in unzip_files_activation:
        file_name = z.split("/")
        split_count = len(file_name)
        file_name = file_name[split_count - 1]
        event_name = file_name.split("_r")[0]
        unique_event_name.add(event_name)

    # Extract all file paths that match each unique event name
    for v in list(unique_event_name):
        tmp_paths = []
        for vv in unzip_files_activation:
            if re.search(v, vv):
                tmp_paths.append(vv)

        # Extract the version number from the file paths
        tmp_versions = []
        for t in tmp_paths:
            version = re.findall(r"_v\d_", t)[0]
            version_number = re.findall(r"\d", version)[0]
            tmp_versions.append(version_number)

        # Locate the latest version of vector data and
        # add it to the empty list created to store the
        # latest version of unzipped files.
        max_version = max(tmp_versions)
        max_version_index = tmp_versions.index(max_version)

        most_recent_ems_version = tmp_paths[max_version_index]
        unzip_files_activation_latest_v.append(most_recent_ems_version)

    # Process only the latest vector products
    unzip_files_activation = unzip_files_activation_latest_v
    code_date = table_activations_ems.loc[i]["CodeDate"]

    # Generate metadata and floodmaps for EMS activation events
    for unzip_folder in unzip_files_activation:
        try:
            # Check that all the .shp files follow the expected conventions 
            # with respect to timestamp and data availability.
            # Get AOI, hydrography, and observed event data from the zip file folder.
            metadata_floodmap = activations.filter_register_copernicusems(
                unzip_folder, code_date
            )

            # Process the .shp files' AOI, hydrography, and observed event
            # into a single geopandas.GeoDataFrame object using generate_floodmap.
            if metadata_floodmap is not None:
                logger.info(f"File {unzip_folder} processed correctly")

                # Combine floodmap and hydrography into one GeoDataFrame
                floodmap = activations.generate_floodmap(
                    metadata_floodmap, folder_files=unzip_folder
                )

                # Save ML4Flood metadata object
                with open(
                    os.path.join(
                        folder_metadata,
                        unzip_folder.split("/")[len((unzip_folder).split("/")) - 1]
                        + ".pickle",
                    ),
                    "wb",
                ) as f:
                    pickle.dump(metadata_floodmap, f)

                # Save floodmap as GeoJSON
                floodmap.to_file(
                    os.path.join(
                        folder_metadata,
                        unzip_folder.split("/")[len((unzip_folder).split("/")) - 1]
                        + ".geojson",
                    ),
                    drive="GeoJSON",
                )

            else:
                logger.warning(
                    f"File {unzip_folder} does not follow the expected format. It won't be processed"
                )
        except:
            logger.exception(f"Could not download {unzip_folder}")

logger.info(f"**********finished**********")