This repo is a proof of concept for some heurestic based mapping for a robot wandering around targets.

Given data.json which containts:
1. Time series of some poses for one robot relative to an origin
1. Time series of some poses for loads relative to the robot

Produce time series of load poses relative to origin complying with the conditions:
* The produced data is to be smooth i.e. implement a filtering mechanism
* The given time series from data.json are mismatched in time so they have to be processed before using.
* Given poses of loads relative to robots flip 180 degrees in angle often, the solution would require to provide a correct orientation.


Solution demo:

https://user-images.githubusercontent.com/43698361/182023452-6c452dad-5a40-4414-be3f-16035a98391f.mp4


How to run

- Build: `./run.sh build`
- Run the C++ program: `./run.sh run [path/to/data.json]`
	- Default input is `main/data.json` and outputs are written alongside it.
- Plot interactively: `./run.sh plot`
		- This runs `python3 main/plot.py` and opens an interactive plot:
			- If a desktop display is available, it uses a native GUI backend (Qt5/Tk).
			- If not (e.g., devcontainer/Codespaces), it falls back to a browser-based interactive backend (WebAgg) and prints a URL/port to open.
- All-in-one: `./run.sh all`

Notes
- Bazel is pinned to 7.x via bazelisk for compatibility with WORKSPACE mode.
- Plotting uses numpy/matplotlib. If not installed, the script attempts a lightweight install at runtime.

macOS GUI (optional)

If you're on macOS and want interactive plots from within a Docker/VS Code dev container, XQuartz must allow network clients and your container must reach the host display. A small helper is provided:

1) On the macOS host, run:

	 ./scripts/macos_xquartz_display.sh

	 This starts/configures XQuartz and suggests a DISPLAY like `host.docker.internal:0` or `<your-mac-ip>:0`.

2) Inside the dev container shell, set DISPLAY (you can add to ~/.bashrc to persist):

	 export DISPLAY=host.docker.internal:0

If the window doesn't appear, ensure XQuartz Preferences -> Security -> "Allow connections from network clients" is enabled, and rerun the helper.

Container GUI backends

- The devcontainer installs python3-pyqt5 and python3-tk so that interactive backends (Qt5Agg/TkAgg) work. After pulling these changes, rebuild the dev container to apply them. In VS Code: Dev Containers: Rebuild Container.

Browser-based interactive fallback (WebAgg)

- If no DISPLAY is available, the plot auto-switches to the WebAgg backend and serves the figure over HTTP (default port 8988). VS Code typically auto-forwards this port; check the Ports panel if needed.
- If prompted to install packages at runtime, the script may add tornado to enable WebAgg.

Linux GUI (optional)

If you're on a Linux host and want interactive plots from within the dev container:

1) Allow local Docker containers to access your X server on the host:

	xhost +local:

2) Inside the container, set DISPLAY to match your host (often :0) and ensure your X server is reachable. For example:

	export DISPLAY=:0

   Alternatively, you can configure your devcontainer to pass DISPLAY and mount the X11 socket by adding to .devcontainer/devcontainer.json (advanced):

	"runArgs": ["-e", "DISPLAY", "-v", "/tmp/.X11-unix:/tmp/.X11-unix:ro"]

3) Verify DISPLAY is set (echo $DISPLAY), then run:

	./run.sh plot

The devcontainer installs python3-pyqt5 and python3-tk so matplotlib can use Qt5Agg/TkAgg backends for interactive windows.


