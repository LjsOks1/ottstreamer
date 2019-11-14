pipeline_description="""
mpegtsmux name=mux prog-map=prog_map,PCR_100=sink_64,sink_64=100,sink_65=100,sink_66=100,sink_67=100,sink_68=100,sink_69=100,\
sink_70=100,sink_71=100,sink_72=100,sink_73=100,sink_74=100,sink_75=100,sink_76=100 
multiqueue name=mq_mux max-size-buffers=0 max-size-bytes=0 use-buffering=true
multiqueue name=mq_out max-size-buffers=0 use-buffering=true 
multiqueue name=mq_enc 
compositor name=mv background=1 latency=1000000000 start-time-selection=1 
                sink_1::xpos=0 sink_1::ypos=100 sink_1::alpha=1.0 
		sink_2::xpos=480 sink_2::ypos=100 sink_2::alpha=1.0 
		sink_3::xpos=960 sink_3::ypos=100 sink_3::alpha=1.0 
		sink_4::xpos=1440 sink_4::ypos=100 sink_4::alpha=1.0 
		sink_5::xpos=0 sink_5::ypos=390 sink_5::alpha=1.0 
		sink_6::xpos=480 sink_6::ypos=390 sink_6::alpha=1.0 
		sink_7::xpos=960 sink_7::ypos=390 sink_7::alpha=1.0 
		sink_8::xpos=1440 sink_8::ypos=390 sink_8::alpha=1.0 
		sink_9::xpos=0 sink_9::ypos=680 sink_9::alpha=1.0 
		sink_10::xpos=480 sink_10::ypos=680 sink_10::alpha=1.0 
		sink_11::xpos=960 sink_11::ypos=680 sink_11::alpha=1.0 
		sink_12::xpos=1440 sink_12::ypos=680 sink_12::alpha=1.0  
! videoconvert ! video/x-raw,format=I420,width=1920,height=1080 ! clockoverlay time-format="%Y-%m-%d %H:%M:%S" ! 
textoverlay text="HUN" x-absolute=0.1 ypos=940 halignment=5 ! textoverlay text="BUL" x-absolute=0.4 ypos=940 halignment=5 ! 
textoverlay text="ROM" x-absolute=0.65 ypos=940 halignment=5 ! textoverlay text="CZE" x-absolute=0.9 ypos=940 halignment=5 ! 
mq_enc.sink_0 mq_enc.src_0 ! tee name=t  
t.src_1 ! queue max-size-bytes=0 max-size-time=0 ! fakesink sync=true
t.src_2 ! identity sync=true ! queue2 use-buffering=true  max-size-bytes=0 max-size-buffers=0 ! x264enc  bitrate=8000 key-int-max=12 interlaced=true ! 
   mq_mux.sink_1 mq_mux.src_1 ! mux.sink_64 
mux.src ! tsparse name=tp parse-private-sections=true tp.program_100 ! identity silent=false ! video/mpegts ! queue max-size-buffers=0 ! tee name=out 
   out.src_1 ! mq_out.sink_1 mq_out.src_1 ! rtpmp2tpay ! udpsink clients=239.211.8.17:1234 sync=true qos=true 
   out.src_2 ! mq_out.sink_2 mq_out.src_2 ! multifilesink name=mfs location={loc} next-file=3 max_files=0 max-file-size=0 post-messages=true index={index}  
udpsrc uri=udp://239.211.8.5:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux1 
   demux1.video_0_085d ! multiqueue name=mq1 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_1 
   demux1.audio_0_085f ! mq1.sink_2 mq1.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw ! mq_enc.sink_1 mq_enc.src_1  !  
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 ! mq_mux.sink_2 mq_mux.src_2 ! mux.sink_65 
udpsrc uri=udp://239.211.8.6:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux2  
   demux2.video_0_085d ! multiqueue name=mq2 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_2 
   demux2.audio_0_0861 ! mq2.sink_2 mq2.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_2 mq_enc.src_2  !  
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_3 mq_mux.src_3 ! mux.sink_66 
udpsrc uri=udp://239.211.8.7:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux3 
   demux3.video_0_085d ! multiqueue name=mq3 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_3 
   demux3.audio_0_0860 ! mq3.sink_2 mq3.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_3 mq_enc.src_3  !  
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_4 mq_mux.src_4 ! mux.sink_67 
udpsrc uri=udp://239.211.8.8:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux4 
   demux4.video_0_085d ! multiqueue name=mq4 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_4 
   demux4.audio_0_0862 ! mq4.sink_2 mq4.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_4 mq_enc.src_4  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_5 mq_mux.src_5 ! mux.sink_68 
udpsrc uri=udp://239.211.8.11:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux5 
   demux5.video_0_046b ! multiqueue name=mq5 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_5 
   demux5.audio_0_046e ! mq5.sink_2 mq5.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_5 mq_enc.src_5  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_6 mq_mux.src_6 ! mux.sink_69 
udpsrc uri=udp://239.211.8.10:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux6 
   demux6.video_0_046b ! multiqueue name=mq6 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_6 
   demux6.audio_0_0471 ! mq6.sink_2 mq6.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_6 mq_enc.src_6  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_7 mq_mux.src_7 ! mux.sink_70 
udpsrc uri=udp://239.211.8.9:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux7 
   demux7.video_0_046b ! multiqueue name=mq7 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_7 
   demux7.audio_0_0470 ! mq7.sink_2 mq7.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_7 mq_enc.src_7  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_8 mq_mux.src_8 ! mux.sink_71 
udpsrc uri=udp://239.211.8.12:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux8 
   demux8.video_0_046b ! multiqueue name=mq8 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! h264parse ! avdec_h264 ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_8 
   demux8.audio_0_046f ! mq8.sink_2 mq8.src_2 ! mpegaudioparse ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_8 mq_enc.src_8  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_9 mq_mux.src_9 ! mux.sink_72 
udpsrc uri=udp://239.211.8.13:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux9 
   demux9.video_0_0579 ! mpegvideoparse ! multiqueue name=mq9 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! avdec_mpeg2video ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_9 
   demux9.audio_0_05b7 ! mpegaudioparse ! mq9.sink_2 mq9.src_2 ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_9 mq_enc.src_9  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_10 mq_mux.src_10 ! mux.sink_73 
udpsrc uri=udp://239.211.8.15:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux10 
   demux10.video_0_0579 ! mpegvideoparse ! multiqueue name=mq10 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! avdec_mpeg2video ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_10 
   demux10.audio_0_05b6 ! mpegaudioparse ! mq10.sink_2 mq10.src_2 ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_10 mq_enc.src_10  ! 
   identity sync=true ! audioconvert !  queue2 use-buffering=true max-size-bytes=0 max-size-time=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_11 mq_mux.src_11 ! mux.sink_74 
udpsrc uri=udp://239.211.8.14:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux11 
   demux11.video_0_0579 ! mpegvideoparse ! multiqueue name=mq11 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! avdec_mpeg2video ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_11 
   demux11.audio_0_05b6 ! mpegaudioparse ! mq11.sink_2 mq11.src_2 ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_11 mq_enc.src_11  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_12 mq_mux.src_12 ! mux.sink_75 
udpsrc uri=udp://239.211.8.16:1234 caps=application/x-rtp ! rtpmp2tdepay ! queue2 use-buffering=true ! tsdemux name=demux12 
   demux12.video_0_0579 ! mpegvideoparse ! multiqueue name=mq12 max-size-bytes=0 max-size-buffers=0 max-size-time=5000000000 ! avdec_mpeg2video ! deinterlace ! 
   videoconvert ! videoscale ! videorate ! video/x-raw,format=AYUV,width=480,height=270,framerate=25/1 ! 
   queue leaky=2  max-size-bytes=0 max-size-time=0 max-size-buffers=200 ! identity ! mv.sink_12 
   demux12.audio_0_05b5 ! mpegaudioparse ! mq12.sink_2 mq12.src_2 ! avdec_mp2float ! audio/x-raw !  mq_enc.sink_12 mq_enc.src_12  ! 
   identity sync=true ! audioconvert ! queue2 use-buffering=true max-size-bytes=0 max-size-buffers=0 ! 
   faac ! aacparse ! audio/mpeg,mpegversion=4,layer=3 !  mq_mux.sink_13 mq_mux.src13 ! mux.sink_76 
"""






