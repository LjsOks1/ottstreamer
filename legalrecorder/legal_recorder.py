#!/usr/bin/python
import sys
import os
import gi
import m3u8
gi.require_version('Gst','1.0')
from gi.repository import GObject,Gst,GLib
import fnmatch
import logging
from logging import FileHandler
import multiviewer
from datetime import date,datetime,timedelta
import signal


formatter=logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
logger=logging.getLogger("recorder")
consoleHandler=logging.StreamHandler(sys.stdout)

logger.addHandler(consoleHandler)
logger.setLevel(logging.DEBUG)
logger.info('Hello from legal_recorder.py')

command=multiviewer.pipeline_description

class Recorder:
    def __init__(self,pipeline_desc,base_path,base_uri):
        self.pipeline_desc=pipeline_desc
        self.base_uri=base_uri
        self.base_path=base_path
        self.daystart=timedelta(hours=6)
        self.insertdiscontinuity=False
        self.broadcastday=(date.today()-self.daystart).strftime("%Y-%m-%d")
        self.exit=False

    def stop_pipeline(self,signum,frame):
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "dump")
        self.exit=True
        self.loop.quit()

    def bus_callback(self, bus,message):
        t = message.type
        if t == Gst.MessageType.EOS:
            logger.info("End-of-stream\n")
            self.playlist.dump(os.path.join(self.segment_path,"playlist.m3u8"))
            logger.info("Break encoding finished without errors. Playlist dumped")
            self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("Error: %s: %s\n" % (err, debug))
            #self.loop.quit()
        elif t== Gst.MessageType.STREAM_COLLECTION:
            stream_collection=message.parse_stream_collection()
            src=message.src
            logger.info("StreamCollection message received from {} with size {}".
                    format(src.name,stream_collection.get_size()))
            streams=[]
            for i in range(0,stream_collection.get_size()):
                stream=stream_collection.get_stream(i)
                logger.info("{} {}".format(stream.get_stream_id(),stream.get_stream_type()))
                streams.append(stream.get_stream_id())
                if stream.get_stream_type()==Gst.StreamType.AUDIO:
                    break
            event=Gst.Event.new_select_streams(streams)
            #result=self.pipeline.send_event(event)
            #logger.info("Select stream event sent with result: {}".format(result))
    
        return True

    def on_element_message(self,element,message):
        structure=message.get_structure()
        if structure.get_name()=="GstMultiFileSink":
            logger.debug('{} finished.'.format(structure.get_string("filename")))
            current_day=(date.today()-self.daystart).strftime("%Y-%m-%d")
            self.playlist.add_segment(m3u8.model.Segment(
                uri=os.path.join(self.base_uri,'/'.join(structure.get_string("filename").split('/')[-3:])),
                duration=15,
                discontinuity = True if self.insertdiscontinuity else False,
                program_date_time=datetime.now()))
            self.playlist.is_endlist=False if self.broadcastday==current_day else True
            self.playlist.dump(os.path.join(self.base_path,self.broadcastday,"playlist.m3u8"))
            self.insertdiscontinuity=False
            if self.broadcastday != current_day:
                self.broadcastday=current_day
                self.loop.quit()

    def run_recorder(self):
        try:
            signal.signal(signal.SIGINT,self.stop_pipeline)
            signal.signal(signal.SIGTERM,self.stop_pipeline)
            Gst.init(None)
            self.loop=GLib.MainLoop()
            while not self.exit:
                segment_path=os.path.join(self.base_path,self.broadcastday,"segment_%05d.ts")
                if not os.path.exists(os.path.dirname(segment_path)):
                    os.makedirs(os.path.dirname(segment_path))
                if os.path.isfile(os.path.join(os.path.dirname(segment_path),"playlist.m3u8")):
                    self.playlist=m3u8.load(os.path.join(os.path.dirname(segment_path),"playlist.m3u8"))
                    self.insertdiscontinuity=True
                    start_index=int(self.playlist.segments[-1].uri[-8:-3])+2 #get the index from the filename
                else:
                    self.playlist=m3u8.M3U8()
                    self.playlist.version="3"
                    self.playlist.is_endlist=False
                    start_index=0
                command=self.pipeline_desc.format(loc=segment_path,index=start_index)
                logger.info("Saving segments to:{}".format(segment_path))
                self.pipeline=Gst.parse_launch(command)
                if not self.pipeline:
                    logger.error( "Couldn't create pipeline for recorder:{}".format(command))
                    return
                bus=self.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message",self.bus_callback)
                bus.connect("message::element",self.on_element_message)
                #bus.connect("message::stream-collection",self.on_stream_connetion)
                self.pipeline.set_state(Gst.State.PLAYING)
                self.loop.run()
                self.pipeline.set_state(Gst.State.NULL)
        except Exception as e:
            logger.error('Encoding failed: '+str(e))
        logger.info("Setting pipline to NULL.")
        self.pipeline.set_state(Gst.State.NULL)
     
if __name__ == '__main__':
    base_path=sys.argv[1]
    base_uri=sys.argv[2]
    rec=Recorder(multiviewer.pipeline_description,base_path,base_uri)
    rec.run_recorder()
