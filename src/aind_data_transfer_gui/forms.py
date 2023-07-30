"""Defines GUI Forms."""

import json

from aind_data_schema.data_description import ExperimentType, Modality
from starlette_wtf import StarletteForm
from wtforms import (
    DateTimeLocalField,
    FieldList,
    Form,
    FormField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired

experiment_type_choices = [
    (experiment_type.name, experiment_type.value)
    for experiment_type in ExperimentType
]

modality_choices = [
    (modality.name, modality.value.name) for modality in Modality
]


class ModalityForm(Form):
    modality = SelectField(
        "Modality", choices=modality_choices, validators=[DataRequired()]
    )
    source = StringField("Source", validators=[DataRequired()])


class JobManifestForm(StarletteForm):
    """Form to add a new upload job."""
    jobs = []
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
    add_job = SubmitField("add_job")
    add_modality = SubmitField("add_modality")
    submit_jobs = SubmitField("submit_jobs")

    def to_job_string(self):
        return json.dumps(
            {
                "experiment_type": self.data.get("experiment_type"),
                "acquisition_datetime": self.data.get("acquisition_datetime"),
                "modalities": self.data.get("modalities"),
            },
            default=str,
        )
