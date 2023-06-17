"""Starts and Runs Starlette Service"""

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_gui.forms import UploadJobForm
from fastapi.templating import Jinja2Templates

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

app = FastAPI()
templates = Jinja2Templates(directory="src/aind_data_transfer_gui/templates")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)

jobs = []


@app.route("/", methods=["GET", "POST"])
@csrf_protect
async def index(request: Request):
    form = await UploadJobForm.from_formdata(request)
    if await form.validate():
        job = {
            "source": form.source.data,
            "experiment_type": form.experiment_type.data,
            "acquisition_datetime": form.acquisition_datetime.data,
            "modality": form.modality.data,
        }
        jobs.append(job)
        return templates.TemplateResponse("jobs.html", {"request": request, "jobs": jobs, "form": form})
    else:
        # Handle form validation errors
        return templates.TemplateResponse("jobs.html", {"request": request, "jobs": jobs, "form": form})

