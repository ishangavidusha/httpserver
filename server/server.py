import socket
import json
from .logger import Logger
from .response import Response, HTTPError
from .cors_config import CORSConfig

class HTTPServer:
    def __init__(
        self, port=80, log_level="INFO", max_request_size=8192, cors_config=None
    ):
        self.port = port
        self.socket = None
        self.routes = {}
        self.logger = Logger(log_level)
        self.max_request_size = max_request_size
        self.cors_config = cors_config or CORSConfig()

    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(("0.0.0.0", self.port))
            self.socket.listen(5)
            self.logger.info(f"Server started on port {self.port}")

            while True:
                conn, addr = self.socket.accept()
                self.logger.info(f"New connection from {addr}")
                try:
                    self.handle_request(conn)
                except Exception as e:
                    self.logger.error(f"Error handling request: {str(e)}")
                finally:
                    conn.close()
        except Exception as e:
            self.logger.critical(f"Server error: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()

    def handle_request(self, conn):
        try:
            request = b""
            while True:
                chunk = conn.recv(4096)
                request += chunk
                if len(chunk) < 4096:
                    break
                if len(request) > self.max_request_size:
                    raise HTTPError(413, "Request Entity Too Large")

            if not request:
                return

            request = request.decode("utf-8")
            method, path, query_params, headers, body = self.parse_request(request)

            self.logger.info(f"Received {method} request for {path}")

            if method == "OPTIONS":
                response = self.handle_preflight(headers)
                self.send_response(conn, response)
            else:
                response = self.process_request(
                    method, path, query_params, headers, body
                )
                origin = headers.get("origin")
                if origin:
                    response.add_cors_headers(self.cors_config, origin)
                self.send_response(conn, response)
        except HTTPError as e:
            self.logger.warning(f"HTTP Error {e.status_code}: {e.message}")
            error_response = Response({"error": e.message}, status_code=e.status_code)
            self.send_response(conn, error_response)
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            error_response = Response(
                {"error": "Internal Server Error"}, status_code=500
            )
            self.send_response(conn, error_response)

    def send_response(self, conn, response):
        conn.send(response.to_bytes())

    def handle_preflight(self, headers):
        requested_method = headers.get("access-control-request-method")
        requested_headers = headers.get("access-control-request-headers")

        if requested_method and requested_method in self.cors_config.allow_methods:
            response = Response("", status_code=204)  # No Content
            if requested_headers:
                self.cors_config.allow_headers.extend(
                    [h.strip() for h in requested_headers.split(",")]
                )
            return response
        else:
            raise HTTPError(400, "Invalid preflight request")

    def parse_request(self, request):
        try:
            lines = request.split("\r\n")
            method, full_path, _ = lines[0].split()

            path, query = (
                full_path.split("?", 1) if "?" in full_path else (full_path, "")
            )
            query_params = self.parse_query_string(query)

            headers = {}
            body_start = 0
            for i, line in enumerate(lines[1:]):
                if not line:
                    body_start = i + 2
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            body = "\r\n".join(lines[body_start:]) if body_start else None

            return method, path, query_params, headers, body
        except Exception as e:
            raise HTTPError(400, f"Bad Request: {str(e)}")

    def parse_query_string(self, query_string):
        params = {}
        if query_string:
            pairs = query_string.split("&")
            for pair in pairs:
                key, value = pair.split("=", 1) if "=" in pair else (pair, "")
                if key in params:
                    if isinstance(params[key], list):
                        params[key].append(value)
                    else:
                        params[key] = [params[key], value]
                else:
                    params[key] = value
        return params

    def process_request(self, method, path, query_params, headers, body):
        if path in self.routes and method in self.routes[path]:
            handler = self.routes[path][method]
            return handler(query_params, headers, body)
        else:
            raise HTTPError(404, "Not Found")

    def route(self, path, methods=None):
        if methods is None:
            methods = ["GET"]

        def decorator(handler):
            if path not in self.routes:
                self.routes[path] = {}
            for method in methods:
                self.routes[path][method] = handler
            return handler

        return decorator

    def set_cors_config(
        self,
        allow_origins=None,
        allow_methods=None,
        allow_headers=None,
        allow_credentials=False,
        max_age=None,
    ):
        self.cors_config = CORSConfig(
            allow_origins, allow_methods, allow_headers, allow_credentials, max_age
        )

    @staticmethod
    def serve_file(file_path, content_type):
        try:
            with open(file_path, "r") as file:
                content = file.read()
            return Response(content, headers={"Content-Type": content_type})
        except Exception:
            return Response("File not found", status_code=404)

    @staticmethod
    def parse_json(body):
        try:
            return json.loads(body)
        except Exception:
            return None