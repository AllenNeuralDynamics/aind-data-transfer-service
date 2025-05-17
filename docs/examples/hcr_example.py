"""This example demonstrates how to submit an HCR job."""

from datetime import datetime

import requests
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
)

job_type = "HCR"

acq_datetime = datetime(2025, 3, 10, 12, 0, 9)

num_of_partitions: int = 4

# Add custom job_settings for the hcr image python command.
spim_task = Task(
    image_resources={"array": f"0-{num_of_partitions - 1}"},
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "HCR_772646_2025-03-10_12-00-00"
        ),
        "num_of_partitions": num_of_partitions,
    },
)

modality_settings = {
    Modality.SPIM.abbreviation: spim_task,
}

gather_preliminary_metadata = Task(
    job_settings={
        "metadata_dir": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "HCR_772646_2025-03-10_12-00-00"
        )
    }
)

# The job_type loads defaults settings from AWS Parameter Store
upload_job_configs_v2 = UploadJobConfigsV2(
    job_type=job_type,
    s3_bucket="open",
    project_name="MSMA Platform",
    platform=Platform.HCR,
    modalities=[Modality.SPIM],
    subject_id="772646",
    acq_datetime=acq_datetime,
    tasks={
        "modality_transformation_settings": modality_settings,
        "gather_preliminary_metadata": gather_preliminary_metadata,
    },
)

upload_jobs = [upload_job_configs_v2]

submit_request = SubmitJobRequestV2(
    upload_jobs=upload_jobs,
)

post_request_content = submit_request.model_dump(
    mode="json", exclude_none=True
)

# Please use the production endpoint for submitting jobs and the dev endpoint
# for running tests.
# endpoint = "http://aind-data-transfer-service"
endpoint = "http://aind-data-transfer-service-dev"  # For testing

submit_job_response = requests.post(
    url=f"{endpoint}/api/v2/submit_jobs",
    json=post_request_content,
)
print(submit_job_response.status_code)
print(submit_job_response.json())
