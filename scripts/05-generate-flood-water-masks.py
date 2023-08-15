# Import modules
import geopandas as gpd
import rasterio
import logging
import numpy as np
import os
from rasterio import features

# Adapted from https://github.com/spaceml-org/ml4floods/blob/main/ml4floods/data/copernicusEMS/activations.py

# Assign values to each category to burn in raster grid cells
# where 0: land, 1: flood, 2: hydrology.
CODES_FLOODMAP = {
    # CopernicusEMS (flood)
    "Flooded area": 1,
    "Previous flooded area": 1,
    "Not Applicable": 1,
    "Not Application": 1,
    "Flood trace": 1,
    "Dike breach": 1,
    "Standing water": 1,
    "Erosion": 1,
    "River": 2,
    "Riverine flood": 1,
    # CopernicusEMS (hydro)
    "BH140-River": 2,
    "BH090-Land Subject to Inundation": 0,
    "BH080-Lake": 2,
    "BA040-Open Water": 2,
    "BA030-Island": 0,  # islands are excluded! see filter_land func
    "BH141-River Bank": 2,
    "BH170-Natural Spring": 2,
    "BH130-Reservoir": 2,
    "BH141-Stream": 2,
    "BA010-Coastline": 0,
    "BH180-Waterfall": 2,
    # UNOSAT ------------
    "preflood water": 2,
    # "Flooded area": 1,  # 'flood water' DUPLICATED
    "flood-affected land / possible flood water": 1,
    # "Flood trace": 1,  # 'probable flash flood-affected land' DUPLICATED
    "satellite detected water": 1,
    # "Not Applicable": 1,  # unknown see document DUPLICATED
    "possible saturated, wet soil/ possible flood water": 1,
    "aquaculture (wet rice)": 1,
    "tsunami-affected land": 1,
    "ran of kutch water": 1,
    "maximum flood water extent (cumulative)": 1,
}


def compute_water(
    floodmap: gpd.GeoDataFrame,
    permanent_water_path: str = None,
    keep_streams: bool = True,
    out_path: str = None,
) -> np.ndarray:
    """
    Rasterise flood map and add land cover layer from ESA and permanent water layer from JRC
    Adapted from https://github.com/spaceml-org/ml4floods/blob/main/ml4floods/data/copernicusEMS/activations.py

    Args:
        floodmap: geopandas dataframe with the annotated polygons
        permanent_water_path: Static images path
        keep_streams: A boolean flag to indicate whether to include streams in the water mask
        out_path: path to save ground truth image output
    Returns:
        water_mask : np.int16 raster same shape as static image tiff file 
        {-1: invalid, 0: land, 1: flood, 2: hydro, 3: permanentwaterjrc}
    """

    # Retrieve the shape, transform, and the CRS
    # of the permanent water raster dataset.
    with rasterio.open(permanent_water_path) as src:
        out_shape = src.shape
        transform = src.transform
        target_crs = src.crs

    # Transform the CRS of floodmap to the CRS of the permanent 
    # water raster if they are not already the same.
    if str(floodmap.crs).lower() != target_crs:
        floodmap.to_crs(crs=target_crs, inplace=True)

    # Subset area_of_interest from the attribute table. 
    # Values outside of AOI should be marked as invalid.
    floodmap_aoi = floodmap[
        floodmap["w_class"] == "area_of_interest"
    ]  

    # Subset everything except area_of_interest from the
    # attribute table for rasterisation.
    floodmap_rasterise = floodmap.copy()
    if floodmap_aoi.shape[0] > 0:
        floodmap_rasterise = floodmap_rasterise[
            floodmap_rasterise["w_class"] != "area_of_interest"
        ]

    # If keep_streams flag is set to "False", subset everything
    # except rows that have source = hydro_1 (river, stream, coastline
    # river bank, rapids, water fall).
    if not keep_streams:
        floodmap_rasterise = floodmap_rasterise[
            floodmap_rasterise["source"] != "hydro_l"
        ]

    # Get the geometry of each object and map each object's w_class 
    # to its corresponding numerical code from CODES_FLOODMAP.
    shapes_rasterise = (
        (g, CODES_FLOODMAP[w])
        for g, w in floodmap_rasterise[["geometry", "w_class"]].itertuples(
            index=False, name=None
        )
        if g and not g.is_empty
    )

    # Rasterise vector floodmaps with the codes from CODES_FLOODMAP.
    # Set all empty grids to 0 (Land).
    water_mask = features.rasterize(
        shapes=shapes_rasterise,
        fill=0,
        out_shape=out_shape,
        dtype=np.int16,
        transform=transform,
        all_touched=keep_streams,
    )

    # Load valid mask using the area_of_interest polygons.
    # Valid pixels are those within the area_of_interest polygons.
    if floodmap_aoi.shape[0] > 0:
        shapes_rasterise = (
            (g, 1)
            for g, w in floodmap_aoi[["geometry", "w_class"]].itertuples(
                index=False, name=None
            )
            if g and not g.is_empty
        )
        valid_mask = features.rasterize(
            shapes=shapes_rasterise,
            fill=0,
            out_shape=out_shape,
            dtype=np.uint8,
            transform=transform,
            all_touched=True,
        )
        # Every pixel outside the area-of-interest is given a value of -1. 
        water_mask[valid_mask == 0] = -1

    # Get permanent water layer from ESA World Cover
    with rasterio.open(permanent_water_path) as src:
        permanent_water = src.read(2)  # ESA WorldCover
        out_meta = src.meta

    # Assign permanent water areas a value of 2. We are only
    # interested in the permanent water, which has a value of 80,  
    # that is within the valid water masks.
    water_mask[(water_mask != -1) & (permanent_water == 80)] = 2

    # Set the number of band and data type for the 
    # new metadata of the ground truth image output.
    out_meta["count"] = 1
    out_meta["dtype"] = np.int16

    # Save the ground truth image output with the new metadata
    with rasterio.open(out_path, "w", **out_meta) as dst:
        dst.write(water_mask, 1)


