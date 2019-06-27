import os
class Config(object):
    SECRET_KEY=os.environ.get('SECRET_KEY') or 'secretkey'
    CHANNELS=[{'name':'Comedy Central Family Poland', 'code':'ccfpol', 'stream':'udp://239.211.8.105:1234'},
             {'name':'MTV Music 24','code':'mtvmusic24','stream':'udp://239.211.8.112:1234'},
            {'name':'Nickelodeon HD','code':'nickhd','stream':'udp://239.211.8.123:1234'},
            {'name':'Nick Hungary','code':'nickhun','stream':'udp://239.211.8.124:1234'},
            {'name':'Nick Romania','code':'nickrom','stream':'udp://239.211.8.126:1234'},
            {'name':'Nicktoons Poland','code':'nicktoonspol','stream':'udp://239.211.8.127:1234'},
            {'name':'RTL Spike','code':'rtlspike','stream':'udp://239.211.8.132:1234'},
        ]
    UPLOAD_FOLDER='/home/lajos/projects/ottstreamer/webapp/'

