# Import modules
import os
import pickle
import shutil
import logging
import pandas as pd

# ----------------------------------------------
# Generate a CSV file with filename, event date, 
# activation date, and satellite date columns 
# for each merged static image
# ----------------------------------------------

# Create a path to access merged raster files
images_merged_path = os.path.join(os.getcwd(), "source-data", "static-images-merged")
merged_images = os.listdir(images_merged_path)

# Store the names of the files without -static-images in a list
merged_file_list = []
for i in merged_images:
    merge_file = i.split("_")
    merge_file = "_".join(merge_file[:-2])
    merged_file_list.append(merge_file)

# Create a DataFrame of merged file names and their corresponding EMSR codes
filecode = []

for i in merged_file_list:
    merge_code = i.split("_")[0:1]
    merge_code = "_".join(merge_code)
    filecode.append(merge_code)
    
filename_code = {
    'File Name': merged_file_list,
    'Code': filecode
}

filename_code_df = pd.DataFrame(filename_code)
    
# Create a path to CSV file of EMS activation table with activation dates 
# and event dates (from Script 02) and read in as DataFrame.
folder_csv_ems_date = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_table")
ems_df = pd.read_csv(os.path.join(folder_csv_ems_date, "tropical_ems_event_date.csv"))

# Get lists of EMSR codes and their corresponding event dates and activation dates.
ems_df_code = ems_df["Code"]
ems_df_date = ems_df["EventDate"]
ems_df_activation_date = ems_df["CodeDate"]
emd_df_activation_country = ems_df["Country"]

# Create a DataFrame of the lists
code_dates = {
    'Code': ems_df_code,
    'Event Date': ems_df_date,
    'Activation Date': ems_df_activation_date,
    'Country': emd_df_activation_country
}
code_dates_df = pd.DataFrame(code_dates)

# Merge filename_code DataFrame with code_dates DataFrame using code as the key.
merged_df = pd.merge(filename_code_df, code_dates_df, on='Code', how='left')

# Create a path to EMS activations metadata
folder_metadata = os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_metadata")

# Get EMS activation metadata pickle files to get satellite dates
metadata_files = os.listdir(folder_metadata)
metadata_files_pickle = []
for i in metadata_files:
    if i.endswith(".pickle"):
        metadata_files_pickle.append(i)

satellite_date = []

# Read the metadata pickle file of each event
for i in metadata_files_pickle:
    fpath = os.path.join(folder_metadata, i)
    with open(fpath, "rb") as f:
            metadata_floodmap = pickle.load(f)
    
    # Extract the satellite date of the event from the metadata
    satellite_date_timestamp = metadata_floodmap["satellite date"]
    satellite_date_ddmmyyyy = satellite_date_timestamp.strftime('%d/%m/%Y')
    satellite_date.append(satellite_date_ddmmyyyy)

# Add the satellite date list to the merged DataFrame as a column
merged_df["Satellite Date"] = satellite_date

# Drop the Code column from the DataFrame
merged_df_dropcode = merged_df.drop("Code", axis=1)
merged_df_dropcode

# Move the 'Country' column to the last column
country_column = merged_df_dropcode.pop('Country')
merged_df_dropcode.insert(4, 'Country', country_column)

# Save the final dataframe as a CSV file
merged_df_dropcode.to_csv(os.path.join(folder_csv_ems_date, "static_images_dates.csv"))

logger.info(f"**********finished**********")