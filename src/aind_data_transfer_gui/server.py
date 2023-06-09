"""Starts and Runs Starlette Service"""

import os

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_gui.forms import UploadJobForm
from aind_data_transfer_gui.templates.index import template

SECRET_KEY = "secret key"
CSRF_SECRET_KEY = "csrf secret key"

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)


@app.route("/", methods=["GET", "POST"])
@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    form = await UploadJobForm.from_formdata(request)

    if await form.validate():
        return PlainTextResponse("SUCCESS")

    html = template.render(form=form)
    return HTMLResponse(html)
