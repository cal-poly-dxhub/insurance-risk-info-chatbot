import json

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  cloudformation_include as cfn_inc,
  aws_opensearchserverless as aws_opss,
  aws_iam as iam
)
from constructs import Construct


class AOSSVectorStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    collection_name = self.node.try_get_context('collection_name') or "chatbot"

    network_security_policy = json.dumps([{
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "dashboard"
        },
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AllowFromPublic": True
    }], indent=2)

    cfn_network_security_policy = aws_opss.CfnSecurityPolicy(self, "NetworkSecurityPolicy",
      policy=network_security_policy,
      name=f"{collection_name}-security-policy",
      type="network"
    )

    encryption_security_policy = json.dumps({
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AWSOwnedKey": True
    }, indent=2)

    cfn_encryption_security_policy = aws_opss.CfnSecurityPolicy(self, "EncryptionSecurityPolicy",
      policy=encryption_security_policy,
      name=f"{collection_name}-security-policy",
      type="encryption"
    )

    cfn_collection = aws_opss.CfnCollection(self, "chatbot-handbook",
      name=collection_name,
      description="Collection to be used for vector analysis using OpenSearch Serverless",
      type="VECTORSEARCH" # [SEARCH, TIMESERIES]
    )
    cfn_collection.add_dependency(cfn_network_security_policy)
    cfn_collection.add_dependency(cfn_encryption_security_policy)
    
    data_access_policy = json.dumps([
      {
        "Rules": [
          {
            "Resource": [
              f"collection/{collection_name}"
            ],
            "Permission": [
              "aoss:CreateCollectionItems",
              "aoss:DeleteCollectionItems",
              "aoss:UpdateCollectionItems",
              "aoss:DescribeCollectionItems"
            ],
            "ResourceType": "collection"
          },
          {
            "Resource": [
              f"index/{collection_name}/*"
            ],
            "Permission": [
              "aoss:CreateIndex",
              "aoss:DeleteIndex",
              "aoss:UpdateIndex",
              "aoss:DescribeIndex",
              "aoss:ReadDocument",
              "aoss:WriteDocument"
            ],
            "ResourceType": "index"
          }
        ],
        "Principal": [
          f"arn:aws:iam::{Stack.of(self).account}:root"  # Grant access to the AWS account
        ],
        "Description": "data-access-rule"
      }
    ], indent=2)

 #XXX: max length of policy name is 32
    data_access_policy_name = f"{collection_name}-{collection_name}-policy"
    assert len(data_access_policy_name) <= 32

    cfn_access_policy = aws_opss.CfnAccessPolicy(self, "OpssDataAccessPolicy",
      name=data_access_policy_name,
      description="Policy for data access",
      policy=data_access_policy,
      type="data"
    )


    self.aoss_endpoint = cdk.CfnOutput(self, f'{self.stack_name}-Endpoint', value=cfn_collection.attr_collection_endpoint)

    # Not supported with AOSS
    # cdk.CfnOutput(self, f'{self.stack_name}-DashboardsURL', value=cfn_collection.attr_dashboard_endpoint)