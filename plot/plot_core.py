import json
import math
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.markers import MarkerStyle

# ----------------------- Geometry helpers -----------------------

def make_polygon(sides: int, x_centre_position: float, y_centre_position: float, radius: float, rotate: float):
    x_coordinates = []
    y_coordinates = []
    theta = rotate + math.pi
    n = sides + 1
    for s in range(n):
        t = 2.0 * math.pi * s / sides + theta
        x_coordinates.append(radius * math.cos(t) + x_centre_position)
        y_coordinates.append(radius * math.sin(t) + y_centre_position)
    return x_coordinates, y_coordinates


def make_pointer(endx: float, endy: float, orientation: float):
    return make_polygon(3, endx, endy, 0.07, orientation)


def generate_direction_ray(x_start: float, y_start: float, angle: float):
    y_end = y_start + 0.7 * math.sin(angle)
    x_end = x_start + 0.7 * math.cos(angle)
    x_data = [x_start, x_end]
    y_data = [y_start, y_end]
    x_polygon_pointer, y_polygon_pointer = make_pointer(x_end, y_end, angle + math.pi)
    x_data.extend(x_polygon_pointer)
    y_data.extend(y_polygon_pointer)
    x_data.append(np.nan)
    y_data.append(np.nan)
    return x_data, y_data


def generate_drawing_object_points(x: float, y: float, orientation: float, polygon_sides: int, radius: float, offset: float = 0.0):
    x_polygon, y_polygon = make_polygon(polygon_sides, x, y, radius, orientation)
    xdata = list(x_polygon)
    ydata = list(y_polygon)
    xdata.append(np.nan)
    ydata.append(np.nan)
    x_line, y_line = generate_direction_ray(x, y, orientation - offset)
    xdata.extend(x_line)
    ydata.extend(y_line)
    return xdata, ydata


def generate_drawing_robot_points(x: float, y: float, orientation: float):
    return generate_drawing_object_points(x, y, orientation, 5, 0.5)


def generate_drawing_carriers_points(poses_list: List[dict]):
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


# ----------------------- Data loading -----------------------

def read_json_raw(path: str):
    with open(path, "r") as f:
        return json.load(f)


def _find_data_dir(explicit: Optional[Path] = None) -> Path:
    if explicit and (explicit / "robot_poses.json").exists():
        return explicit
    here = Path(__file__).resolve().parent
    candidates = [
        here,  # legacy (when code lived in main/)
        here.parent / "main",  # default when code lives in plot/
        Path.cwd() / "main",
        here.parent,  # repo root (if jsons were moved next to root)
    ]
    for c in candidates:
        if (c / "robot_poses.json").exists() and (c / "detections_output.json").exists():
            return c
    # fallback to here
    return here


def load_frames(data_dir: Optional[Path] = None):
    data_dir = _find_data_dir(data_dir)
    robot_poses_path = data_dir / "robot_poses.json"
    detections_output_path = data_dir / "detections_output.json"

    robot_data = read_json_raw(str(robot_poses_path))
    detection_data = read_json_raw(str(detections_output_path))

    robot_entries = robot_data.get("robotPose", [])
    detection_entries = detection_data.get("detections", [])

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
        carrier_centers_x = [float(p.get("x", 0.0)) for p in poses_list]
        carrier_centers_y = [float(p.get("y", 0.0)) for p in poses_list]
        frames.append(
            (
                x_data_robot,
                y_data_robot,
                x_data_carriers,
                y_data_carriers,
                x,
                y,
                carrier_centers_x,
                carrier_centers_y,
                robot_entry.get("time") or (det_entry.get("time") or [""])[0],
            )
        )
        for xv, yv in zip(x_data_robot + x_data_carriers, y_data_robot + y_data_carriers):
            if xv == xv and yv == yv:
                min_x = min(min_x, xv)
                max_x = max(max_x, xv)
                min_y = min(min_y, yv)
                max_y = max(max_y, yv)

    return frames, (min_x, max_x, min_y, max_y)


def compute_aspect_from_bounds(bounds: Tuple[float, float, float, float]):
    min_x, max_x, min_y, max_y = bounds
    if not (min_x < max_x and min_y < max_y):
        return 1.0
    pad_x = max(0.5, 0.02 * (max_x - min_x))
    pad_y = max(0.5, 0.02 * (max_y - min_y))
    x0, x1 = min_x - pad_x, max_x + pad_x
    y0, y1 = min_y - pad_y, max_y + pad_y
    width_range = x1 - x0
    height_range = y1 - y0
    return max(0.25, min(4.0, width_range / max(1e-9, height_range)))


# ----------------------- Figure/Artists -----------------------

def setup_figure_and_artists(bounds, fill_axes: bool, dpi: float = 100.0, height_px: int = 720):
    min_x, max_x, min_y, max_y = bounds
    if not (min_x < max_x and min_y < max_y):
        min_x, max_x, min_y, max_y = 0, 25, 0, 25
    pad_x = max(0.5, 0.02 * (max_x - min_x))
    pad_y = max(0.5, 0.02 * (max_y - min_y))
    x0, x1 = min_x - pad_x, max_x + pad_x
    y0, y1 = min_y - pad_y, max_y + pad_y

    aspect = compute_aspect_from_bounds(bounds)
    width_px = int(height_px * aspect)
    fig = plt.figure(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)
    if fill_axes:
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
    else:
        ax = fig.add_subplot(111)
        ax.grid(True, linestyle=":", alpha=0.4)
        fig.subplots_adjust(left=0.03, right=0.995, top=0.97, bottom=0.05)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    (line_robot,) = ax.plot([], [], "-", color="tab:blue", linewidth=2.0, label="Robot shape")
    (line_carriers,) = ax.plot([], [], "-", color="tab:orange", linewidth=2.0, alpha=0.85, label="Carriers shape")
    sc_robot = ax.scatter([], [], s=50, c="tab:blue", marker=MarkerStyle("o"), edgecolors="k", linewidths=0.5, label="Robot center")
    sc_carriers = ax.scatter([], [], s=30, c="tab:orange", marker=MarkerStyle("x"), linewidths=1.0, label="Carrier centers")

    if not fill_axes:
        ax.legend(loc="upper right")

    artists = (line_robot, line_carriers, sc_robot, sc_carriers)
    return fig, ax, artists


def update_artists(artists, frame, ax=None):
    line_robot, line_carriers, sc_robot, sc_carriers = artists
    xr, yr, xc, yc, rx, ry, cx, cy, _t = frame
    line_robot.set_data(xr, yr)
    line_carriers.set_data(xc, yc)
    sc_robot.set_offsets(np.array([[rx, ry]]))
    if len(cx) and len(cy):
        sc_carriers.set_offsets(np.column_stack([cx, cy]))
    else:
        sc_carriers.set_offsets(np.empty((0, 2)))
    if ax is not None:
        ax.figure.canvas.draw_idle()
