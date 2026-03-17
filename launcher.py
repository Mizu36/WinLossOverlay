import os
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

import gui
import main


class OverlayHttpRequestHandler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		application_root_directory = str(main.get_app_root())
		super().__init__(*args, directory=application_root_directory, **kwargs)

	def end_headers(self):
		requested_path = self.path.split("?", 1)[0].lower()
		if requested_path.endswith("/data/overlay_state.json"):
			self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
			self.send_header("Pragma", "no-cache")
		elif "/overlay/assets/" in requested_path:
			self.send_header("Cache-Control", "public, max-age=31536000, immutable")
		else:
			self.send_header("Cache-Control", "no-cache")
		super().end_headers()


class ReusableTcpServer(TCPServer):
	allow_reuse_address = True


class OverlayLocalServer:
	def __init__(self, host_name="127.0.0.1", port_number=17357):
		self.host_name = host_name
		self.port_number = port_number
		self.server_instance = None
		self.server_thread = None

	def start(self):
		self.server_instance = ReusableTcpServer((self.host_name, self.port_number), OverlayHttpRequestHandler)
		self.server_thread = threading.Thread(target=self.server_instance.serve_forever, daemon=True)
		self.server_thread.start()

	def stop(self):
		if self.server_instance is not None:
			self.server_instance.shutdown()
			self.server_instance.server_close()
			self.server_instance = None


def print_obs_source_urls(port_number):
	stats_source_url = f"http://127.0.0.1:{port_number}/overlay/stats/index.html"
	rank_source_url = f"http://127.0.0.1:{port_number}/overlay/rank/index.html"

	print("=" * 70)
	print("Win/Loss Overlay - OBS Browser Source URLs")
	print(f"Stats Source: {stats_source_url}")
	print(f"Rank Source:  {rank_source_url}")
	print("=" * 70)


def run_launcher():
	os.chdir(main.get_app_root())
	main.main()

	overlay_local_server = OverlayLocalServer()
	overlay_local_server.start()
	print_obs_source_urls(overlay_local_server.port_number)

	try:
		gui.run_gui(overlay_port=overlay_local_server.port_number)
	finally:
		overlay_local_server.stop()


if __name__ == "__main__":
	run_launcher()
