# wordpress aws automation

This project is designed to automate the creation of a Wordpress environment on AWS.

The architecture is similar to the wordpress setup found as part of the [AWS Certified Solutions Architecht-Associate course](https://acloud.guru/learn/aws-certified-solutions-architect-associate) provided by the acloudguru platform, however besides automating it, this project goes beyond by setting up VPCs for better security.

## Table of Contents  
[Architecture](#architecture)  
[Requirements](#requirements)  
[Usage](#Usage)  
<a name="architecture"/>
## Architecture
&nbsp;<a name="requirements"/>
## Requirements
* [Python3](https://www.python.org/downloads/)  
* [Troposphere](https://github.com/cloudtools/troposphere)  

Library used to generate CloudFormation templates
```powershell
$ pip install troposphere
```
* [Stacker](https://github.com/cloudtools/stacker)  

Tool and Library that orchestrate the creation and updates of CloudFormation stacks
```powershell
$ pip install --upgrade pip setuptools
$ pip install stacker
```
&nbsp;<a name="usage"/>
## Usage