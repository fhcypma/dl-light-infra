from typing import Dict
import aws_cdk as cdk

from util.naming_conventions import to_upper_camel

class BasicStack(cdk.Stack):
    """
    Base class for all stacks
    Creates tags on all constructs
    Has some naming convention utility methods
    """

    def __init__(
        self, scope: cdk.App, 
        stack_name: str, 
        dtap: str,
        tags: Dict[str, str],
        **kwargs) -> None:

        self.dtap = dtap
        super().__init__(scope, self.construct_name(stack_name), **kwargs)

        # Setting tags to all resources in stack
        for tag_name, tag_value in tags.items():
            cdk.Tags.of(self).add(tag_name, tag_value)

    def construct_name(self, name: str):
        """Constructs the name for a CDK construct in UpperCamelCase"""
        return to_upper_camel(f"{self.dtap}-{name}")


class DataSetStack(BasicStack):
    """
    Base class for all stacks for a dataset
    """

    def __init__(
        self, scope: cdk.App, 
        stack_name: str, 
        dtap: str,
        data_set_name: str,
        tags: Dict[str, str],
        **kwargs) -> None:

        self.data_set_name = data_set_name
        super().__init__(scope, stack_name, dtap, tags, **kwargs)

    def construct_name(self, name: str):
        """Constructs the name for a CDK construct in UpperCamelCase"""
        return to_upper_camel(f"{self.dtap}-{self.data_set_name}-{name}")
