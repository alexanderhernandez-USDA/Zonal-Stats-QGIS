# Zonal-Stats-QGIS
QGIS plugin for performing zonal statistics, volume calculation, and vegetation index calculation


## Installation

### Prerequisites
Windows: You will need at least QGIS version 3.26  
Mac and Linux: You will need to have Python >= 3.9 on your system and in the PATH

### From the zip file
Download the zonal_stats.zip file in this repository. In QGIS, go to the plugins menu, select 'Manage and Install Plugins', then go to 'Install from ZIP'. Here, select the zip file you downloaded and click 'Install Plugin'. Once it has finished, go to the 'Installed' tab, and uncheck and recheck the checkbox for the Zonal Statistics plugin.

## Usage
Once the plugin has been installed, you can open it by clicking on its icon. The plugin requires the path to an input folder, input geopackage, and output geopackage. Your input folder should contain the images you want to run on. Please verify that these images contain dates in their filenames. Dates can be delimited using ., _, or -. The following are three vaild formats:

YYYY_MM_DD  
DD.MM.YYYY  
MM-DD-YYYY  

After selecting your input folder, input geopackage, and output geopackage, you can then select the calculation/extraction type. There are four options:
1. Raw Extraction - Gets raw values from images
2. Volume Calculation - Calculates volumes for each polygon in geopackage (input images should be DSM/DEM rasters)
3. Volume Calculation with Reference DSM - Calculates volumes for each polygon in geopackage by using a reference DSM/DEM to calculate heights
4. Index Calculations - Allows for a selection of vegetation indices to be calculated and extracted

The Raw Extraction and Index Calculations options require that the image band order be listed as well. Band names should be lowercase, and separated by commas (no spaces), like so:

red,green,blue,rededge,nir

Once the calculation/extraction type has been selected, you can then select additional options. The options include point extraction, generating polygons from points, threading, setting a UID, and saving intermediate calculation rasters. An explanation for each of these options is below:

- Point extraction - If your input geopackage has points, not polygons, you can select this to extract values at those points.
- Polygon generation - If your input geopackage has points, select the option for using points. An additional checkbox will appear for creating buffers around the points. Check this box, and you can then choose between a square or circle buffer, and set the buffer size in meters.
- Save intermediate calculations - When calculating indices, the calculations are temporarily saved to disk. Selecting this option will let you choose a folder to save these intermediate calculations to. They will be saved in a multilayer raster by date.
- Threading - By default, only one thread is used for processing. If you would like to use more threads/cores for processing, you can set the number of threads to use.
- Set UID - By default, the UID 'id' is used for the input geopackage. If your input geopackage doesn't have a field/column named 'id', you can specify the name of your unique identifer column/field.


After setting all the options and inputs as desired, you can then hit 'Run'. This will start the processing. It will run in the background (you should see a new task start, an a loading bar should appear in the bottom bar of QGIS), and when it is finished the loading bar in the plugin will go to 100%. A popup banner will likely appear as well to indicate that the processing task has finished.
