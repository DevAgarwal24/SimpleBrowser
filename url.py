# url.py

import socket
import ssl

class URL:
    def __init__( self, url ):
        self.scheme, url = url.split( "://", 1 )
        assert self.scheme in [ "http", "https" ]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url = url + "/"

        self.host, url = url.split( "/", 1 )
        if ":" in self.host:
            self.host, port = self.host.split( ":", 1 )
            self.port = int( port )

        self.path = "/" + url

    def create_header( self ):
        request = f"GET {self.path} HTTP/1.1\r\n"
        request += f"Host: {self.host}\r\n"
        request += f"Connection: close\r\n"
        request += f"User-Agent: SimpleBrowser/0.1\r\n"
        request += "\r\n"

        return request

    def request( self ):
        s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )

        s.connect( ( self.host, self.port ) )

        if self.scheme == "https":
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