import pandas
import sys
import os
import gi
import m3u8
gi.require_version('Gst','1.0')
from gi.repository import GObject,Gst,GLib
import fnmatch
from config import Config
import logging
from logging import FileHandler

command_header={}
command_body={}
command_footer={}

###   Gstreamer pipeline definition for Nicktoons   ###
command_header["Nicktoons"]="""
concat name=c_v adjust-base=false 
concat name=c_a1 adjust-base=false 
mpegtsmux name=mux prog-map=program_map,PCR_14=sink_2141,sink_2141=14,sink_2142=14,sink_2143=14,sink_2144=14,sink_2145=14,sink_2149=14,PMT_14=1038 
multiqueue name=q max-size-buffers=23 max-size-bytes=0 max-size-time=0 sync-by-running-time=TRUE 
streamsynchronizer name=sync 
"""

command_body["Nicktoons"]="""filesrc location={0} ! decodebin name=d{1} d{1}. ! queue ! video/x-raw ! c_v. d{1}. ! queue ! audio/x-raw ! c_a1. 
"""

command_footer["Nicktoons"]="""
c_v. ! sync. sync. ! videoconvert ! videoscale ! video/x-raw,width=1920,height=1080 ! identity single-segment=true silent=false ! 
  nvh264enc gop-size=12 bitrate=4096 rc-mode=2 preset=1 ! video/x-h264,profile=high ! h264parse ! q.sink_1 q.src_1 ! mux.sink_2141 
c_a1. ! sync. sync. ! audioconvert ! audio/x-raw,channels=2 ! audioresample ! identity single-segment=true ! tee name=t 
  t.src_0 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_2 q.src_2 ! mux.sink_2142 
  t.src_1 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_3 q.src_3 ! mux.sink_2143 
  t.src_2 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_4 q.src_4 ! mux.sink_2144 
  t.src_3 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_5 q.src_5 ! mux.sink_2145 
fakesrc num-buffers=1 sizetype=2 sizemax=5 ! application/x-teletext ! q.sink_6 q.sink_6 ! mux.sink_2149 
mux.src ! tsparse parse-private-sections=true name=p p.program_14 ! 
multifilesink location={} 
  next-file=3 max-files=0 max-file-size=0 post-messages=true
"""

###   Gstreamer pipeline definition for NickJR    ####

command_header["NickJR"]="""
concat name=c_v adjust-base=false 
concat name=c_a1 adjust-base=false 
mpegtsmux name=mux prog-map=program_map,PCR_3=sink_1131,sink_1131=3,sink_1132=3,sink_1133=3,sink_1134=3,sink_1135=3,sink_1136=3,sink_1137=3,sink_1139=3,PMT_3=1023 
multiqueue name=q max-size-buffers=23 max-size-bytes=0 max-size-time=0 sync-by-running-time=TRUE 
streamsynchronizer name=sync 
"""

command_body["NickJR"]="""filesrc location={0} ! decodebin name=d{1} d{1}. ! queue ! video/x-raw ! c_v. d{1}. ! queue ! audio/x-raw ! c_a1. 
"""

command_footer["NickJR"]="""
c_v. ! sync. sync. ! videoconvert ! videoscale ! video/x-raw,width=720,height=576 ! identity single-segment=true silent=false ! 
  nvh264enc gop-size=12 bitrate=3096 rc-mode=2 preset=1 ! video/x-h264,profile=high ! h264parse ! q.sink_1 q.src_1 ! mux.sink_1131 
c_a1. ! sync. sync. ! audioconvert ! audio/x-raw,channels=2 ! audioresample ! identity single-segment=true ! tee name=t 
  t.src_0 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_2 q.src_2 ! mux.sink_1132 
  t.src_1 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_3 q.src_3 ! mux.sink_1133 
  t.src_2 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_4 q.src_4 ! mux.sink_1134 
  t.src_3 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_5 q.src_5 ! mux.sink_1135 
  t.src_4 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_6 q.src_6 ! mux.sink_1136 
  t.src_5 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_7 q.src_7 ! mux.sink_1137 
fakesrc num-buffers=1 sizetype=2 sizemax=5 ! application/x-teletext ! q.sink_8 q.sink_8 ! mux.sink_1139 
mux.src ! tsparse parse-private-sections=true name=p p.program_3 ! 
multifilesink location={} 
  next-file=3 max-files=0 max-file-size=0 post-messages=true
"""

###   Gstreamer pipeline definition for Nickelodeon    ####

command_header["Nick"]="""
concat name=c_v adjust-base=false 
concat name=c_a1 adjust-base=false 
mpegtsmux name=mux prog-map=program_map,PCR_30633=sink_1401,sink_1401=30633,sink_1461=30633,sink_1462=30633,sink_1463=30633,sink_1464=30633,sink_1465=30633,sink_1490=30633,PMT_30633=1402 
multiqueue name=q max-size-buffers=23 max-size-bytes=0 max-size-time=0 sync-by-running-time=TRUE 
streamsynchronizer name=sync 
"""

command_body["Nick"]="""filesrc location={0} ! decodebin name=d{1} d{1}. ! queue ! video/x-raw ! c_v. d{1}. ! queue ! audio/x-raw ! c_a1. 
"""

