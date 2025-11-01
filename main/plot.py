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
    # Hide toolbar unless explicitly disabled
    if os.environ.get("WEBAGG_HIDE_TOOLBAR", "1") != "0":
        mpl.rcParams["toolbar"] = "None"
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
from matplotlib.markers import MarkerStyle
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


def initialize_plot(min_axis_length, max_axis_length, fill_axes=False):
    figure, ax = plt.subplots()
    (line_robot,) = ax.plot([], [], "-", color="tab:blue", linewidth=2.0, label="Robot shape")
    (line_carriers,) = ax.plot([], [], "-", color="tab:orange", linewidth=2.0, alpha=0.85, label="Carriers shape")
    sc_robot = ax.scatter([], [], s=50, c="tab:blue", marker=MarkerStyle("o"), edgecolors="k", linewidths=0.5, label="Robot center")
    sc_carriers = ax.scatter([], [], s=30, c="tab:orange", marker=MarkerStyle("x"), linewidths=1.0, label="Carrier centers")
    # Set initial limits; will be overridden by computed bounds
    ax.set_xlim(min_axis_length, max_axis_length)
    ax.set_ylim(min_axis_length, max_axis_length)
    if not fill_axes:
        ax.grid(True, linestyle=":", alpha=0.4)
        ax.legend(loc="upper right")
        # Maximize usable plot area (helps when going fullscreen)
        figure.subplots_adjust(left=0.03, right=0.995, top=0.97, bottom=0.05)
    else:
        # Fill entire canvas with axes; we'll also reinforce this after bounds are set
        figure.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
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
    # When served via WebAgg, default to filling axes to the canvas for maximum use of page space.
    backend_name = mpl.get_backend().lower()
    fill_axes = ("webagg" in backend_name) and (os.environ.get("WEBAGG_FILL_AXES", "1") != "0")
    figure, ax, line_robot, line_carriers, sc_robot, sc_carriers = initialize_plot(min_axis_length, max_axis_length, fill_axes=fill_axes)

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
    data_aspect = None
    target_w_px = None
    target_h_px = None
    if min_x < max_x and min_y < max_y:
        pad_scale = 0.02 if fill_axes else 0.05
        pad_x = max(0.5, pad_scale * (max_x - min_x))
        pad_y = max(0.5, pad_scale * (max_y - min_y))
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)
        ax.set_aspect("equal", adjustable="box")
        # Match the figure aspect to the data aspect so the axes fill the canvas.
        width_range = (max_x + pad_x) - (min_x - pad_x)
        height_range = (max_y + pad_y) - (min_y - pad_y)
        if height_range > 0:
            data_aspect = max(0.25, min(4.0, width_range / height_range))  # clamp to reasonable range
            try:
                # Choose a pixel size that avoids vertical scrolling on common viewports,
                # while making width large enough to typically fill the page.
                # You can override height via WEBAGG_HEIGHT_PX.
                dpi = float(figure.get_dpi())
                default_h = 740  # reduce slightly more to avoid any scrolling under common browser chrome
                target_h_px = int(os.environ.get("WEBAGG_HEIGHT_PX", str(default_h)))
                target_h_px = max(600, min(1200, target_h_px))
                # Compute width from aspect, but ensure a reasonably wide canvas.
                computed_w = int(target_h_px * data_aspect)
                target_w_px = max(1400, min(2800, computed_w))
                fig_w_in = target_w_px / dpi
                fig_h_in = target_h_px / dpi
                figure.set_size_inches(fig_w_in, fig_h_in, forward=True)
            except Exception:
                pass

    # If filling axes, remove axes decorations and stretch to the full figure area
    if fill_axes:
        try:
            ax.set_axis_off()
            ax.set_position([0.0, 0.0, 1.0, 1.0])
            figure.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
        except Exception:
            pass

    # Use a backend-agnostic timer to drive updates (works reliably with WebAgg/GUI)
    state = {
        "i": -1,
        "playing": True,
        "interval": 50,  # ms
        "show_hud": fill_axes,  # show HUD only in fill mode by default
    }

    # HUD overlay (for fill mode) to keep the view clean but informative
    hud = None
    if fill_axes:
        try:
            hud = ax.text(
                0.01, 0.99, "",
                transform=ax.transAxes,
                ha="left", va="top",
                fontsize=9, color="white",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="black", alpha=0.35, edgecolor="none"),
                zorder=10,
            )
        except Exception:
            hud = None

    def render_frame(i):
        xr, yr, xc, yc, rx, ry, cx, cy, t = frames[i]
        line_robot.set_data(xr, yr)
        line_carriers.set_data(xc, yc)
        sc_robot.set_offsets(np.array([[rx, ry]]))
        if len(cx) and len(cy):
            sc_carriers.set_offsets(np.column_stack([cx, cy]))
        else:
            sc_carriers.set_offsets(np.empty((0, 2)))
        if not fill_axes:
            ax.set_title(f"t={t}")
        if hud is not None and state["show_hud"]:
            fps = 1000.0 / max(1, state["interval"]) if state["playing"] else 0
            hud.set_text(
                f"Frame {i+1}/{len(frames)}  t={t}\n"
                f"Space: play/pause  ←/→: step  [-]: smaller  [+]: bigger  1-5: presets  [: slow  ]: fast"
            )
        elif hud is not None:
            hud.set_text("")
        figure.canvas.draw_idle()

    def step():
        if not state["playing"]:
            # Keep event loop alive without advancing frames
            figure.canvas.draw_idle()
            return
        i = state["i"] + 1
        if i >= len(frames):
            i = len(frames) - 1
            state["playing"] = False
        state["i"] = i
        render_frame(i)

    anim_timer = figure.canvas.new_timer(interval=state["interval"])
    anim_timer.add_callback(step)
    anim_timer.start()

    # Keyboard controls for user-friendly adjustments (especially sizing)
    def on_key(event):
        try:
            key = (event.key or "").lower()
        except Exception:
            key = ""

        mgr = None
        try:
            mgr = plt.get_current_fig_manager()
        except Exception:
            pass

        # Helpers: resizing keeping aspect
        def resize_to_height(h_px):
            nonlocal target_w_px, target_h_px
            try:
                local_aspect = data_aspect if ("data_aspect" in locals() and data_aspect) else (16/9)
            except Exception:
                local_aspect = 16/9
            h_px = int(max(600, min(1400, h_px)))
            w_px = int(max(1000, min(3200, h_px * local_aspect)))
            target_w_px, target_h_px = w_px, h_px
            try:
                if mgr is not None and hasattr(mgr, "resize") and callable(getattr(mgr, "resize")):
                    mgr.resize(w_px, h_px)
                # Also set inches for crispness
                dpi = float(figure.get_dpi())
                figure.set_size_inches(w_px / dpi, h_px / dpi, forward=True)
            except Exception:
                pass

        # Playback controls
        if key in (" ", "space"):
            state["playing"] = not state["playing"]
            return
        if key in ("right",):
            state["playing"] = False
            i = min(len(frames) - 1, state["i"] + 1)
            state["i"] = i
            render_frame(i)
            return
        if key in ("left",):
            state["playing"] = False
            i = max(0, state["i"] - 1)
            state["i"] = i
            render_frame(i)
            return

        # Speed controls
        if key == "[":  # slower
            state["interval"] = int(min(500, state["interval"] * 1.4))
            anim_timer.stop(); anim_timer.interval = state["interval"]; anim_timer.start()
            return
        if key == "]":  # faster
            state["interval"] = int(max(10, state["interval"] / 1.4))
            anim_timer.stop(); anim_timer.interval = state["interval"]; anim_timer.start()
            return

        # HUD toggle
        if key == "h":
            state["show_hud"] = not state["show_hud"]
            return

        # Fullscreen toggle
        if key == "f" and mgr is not None:
            try:
                if callable(getattr(mgr, "full_screen_toggle", None)):
                    mgr.full_screen_toggle()
            except Exception:
                pass
            return

        # Resize presets
        if key in ("1", "2", "3", "4", "5", "+", "="):
            presets = {
                "1": 680, "2": 720, "3": 740, "4": 820, "5": 900,
            }
            if key in presets:
                resize_to_height(presets[key])
            else:
                # '+' or '=' increase in steps
                step_px = 80
                target = (target_h_px or 740) + step_px
                resize_to_height(target)
            return
        if key == "-":
            step_px = 80
            target = (target_h_px or 740) - step_px
            resize_to_height(target)
            return

    try:
        figure.canvas.mpl_connect('key_press_event', on_key)
    except Exception:
        pass

    # Request fullscreen once the backend event loop is running.
    # For WebAgg and most GUI backends, the manager exposes full_screen_toggle().
    try:
        manager = plt.get_current_fig_manager()
        toggle_fullscreen = getattr(manager, "full_screen_toggle", None)
        resize_fn = getattr(manager, "resize", None)
        # Use a one-shot timer so it fires shortly after the window/tab is ready.
        delay = 350 if "webagg" in mpl.get_backend().lower() else 150
        fit_timer = figure.canvas.new_timer(interval=delay)

        def _fit_and_fullscreen():
            try:
                # Attempt fullscreen first (may be blocked by browser policy)
                if callable(toggle_fullscreen):
                    try:
                        toggle_fullscreen()
                    except Exception as e_fs:
                        print("Fullscreen toggle failed:", e_fs)

                # Also try to resize the canvas to a large size with matching aspect
                if callable(resize_fn):
                    # Use computed target size if available; otherwise fall back.
                    target_w = target_w_px if target_w_px else 1600
                    target_h = target_h_px if target_h_px else (int(max(600, min(1200, target_w / data_aspect))) if data_aspect else 900)
                    try:
                        resize_fn(target_w, target_h)
                    except Exception as e_rs:
                        print("Resize failed:", e_rs)
            finally:
                try:
                    fit_timer.stop()
                except Exception:
                    pass

        fit_timer.add_callback(_fit_and_fullscreen)
        fit_timer.start()
    except Exception as e:
        print("Could not request fullscreen/resize:", e)

    # Block and show using the backend's main loop (works for GUI and WebAgg)
    plt.show()


if __name__ == "__main__":
    main()
