"""
This example demonstrates how to set custom Slurm settings to request
additional time for the compression step and additional memory.
"""

import json
import requests

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from datetime import datetime

from aind_data_transfer_service.models.core import (
    Task,
    UploadJobConfigsV2,
    SubmitJobRequestV2,
)

# The job_type contains the default settings for compression and Code Ocean
# pipelines.
job_type = "ecephys"

# If a job is special and requires more slurm resources, then they can be
# defined here. For extra validation, you can pip install aind-slurm-rest-v2
# and import it as:
# from aind_slurm_rest_v2.models.v0040_job_desc_msg import V0040JobDescMsg

ecephys_task = Task(
    image_resources={
        "memory_per_cpu": {"set": True, "number": 2000},  # In MB
        "minimum_cpus_per_node": 4,
        "time_limit": {"set": True, "number": 240},  # In minutes
    },
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "ecephys/ecephys_618197_2022-06-21_14-08-06"
        )
    },
)

modality_transformation_settings = {"ecephys": ecephys_task}

gather_preliminary_metadata = Task(
    job_settings={
        "metadata_dir": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "ecephys/ecephys_618197_2022-06-21_14-08-06"
        )
    }
)


upload_job_configs_v2 = UploadJobConfigsV2(
    job_type=job_type,
    project_name="Ephys Platform",
    platform=Platform.ECEPHYS,
    modalities=[Modality.ECEPHYS],
    subject_id="655019",
    acq_datetime=datetime(2022, 6, 21, 14, 8, 6),
    tasks={
        "modality_transformation_settings": modality_transformation_settings,
        "gather_preliminary_metadata": gather_preliminary_metadata,
    },
)

submit_request_v2 = SubmitJobRequestV2(
    upload_jobs=[upload_job_configs_v2],
)

post_request_content = submit_request_v2.model_dump(
    mode="json", exclude_none=True
)
# Please use the production endpoint for submitting jobs.
# This is the dev endpoint for testing.
submit_job_response = requests.post(
    url="http://aind-data-transfer-service-dev/api/v2/submit_jobs",
    json=post_request_content,
)
print(submit_job_response.status_code)
print(submit_job_response.json())
