import geopandas as gpd
import pandas as pd
import os, sys, re, shutil
import rasterio
from rasterio.mask import mask
import numpy as np
import multiprocessing
import multiprocessing.pool
from shapely import unary_union
from skimage import io
from skimage.color import rgb2hsv
from exactextract import exact_extract
#from osgeo import gdal
#gdal.UseExceptions()
import math
import warnings

# Help screen
helpScreen = """Usage: python3 zonal_stats_3.py [OPTIONS] <index_flag> <index_requirements> input_file.gpkg output_file.gpkg

Reads all tif files in an input directory, performs specified index calculations, and outputs a gpkg file with median calculations for polygons from input gpkg file

Please note that at least one index option (-a, -i, -n, -v or -V) and its corresponding input directory must be used in order to run

All non-volumetric calculations and extractions require band order to be specified as well. The default band order is [red,green,blue,redege,nir], and you can
use the default by using empty square brackets, like [], when specifying band order.

Options
Global Options
    -h      Show this help
    -q      Suppress non-error messages
    -l      Show available vegetation indices
    -u <uid>        Specify a unique ID column name from geopackage/shapefile (verify that it is actually unique, there cannot be any repeats)
    -t <threads>    Specify number of threads for multithreading, by default one thread is used, you can specify up to total thread count - 2
    -p              Use a geopackage that has points instead of polygons, returns values at those points
    -S <distance>   Use a geopackage that has points instead of polygons, and specify a distance in meters for a square buffer around the point
    -C <distance>   Use a geopackage that has points instead of polygons, and specify a distance in meters for a circular buffer around the point
    -o <directory>  Generate multi-layer tifs containing intermediate calculation/extraction data by date in the specified output directory

Index / Calculation options : Specify a directory (and band order if not a volume calc) per flag. Multiple index/calculation options may be used in a single command
    -i [<indices>] <directory> [<bands>]    Pass a list of vegetation indices to be run, in format [index1,index2,...] (try -l option to see available indices)
    -a <directory> [<bands>]         Run all vegetation indices (except DGCI, VOLUME, and NONE)
    -n <directory> [<bands>]         Run zonal_stats without any indices (band order/count of images should match those specified in the -b flag)
    -v <directory>          Specify a path to a folder to run volume calculation on using a plane average calculation.
    -V <directory> <second_dsm.tif>      Specify a path to a folder to run volume calculation on using a secondary DSM to calculate heights, the second DSM should be specified after the folder name.

Examples:
python3 zonal_stats_3.py -i [BI,SCI,GLI] flight/rasters/ [red,green,blue,redege,nir] flight/package.gpkg zonal_stats.gpkg       #Runs with indices BI, SCI, and GLI
python3 zonal_stats_3.py -u pid -a flight/rasters/ [red,green,blue,redege,nir] flight/package.gpkg zonal_stats.gpkg             #Runs with all indices, unique ID column set to 'pid'
python3 zonal_stats_3.py -a flight/rasters/ [red,green,blue,redege,nir] flight/package.gpkg zonal_stats.gpkg    #Runs all indices with band order red, green, blue, NIR, RedEdge
python3 zonal_stats_3.py -n flight/thermals/ [swir] flight/rasters/ flight/package.gpkg zonal_stats.gpkg   #Runs zonal stats on the thermals directory getting raw values
python3 zonal_stats_3.py -v flight/dsms/ flight/package.gpkg zonal_stats.gpkg                       # Performs volume calculation using a plane average
python3 zonal_stats_3.py -V flight/dsms/ flight/ref_dsm.tif flight/package.gpkg zonal_stats.gpkg    # Performs volume calculation using a reference DSM raster
python3 zonal_stats_3.py -t 12 -v flight/dsms/ flight/package.gpkg zonal_stats.gpkg                 # Uses 12 threads to perform volume calculation
python3 zonal_stats_3.py -p -i [BI] flight/rasters/ [red,green,blue,redege,nir] flight/point_package.gpkg point_stats.gpkg      # Gets values at each point of a point-based geopackage after BI calculation
python3 zonal_stats_3.py -C 1 -i [BI] flight/rasters/ [red,green,blue,redege,nir] flight/point_package.gpkg circle_stats.gpkg   # Makes circular buffers with a 1 meter radius from point-based geopackage and performs BI calculation and then gets stats for each buffer
python3 zonal_stats_3.py -S 1 -i [BI] flight/rasters/ [red,green,blue,redege,nir] flight/point_package.gpkg square_stats.gpkg   # Makes square buffers with a 1 meter radius from point-based geopackage and performs BI calculation and then gets stats for each buffer
python3 zonal_stats_3.py -n flight/thermals/ [swir] -i [BI] flight/rasters/ [] flight/package.gpkg output.gpkg  # Get raw values from SWIR images and gets the BI index from images in rasters with default band order
python3 zonal_stats_3.py -o flight/outputs/ -i [BI,SCI,GLI] flight/raster/ [] flight/package.gpkg output.gpkg  # Get BI, SCI and GLI indices and output rasters with calculation data in flight/outputs/
"""
# Screen for available vegetation indices (-l flag)
vegIndices = """Available vegetation indices

Other data extractions: must be run with their respective flags
Index   Description                     Requirements
VOLUME  Plot Volume                     This calculates the volume for each plot from a DSM. It can be run without a reference DSM using -v, or with a reference DSM using -V
NONE    Get Raw Values                  This is for getting the median of raw values for a plot, useful for things like temperatures. It can be run using the -n flag. Band order should match those specified with the -b flag.
DGCI    Dark Green Color Index          Can be run with the -i flag by its index name, ONLY SUPPORTS 8-BIT RGB IMAGES!

Indices from indices.conf
The following can be run multiple at a time via the -i flag, or all can be run with the -a flag
Index   Description
"""
# Global variables
verbose = True
indexFlags = ''
allIndices = False
default_bands = ['red','green','blue','rededge','nir']
valid_types = ['tif','tiff']
dgci = False
no_index = False
uid = 'id'
no_ind_dir = ''
date_regex = "([0-3]?[0-9](_|-|\.)[0-3]?[0-9](_|-|\.)[0-9]{2,4}|[0-9]{2,4}(_|-|\.)[0-3]?[0-9](_|-|\.)[0-3]?[0-9])"
to_run = []
threads = 1
polygons = True
buffer = None
buffer_size = 0
script_dir = os.path.dirname(os.path.realpath(__file__))
output = None


