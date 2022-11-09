from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ecr as ecr

from dl_light_infra.util.bucket_constructs import create_bucket
from dl_light_infra.stack.types import DataSetStack


def flatten(list_to_flatten: List[Any]):
    return [item for sublist in list_to_flatten for item in sublist]


class EtlStack(DataSetStack):
    """
    Contains
    - EtlRole, with s3 readwrite permissions
    - Ingestion application as Lambada
    """

    def __init__(
        self,
        scope: cdk.App,
        dtap: str,
        data_set_name: str,
        data_buckets: List[Union[s3.Bucket, s3.IBucket]],
        ecr_repository_arn: str,
        etl_image_version: str,
        tags: Optional[Dict[str, str]],
        **kwargs,
    ) -> None:

        super().__init__(
            scope,
            stack_name=self.__class__.__name__,
            dtap=dtap,
            data_set_name=data_set_name,
            tags=tags,
            **kwargs,
        )

        # Create role that executes all ETL
        self.etl_role = iam.Role(
            self,
            "EtlRole",
            role_name=self.construct_name("EtlRole"),
            description="Role for ETL execution for this dataset",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
        )

        # Grant access for the role to read/write to the S3 buckets
        self.etl_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=flatten(
                    [
                        [bucket.bucket_arn, bucket.arn_for_objects("*")]
                        for bucket in data_buckets
                    ]
                ),
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
            )
        )

        repo = ecr.Repository.from_repository_arn(
            self, "SparkOnLambdaRepo", ecr_repository_arn
        )

        lambda_.DockerImageFunction(
            self,
            "EtlApplicationsFunction",
            function_name=self.construct_name("EtlApplicationsFunction"),
            description=f"Lambda function wrapping {self.data_set_name} ETL application(s)",
            role=self.etl_role,
            code=lambda_.DockerImageCode.from_ecr(
                repository=repo,
                tag_or_digest=etl_image_version,
            ),
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment={"ENV_FOR_DYNACONF": dtap},
            timeout=cdk.Duration.seconds(100),
            memory_size=512,
        )

        # Grant access to the role to write to cloudwatch
        self.etl_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
            )
        )

        # Create bucket to place code
        self.code_bucket = create_bucket(self, dtap, data_set_name, "code")
