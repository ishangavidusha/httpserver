import socket
import json
import time
import select

class Logger:
    LEVELS = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'CRITICAL': 4
    }

    def __init__(self, level='INFO'):
        self.level = self.LEVELS[level]

    def log(self, level, message):
        if self.LEVELS[level] >= self.level:
            timestamp = time.localtime()
            print(f"{timestamp[0]}-{timestamp[1]:02d}-{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d} [{level}] {message}")

    def debug(self, message):
        self.log('DEBUG', message)

    def info(self, message):
        self.log('INFO', message)

    def warning(self, message):
        self.log('WARNING', message)

    def error(self, message):
        self.log('ERROR', message)

    def critical(self, message):
        self.log('CRITICAL', message)

class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class CORSConfig:
    def __init__(self, allow_origins=None, allow_methods=None, allow_headers=None, allow_credentials=False, max_age=None):
        self.allow_origins = allow_origins or ['*']
        self.allow_methods = allow_methods or ['GET', 'POST', 'OPTIONS']
        self.allow_headers = allow_headers or ['Content-Type']
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
class EventSource:
    def __init__(self):
        self.clients = set()
        self.events = {}

    def add_client(self, client):
        self.clients.add(client)

    def remove_client(self, client):
        self.clients.remove(client)

    def add_event(self, event_name, data):
        self.events[event_name] = data
        self.broadcast(event_name, data)

    def broadcast(self, event_name, data):
        message = self.format_sse_message(event_name, data)
        disconnected_clients = set()
        for client in self.clients:
            try:
                client.send(message)
            except Exception:
                disconnected_clients.add(client)
        
        for client in disconnected_clients:
            self.remove_client(client)

    @staticmethod
    def format_sse_message(event, data):
        return f"event: {event}\ndata: {data}\n\n".encode('utf-8')

