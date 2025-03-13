# insurance-risk-info-chatbot
This chatbot was designed to ingest risk management data and answer questions based on information contained in the set.

# Collaboration
Thanks for your interest in our solution.  Having specific examples of replication and cloning allows us to continue to grow and scale our work. If you clone or download this repository, kindly shoot us a quick email to let us know you are interested in this work!

[wwps-cic@amazon.com] 

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**

(a) is for informational purposes only, 

(b) represents current AWS product offerings and practices, which are subject to change without notice, and 

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers. 

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limitted to, relaxed authentication and authorization and a lack of strict adherence to security best practices

**All work produced is open source. More information can be found in the GitHub repo.**

## Authors
- Nick Riley - njriley@calpoly.edu
- Noor Dhaliwal - rdhali07@calpoly.edu

## Table of Contents
- [Overview](#chatbot-overview)
- [Backend Services](#backend-services)
- [Additional Resource Links](#additional-resource-links)

- The [DxHub](https://dxhub.calpoly.edu/challenges/)
- 
## Steps to Deploy and Configure the System

### Before We Get Started

- Request and ensure model access within AWS Bedrock, specifically:
    - Claude 3.5 Sonnet V2
    - Claude 3
    - Claude 3 Haiku
    - Titan Embeddings

The corresponding model IDs are:
```
anthropic.claude-3-5-sonnet-20241022-v2:0
anthropic.claude-3-sonnet-20240229-v1:0
anthropic.claude-3-haiku-20240307-v1:0
amazon.titan-embed-text-v2:0
```

### 1. Deploy an EC2 Instance
- Deploy an EC2 instance in your desired region and configure it as required (i.e grant a role with required managed polices).


- Normal operation will only require AmazonBedrockFullAccess, AmazonOpenSearchServiceFullAccess and perhaps AmazonS3FullAccess) 

- Additional settings  t3.large and security group to allow SSH traffic and port 8501 for web access

### 2. Pull the Git Repository
- Install git using this command 
    ```
    sudo yum install git
    ```

- Clone the necessary repository to the EC2 instance:
    ```bash
    git clone https://github.com/cal-poly-dxhub/insurance-risk-info-chatbot
    ```

### 3. Run OpenSearch CDK

- Install Node.js for cdk
    ```
    sudo yum install -y nodejs
    ```

- Install cdk
    ```
    sudo npm install -g aws-cdk
    ```

- Install python 3.11
    ```
    sudo yum install python3.11
    ```
    
- Install pip3.11
    ```
    curl -O https://bootstrap.pypa.io/get-pip.py

    python3.11 get-pip.py --user
    ```

- Create and activate venv and install requirements
    ```
    python3.11 -m venv env

    source env/bin/activate

    cd insurance-risk-info-chatbot/demo

    pip3.11 install -r requirements.txt
    ```

- CDK deploy 
    ```
    cd ~/insurance-risk-info-chatbot/cdk

    cdk synth

    cdk bootstrap

    cdk deploy --all

    ```
    Note: Copy the output value of the cdk stack creation cdk-aoss-vector-stack.cdkaossvectorstackEndpoint 
    -- Example
    ```
       https://12345myendpoint.us-west-2.aoss.amazonaws.com
    ```

    Update the domain value listed in create_os_index.py

      Line 14:
      ```
      FROM domain_endpoint = "YOUR-DOMAIN-HERE"
      TO: 12345myendpoint.us-west-2.aoss.amazonaws.com
      ```
    NOTE: remove https:// from output value

  Now run create index
  ```
   python create_os_index.py
  ```


### 4. Prepare dataset for import
- Create a set of URLs that you want to use as a source for your chatbot
- Update data_processing/urls.txt

- Example path: `/home/ec2-user/data_processing/urls.txt`

Create an S3 bucket in your account to hold downloaded files and not the name of the bucket.
Create a folder to store unlocked PDFs

Next we need to update the following files:
 doc_to_opensearch.py
 document_processor.py
 download_prism.py
```
 cd ~/insurance-risk-info-chatbot/data_processing
 vi doc_to_opensearch.py
     Update:
     Line 13 -> BUCKET_NAME = "chatbot_data"
     Line 176 -> password = 'YOUR_PASSWORD'
 save file

 vi document_processor.py
     Update:
     Line 172 -> extractor = Textractor(region_name="YOURREGION")
     Line 740 -> domain_endpoint = "YOUR_OPENSEARCH_ENDPOINT"
     Line 894 -> domain_endpoint = "YOUR_OPENSEARCH_ENDPOINT"
     Line 897 -> awsauth = AWSV4SignerAuth(credentials, "YOUR_AWS_REGION", service)

 vi download_prism.py
     Update:
     Line 15: BUCKET_NAME = "YOUR_BUCKET_NAME"
     Line 16: UNLOCKED_PDFS_FOLDER = "YOUR_FOLDER_NAME"
     Line 288: PASSWORD = "YOUR_PASSWORD"


```
    
Enter the password used to unlock the PDFs on line 288

Save changes

Next modify document_processor.py
```
vi document_processor.py

Update INDEX_NAME on line 38
```
Lastly modify doc_to_opensearch.py

```
Update BUCKET_NAME on Line 16
Update password on Line 179
```

### 5. Run data import process
- python download_prism.py
- p
### 6. Run the streamlit app in the `chatbot` directory with
```
cd /home/ec2-user/insurance-risk-info-chatbot/demo/

streamlit run main.py
```
By following these steps, you will have a properly deployed and configured system with the desired settings.


## Known Bugs/Concerns
- Quick PoC with no intent verification or error checking
- Hardcoded placeholder text in various components.

## Support
For any queries or issues, please contact:
- Darren Kraker, Sr Solutions Architect - dkraker@amazon.com
- Nick Riley, Software Developer Intern - njriley@calpoly.edu
- Noor Dhaliwal, Software Developer Intern - rdhali07@calpoly.edu

