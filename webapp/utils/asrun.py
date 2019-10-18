from config import Config
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas
import os
import m3u8
from datetime import datetime
from datetime import timedelta
import re
import copy

def get_commercial_log(channel,txdate):
    breaks=[]
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["dir"]==channel][0]
    xls_filename=os.path.join(Config.STREAMS_ROOT,local_feed["dir"],"commercials","playlists",
                          txdate,txdate+"_"+local_feed["log"]+".xls")
    df=pandas.read_excel(xls_filename)
    for b in df["Break Number"].unique():
        com_break={}
        com_break["id"]=b
        com_break["starttime"]=df[df["Break Number"] == b].iloc[0]["Start Time"][0:-3]
        com_break["duration"]='{:02d}:{:02d}'.format(int(df[df["Break Number"] == b]["Duartion WORK"].sum()/60),
                                             df[df["Break Number"] == b]["Duartion WORK"].sum()%60)
        if os.path.isfile(os.path.join(Config.STREAMS_ROOT,local_feed["dir"],"commercials","playlists",
                                           txdate,'brk_{:02d}'.format(b),"playlist.m3u8")):
            com_break["manifest"]=os.path.join(Config.BASE_URI,local_feed["dir"],"commercials","playlists",
                                           txdate,'brk_{:02d}'.format(b),"playlist.m3u8")
            com_break["segments"]=[]
            for segment in m3u8.load(com_break["manifest"]).segments:
                com_break["segments"].append(segment.uri)
        breaks.append(com_break)
    return breaks

def ts_to_datetime(ts):
    (hour,min,sec)=ts.split(':')
    return datetime(1900,1,int(int(hour)/24)+1,int(hour)%24,int(min),int(sec.split('.')[0]),int(sec.split('.')[1]))

def ts_to_timedelta(ts):
    (hour,min,sec)=ts.split(':')
    return timedelta(hours=int(hour),minutes=int(min),seconds=int(sec.split('.')[0]),microseconds=int(sec.split('.')[1]))

def get_segments_played(channel,txdate):
    downloads=[]
    parse_packets=[]
    regex_download=r"([^\s]*)(.*)(http:.*)"
    regex_timestamp=r"([^\s]*).*Pushing out pending packets at: ([^\s]*) ([^\s]*).*Timestamp:([^\s]*) DUR:([^\s]*) SIZE:([^\s]*)"
    hls2rtp_logs="/home/lajos/projects/ottstreamer/hls2rtp/logs"
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["dir"]==channel][0]
    txdate_datetime=datetime.strptime(txdate,'%Y-%m-%d')
    if txdate_datetime.date()==datetime.now().date():
        hls2rtp_log=os.path.join(hls2rtp_logs,"hls2rtp_"+local_feed["dir"]+".log")
    else:
        hls2rtp_log=os.path.join(hls2rtp_logs,"hls2rtp_"+local_feed["dir"]+".log-"+txdate_datetime.strftime('%Y%m%d'))

    base_wallclock=datetime(1900, 1, 1, 0, 0)
    base_timestamp=datetime(1900, 1, 1, 0, 0)
    prev_end_timestamp=datetime(1900, 1, 1, 0, 0)
    download={}
    with open(hls2rtp_log) as file:
        for ln,line in enumerate(file):
            if "Pushing out pending packets at:" in line:
                parse_packet={}
                if line.find("percent. ") > 0:
                    line=line[line.find("percent. ")+9:]
                match=re.search(regex_timestamp,line)
                base_timestamp=ts_to_datetime(match.group(1)[0:-3])
                base_wallclock=datetime.strptime(match.group(2) +" " + match.group(3),"%Y-%m-%d %H:%M:%S.%f")
                parse_packet["linenumber"]=ln
                parse_packet["wallclock"]=datetime.strptime(match.group(2) +" " + match.group(3),"%Y-%m-%d %H:%M:%S.%f")
                parse_packet["timestamp"]=ts_to_datetime(match.group(1)[0:-3])
                parse_packet["PCR"]=ts_to_datetime(match.group(4)[0:-3])
                parse_packet["Duration"]=ts_to_timedelta(match.group(5)[0:-3])
                parse_packet["Size"]=int(match.group(6))
                parse_packets.append(parse_packet)

            elif "Downloading fragment uri" in line:
                match=re.search(regex_download,line)
                download={}
                download["gap"]=ts_to_datetime(match.group(1)[0:-3])-prev_end_timestamp
                download["start_linenumber"]=ln
                download["start_timestamp"]=ts_to_datetime(match.group(1)[0:-3])
                download["start_wallclock"]=base_wallclock+(download["start_timestamp"]-base_timestamp)
                download["url"]=match.group(3).split(' ')[0][0:-1]
            elif "fragment download finished" in line:
                match=re.search(regex_download,line)
                download["end_linenumber"]=ln
                download["end_timestamp"]=ts_to_datetime(match.group(1)[0:-3])
                prev_end_timestamp=download["end_timestamp"]
                download["end_wallclock"]=base_wallclock+(download["end_timestamp"]-base_timestamp)
                download["result"]=match.group(3).split(' ')[1]
                download["result2"]=match.group(3).split(' ')[2]
                if "start_wallclock" in download:
                    downloads.append(download)
    return downloads,parse_packets
