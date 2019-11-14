

# Install gstreamer-1.0 (As of now Buster comes with gstreamer-1.14.4)

Let's have git first if we don't have it so far...
'''sudo apt-get install git'''

Install all the gstreamer modules we need.
'''sudo apt-get install libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio'''

Add the dev package for the base plugins.
'''sudo apt-get install libgstreamer-plugins-base1.0-dev'''

********* gst-plugin-bad *****************

'''git clone https://github.com/GStreamer/gst-plugins-bad.git
cd gst-plugins-bad
git checkout tags/1.14.4
git checkout tags/1.16.0 gst/mpegtsmux
git checkout tags/1.16.0 gst/mpegtsdemux
./autogen.sh --disable-gtk-doc'''

Checkout ottstreamer and apply patches to gstreamer bad and good plugins
'''cd ~/projects
git clone https://github.com/LjsOks1/ottstreamer.git
cp ottstreamer/gstreamer-patches/patchfiles/gst-plugins-bad-1.14.4.patch gst-plugins-bad'''

Go back to the root of gst-plugins-bad, check if patch applies without error.
'''patch -p 1 --dry-run < gst-plugins-bad-1.14.4.patch'''

If looks good, apply the patch.
'''patch -p 1 < gst-plugins-bad-1.14.4.patch'''

Than compile and install the modules...
'''cd gst-lib/gst/mpegts
make
sudo cp .libs/libgstmpegts-1.0.so.0 /usr/lib/x86_64-linux-gnu/
cd gst-libs/gst/codecparsers
make
sudo cp .libs/libgstcodecparsers-1.0.so.0 /usr/lib/x86_64-linux-gnu/
cd gst/mpegtsmux
make
sudo cp .libs/libgstmpegtsmux.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0/
cd gst/mpegtsdemux
make
 sudo cp .libs/libgstmpegtsdemux.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0/'''

 ********* gst-plugin-good *****************

 git clone https://github.com/GStreamer/gst-plugins-good.git
 cd gst-plugins-good
 git checkout tags/1.14.4
 ./autogen.sh --disable-gtk-doc

 Go back to the root of gst-plugins-good, check if patch applies without error.
 patch -p 1 --dry-run < gst-plugins-good-1.14.4.patch

 If looks good, apply the patch.
 patch -p 1 < gst-plugins-good-1.14.4.patch

 cd gst/rtp
 make
 sudo cp .libs/libgstrtp.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0/
