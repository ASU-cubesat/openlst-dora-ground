# OpenLST
# Copyright (C) 2018 Planet Labs Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import six
import struct
from abc import ABCMeta, abstractproperty
from ast import literal_eval
from binascii import hexlify, unhexlify
from struct import pack, unpack
#import . messages_pb2
from . messages_pb2 import * 

LST = 0x01
LST_RELAY = 0x11

ACK = 0x10
NACK = 0xff
REBOOT = 0x12
GET_CALLSIGN = 0x19
SET_CALLSIGN = 0x1a
CALLSIGN = 0x1b
GET_TELEM = 0x17
TELEM = 0x18
GET_TIME = 0x13
SET_TIME = 0x14
BOOTLOADER_PING = 0x00
BOOTLOADER_ERASE = 0x0c
BOOTLOADER_WRITE_PAGE = 0x02
BOOTLOADER_ACK = 0x01
BOOTLOADER_NACK = 0x0f
ASCII = 0x11
AES_KEY_SIZE = 16
SET_EXT_DATA_1 = 0x1C
GET_EXT_DATA_1 = 0x1D


@six.add_metaclass(ABCMeta)
class Argument(object):

    @abstractproperty
    def to_bytes(self, value):
        pass

    @abstractproperty
    def from_bytes(self, bstring):
        pass

    def __init__(self, name):
        self.name = name


@six.add_metaclass(ABCMeta)
class IntegerArgument(Argument):

    def __init__(self, name, min=None, max=None):
        super(IntegerArgument, self).__init__(name)
        if min is not None:
            if min < self.min:
                raise ValueError("min is too low for this integer type")
            else:
                self.min = min
        if max is not None:
            if max > self.max:
                raise ValueError("max is too high for this integer type")
            else:
                self.max = max

    @abstractproperty
    def min(self):
        pass

    @abstractproperty
    def max(self):
        pass

    @abstractproperty
    def length(self):
        pass

    @abstractproperty
    def struct_code(self):
        pass

    def to_bytes(self, value):
        v = int(literal_eval(value))
        if v > self.max:
            raise ValueError("value is too large")
        elif v < self.min:
            raise ValueError("value is too small")
        return struct.pack(self.struct_code, v)

    def from_bytes(self, bstring):
        if len(bstring) < self.length:
            raise ValueError("not enough bytes")
        return struct.unpack(self.struct_code, bstring[:self.length])[0], \
            bstring[self.length:]


class Int8Argument(IntegerArgument):
    min = -(2 ** 7)
    max = (2 ** 7) - 1
    struct_code = "<b"
    length = 1


class UInt8Argument(IntegerArgument):
    min = 0
    max = (2 ** 8) - 1
    struct_code = "<B"
    length = 1


class Int16Argument(IntegerArgument):
    min = -(2 ** 15)
    max = (2 ** 15) - 1
    struct_code = "<h"
    length = 2


class UInt16Argument(IntegerArgument):
    min = 0
    max = (2 ** 16) - 1
    struct_code = "<H"
    length = 2


class Int32Argument(IntegerArgument):
    min = -(2 ** 31)
    max = (2 ** 31) - 1
    struct_code = "<l"
    length = 4


class UInt32Argument(IntegerArgument):
    min = 0
    max = (2 ** 32) - 1
    struct_code = "<L"
    length = 4


class HexArgument(Argument):
    def __init__(self, name, length, pad='left'):
        super(HexArgument, self).__init__(name)
        self.length = length
        if pad not in ('left', 'right', 'none'):
            raise ValueError("invalid valude for pad: %s" % pad)
        self.pad = pad

    def to_bytes(self, value):
        v = unhexlify(value.replace(' ', ''))
        if len(v) > self.length:
            raise ValueError("'%s' is too long" % value)
        if self.pad == 'none' and len(v) < self.length:
            raise ValueError("'%s' is too short" % value)
        padding = (self.length - len(v)) * '\0'
        if self.pad == 'left':
            v = padding + v
        else:
            v = v + padding
        return v

    def from_bytes(self, bstring):
        if len(bstring) < self.length:
            raise ValueError("not enough bytes")
        return hexlify(bstring[:self.length]), bstring[self.length:]


