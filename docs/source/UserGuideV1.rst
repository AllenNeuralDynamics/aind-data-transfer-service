User Guide V1
=============

We recommend using V2 and referencing the User Guide V2 documentation. We will
be deprecating the V1 endpoint in a future release.

Thank you for using ``aind-data-transfer-service``! This guide is
intended for scientists and engineers in AIND that wish to upload data
from our shared network drives (e.g., VAST) to the cloud.

Prerequisites
-------------

-  It's assumed that raw data is already stored and organized on a
   shared network drive such as VAST.
-  The raw data should be organized by modality.

   -  Example 1:

      .. code:: bash

         - /allen/aind/scratch/working_group/session_123456_2024-06-19
           - /ecephys_data
           - /behavior_data
           - /behavior_videos
           - /aind_metadata

   -  Example 2:

      .. code:: bash

         - /allen/aind/scratch/ecephys_data/session_123456_2024-06-19
         - /allen/aind/scratch/behavior_data/session_123456_2024-06-19
         - /allen/aind/scratch/behavior_videos/session_123456_2024-06-19
         - /allen/aind/scratch/aind_metadata/session_123456_2024-06-19

-  The different modalities should not be nested

Using the web portal
--------------------

Access to the web portal is available only through the VPN. The web
portal can accessed at
`http://aind-data-transfer-service/ <http://aind-data-transfer-service>`__

-  Download the excel template file by clicking the
   ``Job Submit Template`` link.

-  If there are compatibility issues with the excel template, you can
   try saving it as a csv file and modifying the csv file

-  Create one row per data acquisition session

-  Required fields

   -  project_name: A list of project names can be seen by clicking the
      ``Project Names`` link
   -  subject_id: The LabTracks ID of the mouse
   -  acq_datetime: The date and time the data was acquired. Should be
      in ISO format, for example, 2024-05-27T16:07:59
   -  platform: Standardized way of collecting and processing data
      (chosen from drop down menu)
   -  **modalities**: Two columns must be added per modality. A
      **modality** (chosen from drop down menu) and a Posix style path
      to the data source. For example,

      -  modality0 (e.g., ecephys)
      -  modaltity0.input_source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/ecephys_data)
      -  modality1 (e.g, behavior)
      -  modality1.input_source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/behavior_data)
      -  modality2 (e.g, behavior_videos)
      -  modality2.input_source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/behavior_videos)

-  Optional fields

   -  job_type: We store pre-compiled default configurations in AWS Parameter
      Store (e.g. modality transformation settings, Code Ocean pipeline
      settings). If you set this field, then we will use this preset when
      running the upload job. A list of job types can be seen by clicking the
      ``Job Parameters`` link.
   -  metadata_dir: If metadata files are pre-compiled and saved to a
      directory, you can add the Posix style path to the directory under
      this column
   -  s3_bucket: As default, data will be uploaded to a default bucket
      in S3 managed by AIND. Please reach out to the Scientific
      Computing department if you wish to upload to a different bucket.

Using the REST API
------------------

For more granular configuration, jobs can be submitted via a REST API at the
endpoint:

``http://aind-data-transfer-service/api/v1/submit_jobs``

.. code-block:: python

  from aind_data_transfer_service.configs.job_configs import ModalityConfigs, BasicUploadJobConfigs
  from pathlib import PurePosixPath
  import json
  import requests

  from aind_data_transfer_models.core import ModalityConfigs, BasicUploadJobConfigs, SubmitJobRequest
  from aind_data_schema_models.modalities import Modality
  from aind_data_schema_models.platforms import Platform
  from datetime import datetime

  source_dir = PurePosixPath("/shared_drive/vr_foraging/690165/20240219T112517")

  s3_bucket = "private"
  subject_id = "690165"
  acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
  platform = Platform.BEHAVIOR

  behavior_config = ModalityConfigs(modality=Modality.BEHAVIOR, source=(source_dir / "Behavior"))
  behavior_videos_config = ModalityConfigs(modality=Modality.BEHAVIOR_VIDEOS, source=(source_dir / "Behavior videos"))
  metadata_dir = source_dir / "Config"  # This is an optional folder of pre-compiled metadata json files
  project_name = "Ephys Platform"

  upload_job_configs = BasicUploadJobConfigs(
    project_name=project_name,
    s3_bucket=s3_bucket,
    platform=platform,
    subject_id=subject_id,
    acq_datetime=acq_datetime,
    modalities=[behavior_config, behavior_videos_config],
    metadata_dir=metadata_dir
  )

  # Add more to the list if needed
  upload_jobs = [upload_job_configs]

  # Optional email address and notification types if desired
  user_email = "my_email_address"
  email_notification_types = ["fail"]
  submit_request = SubmitJobRequest(
    upload_jobs=upload_jobs,
    user_email=user_email,
    email_notification_types=email_notification_types,
  )

  post_request_content = json.loads(submit_request.model_dump_json(exclude_none=True))
  # Optionally validate the submit_request before submitting
  validate_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/validate_json", json=post_request_content)
  print(validate_job_response.status_code)
  print(validate_job_response.json())
  # Uncomment the following to submit the request
  # submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
  # print(submit_job_response.status_code)
  # print(submit_job_response.json())

