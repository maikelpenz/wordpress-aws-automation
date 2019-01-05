# from Shared.cloudformationhelper import CloudformationHelper
# import sys
# import os.path

from troposphere import Template, Tags, Ref, ImportValue
from troposphere.ec2 import VPCPeeringConnection, Route

# sys.path.append(
#     os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

# cf_helper = CloudformationHelper()
# cf_helper.profile = "default"

class PeerVPC:
    def __init__(self,stage,source_vpc_name, source_cidr_block, target_vpc_name, target_cidr_block):

        self.stage = stage
        self.source_vpc_name = source_vpc_name
        self.target_vpc_name = target_vpc_name
        self.source_cidr_block = source_cidr_block
        self.target_cidr_block = target_cidr_block

    def create_peering(self):

        template = Template()
        template.add_version('2010-09-09')

        source_vpc_name_formatted = ''.join(
            e for e in self.source_vpc_name if e.isalnum()).capitalize()

        target_vpc_name_formatted = ''.join(
            e for e in self.target_vpc_name if e.isalnum()).capitalize()

        vpc_peering_connection = template.add_resource(
            VPCPeeringConnection(
                '{}{}{}VpcPeering'.format(self.stage,source_vpc_name_formatted,target_vpc_name_formatted),
                VpcId=ImportValue("{}{}VpcId".format(self.stage,source_vpc_name_formatted)),
                PeerVpcId=ImportValue("{}{}VpcId".format(self.stage,target_vpc_name_formatted)),
                Tags=Tags(
                    Name="{}_{}_{}_peering".format(self.stage,source_vpc_name_formatted,target_vpc_name_formatted)
                )
            )
        )

        template.add_resource(
            Route(
                '{}{}PublicRoutePeeringRule'.format(self.stage,source_vpc_name_formatted),                
                VpcPeeringConnectionId=Ref(vpc_peering_connection),
                DestinationCidrBlock=self.target_cidr_block,
                RouteTableId=ImportValue("{}{}PublicRouteTableId".format(self.stage,source_vpc_name_formatted))
            )
        )

        template.add_resource(
            Route(
                '{}{}PrivateRoutePeeringRule'.format(self.stage,source_vpc_name_formatted),
                VpcPeeringConnectionId=Ref(vpc_peering_connection),
                DestinationCidrBlock=self.target_cidr_block,
                RouteTableId=ImportValue("{}{}PrivateRouteTableId".format(self.stage,source_vpc_name_formatted))
            )
        )

        template.add_resource(
            Route(
                '{}{}PublicRoutePeeringRule'.format(self.stage,target_vpc_name_formatted),
                VpcPeeringConnectionId=Ref(vpc_peering_connection),
                DestinationCidrBlock=self.source_cidr_block,
                RouteTableId=ImportValue("{}{}PublicRouteTableId".format(self.stage,target_vpc_name_formatted))
            )
        )

        template.add_resource(
            Route(
                '{}{}PrivateRoutePeeringRule'.format(self.stage,target_vpc_name_formatted),
                VpcPeeringConnectionId=Ref(vpc_peering_connection),
                DestinationCidrBlock=self.source_cidr_block,
                RouteTableId=ImportValue("{}{}PrivateRouteTableId".format(self.stage,target_vpc_name_formatted))
            )
        )

        f = open("modules/template_peer_vpcs.yaml", 'w')
        print(template.to_yaml(), file=f)