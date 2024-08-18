import socket
import json
from .logger import Logger
from .response import Response, HTTPError
from .cors_config import CORSConfig

class HTTPServer:
    """
    A simple HTTP server implementation.

    Args:
        port (int): The port number to listen on. Default is 80.
        log_level (str): The log level for the server. Default is "INFO".
        max_request_size (int): The maximum size of a request in bytes. Default is 8192.
        cors_config (CORSConfig): The CORS (Cross-Origin Resource Sharing) configuration. Default is None.

    Attributes:
        port (int): The port number to listen on.
        socket (socket.socket): The server socket.
        routes (dict): A dictionary of routes and their corresponding handlers.
        logger (Logger): The logger instance for logging server events.
        max_request_size (int): The maximum size of a request in bytes.
        cors_config (CORSConfig): The CORS configuration.

    Methods:
        start(): Start the server.
        handle_request(conn): Handle an incoming request.
        send_response(conn, response): Send a response to the client.
        handle_preflight(headers): Handle a preflight request.
        parse_request(request): Parse an HTTP request.
        parse_query_string(query_string): Parse a query string into a dictionary of parameters.
        process_request(method, path, query_params, headers, body): Process an HTTP request.
        route(path, methods): Decorator for defining a route and its corresponding handler.
        set_cors_config(allow_origins, allow_methods, allow_headers, allow_credentials, max_age): Set the CORS configuration.
        serve_file(file_path, content_type): Serve a file as a response.
        parse_json(body): Parse a JSON string into a Python object.
    """
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
        """
        Starts the server and listens for incoming connections on the specified port.

        Raises:
            Exception: If there is an error starting the server.
        """
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
        """
        Handles an incoming HTTP request.

        Args:
            conn (socket): The socket connection for the request.

        Raises:
            HTTPError: If the request entity is too large (413 status code).
            Exception: If an unexpected error occurs.

        Returns:
            None

        """
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
        """
        Sends the given response to the specified connection.

        Parameters:
        - conn: The connection to send the response to.
        - response: The response to send.

        Returns:
        None
        """
        conn.send(response.to_bytes())

    def handle_preflight(self, headers):
        """
        Handles preflight requests.

        Args:
            headers (dict): The headers of the request.

        Returns:
            Response: The response to the preflight request.

        Raises:
            HTTPError: If the preflight request is invalid.
        """
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
        """
        Parses the HTTP request and extracts the method, path, query parameters, headers, and body.

        Args:
            request (str): The HTTP request string.

        Returns:
            tuple: A tuple containing the method (str), path (str), query parameters (dict), headers (dict), and body (str).

        Raises:
            HTTPError: If there is a bad request.

        """
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
        """
        Parses the given query string and returns a dictionary of parameters.

        Args:
            query_string (str): The query string to be parsed.

        Returns:
            dict: A dictionary containing the parsed parameters.

        """
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
        """
        Process the incoming HTTP request.

        Args:
            method (str): The HTTP method of the request.
            path (str): The path of the request.
            query_params (dict): The query parameters of the request.
            headers (dict): The headers of the request.
            body (str): The body of the request.

        Returns:
            The response generated by the request handler.

        Raises:
            HTTPError: If the requested path and method combination is not found.
        """
        if path in self.routes and method in self.routes[path]:
            handler = self.routes[path][method]
            return handler(query_params, headers, body)
        else:
            raise HTTPError(404, "Not Found")

    def route(self, path, methods=None):
        """
        Decorator function for defining routes in the HTTP server.

        Parameters:
        - path (str): The URL path for the route.
        - methods (list, optional): The HTTP methods allowed for the route. Defaults to ["GET"].

        Returns:
        - decorator (function): The decorator function that adds the route to the server's routes dictionary.
        """
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
        """
        Set the Cross-Origin Resource Sharing (CORS) configuration for the server.

        Parameters:
        - allow_origins (list or str): List of allowed origins or a single origin string. Defaults to None.
        - allow_methods (list or str): List of allowed HTTP methods or a single method string. Defaults to None.
        - allow_headers (list or str): List of allowed HTTP headers or a single header string. Defaults to None.
        - allow_credentials (bool): Whether to allow credentials (cookies, HTTP authentication) to be sent with requests. Defaults to False.
        - max_age (int): Maximum age (in seconds) of the CORS preflight response. Defaults to None.
        """
        self.cors_config = CORSConfig(
            allow_origins, allow_methods, allow_headers, allow_credentials, max_age
        )

    @staticmethod
    def serve_file(file_path, content_type):
        """
        Serves the content of a file as a response.

        Args:
            file_path (str): The path to the file to be served.
            content_type (str): The content type of the file.

        Returns:
            Response: The response object containing the file content.

        Raises:
            Exception: If there is an error while reading the file.
        """
        try:
            with open(file_path, "r") as file:
                content = file.read()
            return Response(content, headers={"Content-Type": content_type})
        except Exception as e:
            return Response({"error": str(e)}, status_code=500)

    @staticmethod
    def parse_json(body):
        """
        Parse the given JSON string and return the corresponding Python object.

        Args:
            body (str): The JSON string to be parsed.

        Returns:
            object: The Python object representing the parsed JSON, or None if parsing fails.
        """
        try:
            return json.loads(body)
        except Exception:
            return None