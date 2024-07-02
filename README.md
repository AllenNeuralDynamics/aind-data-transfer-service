# aind-data-transfer-service

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)

This service can be used to upload data stored in a VAST drive. It uses FastAPI to upload a job submission csv file that will be used to trigger a data transfer job in an on-prem HPC. Based on the information provided in the file, the data upload process fetches the appropriate metadata and starts the upload process.

More information can be found at [readthedocs](https://aind-data-transfer-service.readthedocs.io).
