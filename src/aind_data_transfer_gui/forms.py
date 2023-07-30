"""Defines GUI Forms."""

from aind_data_schema.data_description import ExperimentType, Modality
from starlette_wtf import StarletteForm
from wtforms import Form
from wtforms import DateTimeLocalField, SelectField, StringField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired

experiment_type_choices = [
    (experiment_type.name, experiment_type.value)
    for experiment_type in ExperimentType
]

modality_choices = [
    (modality.name, modality.value.name) for modality in Modality
]


class JobListForm(Form):
    jobs = []


class ModalityForm(Form):
    modality = SelectField(
        "Modality", choices=modality_choices, validators=[DataRequired()]
    )
    source = StringField("Source", validators=[DataRequired()])


class JobManifestForm(StarletteForm):
    """Form to add a new upload job."""

    experiment_type = SelectField(
        "Experiment Type",
        choices=experiment_type_choices,
        validators=[DataRequired()],
    )
    acquisition_datetime = DateTimeLocalField(
        "Acquisition Datetime",
        validators=[DataRequired()],
        format="%Y-%m-%dT%H:%M",
    )
    modalities = FieldList(FormField(ModalityForm), min_entries=1)
    add_modality = SubmitField('add_modality')
    submit_jobs = SubmitField('submit_jobs')
