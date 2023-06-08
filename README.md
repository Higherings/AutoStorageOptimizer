# AutoStorageOptimizer
Easy to configure automation to automatically apply AWS Compute Optimizer recommendations on EBS volumes
It uses CloudFormation, Lambda (Python 3.10), CloudWatch Events and AWS Compute Optimizer (Compute Optimizer should be already working on the account)

You can select the day to check the recommendatios, set the time when should be apply.

You can add Exceptions to never change an EBS to a specific type, Ex: io1, gp2

You can define a TAG to select the EBS Volumes SKIPPED by the Automation. You can set SNS Notifications for this automation.

If it's not working on your Region create an Issue and I will fix it.

> Version 1.0.0

### Files:
- autoStorageOptimizer-template.yml, CloudFormation template to Run in your account, it is already in a public S3 bucket

- autostorageoptimizer.py, Lambda code that actually do the job of implementing the recommendations, source code only for reviewing

- autostorageoptimizer.zip, Zip file used by the template to deploy de Lambda, it is already in a public S3 Bucket

## How To Deploy
Use AWS CloudFormation to deploy the following template:

https://higher-artifacts.s3.amazonaws.com/solutions/autoStorageOptimizer-template.yml

### Parameters:
- *Env Tag*, use to identified the components of the template

- *Exception Tag Key*, sets the Tag used to identify the EBS Volumes to SKIP

- *Exception Tag Value*, sets the Value of the Tag to identify the EBS Volumes to SKIP

- *Day*, specify the day of the week the recommendations will be applied (Mon-Sun)

- *Time*, specify at what time the changes to the EBS Volumes will occur (no downtime will happen) (UTC 24 hours syntax)

- *Tolerable Risk*, select the maximum tolerable Risk of the recommendation to apply

- *Exceptions*, you can add volumes types to NOT use, for example: io1, gp2

- *Email Address*, e-mail address to receive notifications of the implemmented recommendations

`If you edit the template remember to use LF end of lines.`

#### Notes:

- Function DOES modify EBS Volumes types (this will NOT require a reboot) 

- You can set a Tag Key and Value to select the group of EBS Volumes to SKIP modification

## To-Do
- Make a more restrictive policy for the Lambda

- A better error management

- Improve SNS Notifications
