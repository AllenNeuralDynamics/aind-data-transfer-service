"""Starts and Runs Starlette Service"""

import os

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_gui.forms import UploadJobForm
from aind_data_transfer_gui.templates.index import template

SECRET_KEY = os.urandom(32)
CSRF_SECRET_KEY = os.urandom(32)

app = Starlette(
    middleware=[
        Middleware(SessionMiddleware, secret_key=SECRET_KEY),
        Middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY),
    ]
)


@app.route("/", methods=["GET", "POST"])
@csrf_protect
async def index(request):
    """GET|POST /: form handler"""
    form = await UploadJobForm.from_formdata(request)

    if await form.validate_on_submit():
        return PlainTextResponse("SUCCESS")

    html = template.render(form=form)
    return HTMLResponse(html)
