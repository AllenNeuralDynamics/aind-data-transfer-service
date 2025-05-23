"""
This example demonstrates how to set custom configs for the code ocean
pipeline monitor capsule. It is recommended to specify a job_type to set the
code ocean settings.
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
job_type = "default"

acq_datetime = datetime(2023, 4, 3, 18, 17, 7)

# As default, compression won't be run.
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

# For extra validation on the pipeline_monitor_settings field, you can import
# the pydantic model by pip installing aind-codeocean-pipeline-monitor
# and importing aind_codeocean_pipeline_monitor.models.PipelineMonitorSettings.
# We provide a default pipeline monitor capsule id, but you can
# override it by uncommenting the pipeline_monitor_capsule_id key.
ecephys_codeocean_pipeline_settings = Task(
    skip_task=False,
    job_settings={
        # "pipeline_monitor_capsule_id": ...,
        "pipeline_monitor_settings": {
            "run_params": {
                "capsule_id": "87cbe6ce-9b38-4266-8d4a-62f0e23ba2d6",
            },
            "capture_settings": {
                "permissions": {"everyone": "viewer"},
                "tags": ["derived", "test"],
                "custom_metadata": {
                    "data level": "derived",
                },
                "process_name_suffix": "test",
            },
        },
    },
)

# You can specify one pipeline per modality:
codeocean_pipeline_settings = {"ecephys": ecephys_codeocean_pipeline_settings}


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
        "codeocean_pipeline_settings": codeocean_pipeline_settings,
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
