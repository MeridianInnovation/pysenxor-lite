"""Interactive MI6 viewer. Requires opencv-python."""

from argparse import ArgumentParser, BooleanOptionalAction

import cv2
import numpy as np

from senxor.log import setup_console_logger
from senxor.mi6 import MI6
from senxor.proc import apply_colormap, colormaps, enlarge, normalize

STYLES = ("blend", "hot_regions", "edges", "raw_index")
DISTANCES = (0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0)
STREAM_KEYS = {"t": "thermal", "r": "rgb", "f": "fusion"}
TYPE_KEYS = {"h": "person", "c": "drinkware", "a": "appliances", "o": "other"}
KEY_HELP = """\
Focus a preview window to use the keyboard.
  t / r / f      Toggle thermal / RGB / fusion
  0 / 1 / 2 / 3  Blend / hot regions / edges / raw index
  m / [ / ]      Toggle mask / decrease / increase mask shrink
  y              Run or pause YOLO
  h / c / a / o  Toggle person / drinkware / appliances / other
  v / b          Toggle detection overlay / switch between outlines and boxes
  , / .          Move the fusion working distance nearer / farther
  n / l / x      Toggle DnCNN / rolling average / disable all filters
  ? / q          Print help / quit
"""


def main() -> None:
    parser = ArgumentParser(description="View and control MI6 TCP image streams.", epilog="Press ? for viewer keys.")
    parser.add_argument("host", nargs="?", default="10.42.1.3")
    parser.add_argument("--port", type=int, default=5600)
    parser.add_argument("--thermal", action=BooleanOptionalAction, default=True)
    parser.add_argument("--rgb", action=BooleanOptionalAction, default=True)
    parser.add_argument("--fusion", action=BooleanOptionalAction, default=False)
    parser.add_argument("--style", choices=STYLES)
    args = parser.parse_args()
    streams = {"thermal": args.thermal, "rgb": args.rgb, "fusion": args.fusion}
    if not any(streams.values()):
        parser.error("Enable at least one image stream.")

    setup_console_logger()
    print(KEY_HELP)
    cmap = colormaps["inferno"]

    with MI6(args.host, args.port) as dev:
        if args.style is not None:
            dev.set_fusion_config(style=args.style)
        dev.set_streams(thermal=streams["thermal"], rgb=streams["rgb"], fusion=streams["fusion"])
        dev.start_stream()
        try:
            for stream, enabled in streams.items():
                if enabled:
                    cv2.namedWindow(stream)

            while True:
                if streams["thermal"]:
                    _, thermal = dev.read(block=False)
                    if thermal is not None:
                        image = apply_colormap(normalize(thermal, dtype=np.float32), cmap)
                        cv2.imshow("thermal", cv2.cvtColor(enlarge(image, 2), cv2.COLOR_RGB2BGR))
                if streams["rgb"]:
                    rgb = dev.read_rgb(block=False)
                    if rgb is not None:
                        cv2.imshow("rgb", rgb)
                if streams["fusion"]:
                    fusion = dev.read_fusion(block=False)
                    if fusion is not None:
                        cv2.imshow("fusion", fusion)

                code = cv2.waitKey(10)
                if code < 0:
                    continue
                key = chr(code & 0xFF)

                if key == "q":
                    break
                if key in STREAM_KEYS:
                    stream = STREAM_KEYS[key]
                    selected = {**streams, stream: not streams[stream]}
                    if not any(selected.values()):
                        print("Keep at least one preview open, or press q to quit.")
                        continue
                    dev.set_streams(thermal=selected["thermal"], rgb=selected["rgb"], fusion=selected["fusion"])
                    streams = selected
                    if streams[stream]:
                        cv2.namedWindow(stream)
                    else:
                        cv2.destroyWindow(stream)
                elif key in "0123":
                    dev.set_fusion_config(style=STYLES[int(key)])
                elif key == "m":
                    dev.set_fusion_config(mask=not dev.get_fusion_config()["mask"])
                elif key in "[]":
                    step = dev.get_fusion_config()["shrink_step"]
                    change = 1 if key == "]" else -1
                    dev.set_fusion_config(shrink_step=max(0, min(7, step + change)))
                elif key == "y":
                    dev.set_detection_config(enabled=not dev.get_detection_config()["enabled"])
                elif key in TYPE_KEYS:
                    types = dev.get_detection_config()["types"]
                    category = TYPE_KEYS[key]
                    if category in types:
                        types.remove(category)
                    else:
                        types.append(category)  # type: ignore  # noqa: PGH003
                    dev.set_detection_config(types=types)
                elif key in "vb":
                    overlay = dev.get_detection_config()["overlay"]
                    if key == "v":
                        dev.set_detection_config(overlay="outlines" if overlay == "off" else "off")
                    else:
                        dev.set_detection_config(overlay="outlines" if overlay == "boxes" else "boxes")
                elif key in ",.":
                    distance = dev.get_fusion_distance()
                    if key == ",":
                        next_distance = next((value for value in reversed(DISTANCES) if value < distance), None)
                    else:
                        next_distance = next((value for value in DISTANCES if value > distance), None)
                    if next_distance is not None:
                        dev.set_fusion_distance(next_distance)
                    print(f"Fusion working distance: {dev.get_fusion_distance():.1f} m")
                elif key == "n":
                    dev.set_dncnn_enable(not dev.get_dncnn_enable())
                elif key == "l":
                    dev.set_mms_ra_enable(not dev.get_mms_ra_enable())
                elif key == "x":
                    dev.disable_all_filters()
                elif key == "?":
                    print(KEY_HELP)
        finally:
            try:
                dev.stop_stream()
            finally:
                cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
