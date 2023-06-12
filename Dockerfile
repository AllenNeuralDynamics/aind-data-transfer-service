FROM python:3-slim
WORKDIR /app
ADD src ./src
ADD pyproject.toml .
ADD setup.py .

# Pip command
RUN pip install . --no-cache-dir

CMD ["uvicorn", "aind_data_transfer_gui.server:app", "--host", "0.0.0.0", "--port", "5000"]
