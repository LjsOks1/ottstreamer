from flask import request, render_template,flash,redirect,send_from_directory
from app import app 
import psutil
from app.forms import ChannelForm,MissingMediaForm
import os
from config import Config
import re
import traceback
import datetime
from datetime import timedelta
import pandas
import xlrd
from utils import check_for_missing_media as cmm
from utils import reload_playlist as rp
from utils import encode_nicktoons as ent 
from utils.asrun import get_commercial_log,get_segments_played

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/channels',methods=['GET'])
def channels():
    action=request.args.get('action')
    if action=='info':
        return redirect('/channels')
    elif action=='stop':        
        flash('Stopping pid {}'.format(request.args.get('pid')))
        psutil.Process(int(request.args.get('pid'))).terminate()
        return redirect('/channels')
    else:
        rtp2hls_ps=[]
        for proc in  psutil.process_iter():
            try:
                if proc.cmdline()[0] and "rtp2hls" in proc.cmdline()[0].lower():
                    p={}
                    p["pid"]=proc.pid
                    p["channel"]=proc.cmdline()[proc.cmdline().index('-c')+1]
                    p["source"]=proc.cmdline()[proc.cmdline().index('-s')+1]
                    p["baseuri"]=proc.cmdline()[proc.cmdline().index('-u')+1]
                    p["uptime"]=str(timedelta(seconds=int(datetime.datetime.now().timestamp()-
                        proc.create_time())))
                    p["manifest_age"]=str(timedelta(seconds=int(datetime.datetime.now().timestamp()-
                        os.stat(os.path.join(proc.cmdline()[proc.cmdline().index('-b')+1],
                        p["channel"],"playlist.m3u8")).st_mtime)))
                    rtp2hls_ps.append(p)
            except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,IndexError):
                pass
        form = ChannelForm()
        hls2rtp_ps=[]
        for proc in  psutil.process_iter():
            try:
                if proc.cmdline()[0] and "hls2rtp" in proc.cmdline()[0].lower():
                    p={}
                    p["pid"]=proc.pid
                    p["channel"]=proc.cmdline()[proc.cmdline().index('-s')+1].split('/')[-2]
                    p["source"]=proc.cmdline()[proc.cmdline().index('-s')+1]
                    p["manifest_age"]=str(timedelta(seconds=int(datetime.datetime.now().timestamp()-
                        os.stat(os.path.join("/ddrive",'/'.join(proc.cmdline()[proc.cmdline()
                        .index('-s')+1].split('/')[3:]))).st_mtime)))
                    p["multicast"]=proc.cmdline()[proc.cmdline().index('-d')+1]
                    p["uptime"]=str(timedelta(seconds=int(datetime.datetime.now().timestamp()-
                        proc.create_time())))
                    hls2rtp_ps.append(p)
            except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,IndexError):
                pass

        return render_template('channels.html',grabbers=rtp2hls_ps,hls2rtp=hls2rtp_ps,form=form)




@app.route('/channels',methods=['POST'])
def add_channel():
    form=ChannelForm()
    for proc in psutil.process_iter():
        try:
            if proc.cmdline()[3].lower()==form.channel.data:
                flash('{} is already running. Cannot start twice!'.format(form.channel.data))
                return redirect('/channels')
        except:
            pass
    flash('Starting HLS stream for {}'.format(form.channel.data))
    channel=[c for c in Config.CHANNELS if c['code']==form.channel.data]
    os.system("../rtp2hls/tests/rtp2hls.py {} {} /var/www/html/streams http://129.228.120.86/streams&".format(channel[0]['stream'],channel[0]['code']))
    return redirect('/channels')


@app.route('/clients')
def clients():
    # Logformat "%h %l %u %t %{begin:msec}t %{end:msec}t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" combined
    regex='([(\d\.)]+) - - \[(.*?)\] ([0-9]+) ([0-9]+) "(.*?)" ([0-9]+) ([0-9]+) "(.*?)" "(.*?)"'
    logs={}
    with open('/var/log/apache2/access.log','r') as infile:
        for line in infile:
            try:
                item={}
                fields=re.match(regex,line).groups()
                channel=fields[4].split('/')[2]
                item["ip"]=fields[0]
                item["time"]=fields[1]
                item["content"]=fields[4].split('/')[3]
                item["size"]=fields[6]
                item["bitrate"]="{:.2f}".format(float(int(fields[6])*8/((int(fields[3])-int(fields[2]))*1000)))
                item["result"]=fields[5]
                if ".ts" in item["content"]:
                    if channel in logs:
                        logs[channel].insert(0,item)
                    else:
                        logs[channel]=[item]
            except Exception as e:
                #traceback.print_exc()
                pass
    return render_template('clients.html',logs=logs)

