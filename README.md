This repo is a proof of concept for some heurestic based mapping for a robot wandering around targets.

Given data.json which containts:
1. Time series of some poses for one robot relative to an origin
1. Time series of some poses for loads relative to the robot

Produce time series of load poses relative to origin complying with the conditions:
* The produced data is to be smooth i.e. implement a filtering mechanism
* The given time series from data.json are mismatched in time so they have to be processed before using.
* Given poses of loads relative to robots flip 180 degrees in angle often, the solution would require to provide a correct orientation.


Live preview (GIF)

![Warehouse mapping animation](plot/animation.gif)

## High-level flow

```mermaid
flowchart TD
	A[Input: data.json<br/>- Robot poses (origin frame)<br/>- Load detections (robot frame)] --> B[Preprocess timelines<br/>- Align timestamps<br/>- Interpolate gaps]
	B --> C[Resolve orientation ambiguity<br/>- Handle frequent 180° flips]
	C --> D[Transform to global frame<br/>- Compose robot and load transforms]
	D --> E[Smooth trajectories<br/>- Filter noise for stability]
	E --> F[Outputs<br/>- robot_poses.json<br/>- detections_output.json]
	F --> G[Visualize or share (optional)<br/>- Interactive plot<br/>- GIF/MP4 export]
```


How to run

- Build: `./run.sh build`
- Run the C++ program: `./run.sh run [path/to/data.json]`
	- Default input is `main/data.json` and outputs are written alongside it.
- Plot interactively: `./run.sh plot`
		- This runs `python3 plot/plot.py` and opens an interactive plot:
			- If a desktop display is available, it uses a native GUI backend (Qt5/Tk).
			- If not (e.g., devcontainer/Codespaces), it falls back to a browser-based interactive backend (WebAgg) and prints a URL/port to open.
- All-in-one: `./run.sh all`


