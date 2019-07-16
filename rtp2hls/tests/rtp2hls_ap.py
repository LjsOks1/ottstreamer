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

if len(sys.argv) != 1:
        sys.exit("""
Usage: {0} <multicast> <channel> <docroot> <urlroot>
 Where:
   filename: Sourcefile
   channel: The name of the channel. TS segments will be saved to the docroot/channel/date directory.
   docroot: The document root on the local filesystem.
   urlroot: Url root in the media playlist file. Segments will be served from the urlroot/channel/date/filename address.
""".format(sys.argv[0]))



logger = logging.getLogger("rtp2hls_scte35_tsparse")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
#handler = logging.handlers.RotatingFileHandler("./logs/rtp2hls_"+sys.argv[2]+".log", maxBytes=(1048576*5), backupCount=7)
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
        self.length=length
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))        
   
    def renderPlaylist(self):
        fd=open(self.filename,'w',1)
        fd.write("#EXTM3U\n")
        fd.write("#EXT-X-VERSION:3\n")
        fd.write("#EXT-X-TARGETDURATION:19\n")
        fd.write("#EXT-X-MEDIA-SEQUENCE:"+str(self.items[0]["seq_num"])+"\n")
        #FIXME: We should have a better method to find out the exact time of the startime.
        fd.write("#EXT-X-PROGRAM-DATE-TIME:"+datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")
        for i in self.items:
            fd.write("#EXTINF:15.000,\n")
            fd.write(i["segment_name"]+'\n')
        if self.length is None:
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
        self.date=datetime.datetime.today().strftime("%Y%m%d")
 
        #Setup recording pipeline: udpsrc ! rtpmp2tdepay ! tsparse ! multifilesink
        self.pipeline=Gst.Pipeline.new("HLSrecorder_SCTE35")
        self.filesrc=Gst.ElementFactory.make("filesrc","filesrc")
        self.tsparse=Gst.ElementFactory.make("tsparse","tsparse")
        self.multifilesink=Gst.ElementFactory.make("multifilesink","multifilesink")
        #Add elements to the pipeline...
        self.pipeline.add(self.filesrc)
        self.pipeline.add(self.tsparse)        
        self.pipeline.add(self.multifilesink)
        #Link elements....
        self.filesrc.link(self.tsparse)
        self.tsparse.get_request_pad("program_100").link(self.multifilesink.get_static_pad("sink"))
        #Set properties....
        self.filesrc.set_property("location",self.stream)
        self.tsparse.set_property("parse-private-sections",True)
        self.multifilesink.set_property("location",
             os.path.join(self.docroot,self.channel,"animalplanet_%06d.ts"))
        self.multifilesink.set_property("next-file",3) #force-key-unit
        self.multifilesink.set_property("max-files",0)
        self.multifilesink.set_property("max-file-size",0)
        self.multifilesink.set_property("post-messages",True)
        #Connect to message bus...
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        result=self.bus.connect("message",self.on_message)
        #Add probe
        self.multifilesink.get_static_pad("sink").add_probe(
            Gst.PadProbeType.DATA_DOWNSTREAM,self.buffer_received)
        #Construct Playlist
        self.playlist=Playlist(os.path.join(self.docroot,self.channel,"playlist.m3u8"),None)
 
    def buffer_received(self,pad,info):
        if info.type==Gst.PadProbeType.BUFFER:
            buffer=info.get_buffer()
#        print("Buffer received with PCR:%s and Duration:%s Offset:%i Offset_End:%i Size:%i"  % 
#            (convert_ns(buffer.pts),convert_ns(buffer.duration),buffer.offset,buffer.offset_end,buffer.offset_end-buffer.offset))
        return Gst.PadProbeReturn.OK

    def on_message(self,bus,msg):
        if msg.type==Gst.MessageType.ELEMENT:
            structure=msg.get_structure()
            #logger.debug("Message received from:%s",msg.src.get_name())
            #logger.debug("Structure: %s",structure.to_string())
            #GST_LOG("structure is %" GST_PTR_FORMAT,structure)
            if msg.src.get_name()=="multifilesink":         
                if structure.get_name()=="GstMultiFileSink":
                    filename=os.path.basename(structure.get_string("filename"))   
                    (result,index)=structure.get_int("index")
                    (result,running_time)=structure.get_uint64("duration")
                    if not result:
                        logger.error("Couldn't get duration.")
                    logger.info(filename+" received. Dur:"+str(convert_ns(running_time)))
                    logger.info(structure)
                    self.playlist.append_segment({"segment_name":self.urlroot+'/'+self.channel+'/'+filename,"seq_num":index})
                    self.playlist.renderPlaylist()
            if msg.src.get_name()=="tsparse":
                section=GstMpegts.message_parse_mpegts_section(msg)
                #logger.debug("Section received:%s",section.section_type)
        if msg.type==Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            self.mainloop.quit()

    def record(self):     
        result=self.pipeline.set_state(Gst.State.PLAYING)
        logger.debug("Pipeline started with result: "+str(result))
        self.mainloop.run()
      
def main():
    # Collect arguments
    stream = "../transport_streams/ap.ts"
    channel = "ap"
    docroot = "/var/www/html/streams"
    urlroot = "http://129.228.120.86/streams"
 
    # Create the recorder and  start recording
    recorder = HLSRecorder(stream,channel,docroot,urlroot)
    # Blocks until record is done 
    recorder.record()

if __name__ == "__main__":
    main()