@app.route('/logs')
def logs():
    missingform=MissingMediaForm()
    base = datetime.datetime.today()
    date_list = [(base + datetime.timedelta(days=x-1)).strftime("%Y-%m-%d") for x in range(6)]
    overview={}
    for c in Config.LOCALIZED_FEEDS:
        log_list=[]
        for d in date_list:
            status={}
            filename=os.path.join(Config.STREAMS_ROOT,c["dir"],"commercials","playlists",d,d+"_"+c["log"]+".xls")
            if os.path.isfile(filename):
                status["xls"]=True
                df=pandas.read_excel(filename)
                ts_ready=True
                for b in df["Break Number"].unique():
                    if not os.path.isfile(os.path.join(os.path.dirname(filename),"brk_{:02}".format(b),"playlist.m3u8")):
                        ts_ready=False
                status["ts_ready"]=ts_ready
            else:
                status["xls"]=False
                status["ts_ready"]=False
            if os.path.isfile(os.path.join(os.path.dirname(filename),".missing_files")):
                status["missing"]=[line.rstrip('\n') for line in open(os.path.join(os.path.dirname(filename),".missing_files"))]
            log_list.append(status)
            
        overview[c["name"]]=log_list                              
            
    return render_template('logs.html',channels=overview,dates=date_list,missingform=missingform,playlistform=missingform)

@app.route('/logs',methods=['POST'])
def logs_request():
    app.logger.info(request.form)
    data=request.form.to_dict()
    if data["formname"]=="missingform":
        if cmm.check_for_missing_media(data["channel"],data["txdate"]):
            flash('Missing media checked successfully for {} - {}'.format(data["channel"],data["txdate"]),'info')
        else:

            flash('Checking missing media failed for {} - {}. check the logs.'.format(data["channel"],data["txdate"]),'error')
    if data["formname"]=="playlistform":
        if rp.reload_playlist(data["channel"],data["txdate"]):
            flash('Playlist reloaded for {} - {}'.format(data["channel"],data["txdate"]),'info')
        else:
            flash('Playlist reload failed for {} - {}. check the logs.'.format(data["channel"],data["txdate"]),'error')
    if data["formname"]=="commbreak":
        job=app.encode_queue.enqueue(ent.encode_nicktoons,data["channel"],data["txdate"])
        app.logger.info("Encoding of channel {} for date {} queued.".format(data["channel"],data["txdate"]))
    return redirect('logs')

@app.route('/asrun')
def asrun():
    channel=request.args.get('channel')
    txdate=request.args.get('txdate',default=datetime.datetime.now().strftime('%Y-%m-%d'))
    channel_name=[c["name"] for c in Config.LOCALIZED_FEEDS  if c["dir"] == channel][0]
    cl=get_commercial_log(channel,txdate)
    ar,tp=get_segments_played(channel,txdate)
    asrun_log=[]
    for brk in cl:
        try:
            com_fragments=[]
            for segment in brk["segments"]:
                com_fragments.append([a["url"] for a in ar].index(segment))
            asrun_log.append('Break {} scheduled for {} is played at {} with duration:{}.'.
                  format(brk["id"],brk["starttime"],ar[com_fragments[0]]["start_wallclock"].strftime('%H:%M:%S'),
                        (ar[com_fragments[-1]]["end_wallclock"]-ar[com_fragments[0]]["start_wallclock"])))
        except:
            asrun_log.append('Break {} scheduled for {} is not played.'.format(brk["id"],brk["starttime"]))    
    slow_downloads=[]
    for a in [r for r in ar if (r["end_wallclock"]-r["start_wallclock"])>datetime.timedelta(seconds=25)]:
        if a["start_wallclock"]>datetime.datetime(2000,1,1,0,0,0):
            slow_downloads.append("{}: Downloading {} took {}sec to finish.".format(a["start_wallclock"].strftime("%Y-%m-%d %H:%M:%S"),a["url"],int((a["end_wallclock"]-a["start_wallclock"]).total_seconds())))
    long_gaps=[]
    for a in [r for r in ar if r["gap"]>datetime.timedelta(seconds=3)]:
        if a["start_wallclock"]>datetime.datetime(2000,1,1,0,0,0):
            long_gaps.append("{}: Downloading {} started after  {}sec.".format(a["start_wallclock"].strftime("%Y-%m-%d %H:%M:%S"),a["url"],int(a["gap"].total_seconds())))
    bad_packets=[]
    for a in [t for t in tp if t["Duration"]>datetime.timedelta(seconds=2)]:
        bad_packets.append("{}: tsparse sent packet with long duration:{}sec.".format(a["wallclock"].strftime("%Y-%m-%d %H:%M:%S"),a["Duration"].total_seconds()))


    return render_template('asrun.html',asrun_log=asrun_log,channel=channel_name,txdate=txdate,slow_downloads=slow_downloads,long_gaps=long_gaps,bad_packets=bad_packets)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)

