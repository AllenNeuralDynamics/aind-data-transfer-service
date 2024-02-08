"""Module to test job upload template configs and generation"""

import os
import unittest
from pathlib import Path

from openpyxl import load_workbook

from aind_data_transfer_service.configs.job_upload_template import (
    JobUploadTemplate,
)

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
SAMPLE_JOB_TEMPLATE = TEST_DIRECTORY / "resources" / "job_upload_template.xlsx"


class TestJobUploadTemplate(unittest.TestCase):
    """Tests job upload template class"""

    def read_xl_helper(self, source, return_validators=False):
        """Helper function to read xlsx contents and validators"""
        lines = []
        workbook = load_workbook(source, read_only=not return_validators)
        worksheet = workbook.active
        for row in worksheet.rows:
            row_contents = [cell.value for cell in row]
            lines.append(row_contents)
        if return_validators:
            validators = []
            for dv in worksheet.data_validations.dataValidation:
                validators.append(
                    {
                        "name": dv.promptTitle,
                        "options": dv.formula1.strip('"').split(","),
                        "ranges": str(dv.cells).split(" "),
                    }
                )
            result = (lines, validators)
        else:
            result = lines
        workbook.close()
        return result

    def test_create_job_template(self):
        """Tests that xlsx job template is created with
        correct contents and validators"""
        expected_lines = self.read_xl_helper(SAMPLE_JOB_TEMPLATE)
        (template_lines, template_validators) = self.read_xl_helper(
            JobUploadTemplate.create_job_template(), True
        )
        self.assertEqual(expected_lines, template_lines)
        self.assertCountEqual(
            JobUploadTemplate.VALIDATORS, template_validators
        )


if __name__ == "__main__":
    unittest.main()
