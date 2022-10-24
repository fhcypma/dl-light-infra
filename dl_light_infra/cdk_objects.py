from dataclasses import dataclass
import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
from constructs import Construct

from dl_light_infra.util.naming_conventions import to_upper_camel

# class DataSet:
#     def __init__(self, name: str, env: str, data_account_id: str, etl_account_id: str) -> None:
#         self.name = name
#         self.env = env
#         self.data_account_id = data_account_id
#         self.buckets: Dict[str, TableRoot] = {
#             "landing": Bucket(to_dot(f"yds.{env}.{name}.landing")),
#             "preserve": ProtectedBucket(to_dot(f"yds.{env}.{name}.preserve")),
#             "processing": Bucket(to_dot(f"yds.{env}.{name}.processing")),
#             "serving": Bucket(to_dot(f"yds.{env}.{name}.serving")),
#         }


@dataclass
class Bucket:
    name: str

    def id(self):
        return to_upper_camel(f"{self.name}Bucket")

    def get_path(self):
        return "s3://{name}"

    def cdk_ref(self, scope) -> s3.Bucket:
        """Reference an existing bucket"""
        bucket = s3.Bucket.from_bucket_name(scope, self.id(), self.name)
        return bucket

    def cdk_construct(
        self, scope: Construct, read_write_access: iam.PrincipalBase = None
    ) -> s3.Bucket:
        """Create a normal bucket without versioning"""
        bucket = s3.Bucket(
            scope,
            self.id(),
            bucket_name=self.name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Destroy bucket on stack deletion (empty or not)
            auto_delete_objects=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
        )

        if read_write_access:
            bucket.grant_read_write(read_write_access)

        return bucket


@dataclass
class ProtectedBucket(Bucket):
    def cdk_construct(
        self, scope: Construct, read_write_access: iam.PrincipalBase
    ) -> s3.Bucket:
        """
        Create a bucket where objects cannot be deleted.
        Objects that are overwritten are retained via a non-current version and kept for 30 days.
        To delete an object, users must have s3:BypassGovernanceRetention, and include x-amz-bypass-governance-retention:true explicitly as a header.
        Cli example; `aws s3api delete-object --bucket my-bucket-name --key my/key --bypass-governance-retention`
        """
        cfn_bucket = s3.CfnBucket(
            scope,
            self.id() + "Cfn",
            bucket_name=self.name,
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
            scope,
            self.id(),
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
            scope,
            self.id() + "Policy",
            bucket=bucket.bucket_name,
            policy_document=iam.PolicyDocument(statements=policy_statements),
        )

        return bucket
