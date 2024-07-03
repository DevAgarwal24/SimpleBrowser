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

    redirects = 5
    timeout = 20

    def __init__( self, url ):
        parsed_url = urlparse( url )
        scheme = parsed_url.scheme

        self.underlying_scheme = None

        self.host = parsed_url.hostname
        self.port = parsed_url.port
        self.media = None
        self.path = parsed_url.path

        self.socket = None

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

    def __del__( self ):
        if self.socket:
            self.socket.close()

    def create_header( self ):
        request = f"GET {self.path} HTTP/1.1\r\n"
        request += f"Host: {self.host}\r\n"
        request += f"Connection: keep-alive\r\n"
        request += f"Keep-Alive: timeout={URL.timeout}\r\n"
        request += f"User-Agent: SimpleBrowser/0.1\r\n"
        request += "\r\n"

        return request

    def receive_data( self, response, content_length ):
        data = ''
        bytes_read = 0
        buffer_size = 4096  # Adjust as necessary

        while bytes_read < content_length:
            chunk = response.read(min(buffer_size, content_length - bytes_read))
            if not chunk:
                break  # End of file or no more data
            data += chunk
            bytes_read += len(chunk)

        return data

    def request( self ):
        if self.scheme == self.Scheme.DATA:
            return self.path + "\r\n"

        if self.scheme == self.Scheme.UNKNOWN:
            print("path is invalid")
            return
        elif not self.socket:
            self.socket = socket.socket(
                    family=socket.AF_INET,
                    type=socket.SOCK_STREAM,
                    proto=socket.IPPROTO_TCP,
                )
            self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout( URL.timeout )
            self.socket.connect( ( self.host, self.port ) )

        if self.scheme == self.Scheme.HTTPS:
            ctx = ssl.create_default_context()
            self.socket = ctx.wrap_socket( self.socket, server_hostname=self.host )

        self.socket.send( self.create_header().encode( "utf8" ) )

        response = self.socket.makefile( "r", encoding="utf8", newline="\r\n" )

        statusline = response.readline()
        version, status, explanation = statusline.split( " ", 2 )

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split( ":", 1 )
            response_headers[ header.casefold() ] = value.strip()

        if URL.redirects and status == "301":
            URL.redirects -= 1
            new_url = response_headers[ 'location' ]
            url_obj = URL(new_url)
            if url_obj.scheme == self.Scheme.UNKNOWN:
                self.path = new_url
            elif url_obj.host == self.host:
                self.path = url_obj.path
            else:
                return url_obj.request()

            return self.request()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        assert "content-length" in response_headers

        read_bytes = int( response_headers[ 'content-length' ] )

        content = self.receive_data(response, read_bytes)

        if response_headers[ 'connection' ] != "Keep-Alive":
            self.socket.close()

        return content