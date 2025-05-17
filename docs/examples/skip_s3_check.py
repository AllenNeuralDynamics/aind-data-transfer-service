"""
This example demonstrates how to skip the checks on whether the s3 folder. This
is not recommended and should be used sparingly. Please ask a Data Admin to
remove the data from S3 instead.
"""

from datetime import datetime

import requests
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
)

# The job_type contains the default settings for compression and Code Ocean
# pipelines.
job_type = "ecephys"

acq_datetime = datetime(2023, 4, 3, 18, 17, 7)

ecephys_task = Task(
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "ecephys/655019_2023-04-03_18-17-07"
        )
    }
)

modality_transformation_settings = {"ecephys": ecephys_task}

gather_preliminary_metadata = Task(
    job_settings={
        "metadata_dir": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "ecephys/655019_2023-04-03_18-17-07"
        )
    }
)

upload_job_configs_v2 = UploadJobConfigsV2(
    job_type=job_type,
    project_name="Ephys Platform",
    platform=Platform.ECEPHYS,
    modalities=[Modality.ECEPHYS],
    subject_id="655019",
    acq_datetime=acq_datetime,
    tasks={
        "modality_transformation_settings": modality_transformation_settings,
        "check_s3_folder_exists": {"skip_task": True},
        "final_check_s3_folder_exist": {"skip_task": True},
        "gather_preliminary_metadata": gather_preliminary_metadata,
    },
)

submit_request_v2 = SubmitJobRequestV2(
    upload_jobs=[upload_job_configs_v2],
)

post_request_content = submit_request_v2.model_dump(
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
