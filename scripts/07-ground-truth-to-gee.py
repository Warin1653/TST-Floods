# Import modules
import os
import pandas as pd

# Get merged ground truth files
ground_truth_merge_dir = os.path.join(os.getcwd(), "source-data", "ground-truth-merged")
ground_truth_files = os.listdir(ground_truth_merge_dir)

# Get the list of EMSR activations
df = pd.read_csv(
    os.path.join(os.getcwd(), "source-data", "Copernicus_EMS_table", "tropical_ems_event_date.csv")
    )

# Upload the images to GEE
for i in ground_truth_files:
    print(f"processing {i}")
    prefix = i.split(".tif")[0]
    
    # Get event ID and event date
    event_aoi = i.split("_ground")[0]
    event_id = event_aoi.split("_")[0]
    event_date = df.loc[df["Code"] == event_id, "EventDate"].to_list()[0]
    
    # Set metadata properties for the GEE assets
    date_command = f"earthengine asset set -p '(string)event_date={event_date}' projects/fiji-s2-image-stack/assets/tropical-floods-ground-truth/{prefix}"
    os.system(date_command)
    id_command = f"earthengine asset set -p '(string)event_id={event_id}' projects/fiji-s2-image-stack/assets/tropical-floods-ground-truth/{prefix}"
    os.system(id_command)