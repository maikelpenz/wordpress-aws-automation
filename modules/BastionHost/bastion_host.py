import sys
import os.path

from troposphere import Template, Tags, Ref, GetAtt, Parameter, ImportValue, Output, Export
from troposphere.ec2 import SecurityGroup, SecurityGroupRule, Instance

template = Template()
template.add_version('2010-09-09')

template.add_description("BastionHost Instance")


class BastionHost:
    def __init__(self, stage, key_name, security_group_name, instance_name, instance_type, 
                 instance_ami, bastion_vpc_name, bastion_vpc_subnets):
        self.stage = stage
        self.key_name = key_name
        self.security_group_name = security_group_name
        self.instance_name = instance_name
        self.instance_type = instance_type
        self.instance_ami = instance_ami
        self.bastion_vpc_subnets = bastion_vpc_subnets
        self.bastion_vpc_name = bastion_vpc_name

    def create_bastion_host(self):

        template = Template()
        template.add_version('2010-09-09')

        # Wordpress preparation: format vpc name and dump public subnets in a separate list

        vpc_name_formatted = ''.join(
            e for e in self.bastion_vpc_name if e.isalnum()).capitalize()
        
        filter_public_subnets = filter(lambda x : x["type"] == "public", self.bastion_vpc_subnets)

        public_subnets = []
        for subnet in filter_public_subnets:
            subnet_name_formatted = ''.join(e for e in subnet["name"] if e.isalnum()).capitalize()

            public_subnets.append(ImportValue("{}{}{}SubnetId".format(self.stage, vpc_name_formatted, subnet_name_formatted)))

        bastion_host_security_group = template.add_resource(
            SecurityGroup(
                "{}BastionHostSecurityGroup".format(self.stage),
                GroupName=self.security_group_name,
                GroupDescription="Enables external ssh access to the bastion host",
                VpcId=ImportValue("{}{}VpcId".format(self.stage,vpc_name_formatted)),
                SecurityGroupIngress=[
                    SecurityGroupRule(
                        IpProtocol="tcp",
                        FromPort="22",
                        ToPort="22",
                        CidrIp="0.0.0.0/0"
                    )
                ]
            )
        )

        template.add_resource(
            Instance(
                "{}BastionHost".format(self.stage),
                Tags=Tags(
                    Name=self.instance_name
                ),
                SecurityGroupIds=[Ref(bastion_host_security_group)],
                InstanceType=self.instance_type,
                ImageId=self.instance_ami,
                KeyName=self.key_name,
                SubnetId=next(iter(public_subnets))
            )
        )

        template.add_output(
            [
                Output(
                    "{}BastionHostSecurityGroupID".format(self.stage),
                    Description="Group ID of the security group",
                    Value=Ref(bastion_host_security_group),
                    Export=Export("{}BastionHostSecurityGroupID".format(self.stage))
                )
            ]
        )

        f = open("modules/template_bastion_host.yaml", 'w')
        print(template.to_yaml(), file=f)
