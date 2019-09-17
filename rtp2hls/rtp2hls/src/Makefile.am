# name of your binary
bin_PROGRAMS = rtp2hls

# list of source files
# the prefix is the name of the binary
rtp2hls_SOURCES = rtp2hls.c playlist.c

# list of headers we're not going to install
noinst_HEADERS = playlist.h

# our CFLAGS and LDFLAGS used for compiling and linking
# make sure you prefix these with the name of your binary
rtp2hls_CFLAGS = $(GST_CFLAGS) -I/usr/lib/x86_64-linux-gnu/gstreamer1.0/include
rtp2hls_LDFLAGS = $(GST_LIBS)
