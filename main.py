from server.server import HTTPServer, Response, HTTPError
import json
import time

server = HTTPServer(port=8080, log_level='DEBUG', max_request_size=16384)

# Configure CORS
server.set_cors_config(
    allow_origins=['http://localhost:3000', 'https://example.com'],
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

@server.route('/static/style.css', methods=['GET'])
def serve_css(query_params, headers, body):
    return HTTPServer.serve_file('static/style.css', 'text/css')

if __name__ == '__main__':
    server.start()