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
    HEADERS = [
        "platform",
        "acq_datetime",
        "subject_id",
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
            Modality.BEHAVIOR_VIDEOS.abbreviation,
            "/allen/aind/stage/fake/dir",
            Modality.BEHAVIOR.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
        [
            Platform.SMARTSPIM.abbreviation,
            datetime.datetime(2023, 3, 4, 16, 30, 0),
            "654321",
            Modality.SPIM.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
        [
            Platform.ECEPHYS.abbreviation,
            datetime.datetime(2023, 1, 30, 19, 1, 0),
            "654321",
            Modality.ECEPHYS.abbreviation,
            "/allen/aind/stage/fake/dir",
            Modality.BEHAVIOR_VIDEOS.abbreviation,
            "/allen/aind/stage/fake/dir",
        ],
    ]
    VALIDATORS = [
        {
            "name": "platform",
            "options": [p().abbreviation for p in Platform._ALL],
            "column_indexes": [HEADERS.index("platform")],
        },
        {
            "name": "modality",
            "options": [m().abbreviation for m in Modality._ALL],
            "column_indexes": [
                HEADERS.index("modality0"),
                HEADERS.index("modality1"),
            ],
        },
    ]

    @staticmethod
    def create_job_template():
        """Create job template as xlsx filestream"""
        # job template
        xl_io = BytesIO()
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(JobUploadTemplate.HEADERS)
        for job in JobUploadTemplate.SAMPLE_JOBS:
            worksheet.append(job)
        # data validators
        for validator in JobUploadTemplate.VALIDATORS:
            dv = DataValidation(
                type="list",
                formula1=f'"{(",").join(validator["options"])}"',
                allow_blank=True,
                showErrorMessage=True,
                showInputMessage=True,
            )
            dv.promptTitle = validator["name"]
            dv.prompt = f'Select a {validator["name"]} from the dropdown'
            dv.error = f'Invalid {validator["name"]}.'
            for i in validator["column_indexes"]:
                col = get_column_letter(i + 1)
                dv.add(f"{col}2:{col}{JobUploadTemplate.NUM_TEMPLATE_ROWS}")
            worksheet.add_data_validation(dv)
        # formatting
        bold = Font(bold=True)
        for header in worksheet["A1:G1"]:
            for cell in header:
                cell.font = bold
                worksheet.column_dimensions[
                    get_column_letter(cell.column)
                ].auto_size = True
        # save file
        workbook.save(xl_io)
        workbook.close()
        return xl_io
