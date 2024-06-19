User Guide
==========

Thank you for using ``aind-data-transfer-service``! This guide is
intended for scientists and engineers in AIND that wish to upload data
from our shared network drives (e.g., VAST) to the cloud.

Prerequisites
-------------

-  It’s assumed that raw data is already stored and organized on a
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
      -  modaltity0.source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/ecephys_data)
      -  modality1 (e.g, behavior)
      -  modality1.source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/behavior_data)
      -  modality2 (e.g, behavior_videos)
      -  modality2.source (e.g.,
         /allen/aind/scratch/working_group/session_123456_2024-06-19/behavior_videos)

-  Optional fields

   -  metadata_dir: If metadata files are pre-compiled and saved to a
      directory, you can add the Posix style path to the directory under
      this column
   -  process_capsule_id: If you wish to trigger a custom Code Ocean
      Capsule or pipeline, you can add the capsule_id here
   -  input_data_mount: If you wish to trigger a custom Code Ocean
      Pipeline that has been configured with a specific data mount, you
      can add that here
   -  s3_bucket: As default, data will be uploaded to a private bucket
      in S3 managed by AIND. Please reach out to the Scientific
      Computing department if you wish to upload to a different bucket.
   -  metadata_dir_force: We will automatically pull subject and
      procedures data for a mouse. By setting this ``True``, we will
      overwrite any data in the ``metadata_dir`` folder with data
      acquired automatically from our service
   -  force_cloud_sync: We run a check to verify whether there is
      already a data asset with this name saved in our S3 bucket. If
      this field is set to ``True``, we will sync the data to the
      bucket/folder even if it already exists

Using the REST API
------------------

Jobs can also be submitted via a REST API at the endpoint
``http://aind-data-transfer-service/api/v1/submit_jobs``

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

Viewing the status of submitted jobs
------------------------------------

The status of submitted jobs can be viewed at:
http://aind-data-transfer-service/jobs

Reporting bugs or making feature requests
-----------------------------------------

Please report any bugs or feature requests here:
`issues <https://github.com/AllenNeuralDynamics/aind-data-transfer-service/issues/new/choose>`__
