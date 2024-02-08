"""Module to configure constants for generating xlsx job upload template"""
import datetime
from aind_data_schema.core.data_description import Modality, Platform

TEMPLATE_FILENAME = "job_upload_template.xlsx"
TEMPLATE_HEADERS = [
    "platform",
    "acq_datetime",
    "subject_id",
    "s3_bucket",
    "modality0",
    "modality0.source",
    "modality1",
    "modality1.source",
]
TEMPLATE_SAMPLE_JOBS = [
    [
        Platform.BEHAVIOR.abbreviation,
        datetime.datetime(2023, 10, 4, 4, 0, 0),
        "123456",
        "aind-behavior-data",
        Modality.BEHAVIOR_VIDEOS.abbreviation,
        "/allen/aind/stage/fake/dir",
        Modality.BEHAVIOR.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
    [
        Platform.SMARTSPIM.abbreviation,
        datetime.datetime(2023, 3, 4, 16, 30, 0),
        "654321",
        "aind-open-data",
        Modality.SPIM.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
    [
        Platform.ECEPHYS.abbreviation,
        datetime.datetime(2023, 1, 30, 19, 1, 0),
        "654321",
        "aind-ephys-data",
        Modality.ECEPHYS.abbreviation,
        "/allen/aind/stage/fake/dir",
        Modality.BEHAVIOR_VIDEOS.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
]
TEMPLATE_VALIDATORS = [
    {
        "name": "platform",
        "options": [p().abbreviation for p in Platform._ALL],
        "ranges": ["A2:A20"],
    },
    {
        "name": "modality",
        "options": [m().abbreviation for m in Modality._ALL],
        "ranges": ["E2:E20", "G2:G20"],
    },
    {
        "name": "s3_bucket",
        "options": [
            "aind-ephys-data",
            "aind-ophys-data",
            "aind-behavior-data",
            "aind-private-data",
            "aind-open-data",
        ],
        "ranges": ["D2:D20"],
    },
]
