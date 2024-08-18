import json

class HTTPError(Exception):
    """
    Custom exception class for representing HTTP errors.

    Args:
        status_code (int): The HTTP status code of the error.
        message (str): The error message.

    Attributes:
        status_code (int): The HTTP status code of the error.
        message (str): The error message.
    """
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class Response:
    """
    Initializes a Response object.

    Args:
        body (str, optional): The response body. Defaults to "".
        status_code (int, optional): The HTTP status code. Defaults to 200.
        headers (dict, optional): The response headers. Defaults to None.

    Sets the 'Content-Type' header based on the type of the response body.
    If the body is a dictionary, the content type is set to 'application/json'.
    Otherwise, it is set to 'text/html'.

    Adds CORS headers to the response based on the provided CORS configuration and origin.

    Args:
        cors_config (CorsConfig): The CORS configuration.
        origin (str): The origin of the request.

    Converts the response object to bytes.

    Returns:
        bytes: The response as bytes.
    """
    def __init__(self, body="", status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.set_content_type()

    def set_content_type(self):
        """
        Sets the Content-Type header based on the type of the response body.

        If the Content-Type header is not already set, it checks the type of the response body.
        If the body is a dictionary, it sets the Content-Type to "application/json".
        Otherwise, it sets the Content-Type to "text/html".
        """
        if "Content-Type" not in self.headers:
            if isinstance(self.body, dict):
                self.headers["Content-Type"] = "application/json"
            else:
                self.headers["Content-Type"] = "text/html"

    def add_cors_headers(self, cors_config, origin):
        """
        Adds CORS headers to the response.

        Parameters:
        - cors_config (CorsConfig): The CORS configuration.
        - origin (str): The origin of the request.

        Returns:
        None
        """
        if cors_config.allow_origins == ["*"] or origin in cors_config.allow_origins:
            self.headers["Access-Control-Allow-Origin"] = origin
        if cors_config.allow_credentials:
            self.headers["Access-Control-Allow-Credentials"] = "true"
        if self.status_code == 204:  # Preflight response
            self.headers["Access-Control-Allow-Methods"] = ", ".join(
                cors_config.allow_methods
            )
            self.headers["Access-Control-Allow-Headers"] = ", ".join(
                cors_config.allow_headers
            )
            if cors_config.max_age is not None:
                self.headers["Access-Control-Max-Age"] = str(cors_config.max_age)

    def to_bytes(self):
        """
        Converts the HTTP response object to bytes.

        Returns:
            bytes: The HTTP response headers and body encoded as bytes.
        """
        status_codes = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }
        status_text = status_codes.get(self.status_code, "Unknown")

        if isinstance(self.body, dict):
            self.body = json.dumps(self.body)

        headers = [f"HTTP/1.1 {self.status_code} {status_text}"]
        headers.extend([f"{k}: {v}" for k, v in self.headers.items()])
        headers.append(f"Content-Length: {len(self.body)}")
        headers.append("Server: MicroPython-HTTPServer")
        headers.append("\r\n")

        return "\r\n".join(headers).encode("utf-8") + self.body.encode("utf-8")