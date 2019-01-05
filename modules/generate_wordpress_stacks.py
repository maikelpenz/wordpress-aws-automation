from PrivateVPC import private_vpc
from PeerVPC import peer_vpc
from BastionHost import bastion_host
from Wordpress import wordpress

# Top Level Variables
stage = "dev"

# Production VPC
private_vpc_name = "PrivateVPC"
private_cidr_block = "172.16.0.0/22"
private_vpc_subnets = [
    {"name":"public_subnet_a", "type":"public", "cidr_block":"172.16.0.0/24", "availability_zone":"us-east-1a", "map_ip_on_launch":"true", "nat_gateway":"true"},
    {"name":"public_subnet_b", "type":"public", "cidr_block":"172.16.1.0/24", "availability_zone":"us-east-1b", "map_ip_on_launch":"true", "nat_gateway":"false"},
    {"name":"private_subnet_a", "type":"private", "cidr_block":"172.16.2.0/24", "availability_zone":"us-east-1a", "map_ip_on_launch":"false", "nat_gateway":"false"},
    {"name":"private_subnet_b", "type":"private", "cidr_block":"172.16.3.0/24", "availability_zone":"us-east-1b", "map_ip_on_launch":"false", "nat_gateway":"false"}
]
production_vpc = private_vpc.PrivateVPC(stage, private_vpc_name,private_cidr_block, private_vpc_subnets)
production_vpc.create_vpc()

# Bastion VPC
bastion_vpc_name = "BastionVPC"
bastion_cidr_block = "10.10.0.0/26"
bastion_vpc_subnets = [
    {"name":"public_subnet_a", "type":"public", "cidr_block":"10.10.0.0/27", "availability_zone":"us-east-1a", "map_ip_on_launch":"true", "nat_gateway":"false"},
    {"name":"public_subnet_b", "type":"public", "cidr_block":"10.10.0.32/27", "availability_zone":"us-east-1b", "map_ip_on_launch":"true", "nat_gateway":"false"}
]   
bastion_vpc = private_vpc.PrivateVPC(stage,bastion_vpc_name,bastion_cidr_block, bastion_vpc_subnets)
bastion_vpc.create_vpc()

# Bastion Host
key_name = "<INSERT KEY NAME HERE>"
security_group_name = "bastion-host-sg"
instance_name = "BastionHost"
instance_type = "t2.micro"
instance_ami = "<INSERT LINUX AMI HERE>"
bastion_host = bastion_host.BastionHost(stage, key_name, security_group_name, instance_name, instance_type, 
                                        instance_ami, bastion_vpc_name, bastion_vpc_subnets)
bastion_host.create_bastion_host()

# Peer Private and Bastion VPCs
vpc_peering = peer_vpc.PeerVPC(stage,private_vpc_name, private_cidr_block, bastion_vpc_name, bastion_cidr_block)
vpc_peering.create_peering()

## wordpress stack
# rds parameters
database_name = "RdsInstance"
database_instance_class = "db.t2.micro"
database_engine = "MySQL"
database_engine_version = "5.7.23"
database_username = "wordpress"
database_password = "password"
database_port = 3306
database_name_tag = "MySQLInstance"

# write instance
write_instance_image_id = "<INSERT LINUX AMI HERE>"
write_instance_type = "t2.micro"
write_instance_key_name = "<INSERT KEY NAME HERE>"

# read instances
read_instance_image_id = "<INSERT LINUX AMI HERE>"
read_instance_type = "t2.micro"
read_instance_key_name = "<INSERT KEY NAME HERE>"

wordpress = wordpress.WordPress(stage, database_name, database_instance_class, database_engine, 
                                database_engine_version, database_username, database_password, database_port, database_name_tag,
                                write_instance_image_id, write_instance_type, write_instance_key_name,
                                read_instance_image_id, read_instance_type, read_instance_key_name,
                                private_vpc_name, private_vpc_subnets)
wordpress.create_wordpress_environment()