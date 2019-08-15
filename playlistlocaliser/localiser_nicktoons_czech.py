import sys
import time
import os
import m3u8
from watchdog.observers import Observer
import watchdog.events

class M3U8Watcher:
    def __init__(self, src_path,dst_path):
        self.__src_path = src_path
        self.__dst_path=dst_path
        self.__event_handler = watchdog.events.PatternMatchingEventHandler(
            patterns=["*.m3u8"],
            ignore_patterns=[],
            ignore_directories=True)
        #self.__event_handler = M3U8Localiser()
        self.__event_handler.on_modified=self.playlist_modified
        self.__event_observer = Observer()
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
        if self.__src_path == event.src_path:
            print(event.src_path)
            regional_playlist=m3u8.load(event.src_path)
            print(regional_playlist.dumps())


if __name__ == "__main__":
    basedir = os.path.abspath(os.path.dirname(__file__))
    src_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(basedir,'playlist.m3u8')
    dst_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(basedir,'playlist_local.m3u8')
    M3U8Watcher(src_path,dst_path).run()
