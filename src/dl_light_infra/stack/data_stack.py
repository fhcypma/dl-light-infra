from typing import Dict, Optional

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3

from dl_light_infra.util.bucket_constructs import (
    create_bucket,
    create_delete_protected_bucket,
)
from dl_light_infra.stack.types import DataSetStack


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
        tags: Optional[Dict[str, str]],
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
        landing_bucket = create_bucket(
            self, dtap=dtap, data_set_name=data_set_name, bucket_id="landing"
        )
        landing_bucket.grant_read_write(etl_principal)
        landing_bucket.add_lifecycle_rule(
            expiration=cdk.Duration.days(30),
        )

        # Permanent bucket, with additional delete protection
        preserve_bucket = create_delete_protected_bucket(
            self,
            dtap=dtap,
            data_set_name=data_set_name,
            bucket_id="preserve",
            read_write_access=etl_principal,
        )

        # Bucket for all other data
        processing_bucket = create_bucket(
            self, dtap=dtap, data_set_name=data_set_name, bucket_id="processing"
        )
        processing_bucket.grant_read_write(etl_principal)

        self.buckets = [landing_bucket, preserve_bucket, processing_bucket]
