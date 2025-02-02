# Zonal-Stats-QGIS
QGIS plugin for performing zonal statistics, volume calculation, and vegetation index calculation


# Important Note
This QGIS plugin is still under experimental development and testing, as a result it is not unlikely that errors may occur when trying to install or run the plugin. Please feel free to report any errors on the issues page. So far, it has been tested on the following platforms and versions:
|Platform|QGIS Version|Python version|
|:---|:---|:---|
|Linux (RedHat) | 3.30.0rc | 3.10 |
|Linux (Rocky) | 3.30.0 | 3.10 |
|Linux (Ubuntu) | 3.26.3 | 3.9 |
|Windows 11 | 3.32.3 | 3.9 |
|Windows 11 | 3.34.14 | 3.12 |
|Windows 11 | 3.30.0 | 3.9 |

## Installation

### Prerequisites
Windows: You will need at least QGIS version 3.26  
Mac and Linux: You will need to have Python >= 3.9 on your system and in the PATH, and at least QGIS version 3.26

### From the zip file
Download the zonal_stats.zip file in this repository. In QGIS, go to the plugins menu, select 'Manage and Install Plugins', then go to 'Install from ZIP'. Here, select the zip file you downloaded and click 'Install Plugin'. Once it has finished, go to the 'Installed' tab, and uncheck and recheck the checkbox for the Zonal Statistics plugin. There may be delay as the package run some installation steps, which may take a few minutes.







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


After setting all the options and inputs as desired, you can then hit 'Run'. This will start the processing. It will run in the background (you should see a new task start, an a loading bar should appear in the bottom bar of QGIS), and when it is finished the loading bar in the plugin will go to 100%. A popup banner will likely appear as well to indicate that the processing task has finished.