# Get a single band from an image
def get_band(raster,bands,band):
    with rasterio.open(raster) as ras:
        ds = ras.read()
        ds = ds.astype(float)
        return ds[bands.index(band)],ras.meta.copy()

# Write processing tif from raster data for an index, copies over original tags as well
def write_tif(proc_dir,data,t,in_dir,tName,i):
    if data is None:
        print(f"Error in processing {tName}_{i}!",file=sys.stderr)
        return "ERROR"
    meta = data[1]
    data = data[0]

    meta.update({
        "count": 1,
        "dtype": np.float32
    })
    with rasterio.open(os.path.join(proc_dir,tName,tName+'_'+i+'.tif'),'w',**meta) as dst:
        dst.write_band(1,data)

# Run all standard vegetation indices
def run_all(proc_dir,t,in_dir,tName,bands,r=None,gdf=None,pool=None,wide_open=False):
    if len(indexDict.keys()) < 5:
        print("No indices to run on! Likely missing indices.conf!",file=sys.stderr)
        return
    if type(pool) != type(None) and wide_open:
        pool.starmap(sub_process_image,[(proc_dir,i,in_dir,t,bands,tName) for i in list(indexDict.keys())[4:]])
    else:
        for i in list(indexDict.keys())[4:]:
            res = write_tif(proc_dir,indexDict[i](os.path.join(in_dir,t),bands),t,in_dir,tName,i)
            if res=="ERROR":
                return 'ERROR'

