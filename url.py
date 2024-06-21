# url.py

import socket
import ssl
from enum import Enum
from urllib.parse import urlparse

class URL:

    class Scheme(Enum):
        HTTP = 'http'
        HTTPS = 'https'
        FTP = 'ftp'
        FILE = 'file'
        MAILTO = 'mailto'
        VIEW_SOURCE = 'view-source'
        DATA = 'data'
        UNKNOWN = 'unknown'

    scheme_to_enum = {
        'http': Scheme.HTTP,
        'https': Scheme.HTTPS,
        'ftp': Scheme.FTP,
        'file': Scheme.FILE,
        'mailto': Scheme.MAILTO,
        'view-source': Scheme.VIEW_SOURCE,
        'data': Scheme.DATA,
    }

    def __init__( self, url ):
        parsed_url = urlparse( url )
        scheme = parsed_url.scheme

        self.underlying_scheme = None

        self.host = parsed_url.hostname
        self.port = parsed_url.port
        self.media = None
        self.path = parsed_url.path

        if scheme == "view-source":
            self.scheme = self.Scheme.VIEW_SOURCE
            underlying_url = url[ len( 'view-source:' ): ]
            parsed_underlying_url = urlparse(underlying_url)
            self.underlying_scheme = self.scheme_to_enum.get(parsed_underlying_url.scheme, self.Scheme.UNKNOWN)
            self.host = parsed_underlying_url.hostname
            self.port = parsed_underlying_url.port
        else:
            self.scheme = self.scheme_to_enum.get( scheme, self.Scheme.UNKNOWN )

        # Set default ports for http and https if not specified
        if self.port is None:
            if self.scheme == self.Scheme.HTTP:
                self.port = 80
            elif self.scheme == self.Scheme.HTTPS:
                self.port = 443
            elif self.underlying_scheme == self.Scheme.HTTP:
                self.port = 80
            elif self.underlying_scheme == self.Scheme.HTTPS:
                self.port = 443
            else:
                self.port = None

        # Set default host and port for FILE scheme
        if self.scheme == self.Scheme.FILE:
            self.host = 'localhost'
            self.port = 8000
        if self.scheme == self.Scheme.DATA:
            data_parts = parsed_url.path.split(',', maxsplit=1)
            if len(data_parts) > 1:
                self.media = data_parts[0]
                self.path = data_parts[1]
            else:
                self.path = data_parts[0]

    def create_header( self ):
        request = f"GET {self.path} HTTP/1.1\r\n"
        request += f"Host: {self.host}\r\n"
        request += f"Connection: close\r\n"
        request += f"User-Agent: SimpleBrowser/0.1\r\n"
        request += "\r\n"

        return request

    def request( self ):
        if self.scheme == self.Scheme.DATA:
            return self.path + "\r\n"

        s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )

        s.connect( ( self.host, self.port ) )

        if self.scheme == self.Scheme.HTTPS:
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket( s, server_hostname=self.host )

        s.send( self.create_header().encode( "utf8" ) )

        response = s.makefile( "r", encoding="utf8", newline="\r\n" )

        statusline = response.readline()
        version, status, explanation = statusline.split( " ", 2 )

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split( ":", 1 )
            response_headers[ header.casefold() ] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content