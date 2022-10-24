from typing import Dict

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
from util.naming_conventions import to_dot, to_upper_camel

from stack.types import DataSetStack


class DataStack(DataSetStack):
    """
    Contains
    - buckets
    """

    def __init__(
        self,
        scope: cdk.App,
        dtap: str,
        data_set_name: str,
        etl_account_id: str,
        tags: Dict[str, str],
        **kwargs,
    ) -> None:

        super().__init__(
            scope,
            stack_name="DataStack",
            dtap=dtap,
            data_set_name=data_set_name,
            tags=tags,
            **kwargs,
        )

        etl_principal = iam.ArnPrincipal(
            f"arn:aws:iam::{etl_account_id}:role/{self.construct_name('EtlRole')}"
        )

        # Landing bucket, for external data producers to push data
        landing_bucket = self.create_bucket(bucket_id="landing")
        landing_bucket.grant_read_write(etl_principal)
        landing_bucket.add_lifecycle_rule(
            expiration=cdk.Duration.days(30),
        )

        # Permanent bucket, with additional delete protection
        preserve_bucket = self.create_delete_protected_bucket(
            bucket_id="preserve", read_write_access=etl_principal
        )

        # Bucket for all other data
        processing_bucket = self.create_bucket(bucket_id="processing")
        processing_bucket.grant_read_write(etl_principal)

        self.buckets = [landing_bucket, preserve_bucket, processing_bucket]

    def create_bucket_name(self, bucket_id: str):
        return to_dot(f"yds.{self.dtap}.{self.data_set_name}.{bucket_id}")

    def create_bucket(self, bucket_id: str) -> s3.Bucket:
        bucket_name = self.create_bucket_name(bucket_id)
        return s3.Bucket(
            self,
            to_upper_camel(f"{bucket_name}Bucket"),
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Destroy bucket on stack deletion (empty or not)
            auto_delete_objects=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
        )

    def create_delete_protected_bucket(
        self, bucket_id: str, read_write_access: iam.PrincipalBase = None
    ) -> s3.IBucket:
        """
        Create a bucket where objects cannot be deleted.
        Objects that are overwritten are retained via a non-current version and kept for 30 days.
        To delete an object, users must have s3:BypassGovernanceRetention, and include x-amz-bypass-governance-retention:true explicitly as a header.
        Cli example; `aws s3api delete-object --bucket my-bucket-name --key my/key --bypass-governance-retention`
        """
        bucket_name = self.create_bucket_name(bucket_id)
        cfn_bucket = s3.CfnBucket(
            self,
            to_upper_camel(f"{bucket_name}CfnBucket"),
            bucket_name=bucket_name,
            public_access_block_configuration=s3.CfnBucket.PublicAccessBlockConfigurationProperty(
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True,
            ),
            lifecycle_configuration=s3.CfnBucket.LifecycleConfigurationProperty(
                rules=[
                    s3.CfnBucket.RuleProperty(
                        status="Enabled",
                        noncurrent_version_expiration=s3.CfnBucket.NoncurrentVersionExpirationProperty(
                            noncurrent_days=30,
                        ),
                        expired_object_delete_marker=True,
                    )
                ]
            ),
            versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(
                status="Enabled",
            ),
            ownership_controls=s3.CfnBucket.OwnershipControlsProperty(
                rules=[
                    s3.CfnBucket.OwnershipControlsRuleProperty(
                        object_ownership="BucketOwnerEnforced"
                    )
                ]
            ),
            object_lock_enabled=True,
            object_lock_configuration=s3.CfnBucket.ObjectLockConfigurationProperty(
                object_lock_enabled="Enabled",
                rule=s3.CfnBucket.ObjectLockRuleProperty(
                    default_retention=s3.CfnBucket.DefaultRetentionProperty(
                        mode="GOVERNANCE",
                        years=99,
                    )
                ),
            ),
        )
        # Destroy bucket on stack deletion (only if empty)
        cfn_bucket.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        bucket = s3.Bucket.from_bucket_name(
            self,
            to_upper_camel(f"{bucket_name}Bucket"),
            cfn_bucket.ref,
        )

        policy_statements = [
            iam.PolicyStatement(
                sid="AllowSSLRequestsOnly",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[bucket.bucket_arn, bucket.arn_for_objects("*")],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            )
        ]
        if read_write_access:
            policy_statements += [
                iam.PolicyStatement(
                    sid="AllowFullAccess",
                    effect=iam.Effect.ALLOW,
                    principals=[read_write_access],
                    actions=[
                        "s3:ListBucket",
                        "s3:*Object",
                    ],
                    resources=[bucket.bucket_arn, bucket.arn_for_objects("*")],
                )
            ]

        # Enforce SSL
        s3.CfnBucketPolicy(
            self,
            to_upper_camel(f"{bucket_name}BucketPolicy"),
            bucket=bucket.bucket_name,
            policy_document=iam.PolicyDocument(statements=policy_statements),
        )

        return bucket
