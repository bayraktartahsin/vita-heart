"""Vita Heart API: the cloud behind the television.

One FastAPI app, run locally with uvicorn and on AWS Lambda through Mangum.
Nothing in this package reads a credential; the execution role or the local
AWS profile provides them.
"""
__version__ = "0.1.0"