if __name__ == "__main__":
    
    # ----------------------------------------------------------
    # Set up a logger.
    # ----------------------------------------------------------

    # Create a custom logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create handlers
    f_handler = logging.FileHandler("04-generate-flood-water-masks.log")

    # Create formatters and add it to handlers
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)

    # ---------------------------------------
    # Create paths to get flood map and water
    # layer and to save ground truth images
    # ---------------------------------------

    # Path to EMSR activations
    folder_metadata = os.path.join(
        os.getcwd(), "source-data", "Copernicus_EMS_metadata"
    )

    # Path to static images
    static_images_path = os.path.join(
        os.getcwd(), "source-data", "static-images-merged"
    )

    # Get static images of permanent water layer and land cover
    static_images = os.listdir(static_images_path)

    # Path to save ground truth images
    ground_truth_path = os.path.join(os.getcwd(), "source-data", "ground-truth")
    os.makedirs(ground_truth_path, exist_ok=True)

    # Get all processed EMSR vector floodmaps
    emsr_floodmaps = os.listdir(folder_metadata)
    emsr_floodmaps_geojson = []

    for i in emsr_floodmaps:
        if i.endswith(".geojson"):
            emsr_floodmaps_geojson.append(i)
    
    # -----------------------------------------
    # Generate ground truth data for each event 
    # using the compute_water function
    # -----------------------------------------
    
    for i in emsr_floodmaps_geojson:
        logger.info(f"generating ground truth for event {i}")
        try:
            # Get EMSR code and AOI for each event
            emsr_code = i.split("_")[0:2]
            emsr_code = "_".join(emsr_code)

            # Configure output name to be saved and run compute_water function
            for z in static_images:
                if z.startswith(emsr_code):
                    permanent_water_path = os.path.join(static_images_path, z)
                    floodmap = gpd.read_file(os.path.join(folder_metadata, i))
                    out_fname = z.split(".tif")[0]
                    out_fname = out_fname + "_ground_truth.tif"
                    out_path = os.path.join(ground_truth_path, out_fname)
                    compute_water(
                        floodmap, str(permanent_water_path), True, str(out_path)
                    )
                    logger.info(f"ground truth for event {i} saved to {out_path}")
        except:
            logger.warning(f"failed to generate ground truth for event {i}")
            continue

logger.info(f"**********finished**********")