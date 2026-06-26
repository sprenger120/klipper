#!/bin/env python3
import os
import csv
from klippy.msgproto import MessageParser, error
import pyshark
from enum import Enum
import argparse
from pathlib import Path


class Direction(Enum):
    HOST_TO_MCU = 0
    MCU_TO_HOST = 1
    UNKNOWN = -1
class MessageBlock:

    def __init__(self, direction : Direction = Direction.UNKNOWN, data=None, seq : int = -1):
        if data is None:
            data = []
        self.dir : Direction = direction
        self.data : list[int] = data
        self.seq : int = seq

class MessageBlockAssembler:
    def __init__(self, max_delta_t):
        self.communication : list[MessageBlock] = []
        self.previous_byte_t = 0
        self.previous_direction = None
        self.bytes_left_before_split = 0
        self.MAX_DELTA_T = max_delta_t

    def appendByte(self, direction: Direction, time_of_arrival: float, in_data : int):
        if time_of_arrival - self.previous_byte_t > self.MAX_DELTA_T or \
                self.previous_direction != direction or \
                self.bytes_left_before_split == 0:
            self.communication.append(MessageBlock(direction=direction))

        data_target = self.communication[-1].data
        data_target.append(in_data)

        if len(data_target) == 1:
            # messages begin with their length
            self.bytes_left_before_split = data_target[0]

        if len(data_target) == 2:
            self.communication[-1].seq = data_target[1] & 0xf

        self.previous_direction = direction
        self.previous_byte_t = time_of_arrival
        self.bytes_left_before_split -= 1

    def get(self):
        return self.communication


def parse_logic_analyzer_log(filename: str | Path):
    assembler = MessageBlockAssembler(0.0001)
    with open(filename, "r") as file:
        data = csv.DictReader(file)
        for row in data:
            if row["error"] != "":
                continue
            if row["name"] == "Async Serial":
                direction = Direction.MCU_TO_HOST
            if row["name"] == 'Async Serial [1]':
                direction = Direction.HOST_TO_MCU
            time = float(row["start_time"])
            assembler.appendByte(direction, time, int(row["data"], 0))
    return assembler.get()


def parse_wireshark_capture(filename : str | Path):
    HOST_IPV6 = "fe80::60e7:2f2d:54db:f634"
    MCU_IPV6 = "fe80::b455:a4ff:fe36:f61"
    assembler = MessageBlockAssembler(0.003)
    capture = pyshark.FileCapture(filename)
    for pkg in capture:
        if not "ipv6" in pkg or not "udp" in  pkg:
            continue
        if pkg["ipv6"].src == HOST_IPV6:
            direction = Direction.HOST_TO_MCU
        elif pkg["ipv6"].src == MCU_IPV6:
            direction = Direction.MCU_TO_HOST
        else:
            continue
        time = float(pkg.sniff_timestamp)
        for byte in pkg["udp"].payload.split(":"):
            assembler.appendByte(direction, time, int(byte, 16))
    return assembler.get()


def analyse(communication:  list[MessageBlock]):
    parser = MessageParser()
    # cmd = self.msgparser.create_command("identify_response")
    # cmd = self.msgparser.create_command("identify")

    parsedCommunication = []
    data_dict = b''
    for row in communication:
        data = row.data
        seq = row.seq
        try:
            if len(data) == 5:
                # ACK / NACK
                result = {"ack/nack": ''}
            else:
                result = parser.parse(data)
                if result["#name"] == "identify_response":
                    if int(result['offset']) == len(data_dict):
                        data_dict += result['data']
                        if len(result['data']) < 40:
                            parser.process_identify(data_dict)
                            print("data_dict parsed")
                    else:
                        print("data_dict build misaligned")
            result["seq"] = str(seq)
            result["dir"] = row.dir.name
            parsedCommunication.append(result)
        except error as e:
            parsedCommunication.append("parsing error")
            print("parser error")
    # todo check for CRC errors
    print("analysis done, please rerun with debugger to see results")

class Method(str, Enum):
    saleae_logic = "saleae_logic"
    pcapng = "pcapng"

def parse_args():
    parser = argparse.ArgumentParser(description="Process input file with a given method.")
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the input file",
    )
    parser.add_argument(
        "--method",
        required=True,
        choices=[m.value for m in Method],
        help=f"Processing method",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    if not args.file.exists():
        raise FileNotFoundError("File not found")
    method = Method(args.method)

    if method == Method.saleae_logic:
        comm = parse_logic_analyzer_log(args.file)
    elif method == Method.pcapng:
        comm = parse_wireshark_capture(args.file)
    else:
        raise NotImplementedError("Chosen method is not implemented")

    analyse(comm)
