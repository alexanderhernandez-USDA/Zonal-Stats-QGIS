# Zonal-Stats-QGIS
Quantum GIS (QGIS) plugin to perform several tasks that facilitate geospatial predictive modeling from multispectral datasets. The plugin can be used to extract spectral band values, compute vegetation indices such as NDVI, NDRE, RVI and others from the spectral bands as well as estimating volumes from digital surface models (DSMs). The plugin allows the reduction of pixels values contained in polygons to median zonal statistics. Users can process single rasters (i.e. one unmanned aerial vehicle UAV flight mission) or a time series of UAV flights. 


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

### Download the zip file
Download the zonal_stats.zip file in this repository. The zip file can be accesed directly from:
https://github.com/alexanderhernandez-USDA/Zonal-Stats-QGIS/blob/main/zonal_stats.zip

### Instalation in Quantum GIS
In QGIS, go to the plugins menu, select 'Manage and Install Plugins', then go to 'Install from ZIP'. 

![409284208-cc7cd9b3-e39d-497a-a7a1-ea2a9c0eaba9](https://github.com/user-attachments/assets/16eea8e6-6928-48f1-831f-ecbbef116f88)





Here, select the zip file you downloaded and click 'Install Plugin'. You will get a security warning about installing plugins from "untrusted sources". You can click "Yes" to continue with the installation process.

![409285614-b6d5a164-9cf1-463f-a00e-7cfda87e7b25](https://github.com/user-attachments/assets/c05d0d76-b406-4023-a9c7-83b284a8bff4)


Once it has finished, go to the 'Installed' tab, and uncheck and recheck the checkbox for the Zonal Statistics plugin.
![image](https://github.com/user-attachments/assets/c71baf94-af77-487e-9a64-b9de737e9a1b)


There may be delay as the package run some installation steps, which may take a few minutes.

You are done!






## Usage
## Sample data provided
You can download some sample data (i.e. RGB orthophotos and a point geometry geopackage) so that you can test the functionality of the plugin by yourself. The data can be downloaded from the following link:
https://github.com/alexanderhernandez-USDA/Zonal-Stats-QGIS/blob/main/Sample.zip

Once you download the zip file, unzip it and you will get a folder structure as such:
|Folder|Contents|Description|
|:---|:---|:---|
|//Sample | Site_points.gpkg | Point geometries |
|//Sample/Orthos | Three RGB TIFF files | Orthophotos - images |

Pay attention to the *.TIFF file names - Notice that these images contain dates in their filenames. Dates can be delimited using ., _, or -. The following are three valid formats:

YYYY_MM_DD  
DD.MM.YYYY  
MM-DD-YYYY  

**Keep in mind that the plugin has been developed to process one orthophoto or a time series of orthophotos and as such we need to differentiate when the different images were collected**

Once the plugin has been installed, you can open it by clicking on its icon. 
<img width="76" alt="icon" src="https://github.com/user-attachments/assets/826d45ff-26be-4f26-8b28-dcbc1756fb30" />


The plugin requires the path to an input folder, input geopackage, and output geopackage. Your input folder should contain the images you want to run on. 

After selecting your input folder, input geopackage, and output geopackage, you can then select the calculation/extraction type. There are four options:
1. Raw Extraction - Gets raw values from images - i.e. extract the pixel value at each of the sample locations 
2. Volume Calculation - Calculates volumes for each polygon in geopackage (input images should be DSM/DEM rasters)
3. Volume Calculation with Reference DSM - Calculates volumes for each polygon in geopackage by using a reference DSM/DEM to calculate heights
4. Index Calculations - Allows for a selection of vegetation indices to be calculated and extracted

The Raw Extraction and Index Calculations options require that the image band order be listed as well. Band names should be lowercase, and separated by commas (no spaces), like so:

red,green,blue,rededge,nir

**Let's take a look at the first option - where we: a) define the folder containing the images, b) select the input geopackage and c: define a name for the output geopackage:**

![409349033-25237ed3-9c4f-42e3-9d5e-9f9d2d0aa0e1 (1)](https://github.com/user-attachments/assets/b13e939e-fc9e-4b57-b98a-714d207ad0a0)

![409349033-25237ed3-9c4f-42e3-9d5e-9f9d2d0aa0e1](https://github.com/user-attachments/assets/30be1ba5-2694-4e64-8582-b9c512539db4)


**Click Run and once it shows 100% click Close**

If we open the output geopackage in QGIS and open the attribute table we can see that there are columns for the different bands (i.e. red, green, blue) values for each of the dates that the orthophotos were collected and that this information is available for each of the point geometries.

![image](https://github.com/user-attachments/assets/c596356d-dd1c-48b7-8c78-a6629e174f94)

**Now imagine that you want to create polygon geometries around each one of the point geometries. The plugin allows you to create circular or rectangular polygons. Let's try the option to create circular buffers of 55 centimeters (0.55 m) and then extract the median value within each one of the polygon geometries**

![image](https://github.com/user-attachments/assets/bed7db4f-5ec1-4203-a4f0-07e4b05b0f92)

If we open the output geopackage in QGIS, and overlay the input point geometries we can see that we have generated circular buffers. The attribute table for the output geopackage (i.e. Site_points_bandcircles.gpkg) contains the median value for each one of the bands for all of the dates that we are analyzing.

![image](https://github.com/user-attachments/assets/ddfbde77-e3b4-4efa-bec0-9a7ecb378762)

**Now let's try to compute vegetation indices. The plugin has a couple dozen vegetation indices that can be calculate using the input bands. For the sample dataset that we have provided here we only have three bands: RED, GREEN, BLUE. In other words we can only request vegetation indices that build upon these three bands. Let's try to  create polygon rectangular geometries (0.55 m) around each one of the points.**

Observe that we first click on the Calculation Type dropbox and select **Index Calculations**
![image](https://github.com/user-attachments/assets/37dfc616-64cb-4cfc-82cb-fd08166092ae)

We then select the vegetation indices that we need - and in this case we had decided to generate rectangular boxes around each point geometry

![image](https://github.com/user-attachments/assets/338c6005-cca6-49f2-aaf4-914f466115ce)

If we open the output geopackage on QGIS we can see that now we have rectangular geometries around each point.

![image](https://github.com/user-attachments/assets/27a9e88e-0256-4331-8f31-d86e7820bc69)

And if we open the atribute table for the output geopackage (i.e. Site_points_VIs_Boxes.gpkg) you will find the calculated zonal statistics (median value for all the pixels that are contained within each polygon geometry) for each one of the dates that we are analyzing.

![image](https://github.com/user-attachments/assets/a73a8d60-5bfc-45d0-a2c7-17f4c04e382d)





Once the calculation/extraction type has been selected, you can then select additional options. The options include point extraction, generating polygons from points, threading, setting a UID, and saving intermediate calculation rasters. An explanation for each of these options is below:

- Point extraction - If your input geopackage has points, not polygons, you can select this to extract values at those points.
- Polygon generation - If your input geopackage has points, select the option for using points. An additional checkbox will appear for creating buffers around the points. Check this box, and you can then choose between a square or circle buffer, and set the buffer size in meters.
- Save intermediate calculations - When calculating indices, the calculations are temporarily saved to disk. Selecting this option will let you choose a folder to save these intermediate calculations to. They will be saved in a multilayer raster by date.
- Threading - By default, only one thread is used for processing. If you would like to use more threads/cores for processing, you can set the number of threads to use.


After setting all the options and inputs as desired, you can then hit 'Run'. This will start the processing. It will run in the background (you should see a new task start, an a loading bar should appear in the bottom bar of QGIS), and when it is finished the loading bar in the plugin will go to 100%. A popup banner will likely appear as well to indicate that the processing task has finished.
