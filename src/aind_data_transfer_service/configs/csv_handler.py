"""Module to handle processing legacy csv files"""

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform

from aind_data_transfer_service.models.core import Task, UploadJobConfigsV2


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
            modality_configs[modality_key].update({sub_key: clean_val})
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
    return UploadJobConfigsV2(**job_configs)
