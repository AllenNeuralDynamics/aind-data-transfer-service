"""Module to configure and create xlsx job upload template"""
import datetime
from io import BytesIO

from aind_data_schema.models.modalities import Modality
from aind_data_schema.models.platforms import Platform
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation


# TODO: convert to pydantic model
class JobUploadTemplate:
    """Class to configure and create xlsx job upload template"""

    FILE_NAME = "job_upload_template.xlsx"
    NUM_TEMPLATE_ROWS = 20
    XLSX_DATETIME_FORMAT = "YYYY-MM-DDTHH:mm:ss"
    HEADERS = [
        "platform",
        "acq_datetime",
        "subject_id",
        "metadata_dir",
        "modality0",
        "modality0.source",
        "modality1",
        "modality1.source",
    ]
    SAMPLE_JOBS = [
        [
            Platform.BEHAVIOR.abbreviation,
            datetime.datetime(2023, 10, 4, 4, 0, 0),
            "123456",
            "/allen/aind/stage/fake/metadata_dir",
            Modality.BEHAVIOR_VIDEOS.abbreviation,
            "/allen/aind/stage/fake/dir",
            Modality.BEHAVIOR.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
        [
            Platform.SMARTSPIM.abbreviation,
            datetime.datetime(2023, 3, 4, 16, 30, 0),
            "654321",
            "/allen/aind/stage/fake/Config",
            Modality.SPIM.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
        [
            Platform.ECEPHYS.abbreviation,
            datetime.datetime(2023, 1, 30, 19, 1, 0),
            "654321",
            None,
            Modality.ECEPHYS.abbreviation,
            "/allen/aind/stage/fake/dir",
            Modality.BEHAVIOR_VIDEOS.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
    ]
    VALIDATORS = [
        {
            "name": "platform",
            "type": "list",
            "options": [p().abbreviation for p in Platform._ALL],
            "column_indexes": [HEADERS.index("platform")],
        },
        {
            "name": "modality",
            "type": "list",
            "options": [m().abbreviation for m in Modality._ALL],
            "column_indexes": [
                HEADERS.index("modality0"),
                HEADERS.index("modality1"),
            ],
        },
        {
            "name": "datetime",
            "type": "date",
            "column_indexes": [HEADERS.index("acq_datetime")],
        },
    ]

    @staticmethod
    def create_job_template():
        """Create job template as xlsx filestream"""
        # job template
        xl_io = BytesIO()
        workbook = Workbook()
        workbook.iso_dates = True
        worksheet = workbook.active
        worksheet.append(JobUploadTemplate.HEADERS)
        for job in JobUploadTemplate.SAMPLE_JOBS:
            worksheet.append(job)
        # data validators
        for validator in JobUploadTemplate.VALIDATORS:
            dv_type = validator["type"]
            dv_name = validator["name"]
            dv_params = {
                "type": dv_type,
                "promptTitle": dv_name,
                "error": f"Invalid {dv_name}.",
                "allow_blank": True,
                "showErrorMessage": True,
                "showInputMessage": True,
            }
            if dv_type == "list":
                dv_params["formula1"] = f'"{(",").join(validator["options"])}"'
                dv_params["prompt"] = f"Select a {dv_name} from the dropdown"
            elif dv_type == "date":
                dv_params["prompt"] = "Provide a {} using {}".format(
                    dv_name, JobUploadTemplate.XLSX_DATETIME_FORMAT
                )
            dv = DataValidation(**dv_params)
            for i in validator["column_indexes"]:
                col = get_column_letter(i + 1)
                col_range = (
                    f"{col}2:{col}{JobUploadTemplate.NUM_TEMPLATE_ROWS}"
                )
                dv.add(col_range)
                if dv_type != "date":
                    continue
                for (cell,) in worksheet[col_range]:
                    cell.number_format = JobUploadTemplate.XLSX_DATETIME_FORMAT
            worksheet.add_data_validation(dv)
        # formatting
        bold = Font(bold=True)
        for cell in worksheet[1]:
            cell.font = bold
            worksheet.column_dimensions[cell.column_letter].auto_size = True
        # save file
        workbook.save(xl_io)
        workbook.close()
        return xl_io
