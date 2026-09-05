#!/usr/bin/env python3
"""Put the Vita Heart API on a public URL. Idempotent.

    python scripts/deploy.py            # build zip, create/update everything
    python scripts/deploy.py --infra    # only role, table, gateway (no code)

Lambda behind an API Gateway HTTP API, the pattern already proven in this AWS
account (Lambda Function URLs return 403 here regardless of policy). The
deployed code is the same FastAPI app that runs locally; the adapter is four
lines in vitaheart/lambda_handler.py.

Dependencies are installed for the Lambda's platform (manylinux, aarch64) so a
Mac build produces a Linux artifact.
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "api"
REGION = "eu-north-1"
FUNCTION = "vitaheart-api"
ROLE = "vitaheart-lambda"
TABLE = "vitaheart"
API_NAME = "vitaheart"
BUCKET_PREFIX = "vitaheart-photos-"
BUILD = ROOT / ".build"

# strands is NOT bundled: the Lambda calls the fleet on AgentCore. Locally the fleet runs in-process.
DEPS = ["fastapi==0.141.1", "mangum==0.22.0", "pydantic==2.12.5", "httpx==0.28.1"]

TRUST = {"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}


def policy(account: str) -> dict:
    return {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Resource": f"arn:aws:dynamodb:{REGION}:{account}:table/{TABLE}",
         "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]},
        {"Effect": "Allow", "Resource": "*",
         "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                    "bedrock-agentcore:InvokeAgentRuntime"]},
        {"Effect": "Allow", "Resource": [f"arn:aws:s3:::{BUCKET_PREFIX}{account}", f"arn:aws:s3:::{BUCKET_PREFIX}{account}/*"],
         "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]},
        {"Effect": "Allow", "Resource": "arn:aws:logs:*:*:*",
         "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]},
    ]}


def say(msg: str) -> None:
    print(f"• {msg}", flush=True)


def build_zip() -> bytes:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()
    say("installing dependencies for manylinux aarch64")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", str(BUILD),
                    "--platform", "manylinux2014_aarch64", "--implementation", "cp",
                    "--python-version", "3.12", "--only-binary=:all:", *DEPS], check=True)
    shutil.copytree(API_DIR / "vitaheart", BUILD / "vitaheart")
    shutil.copytree(ROOT / "agents", BUILD / "agents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in BUILD.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(BUILD))
    data = buf.getvalue()
    say(f"zip {len(data)/1e6:.1f} MB")
    return data


def ensure_role(iam) -> str:
    account = boto3.client("sts").get_caller_identity()["Account"]
    try:
        arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
    except ClientError:
        arn = iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps(TRUST),
                              Description="Vita Heart API execution role")["Role"]["Arn"]
        say(f"created role {ROLE}; waiting for IAM propagation")
        time.sleep(10)
    iam.put_role_policy(RoleName=ROLE, PolicyName="vitaheart-access", PolicyDocument=json.dumps(policy(account)))
    return arn


def ensure_table(ddb) -> None:
    try:
        ddb.describe_table(TableName=TABLE)
        return
    except ClientError:
        pass
    ddb.create_table(TableName=TABLE, BillingMode="PAY_PER_REQUEST",
                     AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                           {"AttributeName": "SK", "AttributeType": "S"}],
                     KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                                {"AttributeName": "SK", "KeyType": "RANGE"}])
    ddb.get_waiter("table_exists").wait(TableName=TABLE)
    ddb.update_time_to_live(TableName=TABLE, TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"})
    say(f"created table {TABLE}")


def ensure_bucket(s3, account: str) -> str:
    """Private bucket for box photos. Objects expire after 30 days; the TV never needs old photos."""
    name = f"{BUCKET_PREFIX}{account}"
    try:
        s3.head_bucket(Bucket=name)
    except ClientError:
        s3.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": REGION})
        s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        s3.put_bucket_lifecycle_configuration(Bucket=name, LifecycleConfiguration={"Rules": [
            {"ID": "expire-photos", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 30}}]})
        s3.put_bucket_cors(Bucket=name, CORSConfiguration={"CORSRules": [
            {"AllowedOrigins": ["*"], "AllowedMethods": ["PUT", "GET"], "AllowedHeaders": ["*"], "MaxAgeSeconds": 3600}]})
        say(f"created bucket {name}")
    return name


def _wait(lam) -> None:
    for _ in range(60):
        st = lam.get_function_configuration(FunctionName=FUNCTION)
        if st.get("LastUpdateStatus") != "InProgress" and st.get("State") != "Pending":
            return
        time.sleep(2)


def agentcore_arn() -> str | None:
    """The fleet's runtime ARN, if `agentcore deploy` has run. Read from its config file, never typed by hand."""
    cfg = ROOT / ".bedrock_agentcore.yaml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if "agent_arn:" in line:
            return line.split("agent_arn:", 1)[1].strip() or None
    return None


