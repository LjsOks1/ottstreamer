#!/usr/bin/python
import pandas
import sys
import os
import gi
import m3u8
gi.require_version('Gst','1.0')
from gi.repository import GObject,Gst,GLib

Gst.init(None)

### Gstreamer pipeline definition ####    
command_header="""
concat name=c_v adjust-base=false 
concat name=c_a1 adjust-base=false 
mpegtsmux name=mux prog-map=program_map,PCR_14=sink_2141,sink_2141=14,sink_2142=14,sink_2143=14,sink_2144=14,sink_2145=14,sink_2149=14,PMT_14=1038 
multiqueue name=q max-size-buffers=23 max-size-bytes=0 max-size-time=0 sync-by-running-time=TRUE 
streamsynchronizer name=sync 
"""

command_body="""
filesrc location={0} ! decodebin name=d{1} d{1}. ! queue ! video/x-raw ! c_v. d{1}. ! queue ! audio/x-raw ! c_a1. 
"""

command_footer="""
c_v. ! sync. sync. ! videoconvert ! videoscale ! video/x-raw,width=1920,height=1080 ! identity single-segment=true silent=false ! 
  x264enc option-string="no-scenecut:keyint=12" key-int-max=12 bitrate=4096 vbv-buf-capacity=4096 ! video/x-h264,profile=high ! h264parse ! q.sink_1 q.src_1 ! mux.sink_2141 
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

if len(sys.argv)!=4:
    print """
Wrong number of arguments. 
Usage: encode_playlist.py <daily_log> <media_repository> <base_uri>
       <daily_log>: Excel file with the daily commercial log. Ideally should be in the <destination_path>/<YYYY-MM-DD> folder.
                    Filename convension: YYYY-MM-DD_<Channel_Name>.xls Break folders will be created in the same folder where the playlist file sits.
<media_repository>: Folder where the original commercials are stored in. 
        <base_uri>: Initial part of the segment URL
Example:
./encode_playlist.py /var/www/html/streams/nicktoons_hun/commercials/playlists/2019-09-14/2019-09-14_Nicktoons_Hungary.xls /ddrive/commercials http://129.228.120.86/streams/nicktoons_hun/commercials/playlists
"""
    sys.exit()

   
def bus_callback(bus,message,loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True

def on_file_change(bus,message,playlist):
    structure=message.get_structure()
    if structure.get_name()=="GstMultiFileSink":
        playlist.add_segment(m3u8.model.Segment(
            uri=os.path.join(base_uri,'/'.join(structure.get_string("filename").split('/')[-3:])),
            duration=15,
            discontinuity = True if structure.get_string("filename").endswith('0000.ts') else False))

def run_encoder(command):
    pipeline=Gst.parse_launch(command)
    if not pipeline:
        print "Couldn't create pipeline for break:{}".format(b)
    playlist=m3u8.M3U8()
    loop=GLib.MainLoop()
    bus=pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message",bus_callback,loop)
    bus.connect("message::element",on_file_change,playlist)
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    pipeline.set_state(Gst.State.NULL)
    playlist.dump(os.path.join(segment_path,"playlist.m3u8"))
 

 
if __name__=="__main__":
    xls_playlist=sys.argv[1]
    media_repository=sys.argv[2]
    destination_path=os.path.dirname(xls_playlist)
    base_uri=sys.argv[3]

    df=pandas.read_excel(xls_playlist)
    #Check for missing Cart Numbers
    print "Missing commercials:"
    missing=0
    for c in df["Cart Number"].unique():
        if not os.path.isfile(os.path.join(media_repository,c+".mxf")):
            print "{} is missing".format(c)
            missing+=1
    print "---------------------------------"
    if missing:
        print "{} missing files.".format(missing)
        sys.exit()
    else:
        print "All files found. Good."
    for b in df["Break Number"].unique():
        files=""
        command=""
        for i, c in enumerate(df[df['Break Number']==b]["Cart Number"]):
            files+= command_body.format(os.path.join(media_repository,c+".mxf"),i)
        segment_path=os.path.join(destination_path,"brk_{:02d}".format(b))
        command=command_header+files+command_footer.format(os.path.join(segment_path,"segment_%05d.ts"))
        if not os.path.exists(segment_path):
            os.makedirs(segment_path)
        print "converting break:{}".format(b)
        run_encoder(command)

