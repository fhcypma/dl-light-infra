from typing import Dict, Optional, List

import aws_cdk as cdk
import aws_cdk.aws_iam as iam

from dl_light_infra.util.bucket_constructs import (
    create_bucket,
    create_delete_protected_bucket,
)
from dl_light_infra.stack.types import DataSetStack


class DataStack(DataSetStack):
    """
    Contains all data buckets
    """

    def __init__(
        self,
        scope: cdk.App,
        dtap: str,
        data_set_name: str,
        etl_role_arn: str,
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

        etl_principal = iam.ArnPrincipal(etl_role_arn)

        # Landing bucket, for external data producers to push data
        landing_bucket = create_bucket(
            self, dtap=dtap, data_set_name=data_set_name, bucket_id="landing"
        )
        landing_bucket.grant_read_write(etl_principal)
        landing_bucket.add_lifecycle_rule(
            expiration=cdk.Duration.days(30),
        )

        # Permanent bucket, with additional delete protection
        create_delete_protected_bucket(
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

    @staticmethod
    def get_bucket_ids() -> List[str]:
        """
        Returns a list of the bucket_ids this stack will create
        Convenience function for setting up role permissions before data buckets are created
        """
        return ["landing", "preserve", "processing"]
