FROM buster-gst-dev:latest AS build
RUN mkdir /rtp2hls
COPY . /rtp2hls/
RUN cd /rtp2hls && make clean && make

FROM debian:buster-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad
COPY --from=build /rtp2hls/src/rtp2hls /usr/bin
COPY --from=build /usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstmpegtsdemux.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0
COPY --from=build /usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstmpegtsmux.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0
COPY --from=build /usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstrtp.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0
COPY --from=build /usr/lib/x86_64-linux-gnu/libgstmpegts-1.0.so.0.1404.0 /usr/lib/x86_64-linux-gnu
COPY --from=build /usr/lib/x86_64-linux-gnu/libgstcodecparsers-1.0.so.0.1404.0 /usr/lib/x86_64-linux-gnu

ENTRYPOINT ["rtp2hls"]


