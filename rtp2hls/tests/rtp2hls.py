#!/usr/bin/env python

from __future__ import print_function

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstMpegts' , '1.0')

from gi.repository import GObject, Gst, GstMpegts

import datetime


GObject.threads_init()
Gst.init(None)
import sys,os
import logging,logging.handlers
import collections

if len(sys.argv) != 5:
        sys.exit("""
Usage: {0} <multicast> <channel> <docroot> <urlroot>
 Where:
   multicast: The multicast address where stream should be captured from in the format of udp://ip:port.
   channel: The name of the channel. TS segments will be saved to the docroot/channel/date directory.
   docroot: The document root on the local filesystem.
   urlroot: Url root in the media playlist file. Segments will be served from the urlroot/channel/date/filename address.
""".format(sys.argv[0]))



logger = logging.getLogger("rtp2hls")
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler("./logs/rtp2hls_"+sys.argv[2]+".log", maxBytes=(1048576*5), backupCount=7)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)



def exit(msg):
#    print(msg, file=sys.stderr)
    logger.debug(msg)
    sys.exit()
                
def convert_ns(t):
    s, ns = divmod(t, 1000000000)
    m, s = divmod(s, 60)

    if m < 60:
        return "0:%02i:%02i.%i" % (m, s, ns)
    else:
        h, m = divmod(m, 60)
        return "%i:%02i:%02i.%i" % (h, m, s, ns)

class Playlist():
    def __init__(self,filename,length):
        self.filename=filename
        self.items=collections.deque(maxlen=length)
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))        
   
    def renderPlaylist(self):
        fd=open(self.filename,'w',1)
        fd.write("#EXTM3U\n")
        fd.write("#EXT-X-VERSION:3\n")
        fd.write("#EXT-X-TARGETDURATION:15\n")
        fd.write("#EXT-X-MEDIA-SEQUENCE:"+str(self.items[0]["seq_num"])+"\n")
        #FIXME: We should have a better method to find out the exact time of the startime.
        fd.write("#EXT-X-PROGRAM-DATE-TIME:"+datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")
        for i in self.items:
            fd.write("#EXTINF:15.0,\n")
            fd.write(i["segment_name"]+'\n')
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
        self.date=datetime.datetime.today().strftime("%Y%m%d")
 
        #Setup recording pipeline: udpsrc ! rtpmp2tdepay ! tsparse ! multifilesink
        self.pipeline=Gst.Pipeline.new("HLSrecorder")
        self.udpsrc=Gst.ElementFactory.make("udpsrc","udpsrc")
        self.depay=Gst.ElementFactory.make("rtpmp2tdepay","rtpmp2tdepay")
        self.tsparse=Gst.ElementFactory.make("tsparse","tsparse")
        self.multifilesink=Gst.ElementFactory.make("multifilesink","multifilesink")
        #Add elements to the pipeline...
        self.pipeline.add(self.udpsrc)
        self.pipeline.add(self.depay)
        self.pipeline.add(self.tsparse)        
        self.pipeline.add(self.multifilesink)
        #Link elements....
        self.udpsrc.link(self.depay)
        self.depay.link(self.tsparse)
        self.tsparse.link(self.multifilesink)
        #Set properties....
        self.udpsrc.set_property("uri",self.stream)
        #self.udpsrc.set_property("multicast-iface","enp6s0")
        self.udpsrc.set_property("caps",Gst.Caps.from_string("application/x-rtp"))
        self.udpsrc.set_property("auto-multicast",True)
        self.tsparse.set_property("set-timestamps",True)
        self.multifilesink.set_property("location",
             os.path.join(self.docroot,self.channel,str(os.getpid())+"_%06d.ts"))
        self.multifilesink.set_property("next-file",5) #max-file-duration
        self.multifilesink.set_property("max-files",7)
        self.multifilesink.set_property("max-file-duration",15000000000)
        self.multifilesink.set_property("post-messages",True)
        #Connect to message bus...
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        result=self.bus.connect("message::element",self.on_file_change)
        #Add probe
        self.multifilesink.get_static_pad("sink").add_probe(
            Gst.PadProbeType.DATA_DOWNSTREAM,self.buffer_received)
        #Construct Playlist
        self.playlist=Playlist(os.path.join(self.docroot,self.channel,"playlist.m3u8"),5)
 
    def buffer_received(self,pad,info):
        if info.type==Gst.PadProbeType.BUFFER:
            buffer=info.get_buffer()
#        print("Buffer received with PCR:%s and Duration:%s Offset:%i Offset_End:%i Size:%i"  % 
#            (convert_ns(buffer.pts),convert_ns(buffer.duration),buffer.offset,buffer.offset_end,buffer.offset_end-buffer.offset))
        return Gst.PadProbeReturn.OK

    def on_file_change(self,bus,msg):
        if msg.type==Gst.MessageType.ELEMENT:
            structure=msg.get_structure()
            logger.debug("Message received from:%s",msg.src.get_name())
            #logger.debug("Structure: %s",structure.to_string())
            #GST_LOG("structure is %" GST_PTR_FORMAT,structure)
            if msg.src.get_name()=="multifilesink":         
                if structure.get_name()=="GstMultiFileSink":
                    filename=os.path.basename(structure.get_string("filename"))   
                    (result,index)=structure.get_int("index")
                    (result,running_time)=structure.get_clock_time("duration")
                    logger.info(filename+" received. Dur:"+str(convert_ns(running_time)))
                    self.playlist.append_segment({"segment_name":self.urlroot+'/'+self.channel+'/'+filename,"seq_num":index})
                    self.playlist.renderPlaylist()
            if msg.src.get_name()=="tsparse":
                section=GstMpegts.message_parse_mpegts_section(msg)
                logger.debug("Section received:%s",section.section_type)

    def record(self):     
        result=self.pipeline.set_state(Gst.State.PLAYING)
        logger.debug("Pipeline started with result: "+str(result))
        self.mainloop.run()
      
def main():
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