command_footer["Nick"]="""
c_v. ! sync. sync. ! videoconvert ! videoscale ! video/x-raw,width=720,height=576 ! identity single-segment=true silent=false ! 
  avenc_mpeg2video bitrate=3096000 ! video/mpeg,mpegversion=2 ! mpegvideoparse ! q.sink_1 q.src_1 ! mux.sink_1401 
c_a1. ! sync. sync. ! audioconvert ! audio/x-raw,channels=2 ! audioresample ! identity single-segment=true ! tee name=t 
  t.src_0 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_2 q.src_2 ! mux.sink_1461 
  t.src_1 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_3 q.src_3 ! mux.sink_1462 
  t.src_2 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_4 q.src_4 ! mux.sink_1463 
  t.src_3 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_5 q.src_5 ! mux.sink_1464 
  t.src_4 ! avenc_mp2 bitrate=256000 ! mpegaudioparse !  q.sink_6 q.src_6 ! mux.sink_1465 
fakesrc num-buffers=1 sizetype=2 sizemax=5 ! application/x-teletext ! q.sink_8 q.sink_8 ! mux.sink_1490 
mux.src ! tsparse parse-private-sections=true name=p p.program_30633 ! 
multifilesink location={} 
  next-file=3 max-files=0 max-file-size=0 post-messages=true
"""




logger=logging.getLogger("encode_commercials")
media_repository=Config.CACHE_FOLDER
base_uri=Config.BASE_URI


class Encoder:
    def __init__(self,command,segment_path):
        self.command=command
        self.segment_path=segment_path
        self.playlist=m3u8.M3U8()
        self.playlist.version="3"
        self.playlist.is_endlist=True

    def bus_callback(self, bus,message,loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            logger.info("End-of-stream\n")
            self.playlist.dump(os.path.join(self.segment_path,"playlist.m3u8"))
            logger.info("Break encoding finished without errors. Playlist dumped")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("Error: %s: %s\n" % (err, debug))
            loop.quit()
        return True

    def on_file_change(self,bus,message):
        structure=message.get_structure()
        if structure.get_name()=="GstMultiFileSink":
            logger.info('{} finished.'.format(structure.get_string("filename")))
            self.playlist.add_segment(m3u8.model.Segment(
                uri=os.path.join(base_uri,'/'.join(structure.get_string("filename").split('/')[-6:])),
                duration=15,
                discontinuity = True if structure.get_string("filename").endswith('0000.ts') else False))

    def run_encoder(self):
        try:
            pipeline=Gst.parse_launch(self.command)
            if not pipeline:
                app.logger.error( "Couldn't create pipeline for break:{}".format(b))
                return
            loop=GLib.MainLoop()
            bus=pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message",self.bus_callback,loop)
            bus.connect("message::element",self.on_file_change)
            pipeline.set_state(Gst.State.PLAYING)
            loop.run()
        except Exception as e:
            logger.error('Encoding failed: '+str(e))
        logger.info("Setting pipline to NULL.")
        pipeline.set_state(Gst.State.NULL)
     

def encode_nicktoons(channel,txdate): 
    file_handler = FileHandler('/ddrive/ottstreamer/webapp/logs/encode_nicktoons.log')
    file_handler.setFormatter(logging.Formatter(
         '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    logger.info('Hello from encode_nicktoons.py')


    ch= next(item for item in Config.LOCALIZED_FEEDS  if item["name"] == channel)
    xls_playlist=os.path.join(Config.STREAMS_ROOT,ch["dir"],"commercials","playlists",
        txdate,txdate+"_"+ch["log"]+".xls")
    media_repository=Config.CACHE_FOLDER
    destination_path=os.path.dirname(xls_playlist)
    base_uri=Config.BASE_URI
    gst_channel=channel.split(' ')[0]

    df=pandas.read_excel(xls_playlist)
    #Check for missing Cart Numbers
    logger.info("Missing commercials:")
    missing=0
    matches = []
    for root, dirnames, filenames in os.walk(media_repository):
        for filename in fnmatch.filter(filenames, "*.mxf"):
            matches.append(os.path.join(root, filename))
    medias={}
    for c in df["Cart Number"].unique():
        for m in matches:
            if c in m:
                medias[c]=m
                break
        if c not in medias:
            logger.error( "{} is missing".format(c))
            missing+=1
    if missing:
        logger.error("{} missing files.".format(missing))
        sys.exit()
    else:
        logger.info("All files found. Good.")
    Gst.init(None)
    for b in df["Break Number"].unique():
        files=""
        command=""
        for i, c in enumerate(df[df['Break Number']==b]["Cart Number"]):
            files+= command_body[gst_channel].format('"'+medias[c]+'"',i)
        segment_path=os.path.join(destination_path,"brk_{:02d}".format(b))
        command=command_header[gst_channel]+files+command_footer[gst_channel].format(os.path.join(segment_path,"segment_%05d.ts"))
        if not os.path.exists(segment_path):
            os.makedirs(segment_path)
        logger.info( "{} - {} converting break:{}".format(channel,txdate,b))
        logger.info(command)
        enc=Encoder(command,segment_path)
        enc.run_encoder()

if __name__ == '__main__':
    encode_nicktoons(sys.argv[1],sys.argv[2])