def ensure_function(lam, role_arn: str, code: bytes, bucket: str) -> None:
    variables = {"VITAHEART_TABLE": TABLE, "VITAHEART_REGION": REGION, "VITAHEART_BUCKET": bucket}
    arn = agentcore_arn()
    if arn:
        variables["VITAHEART_AGENT_ARN"] = arn
        say(f"fleet on AgentCore: {arn.rsplit('/', 1)[-1]}")
    else:
        say("no AgentCore runtime configured; the API will run the fleet in-process only if strands is bundled")
    env = {"Variables": variables}
    try:
        lam.get_function(FunctionName=FUNCTION)
        lam.update_function_code(FunctionName=FUNCTION, ZipFile=code, Architectures=["arm64"])
        _wait(lam)
        lam.update_function_configuration(FunctionName=FUNCTION, Timeout=29, MemorySize=1024,
                                          Environment=env, Handler="vitaheart.lambda_handler.handler")
        _wait(lam)
        say("updated function")
    except ClientError:
        lam.create_function(FunctionName=FUNCTION, Runtime="python3.12", Role=role_arn,
                            Handler="vitaheart.lambda_handler.handler", Code={"ZipFile": code},
                            Timeout=29, MemorySize=1024, Architectures=["arm64"], Environment=env,
                            Description="Vita Heart API (FastAPI via Mangum)")
        _wait(lam)
        say("created function")


def ensure_api(lam, account: str) -> str:
    api = boto3.client("apigatewayv2", region_name=REGION)
    existing = [a for a in api.get_apis()["Items"] if a["Name"] == API_NAME]
    fn_arn = f"arn:aws:lambda:{REGION}:{account}:function:{FUNCTION}"
    if existing:
        return existing[0]["ApiEndpoint"]
    created = api.create_api(Name=API_NAME, ProtocolType="HTTP", Target=fn_arn,
                             CorsConfiguration={"AllowOrigins": ["*"], "AllowMethods": ["*"], "AllowHeaders": ["*"]})
    api_id = created["ApiId"]
    try:
        lam.add_permission(FunctionName=FUNCTION, StatementId="apigateway-invoke",
                           Action="lambda:InvokeFunction", Principal="apigateway.amazonaws.com",
                           SourceArn=f"arn:aws:execute-api:{REGION}:{account}:{api_id}/*")
    except ClientError as e:
        if "ResourceConflict" not in str(e):
            raise
    say(f"created API {api_id}")
    return created["ApiEndpoint"]


def main(infra_only: bool) -> None:
    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    iam, ddb, lam = session.client("iam"), session.client("dynamodb"), session.client("lambda")
    role_arn = ensure_role(iam)
    ensure_table(ddb)
    bucket = ensure_bucket(session.client("s3"), account)
    if not infra_only:
        ensure_function(lam, role_arn, build_zip(), bucket)
    url = ensure_api(lam, account)
    (ROOT / "docs" / "URLS.md").write_text(f"# Live URLs\n\n- API: {url}\n- Health: {url}/health\n- Demo board: {url}/board?household=AHMET1\n")
    say(f"API: {url}")


if __name__ == "__main__":
    main(infra_only="--infra" in sys.argv)
