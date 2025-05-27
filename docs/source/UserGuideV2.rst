User Guide V2
=============

Thank you for using ``aind-data-transfer-service``! This guide is
intended for scientists and engineers in AIND that wish to upload data
from our shared network drives (e.g., VAST) to the cloud.

Concepts
--------

There are two important concepts that should be highlighted: Tasks and
job_types.

-  The Task model can be imported from
   aind_data_transfer_service.models.core.Task; however, it is simple to build
   it as a python dictionary too. It has the following fields:

   -  skip_task: Whether or not to skip a Task such as checking if the
      s3_folder already exists.
   -  image: A docker image to run for a particular task
   -  image_version: The version of the docker image to run
   -  image_resources: The HPC resources that are being requested.
   -  job_settings: A dictionary that can be passed into the command script.
   -  command_script: The command to run in the docker image.

-  The following Tasks are being run during the transform and upload pipeline.
   The more important ones are in bold.

   -  send_job_start_email: sends an optional email to signal that a workflow
      has started.
   -  check_s3_folder_exists: Raises an error if an s3_folder already exists.
      Set skip_task to True to skip this check.
   -  check_source_folders_exist: Checks that the source folders exist. This
      raises and error earlier in the workflow if the source folders were
      configured incorrectly.
   -  create_staging_folder: Creates a temporary folder on VAST to store some
      temporary files for staging.
   -  **gather_preliminary_metadata**: Automatically gathers metadata for
      subject, procedures, and data_description. Will also gather metadata from
      aind-metadata-mapper if options are set.
   -  **modality_transformation_settings**: This creates the settings for
      transforming the modality folders.
   -  compress_data: This is a mapped task. Each Task in the
      modality_transformation_settings will run in parallel in a separate
      container here.
   -  gather_final_metadata: Automatically generates a processing.json and
      metadata.nd.json file.
   -  check_metadata_files: Checks that the metadata files exist and are json.
   -  upload_data_to_s3: Uploads the data to S3.
   -  register_data_asset_to_codeocean: Registers the data asset to Code Ocean.
   -  update_docdb_record: Updates the DocDB record with the Code Ocean Data
      Asset ID.
   -  **codeocean_pipeline_settings**: As with the
      modality_transformation_settings, the parameters to send to the
      codeocean pipeline monitor capsule.
   -  run_codeocean_pipeline: This is a mapped task that will run each task in
      the codeocean_pipeline_settings dictionary in an individual container.
   -  remove_staging_folder: Removes the staging folder created above.
   -  remove_source_folders: Optionally remove the source folders from VAST.
      As default, this is turned off. Please be careful running this task.
   -  send_job_end_email: sends an optional email to signal that a workflow
      has ended.

-  job_type: Since the majority of workflows may use the same parameters
   repeatedly, the Tasks can be stored in AWS Parameter Store. A user will
   only need to define a job_type, and the presets will be used. This is the
   recommended way of using aind-data-transfer-service. Please reach out to a
   member of Scientific Computing for help with defining a job_type.

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

   -  job_type: We store pre-compiled default configurations in AWS Parameter
      Store (e.g. modality transformation settings, Code Ocean pipeline
      settings). This field determines which preset to use when
      running the upload job. A list of job types can be seen by clicking the
      ``Job Parameters`` link.
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

   -  metadata_dir: If metadata files are pre-compiled and saved to a
      directory, you can add the Posix style path to the directory under
      this column
   -  s3_bucket: As default, data will be uploaded to a default bucket
      in S3 managed by AIND. Please reach out to the Scientific
      Computing department if you wish to upload to a different bucket.
   -  modality{n}.pipeline_id (or modality{n}.capsule_id: It is possible to add
      a Code Ocean pipeline_id or capsule_id to a modality. For more complex
      parameters, please define a job_type or use the REST API.
      -  modality0.capsule_id (e.g., 123-456)
      -  modality1.pipeline_id (e.g., 123-456)
   - force_cloud_sync: We recommend using this flag sparingly. This will skip
     the force a sync to AWS even if the folder already exists in the cloud.
     This will overwrite the data already uploaded, but won't delete any data.
     Please reach out to a member of Scientific Computing for help clearing data
     from AWS.

Using the REST API
------------------

For more granular configuration, jobs can be submitted via a REST API at the
endpoint:

``http://aind-data-transfer-service/api/v2/submit_jobs``

You may pip install aind-data-transfer-service for access to the Task model;
however, this isn't strictly necessary. You can form the post request as a
dictionary. The service will perform validation. We strongly recommend using
customized job_types to simplify the requests. For more detailed examples please
check the scripts in `examples <https://github.com/AllenNeuralDynamics/aind-data-transfer-service/tree/main/docs/examples>`__.


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
