FROM python:3-slim
WORKDIR /app
ADD src ./src
ADD pyproject.toml .
ADD setup.py .

# Pip command. Without '-e' flag, index.html isn't found. There's probably a
# better way to add the static html files to the site-packages.
RUN pip install -e .[server] --no-cache-dir

CMD ["uvicorn", "aind_data_transfer_service.server:app", "--host", "0.0.0.0", "--port", "5000"]
