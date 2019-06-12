from flask import request, render_template,flash,redirect,send_from_directory
from app import app 
import psutil
from app.forms import ChannelForm
import os
from config import Config

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
    print(form.channel.data)
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
    return render_template('clients.html')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)

