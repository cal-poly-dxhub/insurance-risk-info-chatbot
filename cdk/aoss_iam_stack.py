#!/usr/bin/env python3
import json

import aws_cdk as cdk
from aws_cdk import (
  Stack,
  aws_iam as iam
)
from constructs import Construct

class AOSSIamStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #################################################################################
    # IAM Role and Instance Profile for EC2
    #################################################################################
    aoss_role = iam.Role(self, "ec2-helpdesk-role",
      assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonBedrockFullAccess'),
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonOpenSearchServiceFullAccess'),
      ]
    )

    # Create instance profile and add the role to it
    aoss_instance_profile = iam.InstanceProfile(self, "ec2-helpdesk-instance-profile",
      role=aoss_role,
      instance_profile_name="ec2-helpdesk-instance-profile"
    )

    # Export both role and instance profile as stack outputs
    self.aoss_role = aoss_role
    self.aoss_instance_profile = aoss_instance_profile