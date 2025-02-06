# User’s manual for the zonal stats and volume extractions command-line tools and QGIS plugin



Alexander Hernandez and Kaden Patten

US Department of Agriculture—Agricultural Research Service, Forage & Range Research Laboratory, Logan, UT 84322-6300, USA
alexander.hernandez@usda.gov
kaden.patten@usda.gov

Welcome - This is the start point to access geospatial tools that have been developed by the USDA / ARS Forage and Range Research Lab in Logan Utah to process imagery collected using unmanned aerial vehicles - aka "drones".

These tools will help you:

* Generate a suite of vegetation indices (i.e. NDVI, RVI, NDRE, Greenness) from regular Red Green Blue RGB imagery as well as multispectral datasets
* Compute "cut/fill" volumes from digital surface models DSM
* Generate circular or rectangular buffers (areas of interest AOI) around point geometries
* Use polygon geometries (i.e. agricultural plots boundaries) to extract zonal statistics
* Save the vegetation indices as output multilayer rasters that can be used for predictive modeling purposes

 

Click on the link for the version of your interest:


[QGIS Plugin Version](https://github.com/alexanderhernandez-USDA/Zonal-Stats-QGIS/blob/main/README.md)

![icon](https://github.com/user-attachments/assets/4b2626b2-2a63-4172-9d18-ca21280921c1)


<img width="898" alt="Screenshot 2025-02-05 at 10 14 37 AM" src="https://github.com/user-attachments/assets/2c298067-7b53-470f-9268-eb98a873aed9" />





[Python Command-Line Version](https://github.com/alexanderhernandez-USDA/Zonal_Stats_3/blob/main/README.md)

> python3 zonal_stats_3.py -i [BI,SCI,GLI] flight/rasters/ [red,green,blue,redege,nir] flight/package.gpkg zonal_stats.gpkg
#Runs with indices BI, SCI, and GLI

> python3 zonal_stats_3.py -a flight/rasters/ [red,green,blue,redege,nir] flight/package.gpkg zonal_stats.gpkg
#Runs all indices with band order red, green, blue, NIR, RedEdge

> python3 zonal_stats_3.py -v flight/dsms/ flight/package.gpkg zonal_stats.gpkg
Performs volume calculation using a plane average
