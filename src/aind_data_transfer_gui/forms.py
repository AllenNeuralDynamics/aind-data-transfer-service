"""Defines GUI Forms."""

from wtforms import (DateTimeLocalField, SelectField)
from starlette_wtf import StarletteForm
from wtforms.validators import DataRequired
from aind_data_transfer_gui.directory_field import DirectoryField
from aind_data_schema.data_description import Modality, ExperimentType

experiment_type_choices = [(experiment_type.name, experiment_type.value) for experiment_type in ExperimentType]
modality_choices = [(modality.name, modality.value.name) for modality in Modality]


class UploadJobForm(StarletteForm):
    experiment_type = SelectField('Experiment Type',
                                  choices=experiment_type_choices,
                                  validators=[DataRequired()]
                                  )
    acquisition_datetime = DateTimeLocalField("Acquisition Datetime",
                                              validators=[DataRequired()])
    modality = SelectField('Modality',
                           choices=modality_choices,
                           validators=[DataRequired()])
    source = DirectoryField('Source', validators=[DataRequired()])
