# MicroPython HTTP Server

A lightweight, feature-rich HTTP server implementation for MicroPython environments. This server supports basic HTTP methods, CORS, Server-Sent Events (SSE), and more.

## Features

- Support for HTTP methods: GET, POST, PUT, DELETE, OPTIONS
- CORS (Cross-Origin Resource Sharing) support
- Server-Sent Events (SSE) for real-time updates
- Query parameter parsing
- JSON request/response handling
- Static file serving
- Customizable logging
- Error handling with custom HTTP errors

## Requirements

- MicroPython environment
- `socket`, `json`, `time`, and `select` modules (usually included in MicroPython)

## Installation

1. Copy `server` dir to your MicroPython device.
2. Create your main application file (e.g., `main.py`) that imports and uses the server.

## Usage

Here's a basic example of how to use the server:

```python
from server.server import HTTPServer, Response, HTTPError

server = HTTPServer(port=8080, log_level='DEBUG', max_request_size=16384)

# Configure CORS
server.set_cors_config(
    allow_origins=['*'],
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    allow_credentials=True,
    max_age=3600
)

@server.route('/', methods=['GET'])
def home(query_params, headers, body):
    name = query_params.get('name', 'Guest')
    return Response(f"<h1>Welcome to MicroPython HTTP Server, {name}!</h1>")

@server.route('/api/data', methods=['GET', 'POST'])
def api_data(query_params, headers, body):
    if headers.get('content-type') == 'application/json':
        data = HTTPServer.parse_json(body)
        response_data = {
            "message": "Data received",
            "data": data,
            "query_params": query_params
        }
        return Response(response_data)
    raise HTTPError(400, "Invalid Content-Type")

@server.sse_route('/events')
def sse_handler(event_source, headers):
    count = 0
    while True:
        event_source.add_event('update', json.dumps({'count': count, 'time': time.time()}))
        count += 1
        time.sleep(1)

if __name__ == '__main__':
    server.start()
```

## API Reference

### HTTPServer

The main server class.

#### Constructor

```python
HTTPServer(port=8080, log_level='INFO', max_request_size=8192, cors_config=None)
```

- `port`: The port to run the server on (default: 80)
- `log_level`: Logging level (default: 'INFO')
- `max_request_size`: Maximum allowed request size in bytes (default: 8192)
- `cors_config`: CORS configuration (default: None)

#### Methods

- `start()`: Start the server
- `route(path, methods=None)`: Decorator to register a route
- `sse_route(path)`: Decorator to register an SSE route
- `set_cors_config(...)`: Configure CORS settings
- `serve_file(file_path, content_type)`: Serve a static file
- `parse_json(body)`: Parse JSON data

### Response

Class for creating HTTP responses.

#### Constructor

```python
Response(body='', status_code=200, headers=None)
```

### HTTPError

Custom exception for HTTP errors.

#### Constructor

```python
HTTPError(status_code, message)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).