"""Starts and Runs Starlette Service"""
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_gui.forms import UploadJobForm
from aind_data_transfer_gui.jobs_manager import ManageJobsDatabase

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

app = FastAPI()
template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
app.jobs_db = ManageJobsDatabase()


@app.route("/", methods=["GET", "POST"])
@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    form = await UploadJobForm.from_formdata(request)
    if await form.validate():
        job = {
            "source": form.source.data,
            "experiment_type": form.experiment_type.data,
            "acquisition_datetime": form.acquisition_datetime.data,
            "modality": form.modality.data,
        }
        app.jobs_db.insert_job(job)

    jobs = app.jobs_db.retrieve_all_jobs()

    return templates.TemplateResponse(
        "jobs.html", {"request": request, "jobs": jobs, "form": form}
    )
