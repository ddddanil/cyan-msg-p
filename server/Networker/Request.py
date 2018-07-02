from pickle import dumps
from hashlib import sha1
from pprint import pprint
import re


ALLOWED_CHARACTERS = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-/'
ALLOWED_CYAN_VERSION = b'0.1'

REQUIRED_GET_HEADERS = ('CYAN', 'REQ-TYPE', 'USER', 'RESOURCE', 'USER-TOKEN')
ACCEPTABLE_GET_HEADER = ('ACCEPT-TYPE', 'LAST_UPDATE')

REQUIRED_POST_HEADERS = ('CYAN', 'REQ-TYPE', 'USER', 'USER-TOKEN', 'TYPE', 'CHECKSUM', 'TIME-SENT', 'LENGTH', 'TARGET', 'BIN')


class ParseError(Exception):
    def __init__(self, description='', code=400):
        self.code = code
        self.description = description

    def __str__(self):
        return f'CODE: {self.code}\nDESC: {self.description}'


class Request:

    def __init__(self):
        self.headers = {}
        self.file_name = ''
        self.headers_part = b''
        self.file_part = b''
        self.done = False
        self.file_hash = sha1()

    def __bytes__(self):
        data = dumps(self.headers)
        return len(data).to_bytes(4, 'big') + data

    def add(self, data: bytes):
        if not self.headers:
            if b'::' in data:
                headers_part, self.file_part = data.split(b'::', maxsplit=1)
                data = b''
                self.headers_part += headers_part
                self.parse()
            else:
                self.headers_part += data

        if self.headers:
            if self.headers['REQ-TYPE'] == 'GET':
                self.done = True
                return self.file_part + data
            else:
                try:
                    needed_size = int(self.headers['LENGTH']) - len(self.headers['BIN']) + 1
                except ValueError:
                    raise ParseError('INVALID POST REQUEST LENGTH HEADER')
                else:
                    self.headers['BIN'] += self.file_part[:needed_size]
                    self.done = (int(self.headers['LENGTH']) == len(self.headers['BIN']))
                    return self.file_part[needed_size:]
        return b''

    def parse(self):
        lines = self.headers_part.split(b'\n')
        if not lines[-1]:
            lines.pop()
        pprint(lines)
        # check characters
        for num, line in enumerate(lines):
            if (1 < num < len(lines) - 1) and line.count(b':') != 1:
                raise ParseError(f'MORE THAN ONE ":" IN {(num + 1)} LINE')

            for ch in line:
                if ch not in (ALLOWED_CHARACTERS + b' .' if num < 2 else ALLOWED_CHARACTERS + b':'):
                    raise ParseError(f'INVALID CHARACTER {chr(ch)}')

        for num, line in enumerate(lines):

            # Parse string like [CYAN 0.1]
            if num == 0:
                try:
                    name, version = line.split()
                except ValueError:
                    raise ParseError('INVALID FIRST LINE')
                if name != b'CYAN':
                    raise ParseError('INVALID PROTOCOL NAME')

                # Check version for type like [0.1 or 0.2.1 and etc]
                if not re.match(r"[0-9](\.[0-9])+", version.decode('ascii')):
                    raise ParseError('INVALID PROTOCOL VERSION')
                elif version > ALLOWED_CYAN_VERSION:
                    raise ParseError('VERSION NOT SUPPORTED')
                else:
                    self.headers['CYAN'] = version.decode('ascii')

            # Parse string like [GET u000001 /resources/id or POST u000000]
            elif num == 1:
                try:
                    request_type, other = line.split(maxsplit=1)
                    if request_type != b'POST' and request_type != b'GET':
                        raise ParseError('INVALID REQUEST TYPE')

                    if request_type == b'POST':
                        print(other, request_type)
                        user = other.split()[0]
                    else:
                        user, resource = other.split()
                        self.headers['RESOURCE'] = resource.decode('ascii')

                except ValueError:
                    raise ParseError('INVALID SECOND LINE')

                self.headers['REQ-TYPE'] = request_type.decode('ascii')
                self.headers['USER'] = user.decode('ascii')

            # Parse string like [BIN]
            elif num == len(lines) - 1 and self.headers['REQ-TYPE'] == 'POST':
                if line != b'BIN':
                    raise ParseError('')
                else:
                    self.headers['BIN'] = b''

            # Parse string like [KEY:VALUE]
            else:
                key, value = line.split(b':')
                self.headers[key.decode('ascii')] = value.decode('ascii')

        self.check_headers()
        pprint(self.headers)

    def check_headers(self):
        if self.headers['REQ-TYPE'] == 'GET':
            for required_header in REQUIRED_GET_HEADERS:
                if required_header not in self.headers:
                    raise ParseError(f"THERE ISN'T REQUIRED METHOD {required_header}")

            for key, _ in self.headers.items():
                if key not in REQUIRED_GET_HEADERS + ACCEPTABLE_GET_HEADER:
                    raise ParseError(f'METHOD {key} NOT ALLOWED', 405)

        else:
            for required_header in REQUIRED_POST_HEADERS:
                if required_header not in self.headers:
                    raise ParseError(f"THERE ISN'T REQUIRED METHOD {required_header}")


if __name__ == '__main__':
    x = b"""CYAN 0.1
POST u0001
USER-TOKEN:aaaaaa
TARGET:u0002
TYPE:img
CHECKSUM:saaaa
TIME-SENT:6782357087
LENGTH:14
BIN::
binary file here
"""
    r = Request()
    print(r.add(x))
    pprint(r.headers)
