#cdk bootstrap aws://ACCOUNT-NUMBER/REGION
import aws_cdk as cdk

from aoss_vector_stack import AOSSVectorStack
from aoss_iam_stack import AOSSIamStack

app = cdk.App()

aoss_iam_stack = AOSSIamStack(app, "cdk-aoss-iam-stack")
aoss_stack = AOSSVectorStack(app, "cdk-aoss-vector-stack")

app.synth()