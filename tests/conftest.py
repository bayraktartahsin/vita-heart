import os
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-north-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ["VITAHEART_TABLE"] = "vitaheart-test"
os.environ["VITAHEART_LONG_POLL_SECONDS"] = "0.5"


@pytest.fixture
def ddb():
    with mock_aws():
        from vitaheart import store
        store.reset_for_tests()
        client = boto3.client("dynamodb", region_name="eu-north-1")
        client.create_table(TableName="vitaheart-test", BillingMode="PAY_PER_REQUEST",
                            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                                  {"AttributeName": "SK", "AttributeType": "S"}],
                            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                                       {"AttributeName": "SK", "KeyType": "RANGE"}])
        yield client
        store.reset_for_tests()
