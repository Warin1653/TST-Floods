# Start from a core stack version
FROM jupyter/scipy-notebook:2023-01-02

USER root

# Install gcloud
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates gnupg curl sudo
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y
      
USER ${NB_UID}

# Install geospatial python packages
# geopandas noarch
# folium noarch
# ipyleaflet noarch
# rasterio noarch
# traitlets noarch
# leafmap noarch
# localtileserver noarch
# beautifulsoup noarch
# lxml 4.9.2 all linux archs
# bottlenck 1.3.6 all linux archs
RUN mamba install --quiet --yes \
    'geopandas==0.11.1' \ 
    'folium==0.14.0' \
    'ipyleaflet==0.17.2' \
    'pyarrow==9.0.0' \
    'rasterio==1.3.4' \
    'traitlets==5.9.0' \
    'leafmap==0.15.0' \
    'localtileserver==0.6.1' \
    'beautifulsoup4==4.11.1' \
    'lxml==4.9.2' \
    'rioxarray==0.13.3' \
    'bottleneck==1.3.6' \
    'odc-stac==0.3.5' \
    'earthengine-api' \ 
    'gdal==3.6.0' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# # https://github.com/geopandas/geopandas/issues/2442
ENV PROJ_LIB=/opt/conda/share/proj 

# Install requests for working with web APIs 
# Install plotly for visualisation
RUN pip install --quiet --no-cache-dir \
    'requests==2.28.1' \
    'plotly==5.11.0' \
    'html5lib==1.1' \
    'stackstac==0.4.3' \
    'ml4floods==0.0.5' \
    'black' && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"