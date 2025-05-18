"""
This example demonstrates how to set custom Slurm settings to request
additional time for the compression step and additional memory.
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

# If a job is special and requires more slurm resources, then they can be
# defined here. For extra validation, you can pip install aind-slurm-rest-v2
# and import it as:
# from aind_slurm_rest_v2.models.v0040_job_desc_msg import V0040JobDescMsg

ecephys_task = Task(
    image_resources={
        "memory_per_cpu": {"set": True, "number": 6000},  # In MB
        "minimum_cpus_per_node": 6,
        "time_limit": {"set": True, "number": 240},  # In minutes
    },
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/"
            "ecephys/655019_2023-04-03_18-17-07"
        )
    },
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
