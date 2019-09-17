#!/usr/bin/env python
import sys
import time
import os
import m3u8
from watchdog.observers import Observer
import watchdog.events
import logging
import datetime
import pandas

 
if len(sys.argv)!=5:
    print """
Wrong number of arguments.
Usage: ./playlist_localizer.py <src_manifest> <dst_manifest> <channel_name> <break_number>
<src_manifest>: Filename of the regional manifest. Commercial breaks should be located under the commercials/playlists/YYYY-MM-DD subfolder.
<dst_manifest>: Filename of the localized manifest file. 
<channel_name>: Channel name is in the filename of the XLS playlist.
<break_number>: Initial commercial break to start with. (Used if the XLS playlist is not found.)
Example:
./playlist_localizer.py /var/www/html/streams/nicktoons_live/playlist.m3u8 /var/www/html/streams/nicktoons_hun/nicktoons_hun.m3u8 Nicktoons_Hungary 20 &
"""
    sys.exit()

logger=logging.getLogger("playlist-localiser")
logger.setLevel(level=logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
ch_formatter=logging.Formatter("%(asctime)s - %(message)s")
ch.setFormatter(ch_formatter)
logger.addHandler(ch)
fh=logging.FileHandler("logs/localizer_"+sys.argv[3]+".log")
fh.setFormatter(ch_formatter)
logger.addHandler(fh)

class M3U8Watcher:
    def __init__(self, src_path,dst_path,channel_name,break_number):
        self.__src_path = src_path
        self.__dst_path=dst_path
        self.__channel_name=channel_name
        self.__break_number=int(break_number)
        self.__broadcast_date=(datetime.datetime.now()-datetime.timedelta(hours=-6)).strftime('%Y-%m-%d')
        self.__event_handler = watchdog.events.PatternMatchingEventHandler(
            patterns=[self.__src_path],
            ignore_patterns=[],
            ignore_directories=True)
        self.__event_handler.on_moved=self.playlist_modified
        self.__event_observer = Observer()
        self.regional_playlist=None
        self.local_playlist=None
        self.local_window=False
        self.playlist_duration=0
    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    def start(self):
        self.__schedule()
        self.__event_observer.start()
    def stop(self):
        self.__event_observer.stop()
        self.__event_observer.join()
    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler,
            os.path.dirname(self.__src_path),
            recursive=True
        )
    def playlist_modified(self, event):
        if self.__src_path == event.dest_path:
            r_playlist=m3u8.load(event.dest_path)
            if self.regional_playlist is not None:
                for s in r_playlist.segments:
                    if s.uri not in [ r.uri for r in self.regional_playlist.segments]:
                        logger.debug("New segment detected:\n{}".format(s))
                        playlist_duration=((r_playlist.segments[-1].program_date_time-r_playlist.segments[0].program_date_time) +
                                            datetime.timedelta(seconds=r_playlist.segments[0].duration))
                        logger.debug("Playlist duration:%isec",playlist_duration.total_seconds())
                        if self.local_window==False and s.discontinuity==True and s.cue_out==True:
                            #Start of a local window. Replace segments with local commercials.
                            broadcast_date=(datetime.datetime.now()-datetime.timedelta(hours=6)).strftime('%Y-%m-%d')
                            if broadcast_date != self.__broadcast_date:
                                self.__broadcast_date=broadcast_date
                                self.__break_number=1
                            playlist_xls=os.path.join(os.path.dirname(self.__dst_path),"commercials","playlists",broadcast_date,
                                    broadcast_date+"_"+self.__channel_name+".xls")
                            try:
                                df=pandas.read_excel(playlist_xls)
                                self.__break_number=int(df.iloc[(pandas.to_datetime(df["Start Time"],format="%H:%M:%S:00")-
                                    pandas.to_datetime(pandas.Timestamp.now().strftime("%H:%M:%S:00"),format="%H:%M:%S:00")).
                                    abs().argsort()[0]]["Break Number"] )
                            except:
                                logger.warning("Could read in daily commercial log from file {} Estimating break number.".format(playlist_xls))
                            logger.debug("Selected break number is {}.".format(self.__break_number))
                            commercial_log_filename= os.path.join(os.path.dirname(self.__dst_path),
                                "commercials","playlists",self.__broadcast_date,"brk_{:02d}".format(self.__break_number),"playlist.m3u8")   
                            logger.debug("Opening commercial log file: {}".format(commercial_log_filename))
                            try:
                                commercial_brk=m3u8.load(commercial_log_filename)
                                commercial_time=self.local_playlist.segments[-1].program_date_time
                                logger.debug("Start of commercial break detected with time:%s",
                                commercial_time.isoformat())
                                for cs in commercial_brk.segments:
                                    commercial_time+=datetime.timedelta(seconds=cs.duration)
                                    cs.program_date_time=commercial_time
                                    self.local_playlist.add_segment(cs)
                                    logger.debug("Segment to local playlist:\n{}".format(cs))
                                self.local_window=True
                            except Exception:
                                logger.exception("Couldn't parse local manifest file. Keeping regional segments.")
                            self.__break_number+=1
                        if self.local_window==True and s.discontinuity==True and s.cue_out==False:
                            #First segment after the commercial break. Switch back to normal mode
                            self.local_window=False
                        if self.local_window==False:
                            #Default case, add segment to the local playlist
                            self.local_playlist.add_segment(s)
                            logger.debug("Detected segment appended to playlist")
                        while s.program_date_time-self.local_playlist.segments[0].program_date_time > playlist_duration+datetime.timedelta(seconds=3):
                            logger.debug("Segment removed from playlist:\n{}".format(
                                self.local_playlist.segments.pop(0)))
                            self.local_playlist.media_sequence+=1
                            logger.debug("New sequence number:{}\n".format(self.local_playlist.media_sequence))                            
            else:
                logger.debug("Initial playlist recorded.\n")
                self.regional_playlist=r_playlist
                self.local_playlist=r_playlist
                self.local_playlist.media_sequence=1
            self.regional_playlist=r_playlist
            self.local_playlist.dump(dst_path)



if __name__ == "__main__":
    basedir = os.path.abspath(os.path.dirname(__file__))
    src_path = sys.argv[1] 
    dst_path = sys.argv[2] 
    channel_name= sys.argv[3] 
    break_number = sys.argv[4] 
    logger.debug("Application started with command line {}".format(' '.join(sys.argv[1:])))
    M3U8Watcher(src_path,dst_path,channel_name,break_number).run()

