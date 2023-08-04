"""Defines GUI Forms."""

from starlette_wtf import StarletteForm
from wtforms import (
    SubmitField,
    FileField
)


class JobManifestForm(StarletteForm):
    """Form to add a new upload job."""
    upload_csv = FileField("upload_csv")
    submit_jobs = SubmitField("submit_jobs")