# Run a list of vegetation indices
def run_list(proc_dir,t,in_dir,tName,bands,indexFlags):
    for i in indexFlags:
        if i in indexDict:
            res = write_tif(proc_dir,indexDict[i](os.path.join(in_dir,t),bands),t,in_dir,tName,i)
            if res=="ERROR":
                return 'ERROR'
        else:
            print("Unrecognized vegetation index: "+i+", skipping this index")
            continue

# DGCI calculation (questionable if actually works correctly)
def calc_DGCI(raster,bands):
    rgb_img = io.imread(raster)[:,:,:3]
    hsv_img = rgb2hsv(rgb_img)
    hue_img = hsv_img[:, :, 0]
    sat_img = hsv_img[:, :, 1]
    value_img = hsv_img[:, :, 2]

    dgci = (((hue_img - 60)/60) + (1 - sat_img) + (1 - value_img))/3

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with rasterio.open(raster) as ras:
            out_meta=ras.meta.copy()

    return dgci,out_meta

# Run DGCI (wrapper for calc_DGCI)
def run_dgci(proc_dir,t,in_dir,tName,bands,r,gdf):
    res = write_tif(proc_dir,calc_DGCI(os.path.join(in_dir,t),bands),t,in_dir,tName,"DGCI")
    if res=='ERROR':
        return 'ERROR'

# Make a copy of image for raw data statistics
def run_raw(proc_dir,t,in_dir,tName,bands,r,gdf):
    #print(bands)
    for b in bands:
        res = write_tif(proc_dir,get_band(os.path.join(in_dir,t),bands,b),t,in_dir,tName,f"{b}")
        if res=='ERROR':
            return 'ERROR'

# Run volume calculation
def calc_volume(proc_dir,t,in_dir,tName,bands,r,gdf):
    dsm_raw = rasterio.open(os.path.join(in_dir,t))
    dsm_data = dsm_raw.read(1)
    if r['ref'] == "NONE":
        plane_arr = np.zeros([dsm_raw.height,dsm_raw.width])
        pixw = abs(dsm_raw.transform[0])
        pixy = abs(dsm_raw.transform[4])
        pix_area = pixw * pixy
        for n,p in gdf.iterrows():
            if p['geometry'].geom_type == "MultiPolygon":
                x,y = unary_union(p['geometry']).exterior.coords.xy
            elif p['geometry'].geom_type == "Polygon":
                x,y = p['geometry'].exterior.coords.xy
            else:
                print(f"{p['geometry'].geom_type} is an invalid geometry type for volume calculation!",file=sys.stderr)
                sys.exit(-1)
            cor1, cor2 = (dsm_raw.index(min(x),max(y)),dsm_raw.index(max(x),min(y)))
            total = 0
            try:
                for i in range(len(x)):
                    py,px = dsm_raw.index(x[i],y[i])
                    total+=dsm_data[int(py),int(px)]
                avg = total/len(x)
                plane_arr[int(cor1[0]):int(cor2[0])+1,int(cor1[1]):int(cor2[1])+1] = avg
            except Exception as e:
                print(f"Error in calculating volume: {e}.\n Please verify that you are using the right geopackage!",file=sys.stderr)
                sys.exit(-1)

        heights = dsm_data - plane_arr
    else:
        
        alt_dsm_raw = rasterio.open(r['ref'])
        alt_dsm_data = alt_dsm_raw.read(1)
        heights = dsm_data - alt_dsm_data

    volumes = heights * pix_area
    pos = (volumes > 0).astype(int)
    final = volumes * pos
    kwargs = dsm_raw.meta

    with rasterio.open(os.path.join(proc_dir,tName,tName+'_VOLUME.tif'),'w',**kwargs) as dst:
        dst.write(final,1)
        dst.close()

