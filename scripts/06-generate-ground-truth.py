# Import Modules
import geopandas as gpd
import rasterio
from rasterio.windows import Window
import logging
import numpy as np
import os
from rasterio import features


def generate_ground_truth(ground_truth_dir, ground_truth_merge_dir):
    """
    Generate ground truth images of EMS activation flood events and permanent water.

    Combine all flood maps for an EMS activation event (e.g. generated on different dates).

    Args:
        ground_truth_dir: directory of ground truth flood water masks - there can be several
        EMS activations per event as the event unfolds over time.

        ground_truth_merge_dir: directory to store merged ground truth flood water masks
    """
    # Set up output directories
    os.makedirs(ground_truth_bb_fixed_path, exist_ok=True)
    os.makedirs(ground_truth_merge_dir, exist_ok=True)

    # Get a list of EMSR events
    ground_truth_files = os.listdir(ground_truth_dir)

    emsr_events = []

    for i in ground_truth_files:
        emsr_aoi_id = i.split("_")[0:2]
        emsr_aoi_id = "_".join(emsr_aoi_id)
        emsr_events.append(emsr_aoi_id)

    # Get unique EMSR events by removing duplicates
    emsr_events = list(set(emsr_events))
    emsr_events = sorted(emsr_events)

    # Create a list of already processed ground truth files
    processed = os.listdir(ground_truth_merge_dir)
    processed_event = []
    
    for i in processed:
        tmp_event_id = i.split("_")[0:2]
        tmp_event_id = "_".join(tmp_event_id)
        processed_event.append(tmp_event_id)
    
    # Fix bounding box and merge pixel values for each file
    for i in emsr_events:
        if i not in processed_event:
            print(i)
            try:
                logger.info(f"starting to generate ground truth for EMSR event {i}")
               
                # --------------------------------------------------------
                # Fix bounding boxes with different shapes for each AOI to 
                # be the same shape. This ensures successful aggregation 
                # of raster pixels during the merging process.
                # -------------------------------------------------------- 
                
                # Get a list of ground truth files that match the event being processed
                aoi_tmp = []
                for z in ground_truth_files:
                    if z.startswith(i):
                        aoi_tmp.append(z)

                # Get the window for intersecting rasters. This window is the largest
                # bounding box that intersects all raster files within in an AOI.
                bounding_boxes = []

                # Get the bounds of each file of the AOI that is being processed
                for j in aoi_tmp:
                    path = os.path.join(ground_truth_dir, j)
                    with rasterio.open(path) as src:
                        bound = src.bounds
                        bounding_boxes.append(bound)

                    # Get the index of the smallest and the largest bounding boxes
                    index_of_smallest = min(
                        range(len(bounding_boxes)),
                        key=lambda i: (bounding_boxes[i][2] - bounding_boxes[i][0])
                        * (bounding_boxes[i][3] - bounding_boxes[i][1]),
                    )
                    index_of_largest = max(
                        range(len(bounding_boxes)),
                        key=lambda i: (bounding_boxes[i][2] - bounding_boxes[i][0])
                        * (bounding_boxes[i][3] - bounding_boxes[i][1]),
                    )

                    # Create paths to the AOIs that have the smallest and the largest bounding boxes
                    path_smallest_box = os.path.join(
                        ground_truth_dir, aoi_tmp[index_of_smallest]
                    )
                    path_largest_box = os.path.join(
                        ground_truth_dir, aoi_tmp[index_of_largest]
                    )

                # Intersect the largest bounding box with the smallest bounding box
                for k in aoi_tmp:
                    path = os.path.join(ground_truth_dir, k)

                    # Open the raster to be fixed
                    with rasterio.open(path_largest_box) as src:
                        
                        # Open the reference raster for intersection
                        with rasterio.open(path_smallest_box) as ref:
                            
                            # Calculate the intersection bounds
                            intersection_left = max(src.bounds.left, ref.bounds.left)
                            intersection_bottom = max(
                                src.bounds.bottom, ref.bounds.bottom
                            )
                            intersection_right = min(src.bounds.right, ref.bounds.right)
                            intersection_top = min(src.bounds.top, ref.bounds.top)

                            # Convert intersection bounds to a window
                            if (
                                intersection_left < intersection_right
                                and intersection_bottom < intersection_top
                            ):
                                
                                window = rasterio.windows.from_bounds(
                                    intersection_left,
                                    intersection_bottom,
                                    intersection_right,
                                    intersection_top,
                                    transform=src.transform,
                                    width=src.width,
                                    height=src.height,
                                )

                                # Read and crop the source raster using the window
                                cropped_data = src.read(window=window)

                                # Calculate new bounds based on the window
                                new_left, new_top = window.col_off, window.row_off
                                new_right, new_bottom = (
                                    new_left + window.width,
                                    new_top + window.height,
                                )

                                # Transform new bounds to map coordinates
                                new_bounds = (
                                    src.transform * (new_left, new_top),
                                    src.transform * (new_right, new_bottom),
                                )

                                # Extract bound values from the cropped_data
                                # to get the bounds of the window
                                left = new_bounds[0][0]
                                top = new_bounds[0][1]
                                right = new_bounds[1][0]
                                bottom = new_bounds[1][1]

                # Loop over each file again to apply the new window bounds
                for n in aoi_tmp:
                    path = os.path.join(ground_truth_dir, n)

                    # Open the reference raster
                    with rasterio.open(path) as src:
                        window = rasterio.windows.from_bounds(
                            left,
                            bottom,
                            right,
                            top,
                            transform=src.transform,
                            width=src.width,
                            height=src.height,
                        )

                        # Read and crop the source raster using the new window
                        cropped_data = src.read(window=window)

                        # Create a new raster file for the cropped data
                        cropped_meta = src.meta.copy()
                        cropped_meta.update(
                            {
                                "height": window.height,
                                "width": window.width,
                                "transform": rasterio.windows.transform(
                                    window, src.transform
                                ),
                            }
                        )

                        # Save the fixed file to ground_truth_bb_fixed folder
                        out_path = os.path.join(ground_truth_bb_fixed_path, n)
                        with rasterio.open(out_path, "w", **cropped_meta) as dst:
                            dst.write(cropped_data)

                            
                # --------------------------------------------------------------
                # For each AOI, aggregate land, flood, and water pixels from
                # all the flood-water masks associated with the AOI to determine
                # the maximum extent of flood that occured.
                # --------------------------------------------------------------
                
                # Create empty lists for storing land, flood, and water data
                land_tmp = []
                flood_tmp = []
                water_tmp = []

                # Read in the fixed flood-water mask files. Extract land, flood, and water
                # pixels from each file, then store them in their respective lists.
                for m in aoi_tmp:
                    raster_tmp_path = os.path.join(ground_truth_bb_fixed_path, m)

                    src = rasterio.open(raster_tmp_path)
                    raster = src.read(1)
                    meta = src.meta
                    src.close()

                    land = (raster == 1) * 1
                    land_tmp.append(land)
                    flood = (raster == 2) * 1
                    flood_tmp.append(flood)
                    water = (raster > 2) * 1
                    water_tmp.append(water)

                # Sum up the values from each pixel stored in each list to generate
                # a single ground truth image per AOI. A boolean array is used to 
                # indicate the presence of targeted pixels across all flood-water mask files.
                land_sum = (sum(land_tmp) >= 1) * 1
                flood_sum = ((sum(flood_tmp) >= 1) * 1) * 2
                water_sum = ((sum(water_tmp) >= 1) * 1) * 3

                # Transfer pixel values in water_sum and flood_sum to land_sum and assign 
                # flood and water pixels as 2 and 3, respectively, in land_sum. We use 
                # land_sum as the base array because flood values should occupy the pixel 
                # if there are both flood and land values on the same pixel.
                land_sum[flood_sum == 2] = 2
                land_sum[water_sum == 3] = 3

                # Save land_sum array as merged ground truth data in ground_truth_merged folder
                out_fpath = os.path.join(
                    ground_truth_merge_dir, i + "_ground_truth_merged.tif"
                )
                dst = rasterio.open(out_fpath, "w", **meta)
                dst.write(land_sum, 1)
                dst.close()

            except:
                logger.warning(f"failed to generate ground truth for EMSR event {i}")
                continue


if __name__ == "__main__":
    
    # ----------------------------------------------------------
    # Set up a logger.
    # ----------------------------------------------------------

    # Create a custom logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create handlers
    f_handler = logging.FileHandler("05-generate-ground-truth.log")

    # Create formatters and add it to handlers
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)

    # -------------------------------------------------------------
    # Create paths to ground truth folder, fixed ground truth
    # folder, and merged ground truth folder, then generate
    # merged ground truth data using generate_ground_truth function
    # -------------------------------------------------------------

    # Path to ground truth data
    ground_truth_dir = os.path.join(os.getcwd(), "source-data", "ground-truth")

    # Path to ground truth data with fixed bounding boxes
    ground_truth_bb_fixed_path = os.path.join(
        os.getcwd(), "source-data", "ground-truth-bb-fixed"
    )

    # Path to merged ground truth data
    ground_truth_merge_dir = os.path.join(
        os.getcwd(), "source-data", "ground-truth-merged"
    )

    # Run the generate_ground_truth function
    generate_ground_truth(ground_truth_dir, ground_truth_merge_dir)

    logger.info("**** finished ****")