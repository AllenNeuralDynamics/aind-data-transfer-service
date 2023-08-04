"""Starts and Runs Starlette Service"""
import csv
import io
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from aind_data_transfer_service.forms import JobManifestForm
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
import logging

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

app = FastAPI()
template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)


@csrf_protect
@app.route("/", methods=["GET", "POST"])
async def index(request: Request):
    """GET|POST /: form handler"""
    job_manifest_form = await JobManifestForm.from_formdata(request)
    csv_data = []
    if job_manifest_form.is_submitted():
        upload_csv = job_manifest_form.data.get("upload_csv")
        submit_jobs = job_manifest_form.data.get("submit_jobs")

        if upload_csv:
            file = job_manifest_form["upload_csv"].data
            content = await file.read()
            data = content.decode("utf-8")

            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                csv_data.append(row)

        if submit_jobs:
            if csv_data:
                logging.info(f"Will send the following to the HPC: {csv_data}")
                return JSONResponse(
                    content={"message": f"Successfully submitted job.",
                             "data": csv_data},
                    status_code=200,
                )
            else:
                return JSONResponse(
                    content={"error": "Error collecting csv data."},
                    status_code=400,
                )

    return templates.TemplateResponse(
        name="index.html",
        context=({"request": request, "form": job_manifest_form, "csv_data": csv_data}),
    )

