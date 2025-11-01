import os
import sys
import json
import time
import math
import numpy as np
import matplotlib as mpl

# Choose an interactive matplotlib backend explicitly when possible.
# Avoid forcing a headless backend; if no GUI backend is available, fall back to WebAgg.
def _enable_webagg():
    """Configure WebAgg backend to serve an interactive plot over HTTP."""
    # Try to ensure tornado is available for WebAgg
    try:
        import tornado  # noqa: F401
    except Exception:
        # Attempt a lightweight install; ignore failures gracefully
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
from pathlib import Path
from plot_core import (
    load_frames,
    setup_figure_and_artists,
    update_artists,
    compute_aspect_from_bounds,
)


def main():
    # Find data files automatically (prefers the repository's main/ directory)
    frames, bounds = load_frames(None)

    # When served via WebAgg, default to filling axes to the canvas for maximum use of page space.
    backend_name = mpl.get_backend().lower()
    fill_axes = ("webagg" in backend_name) and (os.environ.get("WEBAGG_FILL_AXES", "1") != "0")

    # Compute data aspect and initial canvas size
    data_aspect = compute_aspect_from_bounds(bounds)
    target_h_px = int(os.environ.get("WEBAGG_HEIGHT_PX", "740"))
    target_h_px = max(600, min(1200, target_h_px))
    target_w_px = max(1400, min(2800, int(target_h_px * data_aspect)))

    dpi = float(plt.rcParams.get("figure.dpi", 100))
    figure, ax, artists = setup_figure_and_artists(bounds, fill_axes=fill_axes, dpi=dpi, height_px=target_h_px)

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
        update_artists(artists, frames[i], ax=ax)
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
            h_px = int(max(600, min(1200, h_px)))
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
                    target_h = target_h_px if target_h_px else 900
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