# Dictionary of indices and corresponding index functions
indexDict = {
    'DGCI': calc_DGCI,
    'NONE': run_raw,
    'ALL': run_all,
    'VOLUME': calc_volume
}

# Read indices configuration file
def read_config(conf):
    global vegIndices
    if not os.path.exists(conf):
        return
    with open(conf,"r") as f:
        configs = f.read().split("\n")
    for i in configs:
        if i=="":
            continue
        if i.strip()[0]=="#":
            continue
        if i[0] == "[" and i[-1]=="]":
            name = i[1:-1]
            desc = ""
            calc = ""
        elif "desc" in i:
            desc = i.split(":")[-1].strip()
        elif "calc" in i:
            calc = i.split(':')[-1].strip()
            exec(f"""def calc_{name}(raster,bands):
                                    with warnings.catch_warnings():
                                        warnings.simplefilter("ignore")
                                        with rasterio.open(raster) as ras:
                                            out_meta=ras.meta.copy()
                                            ds = ras.read()
                                            ds = ds.astype(float)
                                            if 'red' in bands:
                                                r = ds[bands.index('red')]
                                            if 'green' in bands:
                                                g = ds[bands.index('green')]
                                            if 'blue' in bands:
                                                b = ds[bands.index('blue')]
                                            if 'nir' in bands:
                                                n = ds[bands.index('nir')]
                                            if 'rededge' in bands:
                                                re = ds[bands.index('rededge')]
                                            try:
                                                res = {calc}
                                            except:
                                                print('Failed to run index {name}: This is likely due to a misspelling of band names. Valid names are:\\nred,green,blue,rededge,nir',file=sys.stderr)
                                                return None
                                            return res, out_meta""")
            indexDict[name] = locals()[f'calc_{name}']
            vegIndices += f"{name}\t{desc}\n"

read_config(os.path.join(script_dir,"indices.conf"))

# sub function for image processing, used for multiprocessing
def sub_process_image(proc_dir,i,in_dir,t,bands,tName):
    if i in indexDict:
        res = write_tif(proc_dir,indexDict[i](os.path.join(in_dir,t),bands),t,in_dir,tName,i)
        if res=='ERROR':
            print(f"Failed to process index: {i} due to previous errors!",file=sys.stderr)
            return "ERROR"
    else:
        print("Unrecognized vegetation index: "+i+", skipping this index")
    return i

# Main image processing function to be called as a process from zonal_stats function
def process_image(proc_dir,r,t,in_dir,tName,index_list,gdf,bands,pool=None,wide_open=False):
    if not os.path.exists(os.path.join(proc_dir,tName)):
        try:
            os.mkdir(os.path.join(proc_dir,tName))
        except FileExistsError:
            None
    if len(index_list) > 0:
        if type(pool) != type(None) and wide_open:
            res = pool.starmap(sub_process_image,[(proc_dir,i,in_dir,t,bands,tName) for i in index_list])
        else:
            res = run_list(proc_dir,t,in_dir,tName,bands,index_list)
    else:
        if r['indices'] == 'ALL' and type(pool) != type(None) and wide_open:
            res = run_all(proc_dir,t,in_dir,tName,bands,None,None,pool,wide_open)
        else:
            res = indexDict[r['indices']](proc_dir,t,in_dir,tName,bands,r,gdf)
    if res is not None and "ERROR" in res:
        return "ERROR"

# sub function for exact extract, used for multiprocessing
def exact_extract_sub(proc_dir,c,tName,gpkg):
    layer = gpd.list_layers(gpkg).iloc[0]['name']
    gpkg = gpd.read_file(gpkg,layer=layer)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if 'VOLUME' in c:
            res = exact_extract(os.path.join(proc_dir,tName,c),gpkg,['sum'],output="pandas",include_cols=[uid])
            res =  res.rename(columns={"sum":c.split("_")[-1].split(".tif")[0]+re.search(date_regex,c).group()})
        else:
            res = exact_extract(os.path.join(proc_dir,tName,c),gpkg,['median'],output="pandas",include_cols=[uid])
            res =  res.rename(columns={"median":c.split("_")[-1].split(".tif")[0]+re.search(date_regex,c).group()})
    return res

