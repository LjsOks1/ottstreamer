from config import Config
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas
import os
import m3u8
import datetime
import re
import copy
import json

day_start=datetime.time(6,0)

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
        com_break["start_time_dt"]=datetime.datetime.strptime(txdate+" "+com_break["starttime"],"%Y-%m-%d %H:%M:%S")
        if datetime.datetime.strptime(com_break["starttime"],"%H:%M:%S").time()<day_start:
            com_break["start_time_dt"]=com_break["start_time_dt"]+datetime.timedelta(days=1)
        com_break["duration"]='{:02d}:{:02d}'.format(int(df[df["Break Number"] == b]["Duartion WORK"].sum()/60),
                                             df[df["Break Number"] == b]["Duartion WORK"].sum()%60)
        com_break["duration_td"]=datetime.timedelta(minutes=int(com_break["duration"].split(':')[0]),
                                                    seconds=int(com_break["duration"].split(':')[1]))
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
    return datetime.datetime(1900,1,int(int(hour)/24)+1,int(hour)%24,int(min),int(sec.split('.')[0]),int(sec.split('.')[1]))

def ts_to_timedelta(ts):
    (hour,min,sec)=ts.split(':')
    return datetime.timedelta(hours=int(hour),minutes=int(min),seconds=int(sec.split('.')[0]),microseconds=int(sec.split('.')[1]))

def get_segments_played(channel,txdate):
    downloads=[]
    parse_packets=[]
    regex_download=r"([^\s]*)(.*)(http:.*)"
    regex_timestamp=r"([^\s]*).*Pushing out pending packets at: ([^\s]*) ([^\s]*).*Timestamp:([^\s]*) DUR:([^\s]*) SIZE:([^\s]*)"
    hls2rtp_logs="/ddrive/ottstreamer/hls2rtp/logs"
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["dir"]==channel][0]
    txdate_datetime=datetime.datetime.strptime(txdate,'%Y-%m-%d')
    if txdate_datetime.date()==datetime.datetime.now().date():
        hls2rtp_log=os.path.join(hls2rtp_logs,"hls2rtp_"+local_feed["dir"]+".log")
    else:
        hls2rtp_log=os.path.join(hls2rtp_logs,"hls2rtp_"+local_feed["dir"]+".log-"+txdate_datetime.strftime('%Y%m%d'))

    base_wallclock=datetime.datetime(1900, 1, 1, 0, 0)
    base_timestamp=datetime.datetime(1900, 1, 1, 0, 0)
    prev_end_timestamp=datetime.datetime(1900, 1, 1, 0, 0)
    download={}
    with open(hls2rtp_log) as file:
        for ln,line in enumerate(file):
            if "Pushing out pending packets at:" in line:
                parse_packet={}
                if line.find("percent. ") > 0:
                    line=line[line.find("percent. ")+9:]
                match=re.search(regex_timestamp,line)
                base_timestamp=ts_to_datetime(match.group(1)[0:-3])
                base_wallclock=datetime.datetime.strptime(match.group(2) +" " + match.group(3),"%Y-%m-%d %H:%M:%S.%f")
                parse_packet["linenumber"]=ln
                parse_packet["wallclock"]=datetime.datetime.strptime(match.group(2) +" " + match.group(3),"%Y-%m-%d %H:%M:%S.%f")
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


def get_timeline(txdate):
    channels={"Nickelodeon":"nick_hun",
              "Nick JR":"nickjr_hun",
              "Nicktoons":"nicktoons_hun"}
    events=[]
    timeline={}
    timeline["title"]={"text":{"text":"Commercial breaks","headline":txdate}}
    for group,channel in channels.items():
        breaks=get_commercial_log(channel,txdate)
        for b in breaks:
            event={}
            event["start_date"]={"year":b["start_time_dt"].year,"month":b["start_time_dt"].month,"day":b["start_time_dt"].day,
                         "hour":b["start_time_dt"].hour,"minute":b["start_time_dt"].minute,"second":b["start_time_dt"].second}
            end_date=b["start_time_dt"]+b["duration_td"]
            event["end_date"]={"year":end_date.year,"month":end_date.month,"day":end_date.day,
                                 "hour":end_date.hour,"minute":end_date.minute,"second":end_date.second}
            event["text"]={"text":"Break {:02d}".format(b["id"]),"headline":""}
            event["group"]=group
            event["background"]={"color":"#0f9bd1"}
            events.append(event)
        timeline["events"]=events

    return json.dumps(timeline)

def get_test_playlist(channel,break_number):
    regex_newsegment=r"New segment detected:"
    regex_opencom=r"Opening commercial log file: ([\S]*\.m3u8)"
    regex_append=r"Detected segment appended to playlist"
    regex_segment=r"(http://[\S]*.ts)"
    local_feed=[lf for lf in Config.LOCALIZED_FEEDS if lf["dir"]==channel][0]
    localizer_log=os.path.join(Config.LOCALIZER_ROOT,"logs","localizer_"+local_feed['log']+'.log')
    playlist=[]
    new_segment=False
    segment=""
    txdate=datetime.datetime.now().strftime("%Y%m%d")
    with open(localizer_log) as file:
        for line in file:
            match=re.search(regex_newsegment,line)
            if match: # New segment detected
                new_segment=True
            match=re.search(regex_segment,line)
            if match: # link to segment
                segment=match.group(1)
            match=re.search(regex_append,line)
            if match and new_segment and len(segment)>0: # Segment appended to playlist
                playlist.append(segment)
            match=re.search(regex_opencom,line)
            if match:
                line=next(file)
                if not "Keeping regional segments." in line:
                    playlist.append(match.group(1))
   # try:
        segment_index=playlist.index([s for s in playlist if "brk_{:02d}".format(int(break_number)) in s][0])
        comm_break=m3u8.M3U8()
        comm_break.version="3"
        comm_break.is_endlist=True
        comm_break.add_segment(m3u8.model.Segment(uri=playlist[segment_index-1],duration=15))
        for s in m3u8.load(playlist[segment_index]).segments:
            comm_break.add_segment(s)
        comm_break.add_segment(m3u8.model.Segment(uri=playlist[segment_index+1],discontinuity=True))
        comm_break.dump(os.path.join(Config.TEST_FOLDER,channel+"_"+txdate+"_brk{:02d}".format(int(break_number))+".m3u8"))
        return Config.TEST_URL+channel+"_"+txdate+"_brk{:02d}".format(int(break_number))+".m3u8"
   # except:
   #     return ""   