Adding a notifications email address
------------------------------------

-  NOTE: This is currently optional, but may be required in the future

You can optionally add your email address to receive email notifications
about the jobs you’ve submitted. The notification types are:

-  BEGIN: When a job starts
-  END: When a job is finished
-  RETRY: When a job step had an issue and was automatically retried
-  FAIL: When a job has failed completely
-  ALL: To receive a notification if any one of the previous events has
   triggered

Custom Slurm settings
---------------------

``aind-data-transfer-service`` is a small service that forwards requests
to run a compression and upload pipeline. The major computation work is
performed on our Slurm cluster.

We have provided default settings that work in most cases. However, for
very large jobs, such as processing more than a TB of data, you may need
to customize the Slurm settings to avoid timeouts or out-of-memory
errors.

Please reach out to Scientific Computing if you think you may need to
customize the Slurm settings.

Session settings for aind-metadata-mapper
-----------------------------------------

There are two methods for adding settings to process session.json files automatically during upload.

1) Creating JobSettings directly and attaching them to the BasicUploadJobConfigs

.. code-block:: python
  
  import json
  import requests
  
  from aind_data_transfer_models.core import (
      ModalityConfigs,
      BasicUploadJobConfigs,
      SubmitJobRequest,
  )
  from aind_metadata_mapper.models import SessionSettings, JobSettings as GatherMetadataJobSettings
  from aind_metadata_mapper.bergamo.models import JobSettings as BergamoSessionSettings
  from aind_data_schema_models.modalities import Modality
  from aind_data_schema_models.platforms import Platform
  from datetime import datetime
  
  acq_datetime = datetime.fromisoformat("2000-01-01T01:11:41")
  
  bergamo_session_settings = BergamoSessionSettings(
      input_source="/allen/aind/scratch/svc_aind_upload/test_data_sets/bci/061022",
      experimenter_full_name=["John Apple"],
      subject_id="655019",
      imaging_laser_wavelength=920,
      fov_imaging_depth=200,
      fov_targeted_structure="Primary Motor Cortex",
      notes="test upload",
  )
  
  session_settings = SessionSettings(job_settings=bergamo_session_settings)
  
  # directory_to_write_to is required, but will be set later by service.
  # We can set it to "stage" for now.
  metadata_job_settings = GatherMetadataJobSettings(directory_to_write_to="stage", session_settings=session_settings)
  
  ephys_config = ModalityConfigs(
      modality=Modality.ECEPHYS,
      source=(
          "/allen/aind/scratch/svc_aind_upload/test_data_sets/ecephys/655019_2023-04-03_18-17-07"
      ),
  )
  project_name = "Ephys Platform"
  subject_id = "655019"
  platform = Platform.ECEPHYS
  s3_bucket = "private"

  upload_job_configs = BasicUploadJobConfigs(
      project_name=project_name,
      s3_bucket=s3_bucket,
      platform=platform,
      subject_id=subject_id,
      acq_datetime=acq_datetime,
      modalities=[ephys_config],
      metadata_configs=metadata_job_settings,
  )
  upload_jobs = [upload_job_configs]
  submit_request = SubmitJobRequest(
      upload_jobs=upload_jobs
  )
  post_request_content = json.loads(submit_request.model_dump_json(exclude_none=True))
  # Uncomment the following to submit the request
  # submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
  # print(submit_job_response.status_code)
  # print(submit_job_response.json())

2) Using a pre-built settings.json file. You can compile the JobSettings class, save it to a json file, and point to that file.

