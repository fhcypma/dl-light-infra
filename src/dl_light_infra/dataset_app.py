#!/usr/bin/env python3
from typing import Dict, Optional
import aws_cdk as cdk
from dl_light_infra.stack.data_stack import DataStack
from dl_light_infra.stack.etl_stack import EtlStack


def create_dataset_app(
    *,
    name: str,
    env: str,
    region: str = "eu-west-1",
    data_account: str,
    etl_account: str,
    ecr_repository_arn: str,
    etl_image_version: str,
    tags: Optional[Dict[str, str]],
) -> cdk.App:
    data_env = cdk.Environment(account=data_account, region=region)
    etl_env = cdk.Environment(account=etl_account, region=region)

    app = cdk.App()

    data_stack = DataStack(
        scope=app,
        dtap=env,
        data_set_name=name,
        etl_account_id=etl_account,
        tags=tags,
        env=data_env,
    )

    EtlStack(
        scope=app,
        dtap=env,
        data_set_name=name,
        data_buckets=data_stack.buckets,
        ecr_repository_arn=ecr_repository_arn,
        etl_image_version=etl_image_version,
        tags=tags,
        env=etl_env,
    )

    return app


# vpc_stack = VpcStack(
#     scope=app,
#     dtap=dtap,
#     cidr=settings.infra.vpc.cidr,
#     tags=aws_tags,
#     env=etl_env,
#     )

# workflow_manager_stack = WorkflowManagerStack(
#     scope=app,
#     dtap=dtap,
#     mwaa_bucket_name=settings.infra.mwaa.bucket_name,
#     mwaa_environment_class=settings.infra.mwaa.environment_class,
#     mwaa_max_workers=settings.infra.mwaa.max_workers,
#     vpc=vpc_stack.vpc,
#     tags=aws_tags,
#     env=etl_env,
#     )