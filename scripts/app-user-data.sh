#!/bin/bash

yum update -y
yum install -y httpd

systemctl enable httpd
systemctl start httpd

echo "<h1>AWS Self-Healing Application Server</h1>" \
> /var/www/html/index.html
