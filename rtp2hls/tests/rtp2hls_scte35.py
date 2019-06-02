#!/usr/bin/env python

from __future__ import print_function

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstMpegts' , '1.0')
gi.require_version('GstVideo','1.0')

from gi.repository import GObject, Gst, GstMpegts,GstVideo

import datetime


GObject.threads_init()
Gst.init(None)
import sys,os
import logging,logging.handlers
import collections

logger = logging.getLogger("rtp2hls_scte35")
logger.setLevel(logging.INFO)
#handler = logging.handlers.RotatingFileHandler("./logs/rtp2hls_scte35.log", maxBytes=(1048576*5), backupCount=7)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def exit(msg):
#    print(msg, file=sys.stderr)
    logger.debug(msg)
    sys.exit()
                
def convert_ns(t,base=1000000000):
    if t==Gst.CLOCK_TIME_NONE:
        return "None"
    s, ns = divmod(t, base)
    m, s = divmod(s, 60)

    if m < 60:
        return "0:%02i:%02i.%i" % (m, s, ns)
    else:
        h, m = divmod(m, 60)
        return "%i:%02i:%02i.%i" % (h, m, s, ns)

class Playlist():
    def __init__(self,filename,length):
        self.length=length
        self.filename=filename
        self.items=collections.deque(maxlen=length)
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))        
   
    def renderPlaylist(self):
        fd=open(self.filename,'w',1)
        fd.write("#EXTM3U\n")
        fd.write("#EXT-X-VERSION:3\n")
        fd.write("#EXT-X-TARGETDURATION:20\n")
        fd.write("#EXT-X-MEDIA-SEQUENCE:"+str(self.items[0]["seq_num"])+"\n")
        #FIXME: We should have a better method to find out the exact time of the startime.
        fd.write("#EXT-X-PROGRAM-DATE-TIME:"+datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")
        for i in self.items:
            fd.write("#EXTINF:15.0,\n")
            fd.write(i["segment_name"]+'\n')
        if self.length==None:
            fd.write("#EXT-X-ENDLIST\n")
        fd.close()
           
    def append_segment(self,segment):
        self.items.append(segment)
       
class HLSRecorder(object):  
    def __init__(self,stream,channel,docroot,urlroot):
        self.fd = None
        self.mainloop = GObject.MainLoop()
        self.stream=stream
        self.channel=channel
        self.docroot=docroot
        self.urlroot=urlroot
 
        #Setup recording pipeline: filesrc ! tsparse ! mpegtsdemux ! video/audio parsers ! splitmuxsink
        self.pipeline=Gst.Pipeline.new("HLSrecorder_SCTE35")
        self.filesrc=Gst.ElementFactory.make("filesrc","filesrc")
        self.tsparse=Gst.ElementFactory.make("tsparse","tsparse")
        self.q=Gst.ElementFactory.make("queue","queue")
        self.tsdemux=Gst.ElementFactory.make("tsdemux","tsdemux")
        self.splitmuxsink=Gst.ElementFactory.make("splitmuxsink","splitmuxsink")
        #Add elements to the pipeline...
        self.pipeline.add(self.filesrc)
        self.pipeline.add(self.tsparse)
        self.pipeline.add(self.q)
        self.pipeline.add(self.tsdemux)        
        self.pipeline.add(self.splitmuxsink)
        #Link elements....
        self.filesrc.link(self.tsparse)    
        self.tsparse.link(self.q)
        self.q.link(self.tsdemux)
        #Set properties....
        self.filesrc.set_property("location",self.stream)
        self.filesrc.set_property("do-timestamp",False)
        self.tsparse.set_property("set-timestamps",True)
        self.tsparse.set_property("parse-private-sections",True)
        self.tsdemux.set_property("emit-stats",True)
        self.splitmuxsink.set_property("muxer",Gst.ElementFactory.make("mpegtsmux",None))
        self.splitmuxsink.set_property("sink",Gst.ElementFactory.make("filesink",None))
        self.splitmuxsink.set_property("location",
              os.path.join(self.docroot,self.channel,"segment_%06d.ts"))
        self.splitmuxsink.set_property("max-size-bytes",0)
        self.splitmuxsink.set_property("max-size-time",0) #max-file-duration
        self.splitmuxsink.set_property("send-keyframe-requests",False)
        self.splitmuxsink.set_property("async-handling",True)
        self.splitmuxsink.set_property("message-forward",True)
        #Connect to message bus...
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::element",self.on_file_change)
        self.bus.connect("message::eos",self.stop)
        self.tsdemux.connect("pad-added",self.on_pad_added)
        self.tsdemux.connect("no-more-pads",self.on_no_more_pads)
        #Construct Playlist
        self.playlist=Playlist(os.path.join(self.docroot,self.channel,"playlist.m3u8"),None)
 
    def on_no_more_pads(self,src):
        print ("No more pads.")
        result=self.pipeline.set_state(Gst.State.PLAYING)
        
    def on_pad_added(self,src,new_pad):
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()
        if new_pad_type.startswith("audio/mpeg"):
            audioparse = Gst.ElementFactory.make("mpegaudioparse",None)
            #q=Gst.ElementFactory.make("queue2",None)
            self.pipeline.add(audioparse)
            #self.pipeline.add(q)
            #q.link(audioparse)
            new_pad.link(audioparse.get_static_pad("sink"))
            audioparse.get_static_pad("src").link(self.splitmuxsink.get_request_pad("audio_%u"))
            audioparse.sync_state_with_parent()
            #q.sync_state_with_parent()
        elif new_pad_type.startswith("video/x-h264"):
            videoparse = Gst.ElementFactory.make("h264parse",None)
            q=Gst.ElementFactory.make("queue",None)
            q.set_property("max-size-buffers",10000)
            q.set_property("max-size-bytes",50000000)
            q.set_property("max-size-time",10000000000)
            identity=Gst.ElementFactory.make("identity",None)
            identity.connect("handoff",self.identity_handoff)        
            self.pipeline.add(videoparse)
            self.pipeline.add(q)
            self.pipeline.add(identity)
            q.link(videoparse)
            videoparse.link(identity)
            new_pad.link(q.get_static_pad("sink"))
            identity.get_static_pad("src").link(self.splitmuxsink.get_request_pad("video"))
            #Add probe
            self.splitmuxsink.get_property("sink").get_static_pad("sink").add_probe(Gst.PadProbeType.DATA_DOWNSTREAM,self.buffer_received)
            videoparse.sync_state_with_parent()
            q.sync_state_with_parent()
            identity.sync_state_with_parent()
        else:
            print(
                "It has type '{0:s}' which is not raw audio/video. Ignoring.".format(new_pad_type))
            fakesink=Gst.ElementFactory.make("fakesink",None)
            self.pipeline.add(fakesink)
            new_pad.link(fakesink.get_static_pad("sink"))
            fakesink.sync_state_with_parent()

    def buffer_received(self,pad,info):
        if info.type & Gst.PadProbeType.BUFFER:
            buffer=info.get_buffer()
            logger.debug("Buffer received with PCR:%s and Duration:%s Offset:%i Offset_End:%i Size:%i"  % 
                (convert_ns(buffer.pts),convert_ns(buffer.duration),buffer.offset,buffer.offset_end,buffer.offset_end-buffer.offset))
        if info.type & Gst.PadProbeType.EVENT_DOWNSTREAM:
            event=info.get_event()
            if event.type==Gst.EventType.SEGMENT:
                segment=event.parse_segment().copy()
                logger.info("SEGMENT event received. Start:%s, Stream time:%s, Offset:%s, Base:%s, Format:%s",
                    convert_ns(segment.start),convert_ns(segment.time),convert_ns(segment.offset),
                    convert_ns(segment.base),segment.format)
            
        return Gst.PadProbeReturn.PASS

    def identity_handoff(self,element,buf):
        pass
        #logger.debug("Identity called.")

    def on_file_change(self,bus,msg):
        if msg.type==Gst.MessageType.ELEMENT:
            structure=msg.get_structure()
            #logger.debug("Message received from:%s",msg.src.get_name())
            #logger.debug("Structure: %s",structure.to_string())
            #GST_LOG("structure is %" GST_PTR_FORMAT,structure)
            if msg.src.get_name()=="tsdemux":
                
                logger.debug("Structure:%s",structure.to_string())
                
            if msg.src.get_name()=="splitmuxsink":         
                logger.debug("Structure:%s",structure.get_name())
                if structure.get_name()=="splitmuxsink-fragment-closed":
                    filename=os.path.basename(structure.get_string("location"))   
                    #(result,index)=structure.get_int("index")
                    index=0
                    (result,running_time)=structure.get_clock_time("running-time")
                    logger.debug(filename+" received. Running-time:"+str(convert_ns(running_time)))
                    self.playlist.append_segment({"segment_name":self.urlroot+'/'+self.channel+'/'+filename,
                                                  "seq_num":index})
                    self.playlist.renderPlaylist()
            if msg.src.get_name()=="tsparse" and structure.get_name()=="sit":
                section=GstMpegts.message_parse_mpegts_section(msg)
                if section:
                    spliceinfo=section.get_scte_splice_info()
                    if spliceinfo.splice_command_type==5:
                        logger.info("Splice Insert received. EventID:%#5.8x, In/~Out:%s, PCR:%s",
                            spliceinfo.splice_insert.splice_event_id,
                            spliceinfo.splice_insert.out_of_network_indicator,
                            convert_ns(spliceinfo.splice_insert.pts_time,90000))
                        force_key_unit_event = GstVideo.video_event_new_upstream_force_key_unit(
                            spliceinfo.splice_insert.pts_time,
                            True,
                            spliceinfo.splice_insert.splice_event_id)
                        result= self.splitmuxsink.get_property("sink").send_event(force_key_unit_event)
                        logger.info("GstForceKeyUnit event sent downstream with result:%s.",result)


    def record(self):     
        result=self.pipeline.set_state(Gst.State.PLAYING)
        logger.debug("Pipeline started with result: "+str(result))
        self.mainloop.run()

    def stop(self,bus,msg):
        logger.debug("EOS received.")
        self.pipeline.set_state(Gst.State.NULL)
        self.mainloop.quit()
      
def main():
    if len(sys.argv) < 5:
        sys.exit("""
Usage: {0} <file> <channel> <docroot> <urlroot>
 Where:
   file: The filename where stream should be read from.
   channel: The name of the channel. TS segments will be saved to the docroot/channel/date directory.
   docroot: The document root on the local filesystem.
   urlroot: Url root in the media playlist file. Segments will be served from the urlroot/channel/date/filename address.
""".format(sys.argv[0]))

    # Collect arguments
    stream = sys.argv[1]
    channel = sys.argv[2]
    docroot = sys.argv[3]
    urlroot = sys.argv[4]
 
    # Create the recorder and  start recording
    recorder = HLSRecorder(stream,channel,docroot,urlroot)
    # Blocks until record is done 
    recorder.record()

if __name__ == "__main__":
    main()
