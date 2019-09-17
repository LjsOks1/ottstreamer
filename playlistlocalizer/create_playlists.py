import pandas
import sys
import m3u8
import os

df=pandas.read_excel(sys.argv[1])
base_uri=sys.argv[2]
dst_file=sys.argv[3]
playlist_id=0
for index,row in df.iterrows():
    if playlist_id!=row['Break Number']:
        if playlist_id>0:
            brk_playlist.dump(os.path.join(dst_file,"brk_{:04d}.m3u8".format(playlist_id)))
        brk_playlist=m3u8.M3U8()
        playlist_id=row['Break Number']
    brk_playlist.add_segment(m3u8.model.Segment(
        uri=os.path.join(base_uri,row['Cart Number']+".ts"),
        title=row['Title'],
        duration=row['Duartion WORK'],
        discontinuity=True,
        base_uri=""))
brk_playlist.dump(os.path.join(dst_file,"brk_{:04d}.m3u8".format(playlist_id)))

