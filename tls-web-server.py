import http.server
import os
import ssl


def run_server(port, certfile, keyfile, target_file):
    # Define a custom handler to restrict access to the specific file
    class RestrictedHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Tell the browser not to cache this report
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def do_GET(self):
            # Check if the requested path matches your specific file
            if self.path == f'/{target_file}':
                super().do_GET()
            else:
                self.send_error(404, "File Not Found")

    # Initialize the server
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, RestrictedHandler)

    # Wrap the socket with TLS
    # certfile should contain the certificate chain
    # keyfile should contain the private key
    httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, certfile=certfile, keyfile=keyfile,
        ssl_version=ssl.PROTOCOL_TLS)

    print(f"Serving {target_file} securely on port {port}...")
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
