"""Starts and Runs Starlette Service"""
import logging
import os

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

logging.basicConfig(level=logging.INFO)

from aind_data_transfer_gui.forms import JobManifestForm

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)


@csrf_protect
async def index(request):
    """GET|POST /: form handler"""
    job_manifest_form = await JobManifestForm.from_formdata(request)

    if job_manifest_form.is_submitted():
        add_modality = job_manifest_form.data.get("add_modality")
        add_job = job_manifest_form.data.get("add_job")
        submit_jobs = job_manifest_form.data.get("submit_jobs")

        if add_modality:
            job_manifest_form.modalities.append_entry()

        if add_job:
            if await job_manifest_form.validate():
                job_manifest_form.jobs.append(job_manifest_form.to_job_string())

        if submit_jobs:
            if await job_manifest_form.validate():
                logging.info(f"Will send the following to the HPC: {job_manifest_form.jobs}")

    return templates.TemplateResponse(
        name="jobs.html",
        context=({"request": request, "form": job_manifest_form}),
    )


routes = [Route("/", endpoint=index, methods=["GET", "POST"])]

app = Starlette(routes=routes)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