# Run exact extract and get zonal statistics for processed images
def run_exact_extract(proc_dir,tName,gpkg,pool,open_pool):
    calc_tifs = os.listdir(os.path.join(proc_dir,tName))
    if len(calc_tifs)==0:
        return None
    if open_pool:
        results = pool.starmap(exact_extract_sub,[(proc_dir,c,tName,gpkg) for c in calc_tifs])
    else:
        results = [exact_extract_sub(proc_dir,c,tName,gpkg) for c in calc_tifs]

    for n,res in enumerate(results):
        if n==0:
            res_out = res
        else:
            res_out =  res_out.merge(res,on=uid)
    
    res_out[uid] = res_out[uid].astype(str)
    return res_out

# Get values from processed images at specific points
def get_point_values(proc_dir,tName,gdf,pool,open_pool):
    calc_tifs = os.listdir(os.path.join(proc_dir,tName))
    gdf = gpd.read_file(gdf)
    data = {uid: gdf[uid]}
    for c in calc_tifs:
        stat_name = c.split("_")[-1].split(".tif")[0]+re.search(date_regex,c).group()
        data[stat_name] = []
        dsm_raw = rasterio.open(os.path.join(proc_dir,tName,c))
        dsm_data = dsm_raw.read(1)
        for n,p in gdf.iterrows():
                x,y = p['geometry'].coords.xy
                py,px = dsm_raw.index(x[0],y[0])
                data[stat_name].append(dsm_data[py,px])
    df = pd.DataFrame(data)
    df[uid] = df[uid].astype(str)
    return df

# Create multilayer tifs by date
def get_multilayer_tif(proc_dir,subs):
    total = 0
    layers = []
    names = []
    for tName in subs:
        tifs = os.listdir(os.path.join(proc_dir,tName))
        if len(tifs)==0:
            return None
        date = re.search(date_regex,tName).group()
        for t in tifs:
            with rasterio.open(os.path.join(proc_dir,tName,t)) as src:
                layers.append(src.read(1))
                names.append(t.split("_")[-1].split(".tif")[0])
                outmeta = src.meta.copy()
            total+=1
    outmeta.update({"count":total})
    with rasterio.open(os.path.join(output,f"{date}_ZS_out.tif"),"w",**outmeta) as dst:
        for n,l in enumerate(layers):
            dst.write_band(n+1,l)
        dst.descriptions = tuple(names)



# Main function for processing a specific 'run' or 'index'
def process_run(proc_dir,r,gdf,pool,open_pool,wide_open=False):
    in_dir = r['path']
    if '[' in r['indices'] and ']' in r['indices']:
        index_list = r['indices'][1:-1].split(",")
    else:
        index_list = []
    if r['bands'] == "[]":
        bands = default_bands
    else:
        bands = r['bands'][1:-1].split(",")
    # Find images to run on, verify that their names are in a specific format
    tifs = os.listdir(in_dir)
    tifs = [t for t in tifs if t.split('.')[-1].lower() in valid_types]
    cont_run = True
    for t in tifs:
        if not re.search(date_regex+'[^0-9]',t):
            print(f"{os.path.join(in_dir,t)} doesn't contain a date in the file name! Please fix filename!")
            cont_run = False
    if not cont_run:
        print("Please correct filenames!")
        return "error"
    # Process images for current index flag
    if verbose:
        print(f"Starting image processing for calculation type(s): {r['indices']}, {len(tifs)} images found...")

    #pool = NDPool(threads)
    if open_pool:
        results = pool.starmap(process_image,[(proc_dir,r,t,in_dir,t.split('.tif')[0],index_list,gdf,bands,pool,wide_open) for t in tifs])
    else:
        results = [process_image(proc_dir,r,t,in_dir,t.split('.tif')[0],index_list,gdf,bands) for t in tifs]
    if "ERROR" in results:
        return "error"
    if verbose:
        print(f"Finished {r['indices']}")

