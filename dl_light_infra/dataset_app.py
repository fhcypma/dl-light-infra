#!/usr/bin/env python3
from typing import Dict
import aws_cdk as cdk
from stack.data_stack import DataStack
from stack.etl_stack import EtlStack

def create_dataset_app(
    *,
    name: str,
    env: str,
    region: str = "eu-west-1",
    data_account: str,
    etl_account: str,
    tags: Dict[str, str] = None,
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

    etl_stack = EtlStack(
        scope=app, 
        dtap=env,
        data_set_name=name,
        data_buckets=data_stack.buckets,
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


