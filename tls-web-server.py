import http.server
import os
import ssl


class RestrictedHandler(http.server.SimpleHTTPRequestHandler):
    target_file = ""

    def end_headers(self):
        # Tell the browser not to cache this report
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        # Check if the requested path matches your specific file
        if self.path == f'/{self.target_file}':
            super().do_GET()
        else:
            self.send_error(404, "File Not Found")


def run_server(port, certfile, keyfile, target_file):
    # Pass the filename to the handler class
    RestrictedHandler.target_file = target_file

    # Initialize the server
    server_address = ('', port)

    handler = lambda request, client_address, server: RestrictedHandler(request, client_address, server)
    httpd = http.server.HTTPServer(server_address, handler)

    # Create a configuration context for the TLS endpoint
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    # Wrap the HTTP socket using the configured TLS context
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Serving {target_file} securely via TLS on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()


if __name__ == "__main__":
    # Configuration
    PORT = 4443
    CERT_CHAIN = "path/to/your/certificate_chain.pem"
    PRIVATE_KEY = "path/to/your/private_key.pem"
    FILE_NAME = "sap-wdp-report.html"

    if os.path.exists(FILE_NAME):
        run_server(PORT, CERT_CHAIN, PRIVATE_KEY, FILE_NAME)
    else:
        print(f"Error: {FILE_NAME} not found in the current directory.")