# Main function
def zonal_stats(to_run,gpkg,out_file):
    global proc_dir
    proc_dir = f".{os.getpid()}_proc_dir"
    # Create processing directories, read geopackage
    if not os.path.exists(proc_dir):
        try:
            os.mkdir(proc_dir)
        except FileExistsError:
            None
    layer = gpd.list_layers(gpkg).iloc[0]['name']
    gdf = gpd.read_file(gpkg,layer=layer)
    try:
        gdf[uid] = gdf[uid].astype(str)
    except KeyError:
        print(f"{uid} wasn't found as a field name in {gpkg}! Try changing the unique geopackage identifier (UID) option when running this script.",file=sys.stderr)
        sys.exit(-1)
    # If a buffer was specified, create buffered geopackage
    if buffer == "circle":
        if verbose:
            print("Calculating circular buffer...")
        #in_crs = str(gdf.crs).upper()
        gdf = gdf.to_crs(str(gdf.estimate_utm_crs()).upper())
        gdf['geometry'] = gdf['geometry'].buffer(buffer_size)
        gdf.to_file(os.path.join(proc_dir,"buffered_circle_gdf.gpkg"),driver="GPKG", mode="w")
        gpkg = os.path.join(proc_dir,"buffered_circle_gdf.gpkg")
    elif buffer == "square":
        if verbose:
            print("Calculating square buffer...")
        #in_crs = str(gdf.crs).upper()
        gdf = gdf.to_crs(str(gdf.estimate_utm_crs()).upper())
        gdf['geometry'] = gdf['geometry'].buffer(buffer_size,cap_style=3)
        gdf.to_file(os.path.join(proc_dir,"buffered_square_gdf.gpkg"),driver="GPKG", mode="w")
        gpkg = os.path.join(proc_dir,"buffered_square_gdf.gpkg")

    # Run index calculations for each index flag specified
    with multiprocessing.Manager() as manager:
        pool = manager.Pool(threads)
        open_pool = threads>(len(to_run)*2)
        total_images = sum([len(os.listdir(r['path'])) for r in to_run])
        wide_open = threads > ((len(to_run)*2)+(total_images*2))
        res = pool.starmap(process_run,[(proc_dir,r,gdf,pool,open_pool,wide_open) for r in to_run])
        pool.close()
        pool.join()
        if "error" in res:
            print("Processing failed for some images, please correct errors and try again!")
            sys.exit(1)

    # Run exact extract and get zonal statistics for generated images, or get point values and/or output rasters
    with multiprocessing.Manager() as manager:
        pool = manager.Pool(threads)
        sub_dirs = os.listdir(proc_dir)
        sub_dirs = [s for s in sub_dirs if os.path.isdir(os.path.join(proc_dir,s))]
        open_pool = threads>(len(sub_dirs)*2)
        if output != None:
            out_dates = {}
            for s in sub_dirs:
                date = re.search(date_regex,s).group()
                if date in out_dates.keys():
                    out_dates[date].append(s)
                else:
                    out_dates[date] = [s]
            if verbose:
                print(f"Outputting calculations/extractions to {output}")
            results = pool.starmap(get_multilayer_tif,[(proc_dir,d) for d in out_dates.values()])
        if polygons:
            if verbose:
                print("Extracting stats from processed images...")
            results = pool.starmap(run_exact_extract,[(proc_dir,s,gpkg,pool,open_pool) for s in sub_dirs])
        else:
            if verbose:
                print("Extracting point values from processed images...")
            results = pool.starmap(get_point_values,[(proc_dir,s,gpkg,pool,open_pool) for s in sub_dirs])
        
        pool.close()
        pool.join()
        
    # Join outputs
    for x in results:
        if type(x) != type(None):
            gdf = gdf.merge(x, on=uid)

    shutil.rmtree(proc_dir)

    # Create output geopackage
    gdf.columns = [c.split("_median")[0] for c in gdf.columns]
    gdf.columns = [c.split("_sum")[0] for c in gdf.columns]
    gdf.to_file(out_file, layer='stats', driver="GPKG", mode="w")
    if verbose:
        print("Finished!")
    


