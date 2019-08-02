from flask import request, render_template,flash,redirect,send_from_directory
from app import app 
import psutil
from app.forms import ChannelForm
import os
from config import Config
import re
import traceback

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
        grabber={}
        for proc in  psutil.process_iter():
            try:
                if proc.cmdline()[1] and "rtp2hls" in proc.cmdline()[1].lower():
                    grabber[proc.pid]=proc.cmdline()
            except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,IndexError):
                pass
        form = ChannelForm()
        return render_template('channels.html',grabbers=[grabber],form=form)




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

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)

