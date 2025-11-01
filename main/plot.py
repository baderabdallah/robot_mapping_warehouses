import os
import sys
import json
import time
import math
import numpy as np
import matplotlib as mpl

# Choose an interactive matplotlib backend explicitly when possible.
# We avoid forcing a headless backend. If no GUI backend is available, we raise
# with a clear message describing how to enable GUI support.
def _enable_webagg():
    """Configure WebAgg backend to serve an interactive plot over HTTP."""
    # Try to ensure tornado is available for WebAgg
    try:
        import tornado  # noqa: F401
    except Exception:
        # As a courtesy, attempt a lightweight install; ignore failures gracefully
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "tornado"], check=False)
        except Exception:
            pass
    port = int(os.environ.get("WEBAGG_PORT", "8988"))
    mpl.rcParams["webagg.address"] = "0.0.0.0"
    mpl.rcParams["webagg.port"] = port
    mpl.rcParams["webagg.open_in_browser"] = False
    mpl.use("WebAgg", force=True)
    import matplotlib.pyplot as plt  # noqa: E402
    url = f"http://127.0.0.1:{port}"
    print("WebAgg backend enabled.")
    print("Open the forwarded port in your editor or browser:", url)
    print("- VS Code dev containers: check the Ports panel; a port should auto-forward.")
    print("- GitHub Codespaces: accept the forwarded port prompt.")
    return plt


def _select_backend_and_get_pyplot():
    if "MPLBACKEND" in os.environ:
        import matplotlib.pyplot as plt
        return plt

    display = os.environ.get("DISPLAY", "")
    if display:
        # Try GUI backends first
        last_err = None
        for backend in ("Qt5Agg", "TkAgg"):
            try:
                mpl.use(backend, force=True)
                import matplotlib.pyplot as plt  # noqa: F401
                return plt
            except Exception as e:
                last_err = e
        # GUI failed; fall back to WebAgg
        print("GUI backends unavailable or headless (last error:", last_err, ") — falling back to WebAgg.")
        return _enable_webagg()
    else:
        # No DISPLAY: use WebAgg for interactive plotting in a browser
        return _enable_webagg()


plt = _select_backend_and_get_pyplot()
from pathlib import Path


def make_polygon(sides, x_centre_position, y_centre_position, radius, rotate):
    """Draw an n-sided regular polygon.

    Args:
            sides (int): Number of polygon sides.
            x_centre_position, y_centre_position (float): Coordinates of center point.
            radius (int): Radius.
            color (int): RGB565 color value.
            rotate (Optional float): Rotation in degrees relative to origin.
        Note:
            The center point is the center of the x_centre_position,y_centre_position pixel.
            Since pixels are not divisible, the radius is integer rounded
            up to complete on a full pixel.  Therefore diameter = 2 x r + 1.
    """
    x_coordinates = []
    y_coordinates = []
    theta = rotate + math.pi
    n = sides + 1
    for s in range(n):
        t = 2.0 * math.pi * s / sides + theta
        x_coordinates.append(radius * math.cos(t) + x_centre_position)
        y_coordinates.append(radius * math.sin(t) + y_centre_position)

    return x_coordinates, y_coordinates


def make_pointer(endx, endy, orientation):
    return make_polygon(3, endx, endy, 0.07, orientation)


def generate_direction_ray(x_start, y_start, angle):
    x_data = []
    y_data = []
    y_end = y_start + 0.7 * math.sin(angle)
    x_end = x_start + 0.7 * math.cos(angle)
    
    x_data = [x_start,x_end]
    y_data = [y_start,y_end]

    x_polygon_pointer, y_polygon_pointer = make_pointer(
        x_end, y_end, angle + math.pi
    )
    x_data.extend(x_polygon_pointer)
    y_data.extend(y_polygon_pointer)
    x_data.append(np.nan)
    y_data.append(np.nan)
    
    return x_data,y_data

def generate_drawing_object_points(x, y, orientation, polygon_sides, radius, offset=0.0):
    x_polygon, y_polygon = make_polygon(polygon_sides, x, y, radius, orientation)

    xdata = x_polygon
    ydata = y_polygon

    xdata.append(np.nan)
    ydata.append(np.nan)
    # find the end point
    x_line, y_line = generate_direction_ray(x,y, orientation - offset)


    xdata.extend(x_line)
    ydata.extend(y_line)


    return xdata, ydata


def generate_drawing_robot_points(x, y, orientation):
    return generate_drawing_object_points(x, y, orientation, 5, 0.5)


def generate_drawing_carriers_points(poses_list):
    xdata = []
    ydata = []
    for pose in poses_list:
        x_val = float(pose.get("x", 0.0))
        y_val = float(pose.get("y", 0.0))
        theta_val = float(pose.get("theta", 0.0))
        x_generated, y_generated = generate_drawing_object_points(
            x_val,
            y_val,
            theta_val + math.pi / 4,
            4,
            0.8,
            math.pi / 4,
        )
        xdata.extend(x_generated)
        ydata.extend(y_generated)

    return xdata, ydata


