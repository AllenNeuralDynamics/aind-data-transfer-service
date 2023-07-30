"""Starts and Runs Starlette Service"""
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
import logging
from starlette.applications import Starlette
from starlette.routing import Route

from aind_data_transfer_gui.forms import (
    JobManifestForm,
)

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

# app = FastAPI()
template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)

# app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


# @app.route("/", methods=["GET", "POST"])
@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    job_manifest_form = await JobManifestForm.from_formdata(request)
    logging.warning("STARTING")
    if await job_manifest_form.validate() and job_manifest_form.data.get("add_modality"):
        logging.warning(f"M: {job_manifest_form.data}")
    if await job_manifest_form.validate() and job_manifest_form.data.get("submit_jobs"):
        logging.warning(f"J: {job_manifest_form.data}")
    logging.warning("OUTSIDE IF")
    return templates.TemplateResponse(
        name="jobs.html",
        context=(
            {"request": request,
             "form": job_manifest_form
             }
        ),
    )


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"])
]

app = Starlette(routes=routes)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