.. code-block:: python
  
  import json
  import requests
  
  from aind_data_transfer_models.core import (
      ModalityConfigs,
      BasicUploadJobConfigs,
      SubmitJobRequest,
  )
  from aind_metadata_mapper.models import SessionSettings, JobSettings as GatherMetadataJobSettings
  from aind_metadata_mapper.bergamo.models import JobSettings as BergamoSessionSettings
  from aind_data_schema_models.modalities import Modality
  from aind_data_schema_models.platforms import Platform
  from datetime import datetime
  
  acq_datetime = datetime.fromisoformat("2000-01-01T01:11:41")
  
  metadata_configs_from_file = {
      "session_settings": {
          "job_settings": {
              "user_settings_config_file":"/allen/aind/scratch/svc_aind_upload/test_data_sets/bci/test_bergamo_settings.json",
              "job_settings_name": "Bergamo"
          }
      }
  }
  
  ephys_config = ModalityConfigs(
      modality=Modality.ECEPHYS,
      source=(
          "/allen/aind/scratch/svc_aind_upload/test_data_sets/ecephys/655019_2023-04-03_18-17-07"
      ),
  )
  project_name = "Ephys Platform"
  subject_id = "655019"
  platform = Platform.ECEPHYS
  s3_bucket = "private"

  upload_job_configs = BasicUploadJobConfigs(
      project_name=project_name,
      s3_bucket=s3_bucket,
      platform=platform,
      subject_id=subject_id,
      acq_datetime=acq_datetime,
      modalities=[ephys_config],
      metadata_configs=metadata_configs_from_file,
  )
  upload_jobs = [upload_job_configs]
  # Because we use a dict, this may raise a pydantic serializer warning.
  # The warning can be suppressed, but it isn't necessary
  with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    submit_request = SubmitJobRequest(
        upload_jobs=upload_jobs
    ) 
  post_request_content = json.loads(submit_request.model_dump_json(exclude_none=True, warnings=False))
  # Uncomment the following to submit the request
  # submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
  # print(submit_job_response.status_code)
  # print(submit_job_response.json())

Code Ocean pipeline settings
----------------------------

More granular control of the Code Ocean pipeline can be used. Up to 5 pipelines can be requested to be run after a data asset is registered to Code Ocean.

Please consult Code Ocean's official Python SDK for more information. [https://github.com/codeocean/codeocean-sdk-python]
`https://github.com/codeocean/codeocean-sdk-python <https://github.com/codeocean/codeocean-sdk-python>`__

Here is an example of attaching custom Code Ocean configurations:

.. code-block:: python

  import json
  import requests
  from aind_codeocean_pipeline_monitor.models import (
      PipelineMonitorSettings,
      CaptureSettings,
  )
  from aind_data_schema_models.data_name_patterns import DataLevel

  from aind_data_transfer_models.core import (
      ModalityConfigs,
      BasicUploadJobConfigs,
      SubmitJobRequest,
      CodeOceanPipelineMonitorConfigs,
  )
  from aind_data_schema_models.modalities import Modality
  from aind_data_schema_models.platforms import Platform
  from datetime import datetime

  from codeocean.computation import RunParams, DataAssetsRunParam
  from codeocean.data_asset import DataAssetParams

  acq_datetime = datetime.fromisoformat("2024-10-23T15:30:39")
  project_name = "Brain Computer Interface"
  subject_id = "731015"
  platform = Platform.SINGLE_PLANE_OPHYS
  s3_bucket = "private"

  pophys_config = ModalityConfigs(
      modality=Modality.POPHYS,
      source=("/allen/aind/scratch/BCI/2p-raw/BCI88/102324/pophys"),
  )
  behavior_video_config = ModalityConfigs(
      modality=Modality.BEHAVIOR_VIDEOS,
      compress_raw_data=False,
      source=("/allen/aind/scratch/BCI/2p-raw/BCI88/102324/behavior_video"),
  )
  behavior_config = ModalityConfigs(
      modality=Modality.BEHAVIOR,
      source=("/allen/aind/scratch/BCI/2p-raw/BCI88/102324/behavior"),
  )

  # Up to 5 PipelineMonitorSettings can be configured
  # Please be careful with the custom_metadata as it is a controlled vocabulary.
  codeocean_configs = CodeOceanPipelineMonitorConfigs(
      register_data_settings=DataAssetParams(
          name="",
          mount="",
          tags=[DataLevel.RAW.value, "test"],
          custom_metadata={"data level": DataLevel.RAW.value},
      ),
      pipeline_monitor_capsule_settings=[
          PipelineMonitorSettings(
              run_params=RunParams(
                  pipeline_id="87cbe6ce-9b38-4266-8d4a-62f0e23ba2d6",
                  data_assets=[DataAssetsRunParam(id="", mount="test_mount")],
                  parameters=["test"],
              ),
              capture_settings=CaptureSettings(
                  process_name_suffix="test-capture",
                  tags=[DataLevel.DERIVED.value, "test-cap", "tag2"],
              ),
          )
      ],
  )

  upload_job_configs = BasicUploadJobConfigs(
      project_name=project_name,
      s3_bucket=s3_bucket,
      platform=platform,
      subject_id=subject_id,
      acq_datetime=acq_datetime,
      modalities=[pophys_config, behavior_config, behavior_video_config],
      codeocean_configs=codeocean_configs,
  )
  upload_jobs = [upload_job_configs]
  submit_request = SubmitJobRequest(upload_jobs=upload_jobs)
  post_request_content = json.loads(submit_request.model_dump_json(exclude_none=True))
  # Uncomment the following to submit the request
  # submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
  # print(submit_job_response.status_code)
  # print(submit_job_response.json())