class Response:
    def __init__(self, body='', status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.set_content_type()

    def set_content_type(self):
        if 'Content-Type' not in self.headers:
            if isinstance(self.body, dict):
                self.headers['Content-Type'] = 'application/json'
            else:
                self.headers['Content-Type'] = 'text/html'

    def add_cors_headers(self, cors_config, origin):
        if cors_config.allow_origins == ['*'] or origin in cors_config.allow_origins:
            self.headers['Access-Control-Allow-Origin'] = origin
        if cors_config.allow_credentials:
            self.headers['Access-Control-Allow-Credentials'] = 'true'
        if self.status_code == 204:  # Preflight response
            self.headers['Access-Control-Allow-Methods'] = ', '.join(cors_config.allow_methods)
            self.headers['Access-Control-Allow-Headers'] = ', '.join(cors_config.allow_headers)
            if cors_config.max_age is not None:
                self.headers['Access-Control-Max-Age'] = str(cors_config.max_age)

    def to_bytes(self):
        status_codes = {
            200: "OK", 201: "Created", 204: "No Content",
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"
        }
        status_text = status_codes.get(self.status_code, "Unknown")
        
        if isinstance(self.body, dict):
            self.body = json.dumps(self.body)
        
        headers = [f"HTTP/1.1 {self.status_code} {status_text}"]
        headers.extend([f"{k}: {v}" for k, v in self.headers.items()])
        headers.append(f"Content-Length: {len(self.body)}")
        headers.append("Server: MicroPython-HTTPServer")
        headers.append("\r\n")
        
        return '\r\n'.join(headers).encode('utf-8') + self.body.encode('utf-8')

class HTTPServer:
    def __init__(self, port=80, log_level='INFO', max_request_size=8192, cors_config=None):
        self.port = port
        self.socket = None
        self.routes = {}
        self.logger = Logger(log_level)
        self.max_request_size = max_request_size
        self.cors_config = cors_config or CORSConfig()
        self.event_source = EventSource()
        
    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(5)
            self.logger.info(f"Server started on port {self.port}")
            
            while True:
                readable, _, _ = select.select([self.socket] + list(self.event_source.clients), [], [], 0.1)
                for sock in readable:
                    if sock is self.socket:
                        conn, addr = self.socket.accept()
                        self.logger.info(f"New connection from {addr}")
                        try:
                            self.handle_request(conn)
                        except Exception as e:
                            self.logger.error(f"Error handling request: {str(e)}")
                        finally:
                            if conn not in self.event_source.clients:
                                conn.close()
                    else:
                        # Handle potential client disconnection
                        try:
                            data = sock.recv(1024)
                            if not data:
                                self.event_source.remove_client(sock)
                                sock.close()
                        except Exception:
                            self.event_source.remove_client(sock)
                            sock.close()
        except Exception as e:
            self.logger.critical(f"Server error: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()
            
    def handle_request(self, conn):
        try:
            request = b''
            while True:
                chunk = conn.recv(4096)
                request += chunk
                if len(chunk) < 4096:
                    break
                if len(request) > self.max_request_size:
                    raise HTTPError(413, "Request Entity Too Large")
            
            if not request:
                return
            
            request = request.decode('utf-8')
            method, path, query_params, headers, body = self.parse_request(request)
            
            self.logger.info(f"Received {method} request for {path}")
            
            if path in self.routes and self.routes[path].get('SSE'):
                self.handle_sse_request(conn, path, headers)
            elif method == 'OPTIONS':
                response = self.handle_preflight(headers)
                self.send_response(conn, response)
            else:
                response = self.process_request(method, path, query_params, headers, body)
                origin = headers.get('origin')
                if origin:
                    response.add_cors_headers(self.cors_config, origin)
                self.send_response(conn, response)
        except HTTPError as e:
            self.logger.warning(f"HTTP Error {e.status_code}: {e.message}")
            error_response = Response({"error": e.message}, status_code=e.status_code)
            self.send_response(conn, error_response)
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            error_response = Response({"error": "Internal Server Error"}, status_code=500)
            self.send_response(conn, error_response)

    def send_response(self, conn, response):
        conn.send(response.to_bytes())

    def handle_sse_request(self, conn, path, headers):
        response_headers = [
            "HTTP/1.1 200 OK",
            "Content-Type: text/event-stream",
            "Cache-Control: no-cache",
            "Connection: keep-alive",
            "\r\n"
        ]
        conn.send('\r\n'.join(response_headers).encode('utf-8'))

        self.event_source.add_client(conn)
        handler = self.routes[path]['GET']
        try:
            handler(self.event_source, headers)
        except Exception as e:
            self.logger.error(f"Error in SSE handler: {str(e)}")
        finally:
            self.event_source.remove_client(conn)

    def handle_preflight(self, headers):
        requested_method = headers.get('access-control-request-method')
        requested_headers = headers.get('access-control-request-headers')

        if requested_method and requested_method in self.cors_config.allow_methods:
            response = Response('', status_code=204)  # No Content
            if requested_headers:
                self.cors_config.allow_headers.extend([h.strip() for h in requested_headers.split(',')])
            return response
        else:
            raise HTTPError(400, "Invalid preflight request")
        
    def parse_request(self, request):
        try:
            lines = request.split('\r\n')
            method, full_path, _ = lines[0].split()
            
            path, query = full_path.split('?', 1) if '?' in full_path else (full_path, '')
            query_params = self.parse_query_string(query)
            
            headers = {}
            body_start = 0
            for i, line in enumerate(lines[1:]):
                if not line:
                    body_start = i + 2
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            body = '\r\n'.join(lines[body_start:]) if body_start else None
            
            return method, path, query_params, headers, body
        except Exception as e:
            raise HTTPError(400, f"Bad Request: {str(e)}")
        
    def parse_query_string(self, query_string):
        params = {}
        if query_string:
            pairs = query_string.split('&')
            for pair in pairs:
                key, value = pair.split('=', 1) if '=' in pair else (pair, '')
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
            methods = ['GET']
        
        def decorator(handler):
            if path not in self.routes:
                self.routes[path] = {}
            for method in methods:
                self.routes[path][method] = handler
            return handler
        
        return decorator

    def sse_route(self, path):
        def decorator(handler):
            self.routes[path] = {'GET': handler, 'SSE': True}
            return handler
        return decorator
    
    def set_cors_config(self, allow_origins=None, allow_methods=None, allow_headers=None, allow_credentials=False, max_age=None):
        self.cors_config = CORSConfig(allow_origins, allow_methods, allow_headers, allow_credentials, max_age)

    @staticmethod
    def serve_file(file_path, content_type):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            return Response(content, headers={'Content-Type': content_type})
        except Exception:
            return Response("File not found", status_code=404)
    
    @staticmethod
    def parse_json(body):
        try:
            return json.loads(body)
        except Exception:
            return None