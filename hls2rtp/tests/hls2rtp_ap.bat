gst-launch-1.0 -v ^
filesrc location=merged.ts ! ^
identity silent=true name=identity_hls ! ^
tsparse name=tp set-timestamps=false ^
tp.program_100 !  video/mpegts ! ^
identity silent=false name=identity_tp ! ^
rtpmp2tpay ! ^
identity silent=true name=identity_pay ! ^
udpsink host=239.211.8.5 sync=true port=1234 auto-multicast=true
rem filesink location=reconstructed.ts
rem filesink location=reconstructed.ts
rem souphttpsrc location=http://localhost:8000/playlist_orig.m3u8 ! ^
rem hlsdemux ! video/mpegts ! ^
rem queue2 max-size-time=30000000000 max-size-buffers=0 max-size-bytes=0 high-watermark=0.99 low-watermark=0.01 use-buffering=true ! ^
rem filesrc location=reconstructed.ts ! ^

