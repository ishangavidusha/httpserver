import json

class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class Response:
    def __init__(self, body="", status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.set_content_type()

    def set_content_type(self):
        if "Content-Type" not in self.headers:
            if isinstance(self.body, dict):
                self.headers["Content-Type"] = "application/json"
            else:
                self.headers["Content-Type"] = "text/html"

    def add_cors_headers(self, cors_config, origin):
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