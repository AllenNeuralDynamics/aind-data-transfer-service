"""Defines GUI Forms."""

from aind_data_schema.data_description import ExperimentType, Modality
from starlette_wtf import StarletteForm
from wtforms import DateTimeLocalField, SelectField, StringField, FieldList, FormField
from wtforms.validators import DataRequired

experiment_type_choices = [
    (experiment_type.name, experiment_type.value)
    for experiment_type in ExperimentType
]
modality_choices = [
    (modality.name, modality.value.name) for modality in Modality
]


class SourceModalityPair(StarletteForm):
    """Form to represent a pair of source and modality."""

    modality = SelectField(
        "Modality", choices=modality_choices, validators=[DataRequired()]
    )
    source = StringField("Source", validators=[DataRequired()])


class UploadJobForm(StarletteForm):
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
    # modality = SelectField(
    #     "Modality", choices=modality_choices, validators=[DataRequired()]
    # )
    # source = StringField("Source", validators=[DataRequired()])
    upload_pairs = FieldList(FormField(SourceModalityPair))


class SubmitJobsForm(StarletteForm):
    """Form to submit multiple upload jobs."""

    jobs = []
