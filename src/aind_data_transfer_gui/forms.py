from flask_wtf import FlaskForm
from wtforms import (StringField, DateTimeLocalField, FileField)
from wtforms.validators import InputRequired


class UploadJobForm(FlaskForm):
    experiment_type = StringField('Experiment Type',
                                  validators=[InputRequired()])
    acquisition_datetime = DateTimeLocalField("Acquisition Datetime",
                                         validators=[InputRequired()])
    modality = StringField('Modality',
                           validators=[InputRequired()])
    source = FileField('Source', validators=[InputRequired()])
