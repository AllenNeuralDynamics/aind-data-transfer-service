from wtforms import (StringField, DateTimeLocalField, FileField)
from starlette_wtf import StarletteForm
from wtforms.validators import DataRequired


class UploadJobForm(StarletteForm):
    experiment_type = StringField('Experiment Type',
                                  validators=[DataRequired()])
    acquisition_datetime = DateTimeLocalField("Acquisition Datetime",
                                              validators=[DataRequired()])
    modality = StringField('Modality',
                           validators=[DataRequired()])
    source = FileField('Source', validators=[DataRequired()])
