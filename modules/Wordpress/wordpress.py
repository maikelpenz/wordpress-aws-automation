from troposphere import Template, ImportValue, Ref, GetAtt, Output, Export, Tags, Join, Base64
from troposphere.ec2 import SecurityGroup, SecurityGroupRule, SpotFleet, SpotFleetRequestConfigData, \
                            LaunchSpecifications, TagSpecifications, \
                            SecurityGroups, SpotFleetTagSpecification, IamInstanceProfile
from troposphere.s3 import Bucket, Private, BucketPolicy
from troposphere.cloudfront import CloudFrontOriginAccessIdentity, CloudFrontOriginAccessIdentityConfig, \
                                   Distribution, DistributionConfig, Origin, DefaultCacheBehavior, ForwardedValues, S3Origin
from troposphere.rds import DBInstance, DBSubnetGroup
from troposphere.iam import Role, Policy, InstanceProfile
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Tag
from troposphere.elasticloadbalancingv2 import LoadBalancer, TargetGroup, Listener, Action


class WordPress:
    def __init__(self, stage, database_name, database_instance_class, database_engine, database_engine_version, 
                       database_username, database_password, database_port, database_multiaz, database_name_tag,
                       write_instance_image_id, write_instance_type, write_instance_key_name,
                       read_instance_image_id, read_instance_type, read_instance_key_name,
                       private_vpc_name, private_vpc_subnets):
        self.stage = stage
        self.database_name = database_name
        self.database_instance_class = database_instance_class
        self.database_engine = database_engine
        self.database_engine_version = database_engine_version 
        self.database_username = database_username
        self.database_password = database_password
        self.database_port = database_port
        self.database_multiaz = database_multiaz
        self.database_name_tag = database_name_tag
        self.write_instance_image_id = write_instance_image_id
        self.write_instance_type = write_instance_type
        self.write_instance_key_name = write_instance_key_name
        self.read_instance_image_id = read_instance_image_id
        self.read_instance_type = read_instance_type
        self.read_instance_key_name = read_instance_key_name
        self.private_vpc_name = private_vpc_name
        self.private_vpc_subnets = private_vpc_subnets

    def create_wordpress_environment(self):

        template = Template()
        template.add_version('2010-09-09')
        
        # Wordpress preparation: format vpc name and split private and public subnets in two lists
       
        vpc_name_formatted = ''.join(
            e for e in self.private_vpc_name if e.isalnum()).capitalize()

        filter_private_subnets = filter(lambda x : x["type"] == "private", self.private_vpc_subnets)
        filter_public_subnets = filter(lambda x : x["type"] == "public", self.private_vpc_subnets)

        private_subnets = []
        for subnet in filter_private_subnets:
            subnet_name_formatted = ''.join(e for e in subnet["name"] if e.isalnum()).capitalize()

            private_subnets.append(ImportValue("{}{}{}SubnetId".format(self.stage, vpc_name_formatted, subnet_name_formatted)))

        public_subnets = []
        for subnet in filter_public_subnets:
            subnet_name_formatted = ''.join(e for e in subnet["name"] if e.isalnum()).capitalize()

            public_subnets.append(ImportValue("{}{}{}SubnetId".format(self.stage, vpc_name_formatted, subnet_name_formatted)))

        # Instances Security Groups

        web_dmz_security_group = template.add_resource(
            SecurityGroup(
                "{}WebDMZSecurityGroup".format(self.stage),
                GroupName="{}webdmz-sg".format(self.stage),
                VpcId=ImportValue("{}{}VpcId".format(self.stage,vpc_name_formatted)),
                GroupDescription="Enables external http access to EC2 instance(s) that host the webpages",
                SecurityGroupIngress=[
                    SecurityGroupRule(
                        IpProtocol="tcp",
                        FromPort="80",
                        ToPort="80",
                        CidrIp="0.0.0.0/0",
                    ),
                    SecurityGroupRule(
                        IpProtocol="tcp",
                        FromPort="22",
                        ToPort="22",
                        SourceSecurityGroupId=ImportValue("{}BastionHostSecurityGroupID".format(self.stage))
                    )
                ]
            )
        )

        rds_private_security_group = template.add_resource(
            SecurityGroup(
                "{}RdsPrivateSecurityGroup".format(self.stage),
                GroupName="{}rds-private-sg".format(self.stage),
                VpcId=ImportValue("{}{}VpcId".format(self.stage,vpc_name_formatted)),
                GroupDescription="Allow access to the mysql port from the webservers",
                SecurityGroupIngress=[
                    SecurityGroupRule(
                        IpProtocol="tcp",
                        FromPort=self.database_port,
                        ToPort=self.database_port,
                        SourceSecurityGroupId=Ref(web_dmz_security_group)
                    )
                ]
            )
        )

        # S3 Buckets for wordpress content

        bucket_wordpress_code = template.add_resource(
            Bucket(
                "{}BucketWordpressCode".format(self.stage),
                BucketName="{}-wordpress-code".format(self.stage),
                AccessControl=Private
            )
        )

        bucket_wordpress_media_assets = template.add_resource(
            Bucket(
                "{}BucketWordpressMediaAssets".format(self.stage),
                BucketName="{}-wordpress-media-assets".format(self.stage),
                AccessControl=Private
            )
        )

        # Database Instance to store wordpress data

        rds_subnet_group = template.add_resource(
            DBSubnetGroup(
                "{}PrivateRDSSubnetGroup".format(self.stage),
                DBSubnetGroupName="{}private-rds-subnet-group".format(self.stage),
                DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
                SubnetIds=private_subnets
            )
        )

        template.add_resource(
            DBInstance(
                "{}RdsInstance".format(self.stage),
                DBInstanceIdentifier="{}RdsInstance".format(self.stage),
                DBName=self.database_name,
                AllocatedStorage="20",
                DBInstanceClass=self.database_instance_class,
                Engine=self.database_engine,
                EngineVersion=self.database_engine_version,
                MasterUsername=self.database_username,
                MasterUserPassword=self.database_password,
                Port=self.database_port,
                BackupRetentionPeriod=0,
                MultiAZ=self.database_multiaz,
                DBSubnetGroupName=Ref(rds_subnet_group),
                VPCSecurityGroups=[Ref(rds_private_security_group)],
                Tags=Tags(
                    Name=self.database_name_tag
                )
            )
        )

        # Cloudfront Distribution to load images

        cloudfront_origin_access_identity = template.add_resource(
            CloudFrontOriginAccessIdentity(
                "{}CloudfrontOriginAccessIdentity".format(self.stage),
                CloudFrontOriginAccessIdentityConfig=CloudFrontOriginAccessIdentityConfig(
                    "{}CloudFrontOriginAccessIdentityConfig".format(self.stage),
                    Comment="WordPress Origin Access Identity"
                )
            )
        )

        template.add_resource(BucketPolicy(
            "{}BucketWordpressMediaAssetsPolicy".format(self.stage),
            Bucket=Ref(bucket_wordpress_media_assets),
            PolicyDocument={
                "Version": "2008-10-17",
                "Id": "PolicyForCloudFrontPrivateContent",
                "Statement": [
                    {
                        "Sid": "1",
                        "Effect": "Allow",
                        "Principal": {
                            "CanonicalUser": GetAtt(cloudfront_origin_access_identity, 'S3CanonicalUserId')
                        },
                        "Action": "s3:GetObject",
                        "Resource": "arn:aws:s3:::{}-wordpress-media-assets/*".format(self.stage)
                    }
                ]
            }
        ))

        cloudfront_distribution = template.add_resource(
            Distribution(
                "{}CloudfrontDistribution".format(self.stage),
                DistributionConfig=DistributionConfig(
                    Origins=[
                        Origin(
                            Id="MediaAssetsOrigin",
                            DomainName=GetAtt(bucket_wordpress_media_assets, 'DomainName'),
                            S3OriginConfig=S3Origin(
                                OriginAccessIdentity=Join("", [
                                    "origin-access-identity/cloudfront/",
                                    Ref(cloudfront_origin_access_identity)
                                ])
                            )
                        )
                    ],
                    DefaultCacheBehavior=DefaultCacheBehavior(
                        TargetOriginId="MediaAssetsOrigin",
                        ForwardedValues=ForwardedValues(
                            QueryString=False
                        ),
                        ViewerProtocolPolicy="allow-all"
                    ),
                    Enabled=True,
                    HttpVersion='http2'
                )
            )
        )

        # Wordpress EC2 Instances
        
        ''' 
            EC2 Instances types:
                Write node = To make changes to your blog. E.g: add new posts
                Read Nodes = Instances open to the internet for blog reading
        '''

        wordpress_ec2_role = template.add_resource(
            Role(
                "{}WordPressEC2InstanceRole".format(self.stage),
                RoleName="{}WordPressEC2InstanceRole".format(self.stage),
                Path="/",
                AssumeRolePolicyDocument={"Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "Service": ["ec2.amazonaws.com"]
                    },
                    "Action": ["sts:AssumeRole"]
                }]},
                Policies=[
                    Policy(
                        PolicyName="S3FullAccess",
                        PolicyDocument={
                            "Statement": [{
                                "Effect": "Allow",
                                "Action": "s3:*",
                                "Resource": "*"
                            }],
                        }
                    )
                ]
            )
        )

        spotfleetrole = template.add_resource(
            Role(
                "{}spotfleetrole".format(self.stage),
                AssumeRolePolicyDocument={
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {
                                "Service": "spotfleet.amazonaws.com"
                            },
                            "Effect": "Allow",
                            "Sid": ""
                        }
                    ],
                    "Version": "2012-10-17"
                },
                ManagedPolicyArns=[
                    "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetRole"
                ]
            )
        )

        ec2_instance_profile = template.add_resource(
            InstanceProfile(
                "{}WriteWordpressEc2InstanceProfile".format(self.stage),
                Roles=[Ref(wordpress_ec2_role)]
            )
        )

        template.add_resource(
            SpotFleet(
                "{}WriteWordpressEc2Instance".format(self.stage),
                SpotFleetRequestConfigData=SpotFleetRequestConfigData(
                    AllocationStrategy="lowestPrice",
                    IamFleetRole=GetAtt(spotfleetrole,"Arn"),
                    LaunchSpecifications=[LaunchSpecifications(
                        IamInstanceProfile=IamInstanceProfile(
                            Arn=GetAtt(ec2_instance_profile, "Arn")
                        ),
                        ImageId=self.write_instance_image_id,
                        InstanceType=self.write_instance_type,
                        KeyName=self.write_instance_key_name,
                        SecurityGroups=[SecurityGroups(GroupId=Ref(web_dmz_security_group))],
                        SubnetId=next(iter(public_subnets)),
                        UserData=Base64(
                            Join("", [
                                """ #!/bin/bash
                                yum install httpd php php-mysql -y
                                cd /var/www/html
                                echo \"healthy\" > healthy.html
                                wget https://wordpress.org/latest.tar.gz
                                tar -xzf latest.tar.gz
                                cp -r wordpress/* /var/www/html/
                                rm -rf wordpress
                                rm -rf latest.tar.gz
                                chmod -R 755 wp-content
                                chown -R apache:apache wp-content
                                echo -e 'Options +FollowSymlinks \nRewriteEngine on \nrewriterule ^wp-content/uploads/(.*)$ http://""",
                                GetAtt(cloudfront_distribution, 'DomainName'),
                                """/$1 [r=301,nc]' > .htaccess
                                chkconfig httpd on
                                cd /var/www
                                sudo chown -R apache /var/www/html
                                cd html/
                                sudo find . -type d -exec chmod 0755 {} \;
                                sudo find . -type f -exec chmod 0644 {} \;
                                sed -i 's/AllowOverride None/AllowOverride All/g' /etc/httpd/conf/httpd.conf
                                sed -i 's/AllowOverride none/AllowOverride All/g' /etc/httpd/conf/httpd.conf
                                echo -e "*/1 * * * * root aws s3 sync --delete /var/www/html s3://""",
                                Ref(bucket_wordpress_code),
                                """">> /etc/crontab 
                                echo -e "*/1 * * * * root aws s3 sync --delete /var/www/html/wp-content/uploads s3://""",
                                Ref(bucket_wordpress_media_assets),
                                """">> /etc/crontab
                                service httpd start
                                """
                            ])
                        )
                    )],
                    TargetCapacity=1,
                    Type="request"
                )
            )
        )

        template.add_resource(
            LaunchConfiguration(
                "{}WordPressReadLaunchConfiguration".format(self.stage),
                InstanceType=self.read_instance_type,
                ImageId=self.read_instance_image_id,
                KeyName=self.read_instance_key_name,
                LaunchConfigurationName="{}-wordpress-launch-config".format(self.stage),
                SecurityGroups=[Ref(web_dmz_security_group)],
                IamInstanceProfile=Ref(ec2_instance_profile),
                SpotPrice="0.5",
                UserData=Base64(
                    Join("", [
                        """ #!/bin/bash
                        yum install httpd php php-mysql -y
                        cd /var/www/html
                        echo \"healthy\" > healthy.html
                        wget https://wordpress.org/latest.tar.gz
                        tar -xzf latest.tar.gz
                        cp -r wordpress/* /var/www/html/
                        rm -rf wordpress
                        rm -rf latest.tar.gz
                        chmod -R 755 wp-content
                        chown -R apache:apache wp-content
                        echo -e 'Options +FollowSymlinks \nRewriteEngine on \nrewriterule ^wp-content/uploads/(.*)$ http://""",
                        GetAtt(cloudfront_distribution, 'DomainName'),
                        """/$1 [r=301,nc]' > .htaccess
                        chkconfig httpd on
                        cd /var/www
                        sudo chown -R apache /var/www/html
                        cd html/
                        sudo find . -type d -exec chmod 0755 {} \;
                        sudo find . -type f -exec chmod 0644 {} \;
                        sed -i 's/AllowOverride None/AllowOverride All/g' /etc/httpd/conf/httpd.conf
                        sed -i 's/AllowOverride none/AllowOverride All/g' /etc/httpd/conf/httpd.conf
                        echo -e "*/1 * * * * root aws s3 sync --delete s3://""",
                        Ref(bucket_wordpress_code),
                        """ /var/www/html">> /etc/crontab 
                        echo -e "*/1 * * * * root aws s3 sync --delete s3://""",
                        Ref(bucket_wordpress_media_assets),
                        """/var/www/html/wp-content/uploads">> /etc/crontab
                        service httpd start
                        """
                    ])
                )
            )
        )

        alb = template.add_resource(
            LoadBalancer(
                "{}ApplicationLoadBalancer".format(self.stage),
                Name="{}-wordpress-alb".format(self.stage),
                SecurityGroups=[Ref(web_dmz_security_group)],
                Subnets=public_subnets,
                Type="application"
            )
        )

        target_group = template.add_resource(
            TargetGroup(
                "{}TargetGroup".format(self.stage),
                Name="{}-wordpress-target-group".format(self.stage),
                Port=80,
                Protocol="HTTP",
                VpcId=ImportValue("{}{}VpcId".format(self.stage,vpc_name_formatted)),
                HealthCheckPort=8080
            )
        )

        template.add_resource(
            AutoScalingGroup(
                "{}AutoScalingGroup".format(self.stage),
                DependsOn="{}WordPressReadLaunchConfiguration".format(self.stage),
                AutoScalingGroupName="{}-wordpress-auto-scaling".format(self.stage),
                LaunchConfigurationName="{}-wordpress-launch-config".format(self.stage),
                TargetGroupARNs=[Ref(target_group)],
                MaxSize="3",
                MinSize="1",
                VPCZoneIdentifier=private_subnets,
                Tags=[
                    Tag("Name", "{}-wordpress-read-node".format(self.stage), True)
                ]
            )
        )

        template.add_resource(
            Listener(
                "ALBListener",
                DefaultActions=[
                    Action(
                        TargetGroupArn=Ref(target_group), 
                        Type="forward"
                    )
                ],
                LoadBalancerArn=Ref(alb),
                Port=80,
                Protocol="HTTP"
            )
        )

        f = open("modules/template_wordpress.yaml", 'w')
        print(template.to_yaml(), file=f)
