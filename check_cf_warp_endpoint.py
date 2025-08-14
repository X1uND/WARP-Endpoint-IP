"""
Test cloudflare WARP endpoints
Select all the best WARP endpoints
Thanks to https://gitlab.com/Misaka-blog/warp-script#warp-endpoint-ip-优选脚本
"""

import asyncio
import csv
import ipaddress
import logging
import random
import socket
import time

"""
Parameters
"""

MAX_LATENCY = 400  # Maximum latency expected in milliseconds
MIN_EXPECTED_RESULT_COUNT = 20  # Minimum expected result count
OUTPUT_FILENAME = "endpoints.csv"  # Output filename
CHECK_IPV6 = False  # Whether to check IPv6, NOT IMPLEMENTED YET


"""
Predefined Constants
"""
CDIRS_V4 = (
    "162.159.192.0/24",
    "162.159.193.0/24",
    "162.159.195.0/24",
    "162.159.204.0/24",
    "188.114.96.0/24",
    "188.114.97.0/24",
    "188.114.98.0/24",
    "188.114.99.0/24",
)
CDIRS_V6 = ("2606:4700:d0::/48", "2606:4700:d1::/48")
PORTS = (
    2408,
    500,
    864,
    880,
    894,
    934,
    1070,
    1180,
    3476,
    3581,
    4198,
    4500,
    5279,
    5956,
    7103,
    7152,
    7559,
    8319,
    8854,
    8886,
)
DATA = bytes.fromhex(
    "041d69e67922099aa0b93d1e7b309ec5"
    "851ae2a3d6bf82a8bb5bb03ed46fb234"
    "6500000000000000000000000077a4a8"
    "cd5d883e66088e5f70adb42f8a"
)


async def check_endpoint(dst):
    udp_client = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    udp_client.settimeout(MAX_LATENCY / 1000)  # ms

    # Only start timing when actually sending the request
    def send_request():
        start_time = time.time()
        udp_client.sendto(DATA, dst)
        resp = udp_client.recvfrom(32)
        end_time = time.time()
        return resp, end_time - start_time

    try:
        resp, latency = await asyncio.to_thread(send_request)
        return (
            resp[0][0:5]
            == bytes.fromhex(
                "cf00000000"
            ),  # Check whether the response is correct
            round(latency * 1000),  # ms
        )
    except socket.error:
        return (False, -1)  # -1 for an error


async def main():
    logging.basicConfig(level=logging.INFO)
    endpoints = []

    logging.info("Initialising IPv4 list...")
    endpoints += [
        (str(ip_v4), random.choice(PORTS))
        for ipv4_cdri in CDIRS_V4
        for ip_v4 in ipaddress.IPv4Network(ipv4_cdri)
    ]

    if CHECK_IPV6:
        logging.info("Initialising IPv6 list...")
        endpoints += [
            (str(ip_v6), random.choice(PORTS))
            for ipv6_cdri in CDIRS_V6
            for ip_v6 in ipaddress.IPv6Network(ipv6_cdri)
        ]

    logging.info("Checking connections...")
    random.shuffle(endpoints)
    output = []
    window_start = 0
    while window_start < len(endpoints):
        window_size = min(MIN_EXPECTED_RESULT_COUNT, len(endpoints) - window_start)
        logging.info(
            f"Checking {window_size} endpoints, "
            f"{len(endpoints) - (window_start + window_size)} left"
        )
        tasks = [
            check_endpoint(endpoints[index])
            for index in range(window_start, window_start + window_size)
        ]
        check_results = await asyncio.gather(*tasks)
        output += [
            (":".join(map(str, endpoints[index])), check_result[1])
            for index, check_result in zip(
                range(window_start, window_start + window_size),
                check_results,
            )
            if check_result[0]
        ]
        window_start += window_size
        if len(output) >= MIN_EXPECTED_RESULT_COUNT:
            logging.info(f"Got {len(output)} results, which is enough, stop checking")
            break

    logging.info(f'End up with {len(output)} results, export to "{OUTPUT_FILENAME}"')
    output.sort(key=lambda row: row[-1])
    with open(OUTPUT_FILENAME, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("Endpoint", "Latency (ms)"))
        writer.writerows(output)


asyncio.run(main())
