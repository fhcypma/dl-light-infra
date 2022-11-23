from typing import Dict, Optional, List

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_ecr as ecr

from dl_light_infra.util.bucket_constructs import (
    create_bucket,
    create_read_write_policy_statement,
    name_to_arn,
)
from dl_light_infra.stack.types import DataSetStack


class EtlRoleStack(DataSetStack):
    """
    Contains
    - IAM Role to execute ETL
    """

    def __init__(
        self,
        scope: cdk.App,
        dtap: str,
        data_set_name: str,
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

        # Pass role/arn to other stacks
        self.etl_role_arn = self.etl_role.role_arn


class EtlStack(DataSetStack):
    """
    Contains
    - EtlRole managed policies
    - Ingestion application as Lambada
    """

    def __init__(
        self,
        scope: cdk.App,
        dtap: str,
        data_set_name: str,
        etl_role_arn: str,
        data_bucket_names: List[str],
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

        etl_irole = iam.Role.from_role_arn(self, "EtlRole", etl_role_arn)

        # Grant read/write for data buckets
        iam.ManagedPolicy(
            self,
            "ReadWriteDataPolicy",
            managed_policy_name=self.construct_name("ReadWriteDataPolicy"),
            description=f"Read-write access to the {self.data_set_name} S3 buckets",
            roles=[etl_irole],
            statements=[
                create_read_write_policy_statement(
                    [name_to_arn(name) for name in data_bucket_names]
                )
            ],
        )

        # Create Lambda using the given ECR image
        repo = ecr.Repository.from_repository_arn(
            self, "SparkOnLambdaRepo", ecr_repository_arn
        )
        lambda_.DockerImageFunction(
            self,
            "EtlApplicationsFunction",
            function_name=self.construct_name("EtlApplicationsFunction"),
            description=f"Lambda function wrapping {self.data_set_name} ETL application(s)",
            role=etl_irole,
            code=lambda_.DockerImageCode.from_ecr(
                repository=repo,
                tag_or_digest=etl_image_version,
            ),
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment={"ENV_FOR_DYNACONF": dtap},
            timeout=cdk.Duration.seconds(100),
            memory_size=512,
        )

        # Create bucket to place code
        self.code_bucket = create_bucket(self, dtap, data_set_name, "code")
        self.code_bucket.grant_read(etl_irole)
