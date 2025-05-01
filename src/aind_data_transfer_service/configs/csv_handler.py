"""Module to handle processing legacy csv files"""

import re
from datetime import datetime

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.models.core import Task, UploadJobConfigsV2

DATETIME_PATTERN2 = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [APap][Mm]$"
)


def map_csv_row_to_job(row: dict) -> UploadJobConfigsV2:
    """
    Maps csv row into a UploadJobConfigsV2 model
    Parameters
    ----------
    row : dict

    Returns
    -------
    UploadJobConfigsV2

    """
    modality_configs = dict()
    job_configs = dict()
    check_s3_folder_exists_task = None
    final_check_s3_folder_exist = None
    for key, value in row.items():
        # Strip white spaces and replace dashes with underscores
        clean_key = str(key).strip(" ").replace("-", "_")
        clean_val = str(value).strip(" ")
        # Check empty strings or None values
        if clean_val is None or clean_val == "":
            continue
        if clean_key.startswith("modality"):
            modality_parts = clean_key.split(".")
            modality_key = modality_parts[0]
            sub_key = (
                "modality" if len(modality_parts) == 1 else modality_parts[1]
            )
            modality_configs.setdefault(modality_key, dict())
            # Temp backwards compatibility check
            if sub_key == "source":
                sub_key = "input_source"
            modality_configs[modality_key].update({sub_key: clean_val})
        elif clean_key == "force_cloud_sync" and clean_val.upper() in [
            "TRUE",
            "T",
        ]:
            check_s3_folder_exists_task = {"skip_task": True}
            final_check_s3_folder_exist = {"skip_task": True}
        else:
            job_configs[clean_key] = clean_val
    # Create Tasks from parsed configs
    modality_tasks = {
        m.pop("modality"): Task(job_settings=m)
        for m in modality_configs.values()
        if m.get("modality") is not None
    }
    metadata_task = (
        Task(job_settings={"metadata_dir": job_configs.pop("metadata_dir")})
        if "metadata_dir" in job_configs
        else None
    )
    tasks = {
        "gather_preliminary_metadata": metadata_task,
        "check_s3_folder_exists_task": check_s3_folder_exists_task,
        "final_check_s3_folder_exist": final_check_s3_folder_exist,
        "modality_transformation_settings": modality_tasks,
    }
    job_configs.update(
        {
            "platform": Platform.from_abbreviation(job_configs["platform"]),
            "modalities": [
                Modality.from_abbreviation(m) for m in modality_tasks.keys()
            ],
            "tasks": {k: v for k, v in tasks.items() if v is not None},
        }
    )
    acq_dt = job_configs.get("acq_datetime")
    if acq_dt is not None and re.match(DATETIME_PATTERN2, acq_dt):
        job_configs["acq_datetime"] = datetime.strptime(
            acq_dt, "%m/%d/%Y %I:%M:%S %p"
        )

    return UploadJobConfigsV2(**job_configs)