class StringArgument(Argument):
    def __init__(self, name):
        super(StringArgument, self).__init__(name)
        pass

    def to_bytes(self, value):
        return value

    def from_bytes(self, bstring):
        return '"' + str(bstring) + '"', ""

class ProtobufTelemArgument(Argument):
    def __init__(self, name):
        super(ProtobufTelemArgument, self).__init__(name)
        pass

    def to_bytes(self, value):
        return value

    def from_bytes(self, bstring):
        trueLength = int(bstring[0])
        toParse = bstring[1:(trueLength+1)]
        outputString = ""
        incomingTelemetry = RadioTelemetry()
        #incomingTelemetry.tid = TelemetryID.SOH
        #incomingTelemetry.soh.CopyFrom(RadioSOH())
        #incomingTelemetry.soh.solarVoltage.CopyFrom(SolarVoltage())
        #incomingTelemetry.soh.solarVoltage.side1 = 10
        #incomingTelemetry.soh.solarVoltage.side2 = 11
        #x = incomingTelemetry.SerializeToString()
        #print(x)
        try:
            incomingTelemetry.ParseFromString(toParse)
            outputString = str(incomingTelemetry)
        except Exception as e:
            print("hit exception parsing protobuf")
            print("Full message is this")
            print(bstring)
            print("first byte length is: %d" % trueLength)
            print("parsing this message bstring[1:(trueLength+1)")
            print(toParse)
            print(e)

        #print(incomingTelemetry)
        return '"' + outputString + '"', ""



class EnumArgument(Argument):
    def __init__(self, name, mapping, valuepack='<B', length=1):
        super(EnumArgument, self).__init__(name)
        self.mapping = mapping
        self.valuepack = valuepack
        self.length = 1

    def to_bytes(self, value):
        if value in self.mapping.keys():
            return self.mapping[value]
        elif value in self.mapping.values():
            return struct.pack(self.valuepack, value)
        else:
            raise ValueError("invalid value for enumeration '%s'" % value)

    def from_bytes(self, bstring):
        u = struct.unpack(self.valuepack, bstring[:self.length])
        key = next(k for k, v in self.mapping.items() if v == u)
        return key, bstring[self.length:]


class Command(object):
    def __init__(self, key, opcode, *args, **kwargs):
        self.key = key
        self.opcode = opcode
        self.args = args
        self.optional_args = kwargs.pop('optional_args', 0)

    def tokens_to_bytes(self, tokens):
        tokens = list(tokens)
        rv = b""
        rv += self.opcode.to_bytes(1, "little")
        for i, arg in enumerate(self.args):
            optional = (len(self.args) - i <= self.optional_args)
            try:
                key = tokens.pop(0)
                rv += arg.to_bytes(key)
            except IndexError:
                if not optional:
                    raise Exception(
                        "missing argument for command %s" % self.key)
        if tokens:
            raise ValueError(
                "unparsed extras args: {}".format(", ".join(tokens)))
        return rv

    def bytes_to_string(self, msg):
        rv = []

        for i, arg in enumerate(self.args):
            optional = (len(self.args) - i <= self.optional_args)
            try:
                k, msg = arg.from_bytes(msg)
            except Exception:
                if not optional:
                    raise
            else:
                rv.append(str(k))
        return ' '.join(rv)


