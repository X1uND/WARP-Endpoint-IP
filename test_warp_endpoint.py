"""
Select all the best WARP endpoints
Thanks to https://gitlab.com/Misaka-blog/warp-script#warp-endpoint-ip-%E4%BC%98%E9%80%89%E8%84%9A%E6%9C%AC
"""

import asyncio
import csv
import ipaddress
import random
import socket
import time

TIMEOUT = 1  # s
OUTPUT_FILENAME = "result.csv"

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
    "041d69e67922099aa0b93d1e7b309ec5851ae2a3d6bf82a8bb5bb03ed46fb2346500000000000000000000000077a4a8cd5d883e66088e5f70adb42f8a"
)


async def check_connection(dst):
    udp_client = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    udp_client.settimeout(TIMEOUT)

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
            resp[0] == bytes.fromhex("cf0000007922099aa0b93d1e7b309ec5"),
            round(latency * 1000),  # ms
        )
    except socket.error:
        return (False, TIMEOUT * 1000)  # ms


async def main():
    dsts = []

    for v4_cdri in CDIRS_V4:
        for ip_v4 in ipaddress.IPv4Network(v4_cdri):
            dsts.append((str(ip_v4), random.choice(PORTS)))  # Port isn't very important

    # for v6_cdri in CDIRS_V6:
    #     for ip_v6 in ipaddress.IPv6Network(v6_cdri):
    #         dsts.append((str(ip_v6), random.choice(PORTS)))

    tasks = [check_connection(dst) for dst in dsts]
    result = await asyncio.gather(*tasks)
    output = [dsts + result for dsts, result in zip(dsts, result)]
    output.sort(key=lambda row: row[-1])

    with open(OUTPUT_FILENAME, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(("ip", "port", "connectivity", "latency"))
        writer.writerows(output)


asyncio.run(main())
