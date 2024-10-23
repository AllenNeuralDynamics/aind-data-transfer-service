"""Module to handle processing legacy csv files"""

import json

from aind_data_transfer_models.core import (
    BasicUploadJobConfigs,
    CodeOceanPipelineMonitorConfigs,
    ModalityConfigs,
)


def map_csv_row_to_job(row: dict) -> BasicUploadJobConfigs:
    """
    Maps csv row into a BasicUploadJobConfigs model
    Parameters
    ----------
    row : dict

    Returns
    -------
    BasicUploadJobConfigs

    """
    modality_configs = dict()
    basic_job_configs = dict()
    for key, value in row.items():
        # Strip white spaces and replace dashes with underscores
        clean_key = str(key).strip(" ").replace("-", "_")
        clean_val = str(value).strip(" ")
        # Replace empty strings with None.
        clean_val = None if clean_val is None or clean_val == "" else clean_val
        if clean_key.startswith("modality"):
            modality_parts = clean_key.split(".")
            if len(modality_parts) == 1:
                modality_key = modality_parts[0]
                sub_key = "modality"
            else:
                modality_key = modality_parts[0]
                sub_key = modality_parts[1]
            if (
                modality_configs.get(modality_key) is None
                and clean_val is not None
            ):
                modality_configs[modality_key] = {sub_key: clean_val}
            elif clean_val is not None:
                modality_configs[modality_key].update({sub_key: clean_val})
        elif clean_key == "job_type":
            if clean_val is not None:
                codeocean_configs = json.loads(
                    CodeOceanPipelineMonitorConfigs().model_dump_json()
                )
                codeocean_configs["job_type"] = clean_val
                basic_job_configs["codeocean_configs"] = codeocean_configs
        else:
            basic_job_configs[clean_key] = clean_val
    modalities = []
    for modality_value in modality_configs.values():
        modalities.append(ModalityConfigs(**modality_value))
    return BasicUploadJobConfigs(modalities=modalities, **basic_job_configs)
