gst-launch-1.0  ^
mpegtsmux name=mux prog-map=program_map,PCR_100=sink_100,sink_100=100,sink_101=100,sink_104=100,PMT_100=190 ^
multiqueue name=q max-size-buffers=23 max-size-bytes=0 max-size-time=0 sync-by-running-time=TRUE ^
filesrc location=..\\..\\streams\\ad2.mp4 ! ^
decodebin name=dec ^
dec.src_0 ! videoscale ! video/x-raw,width=720,height=576 ! ^
   x264enc option-string="no-scenecut:keyint=12" key-int-max=12 ! h264parse ! q.sink_1 q.src_1 ! identity name=i_v silent=false ! mux.sink_100 ^
dec.src_1 ! audioconvert ! audioresample ! tee name=t ^
   t.src_0 ! avenc_aac bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=2 ! q.sink_2 q.src_2 ! identity name=i_a1 silent=false ! mux.sink_104 ^
   t.src_1 ! avenc_aac bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=2 ! q.sink_3 q.src_3 ! identity name=i_a2 silent=false ! mux.sink_101 ^
mux.src ! filesink location=..\\..\\rtp2hls\\tests\\ad2.ts
REM   t.src_0 ! avenc_mp2 perfect-timestamp=true ! mpegaudioparse ! q.sink_2 q.src_2 ! mux.sink_104 ^
