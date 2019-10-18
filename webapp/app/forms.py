from flask_wtf import FlaskForm
from wtforms import SelectField,SubmitField,HiddenField
from wtforms.validators import DataRequired
from config import Config

class ChannelForm(FlaskForm):
    channel=SelectField('Channel to start',
    choices=[(c['code'],c['name']+' ('+c['stream']+')')   for c in Config.CHANNELS ])
    submit=SubmitField('Start')

class MissingMediaForm(FlaskForm):
    channel=HiddenField('channel')
    txdate=HiddenField('txdate')
    formname=HiddenField('formname')
    submit=SubmitField('Check again...')

