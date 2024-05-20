# aind-data-transfer-service

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)

This service can be used to upload data stored in a VAST drive. It uses FastAPI to upload a job submission csv file that will be used to trigger a data transfer job in an on-prem HPC. Based on the information provided in the file, the data upload process fetches the appropriate metadata and starts the upload process.

## Metadata Sources

The associated metadata files get pulled from different sources. 

- subject from LabTracks
- procedures from NSB Sharepoint, TARS
- instrument/rig from SLIMS


## Usage

There are two options for uploading data: a python API or a browser UI service.

### Browser UI
You can go to http://aind-data-transfer-service to submit a `.csv` or `.xlsx` file with the necessary parameters needed to launch a data upload job. Click on **Job Submit Template** to download a template which you may use as a reference. 

What each column means in the job submission template:

- **project_name**: Project name. A full list can be downloaded at [Project Names](http://aind-metadata-service/project_names)
- **process_capsule_id**: Optional Code Ocean capsule or pipeline to run when data is uploaded
- **platform**: For a list of platforms click [here](https://github.com/AllenNeuralDynamics/aind-data-schema/blob/main/src/aind_data_schema/models/platforms.py).
- **acq_datetime**: The time that the data was acquired
- **subject_id**: The unique id of the subject
- **modality0**: For a list of modalities, click [here](https://github.com/AllenNeuralDynamics/aind-data-schema/blob/main/src/aind_data_schema/models/modalities.py). 
- **modality0.source**: The source (path to file) of **modality0** in VAST drive
- **metadata_dir**: An optional folder for pre-compiled metadata json files

Modify the job template as needed and click on **Browse** to upload the file. A rendered table with a message **Successfully validated jobs from file**  appears to indicate a valid file. If there are errors in the job submit file, a message that says **Error validating jobs from file** appears. 

To launch a data upload job, click on `Submit`. A message that says **Successfuly submitted jobs** should appear. 

After submission, click on `Job Status` to see the status of the data upload job process.  

### Python API
It's also possible to submit a job via a python api. Here is an example script that can be used.

Assuming that the data on a shared drive is organized as:
```
/shared_drive/vr_foraging/690165/20240219T112517
  - Behavior
  - Behavior videos
  - Configs
```
then a job request can be submitted as:
```python
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
project_name="Ephys Platform"

upload_job_configs = BasicUploadJobConfigs(
  project_name=project_name,
  s3_bucket = s3_bucket,
  platform = platform,
  subject_id = subject_id,
  acq_datetime=acq_datetime,
  modalities = [behavior_config, behavior_videos_config],
  metadata_dir = metadata_dir
)

# Add more to the list if needed
upload_jobs=[upload_job_configs]

# Optional email address and notification types if desired
user_email = "my_email_address"
email_notification_types = ["fail"]
submit_request = SubmitJobRequest(
    upload_jobs=upload_jobs,
    user_email=user_email,
    email_notification_types=email_notification_types,
)

post_request_content = json.loads(submit_request.model_dump_json(round_trip=True))
submit_job_response = requests.post(url="http://aind-data-transfer-service/api/v1/submit_jobs", json=post_request_content)
print(submit_job_response.status_code)
print(submit_job_response.json())
```

## Installation
To use the software, in the root directory, run
```bash
pip install -e .
```

To develop the code, run
```bash
pip install -e .[dev]
```

## Local Development
Run uvicorn:
```bash
export AIND_METADATA_SERVICE_PROJECT_NAMES_URL='http://aind-metadata-service-dev/project_names'
export AIND_AIRFLOW_SERVICE_URL='http://localhost:8080/api/v1/dags/run_list_of_jobs/dagRuns'
export AIND_AIRFLOW_SERVICE_JOBS_URL='http://localhost:8080/api/v1/dags/transform_and_upload/dagRuns'
export AIND_AIRFLOW_SERVICE_PASSWORD='*****'
export AIND_AIRFLOW_SERVICE_USER='user'
uvicorn aind_data_transfer_service.server:app --host 0.0.0.0 --port 5000
```
You can now access `http://localhost:5000`.

## Contributing

### Linters and testing

There are several libraries used to run linters, check documentation, and run tests.

- Please test your changes using the **coverage** library, which will run the tests and log a coverage report:

```bash
coverage run -m unittest discover && coverage report
```

- Use **interrogate** to check that modules, methods, etc. have been documented thoroughly:

```bash
interrogate .
```

- Use **flake8** to check that code is up to standards (no unused imports, etc.):
```bash
flake8 .
```

- Use **black** to automatically format the code into PEP standards:
```bash
black .
```

- Use **isort** to automatically sort import statements:
```bash
isort .
```

### Pull requests

For internal members, please create a branch. For external members, please fork the repository and open a pull request from the fork. We'll primarily use [Angular](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit) style for commit messages. Roughly, they should follow the pattern:
```text
<type>(<scope>): <short summary>
```

where scope (optional) describes the packages affected by the code changes and type (mandatory) is one of:

- **build**: Changes that affect build tools or external dependencies (example scopes: pyproject.toml, setup.py)
- **ci**: Changes to our CI configuration files and scripts (examples: .github/workflows/ci.yml)
- **docs**: Documentation only changes
- **feat**: A new feature
- **fix**: A bugfix
- **perf**: A code change that improves performance
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **test**: Adding missing tests or correcting existing tests

### Semantic Release

The table below, from [semantic release](https://github.com/semantic-release/semantic-release), shows which commit message gets you which release type when `semantic-release` runs (using the default configuration):

| Commit message                                                                                                                                                                                   | Release type                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `fix(pencil): stop graphite breaking when too much pressure applied`                                                                                                                             | ~~Patch~~ Fix Release, Default release                                                                          |
| `feat(pencil): add 'graphiteWidth' option`                                                                                                                                                       | ~~Minor~~ Feature Release                                                                                       |
| `perf(pencil): remove graphiteWidth option`<br><br>`BREAKING CHANGE: The graphiteWidth option has been removed.`<br>`The default graphite width of 10mm is always used for performance reasons.` | ~~Major~~ Breaking Release <br /> (Note that the `BREAKING CHANGE: ` token must be in the footer of the commit) |

### Documentation
To generate the rst files source files for documentation, run
```bash
sphinx-apidoc -o doc_template/source/ src
```
Then to create the documentation HTML files, run
```bash
sphinx-build -b html doc_template/source/ doc_template/build/html
```
More info on sphinx installation can be found [here](https://www.sphinx-doc.org/en/master/usage/installation.html).
