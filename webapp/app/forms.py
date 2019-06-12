from flask_wtf import FlaskForm
from wtforms import SelectField,SubmitField
from wtforms.validators import DataRequired
from config import Config

class ChannelForm(FlaskForm):
    channel=SelectField('Channel to start',
    choices=[(c['code'],c['name']+' ('+c['stream']+')')   for c in Config.CHANNELS ])
    submit=SubmitField('Start')



