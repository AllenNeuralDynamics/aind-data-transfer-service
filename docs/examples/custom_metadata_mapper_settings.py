"""
This example demonstrates how to pass in custom job_settings into the metadata
mapper package. It assumes a user has pip installed the aind-metadata-mapper
package. If there are dependency conflicts it may also be possible to use raw
dictionaries.
"""

from datetime import datetime

import requests
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_metadata_mapper.bergamo.models import (
    JobSettings as BergamoSessionSettings,
)
from aind_metadata_mapper.models import (
    JobSettings as GatherMetadataJobSettings,
)
from aind_metadata_mapper.models import SessionSettings

from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
)

# This job_type contains the default settings for compression and Code Ocean
# pipelines. We recommend creating a custom one for your experiments. Reach
# out to Scientific Computing for more information.
job_type = "default"

# acq_datetime = datetime(2025, 4, 25, 16, 41, 23)
acq_datetime = datetime(2020, 4, 25, 16, 41, 0)

# Compression settings. As job_type default, no compression will be performed.
pophys_task = Task(
    job_settings={
        "input_source": (
            "/allen/aind/scratch/svc_aind_upload/test_data_sets/bci/"
            "042525/042525/pophys"
        )
    }
)

modality_transformation_settings = {"pophys": pophys_task}

# 1. Define the JobSettings for the GatherMetadataJob in aind-metadata-mapper
bergamo_session_settings = BergamoSessionSettings(
    input_source=(
        "/allen/aind/scratch/svc_aind_upload/test_data_sets/bci/"
        "042525/042525/pophys"
    ),
    experimenter_full_name=["John Apple"],
    subject_id="784746",
    imaging_laser_wavelength=920,
    fov_imaging_depth=100,
    fov_targeted_structure="Primary Motor Cortex",
    notes="test upload",
)

# 2. Define SessionSettings object with defined job settings
session_settings = SessionSettings(job_settings=bergamo_session_settings)

# 3. Define GatherMetadataJobSettings with session_settings.
# %OUTPUT_LOCATION is a special string that will be replaced by the service
# with the correct staging location.
metadata_job_settings = GatherMetadataJobSettings(
    directory_to_write_to="%OUTPUT_LOCATION",
    session_settings=session_settings,
    metadata_dir=(
        "/allen/aind/scratch/svc_aind_upload/test_data_sets/bci/042525/042525"
    ),
)

gather_preliminary_metadata = Task(
    job_settings=metadata_job_settings.model_dump(
        mode="json", exclude_none=True
    )
)


upload_job_configs_v2 = UploadJobConfigsV2(
    job_type=job_type,
    project_name="Brain Computer Interface",
    platform=Platform.SINGLE_PLANE_OPHYS,
    modalities=[Modality.POPHYS],
    subject_id="784746",
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
