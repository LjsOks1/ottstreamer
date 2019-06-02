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

logger = logging.getLogger("scte35")
logger.setLevel(logging.DEBUG)
#handler = logging.handlers.RotatingFileHandler("./logs/scte35.log", maxBytes=(1048576*5), backupCount=7)
handler =logging.StreamHandler(sys.stdout)
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

def pts_time(t):
    s, ns = divmod(t, 90000)
    m, s = divmod(s, 60)

    if m < 60:
        return "0:%02i:%02i.%i" % (m, s, ns)
    else:
        h, m = divmod(m, 60)
        return "%i:%02i:%02i.%i" % (h, m, s, ns)

     
class SCTE35(object):  
    def __init__(self):
        self.mainloop = GObject.MainLoop()

        #Setup recording pipeline: udpsrc ! rtpmp2tdepay ! tsparse ! multifilesink
        self.pipeline=Gst.Pipeline.new("SCTE35")
        self.filesrc=Gst.ElementFactory.make("filesrc","filesrc")
        self.tsparse=Gst.ElementFactory.make("tsparse","tsparse")
        self.fakesink=Gst.ElementFactory.make("fakesink","fakesink")
        #Add elements to the pipeline...
        self.pipeline.add(self.filesrc)
        self.pipeline.add(self.tsparse)        
        self.pipeline.add(self.fakesink)
        #Link elements....
        self.filesrc.link(self.tsparse)
        self.tsparse.link(self.fakesink)
        #Set properties....
        self.filesrc.set_property("location","plp0_1010.ts")
        self.tsparse.set_property("parse-private-sections",True)
        self.tsparse.set_property("set-timestamps",True)
        #Connect to message bus...
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message",self.on_message)
        #Add probe
        self.fakesink.get_static_pad("sink").add_probe(
            Gst.PadProbeType.DATA_DOWNSTREAM,self.buffer_received)

    def buffer_received(self,pad,info):
#        if info.type==Gst.PadProbeType.BUFFER:       
#            buffer=info.get_buffer()
#        print("Buffer received with PCR:%s and Duration:%s Offset:%i Offset_End:%i Size:%i"  % 
#            (convert_ns(buffer.pts),convert_ns(buffer.duration),buffer.offset,buffer.offset_end,buffer.offset_end-buffer.offset))
        return Gst.PadProbeReturn.OK

    def on_message(self,bus,msg):
        if msg.type==Gst.MessageType.ELEMENT:
            structure=msg.get_structure()
            logger.debug("Message received from:%s with structure:%s" ,msg.src.get_name(),structure.get_name())
            if msg.src.get_name()=="tsparse" and structure.get_name()=='sit':
                section=GstMpegts.message_parse_mpegts_section(msg)
                if section:
                    spliceinfo=section.get_scte_splice_info()
                    logger.debug("PTS Offset:%i",spliceinfo.pts_adjustment)
                    logger.debug("Command type:%i",spliceinfo.splice_command_type)
                    if spliceinfo.splice_command_type==5:
                        logger.debug("EventID:%#5.8x",spliceinfo.splice_insert.splice_event_id)
                        logger.debug("In/Out flag:%s",spliceinfo.splice_insert.out_of_network_indicator)
                        logger.debug("PCR: %s (%i)",pts_time(spliceinfo.splice_insert.pts_time),spliceinfo.splice_insert.pts_time)
                        logger.debug("Program/~Component Splice:%s",spliceinfo.splice_insert.program_splice_flag)
            if msg.src.get_name()=="tsparse" and structure.get_name()=='pmt':
                section=GstMpegts.message_parse_mpegts_section(msg)
                if section:
                    pmt=section.get_pmt()
                    logger.debug("PMT streams:%i",pmt.streams[0].stream_type)
        if msg.type==Gst.MessageType.EOS:
            self.stop()

    def stop(self):
        logger.debug("EOS received.")
        self.pipeline.set_state(Gst.State.NULL);
        self.mainloop.quit()

    def run(self):     
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.debug("Pipeline started.")
        self.mainloop.run()
      
def main():
    pl= SCTE35()
    # Blocks until record is done 
    pl.run()

if __name__ == "__main__":
    main()
