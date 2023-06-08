from wtforms import (StringField, DateTimeLocalField)
from starlette_wtf import StarletteForm
from wtforms.validators import DataRequired
from aind_data_transfer_gui.directory_field import DirectoryField


class UploadJobForm(StarletteForm):
    experiment_type = StringField('Experiment Type',
                                  validators=[DataRequired()])
    acquisition_datetime = DateTimeLocalField("Acquisition Datetime",
                                              validators=[DataRequired()])
    modality = StringField('Modality',
                           validators=[DataRequired()])
    source = DirectoryField('Source', validators=[DataRequired()])
