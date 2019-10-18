import datetime
import os
from stat import *
from shutil import copyfile
from config import Config
import pandas
import xlrd
import fnmatch
from app import app
import sys
from utils import check_for_missing_media as cmm

def reload_playlist(channel,txdate):
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["name"]==channel][0]
    d=datetime.datetime.strptime(txdate,'%Y-%m-%d')
    src_xls_filename=os.path.join(local_feed["xls"],d.strftime("%Y"),'Sent',d.strftime("%m")+"_"+d.strftime('%B'),d.strftime("%Y-%m-%d")+"_"+local_feed["log"]+".xls")
    dst_xls_filename=os.path.join(Config.STREAMS_ROOT,local_feed["dir"],"commercials","playlists",d.strftime("%Y-%m-%d"),d.strftime("%Y-%m-%d")+"_"+local_feed["log"]+".xls")
    app.logger.info('Searching for file {}'.format(src_xls_filename))
    try:
        if os.path.isfile(src_xls_filename):
            src_stat=os.stat(src_xls_filename)
            if os.path.isfile(dst_xls_filename):
                dst_stat=os.stat(dst_xls_filename)
                if src_stat[ST_SIZE]==dst_stat[ST_SIZE] and src_stat[ST_MTIME]<dst_stat[ST_MTIME]:
                    return True
            df=pandas.read_excel(src_xls_filename)
            os.makedirs(os.path.dirname(dst_xls_filename), exist_ok=True, mode=0o774)
            os.chmod(os.path.dirname(dst_xls_filename),0o774)
            copyfile(src_xls_filename,dst_xls_filename)
            app.logger.info('Playlist {} copied to {}'.format(src_xls_filename,dst_xls_filename))
            cmm.check_for_missing_media(channel,txdate)
            return True
        else:
            app.logger.error('{} not found.'.format(src_xls_filename))
            return False
    except Exception as e:
        app.logger.error('Failed to build file list on CACHE folder: '+ str(e))
        return False
    return True
 
if __name__ == "__main__":
    reload_playlist(sys.argv[1],sys.argv[2])
