import datetime
import os
from stat import *
from shutil import copyfile
from config import Config
import pandas
import xlrd
import fnmatch
import sys
from app import app
from utils.cache_commercials import cache_commercials 

def check_for_missing_media(channel,txdate):
    cached_files=[]
    try:
        for root, dirnames, filenames in os.walk(Config.CACHE_FOLDER):
            for filename in fnmatch.filter(filenames, "*.mxf"):
                cached_files.append(os.path.join(root, filename))
        app.logger.info("Found {} mxf files in {}".format(len(cached_files),Config.CACHE_FOLDER))
    except Exception as e:
        app.logger.error('Failed to build file list on CACHE folder: '+ str(e))
        return False

    missing=set()
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["name"]==channel][0]
    xls_filename=os.path.join(Config.STREAMS_ROOT,local_feed["dir"],"commercials","playlists",txdate,txdate+"_"+local_feed["log"]+".xls")
    if os.path.isfile(xls_filename):
        try:
            app.logger.info("Checking {} for missing files".format(xls_filename))
            df=pandas.read_excel(xls_filename)
            for c in df["Cart Number"].unique():
                found_cart=False
                for m in cached_files:
                    if c in m:
                        found_cart=True
                        break
                if not found_cart:
                    missing.add(c)
        except Exception as e:
            app.logger.error('Failed to check missing media files: '+ str(e))
            return False            
    else:
        app.logger.error("Didn't find playlist file:{}".format(xls_filename))
        return False
    with open(os.path.join(os.path.dirname(xls_filename),".missing_files"), 'w') as f:
        for item in missing:
            f.write("%s\n" % item)
    f.close()
    if len(missing)>0:
        job=app.cache_queue.enqueue(cache_commercials)
        app.logger.info("Caching commercials with job_id:{}".format(job.get_id()))
    return True

if __name__ == '__main__':
    check_for_missing_media(sys.argv[1],sys.argv[2])