The results from the pipelines will be captured to a default bucket. To override this behavior, set capture_results_to_default_bucket field to False.

To not capture the results, the capture_settings can be set to None.

Submitting SmartSPIM jobs
-------------------------

SmartSPIM jobs are unique in that the compression step will be performed as a job array. If the directory structure looks like:

.. code-block:: bash

  SmartSPIM/
    - Ex_488_Em_525/
      - 471320/
        - 471320_701490
        ...
        - 471320_831090
      ...
      - 568520/
        ...
    ...
    - Ex_639_Em_680/
     ...

Then each "stack" (e.g., 471320_701490) will be processed individually.
If there are 60 stacks, then a good number_of_partitions will be 20.
In this case, the total time for the job will be around 3 times it takes to process one stack.
As a default, the SmartSPIM job will use a number_of_partitions of 10 and distribute the stacks evenly across 10 slurm jobs.
It's possible to customize the number_of_partitions as in the following example:

.. code-block:: python

  import json
  import requests

  from aind_data_transfer_models.core import (
      ModalityConfigs,
      BasicUploadJobConfigs,
      SubmitJobRequest,
  )
  from aind_data_schema_models.modalities import Modality
  from aind_data_schema_models.platforms import Platform
  from aind_slurm_rest.models import V0036JobProperties
  from datetime import datetime

  # Optional settings. Default partition size will be set to 10, but can also be
  # provided as such. If partition_size is larger than the number of stacks, this
  # may lead to inefficiencies and errors.
  partition_size: int = 20
  job_props = V0036JobProperties(
      environment=dict(),
      array=f"0-{partition_size-1}"
  )
  acq_datetime = datetime.fromisoformat("2023-10-18T20:30:30")
  spim_config = ModalityConfigs(
      modality=Modality.SPIM,
      slurm_settings=job_props,
      compress_raw_data=True,
      source=(
          "/allen/aind/scratch/svc_aind_upload/test_data_sets/smartspim/"
          "SmartSPIM_695464_2023-10-18_20-30-30"
      ),
  )

  project_name = "MSMA Platform"
  subject_id = "695464"
  platform = Platform.SMARTSPIM
  # can also be set to "open" if writing to the open bucket.
  s3_bucket = "private"

  upload_job_configs = BasicUploadJobConfigs(
      project_name=project_name,
      s3_bucket=s3_bucket,
      platform=platform,
      subject_id=subject_id,
      acq_datetime=acq_datetime,
      modalities=[spim_config],
  )

  # Add more to the list if needed
  upload_jobs = [upload_job_configs]

  # Optional email address and notification types if desired
  submit_request = SubmitJobRequest(
      upload_jobs=upload_jobs,
  )

  post_request_content = json.loads(
      submit_request.model_dump_json(exclude_none=True)
  )
  # Uncomment the following to submit the request
  # submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
  # print(submit_job_response.status_code)
  # print(submit_job_response.json())


Viewing the status of submitted jobs
------------------------------------

The status of submitted jobs can be viewed at:
http://aind-data-transfer-service/jobs

Viewing job parameters based on job type
--------------------------------------------

We store pre-compiled job configurations in AWS Parameter Store based on `job_type`.
Available job types and their configurations can be viewed at:
http://aind-data-transfer-service/job_params

To request a new job type, please reach out to Scientific Computing.

Reporting bugs or making feature requests
-----------------------------------------

Please report any bugs or feature requests here:
`issues <https://github.com/AllenNeuralDynamics/aind-data-transfer-service/issues/new/choose>`__
