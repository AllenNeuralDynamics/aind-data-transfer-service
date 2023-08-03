"""Starts and Runs Starlette Service"""
import os

from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
from starlette.routing import Route
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
import csv
import io

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
    return templates.TemplateResponse("index.html", {"request": request, "json_data": ""})


@app.post("/upload/")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    """POST /: csv handler"""
    try:
        content = await file.read()
        data = content.decode("utf-8")

        csv_data = []
        csv_reader = csv.DictReader(io.StringIO(data))
        for row in csv_reader:
            csv_data.append(row)

        return templates.TemplateResponse(
            name="index.html",
            context=({"request": request, "csv_data": csv_data}),
        )

    except Exception as e:
        return JSONResponse(content={"error": f"Error processing CSV: {e}"}, status_code=400)

app = FastAPI()
app.routes.append(Route("/", index, methods=["GET"]))
app.routes.append(Route("/upload/", upload_csv, methods=["POST"]))