def read_json_raw(path):
    with open(path, "r") as f:
        return json.load(f)


def initialize_plot(min_axis_length, max_axis_length):
    figure, ax = plt.subplots()
    (line_robot,) = ax.plot([], [], "-", color="tab:blue", linewidth=2.0, label="Robot shape")
    (line_carriers,) = ax.plot([], [], "-", color="tab:orange", linewidth=2.0, alpha=0.85, label="Carriers shape")
    sc_robot = ax.scatter([], [], s=50, c="tab:blue", marker="o", edgecolors="k", linewidths=0.5, label="Robot center")
    sc_carriers = ax.scatter([], [], s=30, c="tab:orange", marker="x", linewidths=1.0, label="Carrier centers")
    # Set initial limits; will be overridden by computed bounds
    ax.set_xlim(min_axis_length, max_axis_length)
    ax.set_ylim(min_axis_length, max_axis_length)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(loc="upper right")
    return figure, ax, line_robot, line_carriers, sc_robot, sc_carriers


def draw_data_snap_shot(x_data, y_data, lines, ax, figure):
    # Kept for reference; no longer used in the animation-driven flow.
    lines.set_xdata(x_data)
    lines.set_ydata(y_data)
    ax.relim()
    ax.autoscale_view()
    figure.canvas.draw()
    # Avoid plt.pause() to keep compatibility across backends, especially WebAgg.
    # Event processing will be handled by the backend's main loop (via plt.show()).


def main():
    # Locate outputs next to this script by default
    script_dir = Path(__file__).resolve().parent
    robot_poses_path = Path(script_dir) / "robot_poses.json"
    detections_output_path = Path(script_dir) / "detections_output.json"

    robot_data = read_json_raw(str(robot_poses_path))
    detection_data = read_json_raw(str(detections_output_path))

    robot_entries = robot_data.get("robotPose", [])
    detection_entries = detection_data.get("detections", [])

    min_axis_length = 0
    max_axis_length = 25
    figure, ax, line_robot, line_carriers, sc_robot, sc_carriers = initialize_plot(min_axis_length, max_axis_length)

    # Prepare frames for animation and compute global bounds
    frames = []
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")
    for robot_entry, det_entry in zip(robot_entries, detection_entries):
        x = float(robot_entry.get("x", 0.0))
        y = float(robot_entry.get("y", 0.0))
        orientation = float(robot_entry.get("theta", 0.0))
        poses_list = det_entry.get("poses", [])
        x_data_robot, y_data_robot = generate_drawing_robot_points(x, y, orientation)
        x_data_carriers, y_data_carriers = generate_drawing_carriers_points(poses_list)
        # Centers
        carrier_centers_x = [float(p.get("x", 0.0)) for p in poses_list]
        carrier_centers_y = [float(p.get("y", 0.0)) for p in poses_list]
        frames.append((
            x_data_robot, y_data_robot,
            x_data_carriers, y_data_carriers,
            x, y,
            carrier_centers_x, carrier_centers_y,
            robot_entry.get("time") or (det_entry.get("time") or [""])[0]
        ))
        # Update bounds, skipping NaNs (consider both robot and carriers)
        for xv, yv in zip(x_data_robot + x_data_carriers, y_data_robot + y_data_carriers):
            if xv == xv and yv == yv:  # NaN check
                if xv < min_x: min_x = xv
                if xv > max_x: max_x = xv
                if yv < min_y: min_y = yv
                if yv > max_y: max_y = yv

    # If we computed valid bounds, set axes to fit data with padding and equal aspect
    if min_x < max_x and min_y < max_y:
        pad_x = max(1.0, 0.05 * (max_x - min_x))
        pad_y = max(1.0, 0.05 * (max_y - min_y))
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)
        ax.set_aspect("equal", adjustable="box")

    # Use a backend-agnostic timer to drive updates (works reliably with WebAgg/GUI)
    idx = {"i": -1}

    def step():
        i = idx["i"] + 1
        if i >= len(frames):
            # Stop at last frame
            return
        idx["i"] = i
        xr, yr, xc, yc, rx, ry, cx, cy, t = frames[i]
        line_robot.set_data(xr, yr)
        line_carriers.set_data(xc, yc)
        sc_robot.set_offsets(np.array([[rx, ry]]))
        if len(cx) and len(cy):
            sc_carriers.set_offsets(np.column_stack([cx, cy]))
        else:
            sc_carriers.set_offsets(np.empty((0, 2)))
        ax.set_title(f"t={t}")
        figure.canvas.draw_idle()

    anim_timer = figure.canvas.new_timer(interval=50)
    anim_timer.add_callback(step)
    anim_timer.start()

    # Block and show using the backend's main loop (works for GUI and WebAgg)
    plt.show()


if __name__ == "__main__":
    main()
