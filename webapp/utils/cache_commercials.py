import datetime
import os
from stat import *
from shutil import copyfile
from config import Config
import pandas
import xlrd
import fnmatch
from config import Config
import logging
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler('/ddrive/ottstreamer/webapp/logs/cache_commercials.log', 
    maxBytes=10240,backupCount=10)
file_handler.setFormatter(logging.Formatter(
     '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.DEBUG)
logger=logging.getLogger("cache_commercials")
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
logger.info('Hello from cache_commercials.py')



def cache_commercials():
        base = datetime.datetime.today()
        date_list = [(base + datetime.timedelta(days=x)) for x in range(5)]

        media_files=[]
        try:
            for root, dirnames, filenames in os.walk(Config.MEDIA_FOLDER):
                for filename in fnmatch.filter(filenames, "*.mxf"):
                    media_files.append(os.path.join(root, filename))
            logger.info("Found {} mxf files in {}".format(len(media_files),Config.MEDIA_FOLDER))
        except Exception as e:
            logger.error('Failed to build file list on SAN drive: '+ str(e))
            raise e
            
        cached_files=[]
        try:
            for root, dirnames, filenames in os.walk(Config.CACHE_FOLDER):
                for filename in fnmatch.filter(filenames, "*.mxf"):
                    cached_files.append(os.path.join(root, filename))
            logger.info("Found {} mxf files in {}".format(len(cached_files),Config.CACHE_FOLDER))
        except Exception as e:
            logger.error('Failed to build file list on CACHE folder: '+ str(e))
            raise e

        missing=set()

        for lf in Config.LOCALIZED_FEEDS:
            for d in date_list:
                src_xls_filename=os.path.join(lf["xls"],d.strftime("%Y"),'Sent',d.strftime("%m")+"_"+d.strftime('%B'),d.strftime("%Y-%m-%d")+"_"+lf["log"]+".xls")
                if os.path.isfile(src_xls_filename):
                    try:
                        df=pandas.read_excel(src_xls_filename)
                        for c in df["Cart Number"].unique():
                            found_cart=False
                            for m in cached_files:
                                if c in m:
                                    # print("{} found in {}".format(c,m))
                                    found_cart=True
                                    break
                            if not found_cart:
                                # print("Adding {} to missing list.".format(c))
                                missing.add(c)
                    except Exception as e:
                        logger.error('Failed to check missing media files: '+ str(e))
                        continue
                     
        for m in missing:
            for f in media_files:
                if m in f:
                    logger.info("Copy {} to {}".format(f,os.path.join(Config.CACHE_FOLDER,m+".mxf")))
                    copyfile(f,os.path.join(Config.CACHE_FOLDER,m+".mxf"))
                    break

