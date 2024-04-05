"""Init package"""
import os

__version__ = "0.9.5"

# Global constants
OPEN_DATA_BUCKET_NAME = os.getenv("OPEN_DATA_BUCKET_NAME", "open")
PRIVATE_BUCKET_NAME = os.getenv("PRIVATE_BUCKET_NAME", "private")
SCRATCH_BUCKET_NAME = os.getenv("SCRATCH_BUCKET_NAME", "scratch")