COMMANDS = [
    Command("ack", ACK),
    Command("nack", NACK),
    Command("bootloader_ack", BOOTLOADER_ACK,
            UInt8Argument("reason"), optional_args=1),
    Command("bootloader_nack", BOOTLOADER_NACK),
    Command("bootloader_ping", BOOTLOADER_PING),
    Command("bootloader_erase", BOOTLOADER_ERASE,
            UInt8Argument("status"), optional_args=1),
    Command("bootloader_write_page", BOOTLOADER_WRITE_PAGE,
            UInt8Argument("page"),
            HexArgument("data", length=128, pad="none"),
            optional_args=1),
    Command("reboot", REBOOT,
            UInt32Argument("delay"), optional_args=1),
    Command("get_time", GET_TIME),
    Command("set_time", SET_TIME,
            UInt32Argument("seconds"),
            UInt32Argument("nanoseconds")),
    Command("get_callsign", GET_CALLSIGN),
    Command("set_callsign", SET_CALLSIGN,
            StringArgument("callsign")),
    Command("callsign", CALLSIGN,
            StringArgument("callsign")),
    Command("get_telem", GET_TELEM),
    Command("telem", TELEM,
            UInt8Argument("reserved"),
            UInt32Argument("uptime"),
            UInt32Argument("uart0_rx_count"),
            UInt32Argument("uart1_rx_count"),
            UInt8Argument("rx_mode"),
            UInt8Argument("tx_mode"),
            Int16Argument("adc0"),
            Int16Argument("adc1"),
            Int16Argument("adc2"),
            Int16Argument("adc3"),
            Int16Argument("adc4"),
            Int16Argument("adc5"),
            Int16Argument("adc6"),
            Int16Argument("adc7"),
            Int16Argument("adc8"),
            Int16Argument("adc9"),
            Int8Argument("last_rssi"),
            UInt8Argument("last_lqi"),
            Int8Argument("last_freqest"),
            UInt32Argument("packets_sent"),
            UInt32Argument("cs_count"),
            UInt32Argument("packets_good"),
            UInt32Argument("packets_rejected_checksum"),
            UInt32Argument("packets_rejected_reserved"),
            UInt32Argument("packets_rejected_other"),
            UInt32Argument("reserved0"),
            UInt32Argument("reserved1"),
            UInt32Argument("custom0"),
            UInt32Argument("custom1")),
    Command("ascii", ASCII, StringArgument("text")),
    Command("get_ext", GET_EXT_DATA_1),
    Command("set_ext_data_1", SET_EXT_DATA_1,
            ProtobufTelemArgument("ext data 1")),
]


CMD_OPCODE_MAP = {cmd.opcode: cmd for cmd in COMMANDS}
CMD_STRING_MAP = {cmd.key: cmd for cmd in COMMANDS}
CMD_TREE = {'lst': {cmd.key: [a.name for a in cmd.args] for cmd in COMMANDS}}


class Translator(object):

    def _assert_len(self, tokens, l):
        if len(tokens) != l:
            raise ValueError("command too short '%r'" % ' '.join(tokens))

    # TODO: better parser
    def bytes_from_string(self, hwid, seqnum, s):
        rv = bytearray(pack('<HH', int(hwid), int(seqnum)))

        tokens = s.split()

        if len(tokens) < 2:
            raise ValueError("command too short '%r'" % ' '.join(tokens))

        if tokens[0] == 'lst':
            rv += LST.to_bytes(1, "little")
        else:
            raise ValueError("don't know system '%r'" % s)
        rv.extend(CMD_STRING_MAP[tokens[1]].tokens_to_bytes(tokens[2:]))

        return rv

    def string_from_bytes(self, b):
        #for op in CMD_OPCODE_MAP:
        #    print(type(op))
        #    print((op))
        #print("here")
        #print(b[3])
        #print(type(b[3]))
        #print(b[4])
        #print(b[5])
        #print(str(b[5]))
        if len(b) < 6:
            return "too_short " + str(hexlify(b))
        if b[4] == LST:
            try:
                    out = "lst "
                    out += CMD_OPCODE_MAP[b[5]].key
                    out += " "
                    out += CMD_OPCODE_MAP[b[5]].bytes_to_string(b[6:])
                    return out
            except Exception:
                return "lst unknown " + hexlify(b[5:])
        else:
            return "unknown_sys " + str(hexlify(b[4:]))

    def int_from_bytes(self, bytearr):
        # assumes 2 bytes
        return unpack('<H', bytearr)[0]
