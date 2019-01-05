from troposphere import Template, Tags, Ref, GetAtt, Output, Export, Sub, Parameter
from troposphere.ec2 import Route, VPCGatewayAttachment, SubnetRouteTableAssociation, \
    VPC, Subnet, RouteTable, EIP, Instance, InternetGateway,  \
    SecurityGroup, NatGateway

class PrivateVPC:
    def __init__(self, stage, vpc_name, vpc_cidr_block, subnets):

        self.stage = stage
        self.vpc_name = vpc_name
        self.vpc_cidr_block = vpc_cidr_block
        self.subnets = subnets
        self.output_list = []

    def create_vpc(self):

        template = Template()
        template.add_version('2010-09-09')

        vpc_name_formatted = ''.join(
            e for e in self.vpc_name if e.isalnum()).capitalize()

        private_vpc = template.add_resource(
            VPC(
                '{}{}'.format(self.stage, vpc_name_formatted),
                CidrBlock=self.vpc_cidr_block,
                EnableDnsHostnames="true",
                Tags=Tags(
                    Name="{}_{}".format(self.stage,vpc_name_formatted)
                )
            )
        )

        internet_gateway = template.add_resource(
            InternetGateway(
                '{}{}InternetGateway'.format(self.stage, vpc_name_formatted),
                Tags=Tags(
                    Name="{}_{}_internet_gateway".format(self.stage,vpc_name_formatted)
                )
            )
        )

        template.add_resource(
            VPCGatewayAttachment(
                '{}{}InternetGatewayAttachment'.format(self.stage, vpc_name_formatted),
                VpcId=Ref(private_vpc),
                InternetGatewayId=Ref(internet_gateway)
            )
        )

        public_route_table = template.add_resource(
            RouteTable(
                '{}{}PublicRouteTable'.format(self.stage, vpc_name_formatted),
                VpcId=Ref(private_vpc),
                Tags=Tags(
                    Name="{}_{}_public_route_table".format(self.stage,vpc_name_formatted)
                )
            )
        )

        template.add_resource(
            Route(
                '{}{}PublicRouteIGRule'.format(self.stage,vpc_name_formatted),
                DependsOn='{}{}InternetGatewayAttachment'.format(self.stage, vpc_name_formatted),
                GatewayId=Ref(internet_gateway),
                DestinationCidrBlock='0.0.0.0/0',
                RouteTableId=Ref(public_route_table)
            )
        )

        private_route_table = template.add_resource(
            RouteTable(
                '{}{}PrivateRouteTable'.format(self.stage, vpc_name_formatted),
                VpcId=Ref(private_vpc),
                Tags=Tags(
                    Name="{}_{}_private_route_table".format(self.stage,vpc_name_formatted)
                )
            )
        )

        for sub in self.subnets:

            subnet_name = sub["name"]
            subnet_type = sub["type"]
            subnet_cidr_block = sub["cidr_block"]
            subnet_availability_zone = sub["availability_zone"]
            subnet_map_ip_on_launch = sub["map_ip_on_launch"]
            subnet_nat_gateway = sub["nat_gateway"]

            subnet_name_formatted = ''.join(
                e for e in subnet_name if e.isalnum()).capitalize()

            subnet = template.add_resource(
                Subnet(
                    '{}{}{}Subnet'.format(self.stage,vpc_name_formatted,subnet_name_formatted),
                    CidrBlock=subnet_cidr_block,
                    AvailabilityZone=subnet_availability_zone,
                    MapPublicIpOnLaunch=subnet_map_ip_on_launch,
                    VpcId=Ref(private_vpc),
                    Tags=Tags(
                        Name="{}_{}_{}".format(self.stage,vpc_name_formatted,subnet_name)
                    )
                )
            )

            self.output_list.append(
                Output(
                    '{}{}{}SubnetId'.format(self.stage, vpc_name_formatted,subnet_name_formatted),
                    Description="ID of the Subnet",
                    Value=Ref(subnet),
                    Export=Export('{}{}{}SubnetId'.format(self.stage, vpc_name_formatted,subnet_name_formatted))
                )
            )

            if subnet_nat_gateway == "true":
                nat_eip = template.add_resource(EIP(
                    '{}{}{}NatEip'.format(self.stage, vpc_name_formatted,subnet_name_formatted),
                    Domain="private_vpc"
                ))

                nat_gateway = template.add_resource(NatGateway(
                    '{}{}{}NatGateway'.format(self.stage,vpc_name_formatted,subnet_name_formatted),
                    AllocationId=GetAtt(nat_eip, 'AllocationId'),
                    SubnetId=Ref(subnet)
                ))

                template.add_resource(
                    Route(
                        '{}{}{}NatGatewayRouteRule'.format(self.stage,vpc_name_formatted,subnet_name_formatted),
                        NatGatewayId=Ref(nat_gateway),
                        DestinationCidrBlock='0.0.0.0/0',
                        RouteTableId=Ref(private_route_table)
                    )
                )

            if subnet_type == "public":
                template.add_resource(
                    SubnetRouteTableAssociation(
                        '{}{}{}SubnetRouteAssociation'.format(self.stage,vpc_name_formatted,subnet_name_formatted),
                        SubnetId=Ref(subnet),
                        RouteTableId=Ref(public_route_table)
                    )
                )
            elif subnet_type == "private":
                template.add_resource(
                    SubnetRouteTableAssociation(
                        '{}{}{}SubnetRouteAssociation'.format(self.stage,vpc_name_formatted,subnet_name_formatted),
                        SubnetId=Ref(subnet),
                        RouteTableId=Ref(private_route_table)
                    )
                )

        # #################### OUTPUTS #####################

        self.output_list.append(
            Output(
                "{}{}VpcId".format(self.stage, vpc_name_formatted),
                Description="ID of {} VPC".format(vpc_name_formatted),
                Value=Ref(private_vpc),
                Export=Export("{}{}VpcId".format(self.stage, vpc_name_formatted))
            )
        )

        self.output_list.append(
            Output(
                "{}{}PublicRouteTableId".format(self.stage,vpc_name_formatted),
                Description="ID of {} VPC".format(vpc_name_formatted),
                Value=Ref(public_route_table),
                Export=Export("{}{}PublicRouteTableId".format(self.stage,vpc_name_formatted))
            )
        )

        self.output_list.append(
            Output(
                "{}{}PrivateRouteTableId".format(self.stage,vpc_name_formatted),
                Description="ID of {} VPC".format(vpc_name_formatted),
                Value=Ref(private_route_table),
                Export=Export("{}{}PrivateRouteTableId".format(self.stage,vpc_name_formatted))
            )
        )

        template.add_output(self.output_list)

        f = open("modules/template_vpc_{}.yaml".format(vpc_name_formatted), 'w')
        print(template.to_yaml(), file=f)