# Argument handling and parsing
if __name__ == '__main__':
    if len(sys.argv) < 4:
        if len(sys.argv) == 1:
            print(helpScreen)
            sys.exit(-1)
        if sys.argv[1][0] == '-':
            if 'l' in sys.argv[1]:
                print(vegIndices)
            else:
                print(helpScreen)
        sys.exit(-1)
    else:
        toRemove = []
        for n,a in enumerate(sys.argv):
            if a[0] == "-":
                flag = False
                if "h" in a:
                    print(helpScreen)
                    flag = True
                    sys.exit(-1)
                elif "l" in a:
                    print(vegIndices)
                    sys.exit(-1)
                else:
                    if "q" in a:
                        verbose = False
                        flag = True
                    if "u" in a:
                        flag = True
                        uid = sys.argv[n+1]
                        toRemove.append(sys.argv[n+1])
                    if "o" in a:
                        flag = True
                        if os.path.exists(sys.argv[n+1]):
                            output = sys.argv[n+1]
                            toRemove.append(sys.argv[n+1])
                        else:
                            print(f"{sys.argv[n+1]} is an invalid path for output directory!")
                    if "i" in a:
                        flag = True
                        if sys.argv[n+1][0] == "[" and sys.argv[n+1][-1] == "]":
                            if sys.argv[n+3][0] == "[" and sys.argv[n+3][-1] == "]":
                                if os.path.isdir(sys.argv[n+2]):
                                    toRemove.append(sys.argv[n+1])
                                    toRemove.append(sys.argv[n+2])
                                    toRemove.append(sys.argv[n+3])
                                    to_run.append({"indices": sys.argv[n+1], "path": sys.argv[n+2], "bands": sys.argv[n+3]})
                                else:
                                    print("Invalid use of -i flag, specified directory "+sys.argv[n+2]+" isn't a directory")
                                    sys.exit(-1)
                            else:
                                print(f"Invalid use of -i flag, {sys.argv[n+3]} is invalid format for band order")
                                sys.exit(-1)
                        else:
                            print("Invalid use of -i flag, expected [<vegetation indices>], not "+sys.argv[n+1])
                            sys.exit(-1)
                    
                    if "a" in a:
                        flag = True
                        if sys.argv[n+2][0] == "[" and sys.argv[n+2][-1] == "]":
                            if os.path.isdir(sys.argv[n+1]):
                                toRemove.append(sys.argv[n+1])
                                toRemove.append(sys.argv[n+2])
                                to_run.append({"indices": "ALL", "path": sys.argv[n+1], "bands": sys.argv[n+2]})
                            else:
                                print("Invalid use of -a flag, specified directory "+sys.argv[n+1]+" isn't a directory")
                                sys.exit(-1)
                        else:
                            print(f"Invalid use of -a flag, {sys.argv[n+1]} is invalid format for band order")
                            sys.exit(-1)
                    if "n" in a:
                        flag = True
                        if sys.argv[n+2][0] == "[" and sys.argv[n+2][-1] == "]":
                            if os.path.isdir(sys.argv[n+1]):
                                toRemove.append(sys.argv[n+1])
                                toRemove.append(sys.argv[n+2])
                                to_run.append({"indices": "NONE", "path": sys.argv[n+1], "bands": sys.argv[n+2]})
                            else:
                                print("Invalid use of -n flag, specified directory "+sys.argv[n+1]+" isn't a directory")
                                sys.exit(-1)
                        else:
                            print(f"Invalid use of -n flag, {sys.argv[n+1]} is invalid format for band order")
                            sys.exit(-1)
                    if "v" in a:
                        flag = True
                        if os.path.isdir(sys.argv[n+1]):
                            toRemove.append(sys.argv[n+1])
                            to_run.append({"indices": "VOLUME", "path": sys.argv[n+1], "ref": "NONE", "bands": "[height]"})
                        else:
                            print("Invalid use of -v flag, specified directory "+sys.argv[n+1]+" isn't a directory")
                            sys.exit(-1)
                    if "V" in a:
                        flag = True
                        if os.path.isdir(sys.argv[n+1]):
                            if os.path.isfile(sys.argv[n+2]) and sys.argv[n+2].split(".")[-1] in valid_types:
                                toRemove.append(sys.argv[n+1])
                                toRemove.append(sys.argv[n+2])
                                to_run.append({"indices": "VOLUME", "path": sys.argv[n+1], "ref": sys.argv[n+2], "bands": "[height]"})
                            else:
                                print("Invalid use of -V flag, specified references DSM, "+sys.argv[n+2]+" isn't a file or isn't correct file type")
                                sys.exit(-1)
                        else:
                            print("Invalid use of -V flag, specified directory "+sys.argv[n+1]+" isn't a directory")
                            sys.exit(-1)
                    if "t" in a:
                        flag = True
                        if re.search("^[1-9][0-9]*",sys.argv[n+1]):
                            if multiprocessing.cpu_count()-2 >= int(sys.argv[n+1]):
                                threads = int(sys.argv[n+1])
                                toRemove.append(sys.argv[n+1])
                            else:
                                print(f"{sys.argv[n+1]} is too many threads, max threads you can specify on this device is {multiprocessing.cpu_count()-2}")
                                sys.exit(-1)
                        else:
                            print(f"{sys.argv[n+1]} is an invalid format for threads, should be an integer greater than 1")
                    if "p" in a:
                        flag = True
                        if buffer!=None:
                            print("-p flag cannot be used with -S or -C flags!")
                            sys.exit(-1)
                        polygons = False
                    if "C" in a:
                        flag = True
                        if buffer == None and polygons:
                            buffer = "circle"
                            if re.search("^([1-9]|0\.[0-9])[0-9]*",sys.argv[n+1]):
                                buffer_size = float(sys.argv[n+1])
                                if buffer_size <= 0:
                                    print(f"Invalid distance {sys.argv[n+1]} for buffer size, should be a positive non-zero value!")
                                    sys.exit(-1)
                                toRemove.append(sys.argv[n+1])
                            else:
                                print(f"Invalid distance {sys.argv[n+1]} for buffer size, should be a numerical distance in meters!")
                                sys.exit(-1)
                        else:
                            print(f"-C flag cannot be used with -S or -p!")
                            sys.exit(-1)
                    if "S" in a:
                        flag = True
                        if buffer == None and polygons:
                            buffer = "square"
                            if re.search("^([1-9]|0\.[0-9])[0-9]*",sys.argv[n+1]):
                                buffer_size = float(sys.argv[n+1])
                                if buffer_size <= 0:
                                    print(f"Invalid distance {sys.argv[n+1]} for buffer size, should be a positive non-zero value!")
                                    sys.exit(-1)
                                toRemove.append(sys.argv[n+1])
                            else:
                                print(f"Invalid distance {sys.argv[n+1]} for buffer size, should be a numerical distance in meters!")
                                sys.exit(-1)
                        else:
                            print(f"-S flag cannot be used with -C or -p!")
                            sys.exit(-1)
                if not flag:
                    print("Flag "+a+" unrecognized")
                    sys.exit(-1)
                toRemove.append(a)
        for i in toRemove:
            sys.argv.remove(i)
        if len(sys.argv) < 3:
            print(helpScreen)
            sys.exit(-1)
        else:
            if len(to_run) == 0:
                print("Please pass indices to be run!!")
                sys.exit(-1)
            zonal_stats(to_run,sys.argv[1],sys.argv[2])
