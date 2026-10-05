import logging
import time

import boto3


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

region = "ap-south-1"  # Mumbai

instance_ids = [
    "i-00e43d32325035a61",  # inst-1
    "i-0cced7a0b653ed857",  # inst-2
]

ec2 = boto3.client("ec2", region_name=region)

# Added for middleware monitoring
ssm = boto3.client("ssm", region_name=region)

# Added middleware name
middleware_service = "httpd"


# Added middleware check
def check_middleware(instance_id, name):

    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": [
                    f"systemctl is-active {middleware_service}"
                ]
            },
        )

        command_id = response["Command"]["CommandId"]

        time.sleep(2)

        result = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )

        status = result["StandardOutputContent"].strip()

        logging.info(
            "%s (%s): %s status = %s",
            name,
            instance_id,
            middleware_service,
            status,
        )

        # Middleware down -> restart
        if status != "active":

            logging.warning(
                "%s (%s): %s is down. Restarting...",
                name,
                instance_id,
                middleware_service,
            )

            ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    "commands": [
                        f"sudo systemctl start {middleware_service}"
                    ]
                },
            )

            logging.info(
                "%s (%s): %s restart command sent",
                name,
                instance_id,
                middleware_service,
            )

    except Exception:
        logging.exception(
            "%s (%s): Middleware check failed",
            name,
            instance_id,
        )


while True:
    try:
        response = ec2.describe_instances(InstanceIds=instance_ids)

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                state = instance["State"]["Name"]

                name = next(
                    (
                        tag["Value"]
                        for tag in instance.get("Tags", [])
                        if tag["Key"] == "Name"
                    ),
                    instance_id,
                )

                logging.info(
                    "%s (%s): %s",
                    name,
                    instance_id,
                    state,
                )

                if state == "stopped":
                    ec2.start_instances(InstanceIds=[instance_id])

                    logging.warning(
                        "Start requested for %s (%s)",
                        name,
                        instance_id,
                    )

                # Added middleware monitoring
                if state == "running":
                    check_middleware(
                        instance_id,
                        name,
                    )

    except Exception:
        logging.exception("Check failed; retrying")

    time.sleep(10)

