# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired

class CarbonTrackerForm(FlaskForm):
    #city field
    city = StringField('City', validators=[DataRequired()])
    # Transportation fields
    transport_distance = FloatField('Distance (km)', validators=[DataRequired()])
    mode_of_transport = StringField('Mode of Transport', validators=[DataRequired()])

    # Electricity fields
    previous_month_usage = FloatField('Previous Month Usage (kWh)', validators=[DataRequired()])
    todays_usage = FloatField('Today\'s Usage (kWh)', validators=[DataRequired()])

    # Waste fields
    dry_waste = FloatField('Dry Waste (kg)', validators=[DataRequired()])
    wet_waste = FloatField('Wet Waste (kg)', validators=[DataRequired()])

    submit = SubmitField('Calculate Carbon Footprint')



    
