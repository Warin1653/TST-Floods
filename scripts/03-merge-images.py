# Import modules
import os
import pickle
import shutil
import logging
import pandas as pd

#----------------------------------------------------------
# Set up a logger.
#----------------------------------------------------------

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers
f_handler = logging.FileHandler("03-merge-images.log")

# Create formatters and add it to handlers
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


# -------------------------------------------------
# Merging raster images. 
# This function will be used to merge static images 
# downloaded in Script 01-downlaod-images.py
# -------------------------------------------------

def merge_rasters(
    images_path,
    images,
    images_merged_path
):
    """
    Check for images that were split in GEE export and merge.
    
    Args:
        images_path (string): path to images
        images (list): list of images
        images_merged_path (string): path to directory to save merged images
        
    Returns:
        dictionary: dictionary with each element storing paths to ems vectors and images
    """

    event_id_list = []

    os.makedirs(images_merged_path, exist_ok=True)

    # Get a list of events and AOIs
    for i in images:
        event_id = i.split("_")
        event_id = "_".join(event_id[:-2])
        event_id_list.append(event_id)
        
    # Remove duplicate IDs to get unique event IDs 
    event_id_list = list(set(event_id_list))

    # Iterate over each event and AOI to merge images
    for f in event_id_list:
        logger.info(f"processing event {f}")

        # Create an empty List to store file names matching event and AOI
        event_aoi_tmp = []

        # Create an empty list to store products matching event and AOI
        event_aoi_product_tmp = []
        
        for i in images:
            if i.startswith(f):
                event_aoi_tmp.append(i)
                event_aoi_product = i.split("_static")[0]
                event_aoi_product_tmp.append(event_aoi_product)
        
        # Remove duplicate IDs to get unique event IDs and generate item
        # for only the first product. Images should be the same for all
        # products of the same event and AOI combination.
        event_aoi_product_tmp = list(set(event_aoi_product_tmp))[0]
        
        list_to_merge = []

        for i in event_aoi_tmp:
            if i.startswith(event_aoi_product_tmp):
                list_to_merge.append(os.path.join(images_path, i))

        # For events with multiple images, merge images using 
        # the merge command-line tool from GDAL. For events with 
        # a single image, simply copy to the destination folder.
        if len(list_to_merge) > 1:
            logger.info(f"merging images for {i}")
            merge_out_path = os.path.join(images_merged_path, f + "_static_images.tif")
            merge_infiles = " ".join(list_to_merge)
            merge_command = "gdal_merge.py -o " + merge_out_path + " " + merge_infiles + " -co COMPRESS=LZW -co BIGTIFF=YES -co PREDICTOR=2 -co TILED=YES"
            os.system(merge_command)
        else:
            logger.info(f"not merging images for {f}")
            logger.info(f"copying image for {f}")
            merge_out_path = os.path.join(images_merged_path, f + "_static_images.tif")
            file_to_copy = list_to_merge[0]
            shutil.copy(file_to_copy, merge_out_path)

# Run the merge_rasters function
if __name__ == "__main__":
    images_path = os.path.join(os.getcwd(), "source-data", "static-images")
    images = os.listdir(images_path)
    images_merged_path = os.path.join(os.getcwd(), "source-data", "static-images-merged")

    merge_rasters(images_path, images, images_merged_path)

logger.info(f"**********finished**********")