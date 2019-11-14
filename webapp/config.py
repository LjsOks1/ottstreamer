import os
class Config(object):
    STREAMS_ROOT="/ddrive/streams"
    SECRET_KEY=os.environ.get('SECRET_KEY') or 'secretkey'
    CHANNELS=[{'name':'Comedy Central Family Poland', 'code':'ccfpol', 'stream':'udp://239.211.8.105:1234'},
             {'name':'MTV Music 24','code':'mtvmusic24','stream':'udp://239.211.8.112:1234'},
            {'name':'Nickelodeon HD','code':'nickhd','stream':'udp://239.211.8.123:1234'},
            {'name':'Nick Hungary','code':'nickhun','stream':'udp://239.211.8.124:1234'},
            {'name':'Nick Romania','code':'nickrom','stream':'udp://239.211.8.126:1234'},
            {'name':'Nicktoons Poland','code':'nicktoonspol','stream':'udp://239.211.8.127:1234'},
            {'name':'RTL Spike','code':'rtlspike','stream':'udp://239.211.8.132:1234'},
        ]
    BASE_URI="http://129.228.120.86/streams"
    UPLOAD_FOLDER='/home/lajos/projects/ottstreamer/webapp/'
    LOCALIZER_ROOT='/ddrive/ottstreamer/playlistlocalizer'
    MEDIA_FOLDER="/mnt/operations/Operations/"
    CACHE_FOLDER="/ddrive/commercials"
    TEST_FOLDER="/ddrive/streams/test"
    TEST_URL="http://129.228.120.86/streams/test/"
    LOCALIZED_FEEDS=[
        {"name":"Nick Hungary",
         "log":"nickelodeon_HUN",
         "dir":"nick_hun",
         "xls":"/mnt/fs_operations/04\040Nickelodeon/Nickelodeon\040Hungary/Schedule"},
        {"name":"Nick Romania",
         "log":"nickelodeonro",
         "dir":"nick_rom",
         "xls":"/mnt/fs_operations/04\040Nickelodeon/Nickelodeon\040Romania/"},
        {"name":"Nick Czech",
         "log":"nickelodeoncze",
         "dir":"nick_cze",
         "xls":"/mnt/fs_operations/04\040Nickelodeon/Nickelodeon\040Czech/"},
        {"name":"Nick Bulgaria",
         "log":"nickelodeon_BUL",
         "dir":"nick_bul",
         "xls":"/mnt/fs_operations/04\040Nickelodeon/Nickelodeon\040Bulgaria/"},
        {"name":"NickJR Hungary",
         "log":"nickjrhu",
         "dir":"nickjr_hun",
         "xls":"/mnt/fs_operations/10\040Nick\040Jr/Nick\040Jr\040HUN/"},
        {"name":"NickJR Romania",
         "log":"nickjrro",
         "dir":"nickjr_rom",
         "xls":"/mnt/fs_operations/10\040Nick\040Jr/Nick\040Jr\040RO/"},
        {"name":"NickJR Czech",
         "log":"nickjrcz",
         "dir":"nickjr_cze",
         "xls":"/mnt/fs_operations/10\040Nick\040Jr/Nick\040Jr\040CZ/"},
        {"name":"NickJR Bulgaria",
         "log":"nickjrbul",
         "dir":"nickjr_bul",
         "xls":"/mnt/fs_operations/10\040Nick\040Jr/Nick\040Jr\040BUL/"},
        {"name":"Nicktoons Hungary",
         "log":"Nicktoons_Hungary",
         "dir":"nicktoons_hun",
         "xls":"/mnt/fs_operations/12\040Nicktoons/Nicktoons\040HU\040Schedule"},
        {"name":"Nicktoons Romania",
         "log":"nicktoonsro",
         "dir":"nicktoons_rom",
         "xls":"/mnt/fs_operations/12\040Nicktoons/Nicktoons\040RO\040Schedule/Schedule"},
        {"name":"Nicktoons Czech",
         "log":"nicktoonscz",
         "dir":"nicktoons_cze",
         "xls":"/mnt/fs_operations/12\040Nicktoons/Nicktoons\040CZ\040Schedule"},
        {"name":"Nicktoons Bulgaria",
         "log":"Nicktoons_Bulgaria",
         "dir":"nicktoons_bul",
         "xls":"/mnt/fs_operations/12\040Nicktoons/Nicktoons\040BG\040Schedule"}]

