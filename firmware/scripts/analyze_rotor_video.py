#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
#   "opencv-python-headless>=4.10",
# ]
# ///
"""Measure physical rotor motion from the green tape marker in a bench video."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    frame: int
    time_s: float
    x: float
    y: float
    area: int


def parse_pair(value: str) -> tuple[float, float]:
    try:
        left, right = value.split(",", 1)
        return float(left), float(right)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected X,Y") from error


def marker_detection(
    frame: np.ndarray,
    frame_index: int,
    fps: float,
    center: tuple[float, float],
    radius: tuple[float, float],
) -> Detection | None:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Painter's-tape green. Saturation rejects the white rotor and grey motor shell.
    mask = cv2.inRange(hsv, (32, 65, 35), (95, 255, 255))
    yy, xx = np.ogrid[: frame.shape[0], : frame.shape[1]]
    distance_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    annulus = (distance_sq >= radius[0] ** 2) & (distance_sq <= radius[1] ** 2)
    mask[~annulus] = 0
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    best: tuple[float, int] | None = None
    for label in range(1, count):
        x, y, width, height, area = (int(v) for v in stats[label])
        if not 12 <= area <= 5_000 or width == 0 or height == 0:
            continue
        fill = area / (width * height)
        aspect = max(width, height) / max(1, min(width, height))
        # Prefer a compact tape patch over a thin green wire crossing the annulus.
        score = area * fill / max(1.0, aspect / 2.5)
        if best is None or score > best[0]:
            best = (score, label)
    if best is None:
        return None
    label = best[1]
    x, y = centroids[label]
    return Detection(frame_index, frame_index / fps, float(x), float(y), int(stats[label, 4]))


def fit_trajectory(detections: list[Detection]) -> tuple[tuple[float, float], tuple[float, float], float]:
    points = np.array([(item.x, item.y) for item in detections], dtype=np.float32)
    if len(points) < 20:
        raise ValueError("fewer than 20 marker detections")
    if np.ptp(points[:, 0]) < 20 or np.ptp(points[:, 1]) < 20:
        raise ValueError("marker did not traverse enough of its orbit to fit a trajectory")
    (cx, cy), (width, height), angle_deg = cv2.fitEllipse(points.reshape(-1, 1, 2))
    return (float(cx), float(cy)), (float(width / 2), float(height / 2)), math.radians(angle_deg)


def unwrap_angles(
    detections: list[Detection],
    ellipse_center: tuple[float, float],
    ellipse_axes: tuple[float, float],
    ellipse_rotation: float,
) -> np.ndarray:
    points = np.array([(item.x - ellipse_center[0], item.y - ellipse_center[1]) for item in detections])
    cosine, sine = math.cos(ellipse_rotation), math.sin(ellipse_rotation)
    rotated_x = cosine * points[:, 0] + sine * points[:, 1]
    rotated_y = -sine * points[:, 0] + cosine * points[:, 1]
    normalized_x = rotated_x / max(ellipse_axes[0], 1.0)
    normalized_y = rotated_y / max(ellipse_axes[1], 1.0)
    return np.unwrap(np.arctan2(normalized_y, normalized_x))


def rolling_speed(times: np.ndarray, angles: np.ndarray, window_s: float = 0.35) -> np.ndarray:
    half = window_s / 2
    left = np.searchsorted(times, times - half, side="left")
    right = np.searchsorted(times, times + half, side="right")
    count = right - left

    def prefix(values: np.ndarray) -> np.ndarray:
        return np.concatenate(([0.0], np.cumsum(values, dtype=float)))

    sum_t = prefix(times)
    sum_angle = prefix(angles)
    sum_tt = prefix(times * times)
    sum_ta = prefix(times * angles)
    st = sum_t[right] - sum_t[left]
    sa = sum_angle[right] - sum_angle[left]
    stt = sum_tt[right] - sum_tt[left]
    sta = sum_ta[right] - sum_ta[left]
    denominator = count * stt - st * st
    result = np.full_like(angles, np.nan, dtype=float)
    usable = (count >= 4) & (np.abs(denominator) > 1e-12)
    result[usable] = (
        (count[usable] * sta[usable] - st[usable] * sa[usable]) / denominator[usable]
    ) * 60 / (2 * math.pi)
    return result


def flow_rotation(
    video: Path,
    center: tuple[float, float],
    radius: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, float, int]:
    """Track the textured rotor face, independent of color or night mode."""
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"cannot open video: {video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, previous_frame = capture.read()
    if not ok or not math.isfinite(fps) or fps < 1:
        capture.release()
        raise ValueError("video has no usable frames or frame rate")
    previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    mask = np.zeros_like(previous)
    cv2.circle(mask, (round(center[0]), round(center[1])), round(radius[1]), 255, -1)
    cv2.circle(mask, (round(center[0]), round(center[1])), round(radius[0]), 0, -1)

    def features(image: np.ndarray) -> np.ndarray | None:
        return cv2.goodFeaturesToTrack(
            image,
            maxCorners=250,
            qualityLevel=0.01,
            minDistance=6,
            mask=mask,
            blockSize=5,
        )

    points = features(previous)
    times = [0.0]
    angles = [0.0]
    valid_transforms = 0
    frame_index = 1
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        delta: float | None = None
        next_points: np.ndarray | None = None
        if points is not None and len(points) >= 8:
            tracked, status, _ = cv2.calcOpticalFlowPyrLK(
                previous,
                current,
                points,
                None,
                winSize=(31, 31),
                maxLevel=4,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
            )
            if tracked is not None and status is not None:
                good = status.reshape(-1).astype(bool)
                source = points.reshape(-1, 2)[good]
                destination = tracked.reshape(-1, 2)[good]
                if len(source) >= 8:
                    valid_transforms += 1
                    source_radius = np.linalg.norm(source - np.asarray(center), axis=1)
                    destination_radius = np.linalg.norm(destination - np.asarray(center), axis=1)
                    displacement = np.linalg.norm(destination - source, axis=1)
                    rotor_points = (np.abs(destination_radius - source_radius) <= 3.0) & (
                        displacement >= 5.00
                    )
                    if np.count_nonzero(rotor_points) >= 8:
                        source_angle = np.arctan2(
                            source[rotor_points, 1] - center[1],
                            source[rotor_points, 0] - center[0],
                        )
                        destination_angle = np.arctan2(
                            destination[rotor_points, 1] - center[1],
                            destination[rotor_points, 0] - center[0],
                        )
                        point_delta = np.angle(np.exp(1j * (destination_angle - source_angle)))
                        candidate = float(np.median(point_delta))
                        deviation = np.abs(point_delta - candidate)
                        tolerance = max(math.radians(0.5), 3 * float(np.median(deviation)))
                        rotational_inliers = deviation <= tolerance
                        if (
                            np.count_nonzero(rotational_inliers) >= 8
                            and abs(candidate) <= math.radians(60)
                        ):
                            delta = float(np.median(point_delta[rotational_inliers]))
                    next_points = destination.reshape(-1, 1, 2)
        if delta is None:
            delta = 0.0
            next_points = features(current)
        else:
            if next_points is None or len(next_points) < 30 or frame_index % 30 == 0:
                next_points = features(current)
        angles.append(angles[-1] + delta)
        times.append(frame_index / fps)
        previous = current
        points = next_points
        frame_index += 1
    capture.release()
    quality = valid_transforms / max(1, frame_index - 1)
    return np.asarray(times), np.asarray(angles), quality, frame_count


def stick_rotation(
    video: Path,
    center: tuple[float, float],
    radius: tuple[float, float],
    maximum_gap_s: float = 0.20,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    """Track the unique radial stick as an unoriented line through the rotor centre.

    The rotor face has fourfold-symmetric holes, so generic optical flow can alias at high
    speed. The stick's line angle is unique modulo 180 degrees; doubling that angle before
    unwrapping recovers continuous physical rotation while each frame advances <90 degrees.
    """
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"cannot open video: {video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not math.isfinite(fps) or fps < 1:
        capture.release()
        raise ValueError("video has no usable frame rate")

    mask: np.ndarray | None = None
    orientations: list[float] = []
    previous_orientation: float | None = None
    recent_steps: list[float] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if mask is None:
            mask = np.zeros_like(gray)
            cv2.circle(mask, (round(center[0]), round(center[1])), round(radius[1]), 255, -1)
            cv2.circle(mask, (round(center[0]), round(center[1])), round(radius[0]), 0, -1)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 35, 90)
        edges[mask == 0] = 0
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 360,
            threshold=45,
            minLineLength=105,
            maxLineGap=28,
        )
        candidates: list[tuple[float, float, float]] = []
        if lines is not None:
            for x1, y1, x2, y2 in lines.reshape(-1, 4):
                dx = float(x2 - x1)
                dy = float(y2 - y1)
                length = math.hypot(dx, dy)
                if length == 0:
                    continue
                distance = abs(dy * (center[0] - x1) - dx * (center[1] - y1)) / length
                midpoint_distance = math.hypot((x1 + x2) / 2 - center[0], (y1 + y2) / 2 - center[1])
                if distance > 24 or midpoint_distance > 115:
                    continue
                angle = math.atan2(dy, dx) % math.pi
                score = length - 2.5 * distance - 0.2 * midpoint_distance
                candidates.append((score, angle, length))
        best: tuple[float, float] | None = None
        for _, anchor, _ in candidates:
            members = [
                item
                for item in candidates
                if abs((item[1] - anchor + math.pi / 2) % math.pi - math.pi / 2)
                <= math.radians(4)
            ]
            weights = np.asarray([item[2] for item in members])
            doubled = np.asarray([2 * item[1] for item in members])
            angle = math.atan2(
                float(np.sum(weights * np.sin(doubled))),
                float(np.sum(weights * np.cos(doubled))),
            ) / 2 % math.pi
            score = sum(max(0.0, item[0]) for item in members) + 30 * len(members)
            if previous_orientation is not None:
                delta = (angle - previous_orientation + math.pi / 2) % math.pi - math.pi / 2
                expected_step = float(np.median(recent_steps)) if recent_steps else 0.0
                score -= 400 * abs(delta - expected_step)
            if best is None or score > best[0]:
                best = (score, angle)
        if best is None:
            orientations.append(math.nan)
        else:
            angle = best[1]
            if previous_orientation is not None:
                delta = (angle - previous_orientation + math.pi / 2) % math.pi - math.pi / 2
                expected_step = float(np.median(recent_steps)) if recent_steps else 0.0
                if not recent_steps or abs(delta - expected_step) <= math.radians(20):
                    recent_steps.append(delta)
                    recent_steps = recent_steps[-7:]
            previous_orientation = angle
            orientations.append(angle)
    capture.release()

    observed = np.isfinite(orientations)
    if np.count_nonzero(observed) < 20:
        raise ValueError("fewer than 20 stick-line detections")
    longest_gap = 0
    current_gap = 0
    for tracked in observed:
        current_gap = 0 if tracked else current_gap + 1
        longest_gap = max(longest_gap, current_gap)
    if longest_gap / fps > maximum_gap_s:
        raise ValueError(
            f"stick tracking gap {longest_gap / fps:.3f}s exceeds {maximum_gap_s:.3f}s"
        )
    indices = np.arange(len(orientations), dtype=float)
    observed_angles = np.asarray(orientations, dtype=float)[observed]
    unwrapped_observed = np.unwrap(2 * observed_angles) / 2
    angles = np.interp(indices, indices[observed], unwrapped_observed)
    # At 30 fps the 170 RPM hardware ceiling advances 34 degrees/frame. A sporadic Hough
    # choice of a rotor label or cable jumps roughly 40-90 degrees and then jumps back;
    # reject those impossible increments without smoothing away real speed ripple.
    maximum_step = math.radians(37)
    raw_steps = np.diff(angles, prepend=angles[0])
    filtered_steps = raw_steps.copy()
    for index in range(len(raw_steps)):
        start = max(0, index - 2)
        end = min(len(raw_steps), index + 3)
        local_median = float(np.median(raw_steps[start:end]))
        if abs(raw_steps[index] - local_median) > math.radians(8):
            filtered_steps[index] = local_median
    accepted_steps = np.where(np.abs(filtered_steps) <= maximum_step, filtered_steps, 0.0)
    angles = angles[0] + np.cumsum(accepted_steps)
    times = indices / fps
    quality = float(np.count_nonzero(observed) / len(observed))
    return times, angles, quality, frame_count


def contiguous_duration(condition: np.ndarray, times: np.ndarray) -> float:
    longest = 0.0
    start: float | None = None
    for matches, time_s in zip(condition, times, strict=True):
        if matches and start is None:
            start = float(time_s)
        elif not matches and start is not None:
            longest = max(longest, float(time_s) - start)
            start = None
    if start is not None:
        longest = max(longest, float(times[-1]) - start)
    return longest


def first_sustained_motion(condition: np.ndarray, times: np.ndarray, window_s: float = 1.0) -> int | None:
    """Return the first sample beginning a mostly-moving one-second window."""
    for index, time_s in enumerate(times):
        if not condition[index]:
            continue
        end = int(np.searchsorted(times, time_s + window_s, side="right"))
        if end - index < 4 or times[end - 1] - time_s < window_s * 0.8:
            continue
        if np.count_nonzero(condition[index:end]) / (end - index) >= 0.8:
            return index
    return None


def analyze(args: argparse.Namespace) -> int:
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        print(f"cannot open video: {args.video}", file=sys.stderr)
        return 2
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not math.isfinite(fps) or fps < 1:
        print("video has no usable frame rate", file=sys.stderr)
        return 2

    detections: list[Detection] = []
    detection_fraction = 0.0
    trajectory_center: tuple[float, float] | None = None
    trajectory_axes: tuple[float, float] | None = None
    tracking_method = "green_marker"
    if args.method == "stick":
        capture.release()
        times, angles, detection_fraction, frame_count = stick_rotation(
            args.video, args.center, args.stick_radius, args.maximum_tracking_gap
        )
        tracking_method = "radial_stick"
    elif args.method != "flow":
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            detection = marker_detection(frame, index, fps, args.center, args.radius)
            if detection is not None:
                detections.append(detection)
            index += 1
        capture.release()
        detection_fraction = len(detections) / max(1, frame_count)
        if detection_fraction >= args.minimum_detection:
            try:
                trajectory_center, trajectory_axes, trajectory_rotation = fit_trajectory(detections)
                times = np.array([item.time_s for item in detections])
                angles = unwrap_angles(detections, trajectory_center, trajectory_axes, trajectory_rotation)
            except ValueError:
                if args.method == "green":
                    raise
                times, angles, detection_fraction, frame_count = flow_rotation(
                    args.video, args.center, args.flow_radius
                )
                tracking_method = "rotor_features"
        elif args.method == "green":
            print(
                json.dumps(
                    {
                        "type": "rotor_tracking_summary",
                        "ok": False,
                        "error": "marker_detection_too_sparse",
                        "detections": len(detections),
                        "frames": frame_count,
                        "detection_fraction": round(detection_fraction, 4),
                    },
                    separators=(",", ":"),
                )
            )
            return 1
        else:
            times, angles, detection_fraction, frame_count = flow_rotation(
                args.video, args.center, args.flow_radius
            )
            tracking_method = "rotor_features"
    else:
        capture.release()
        times, angles, detection_fraction, frame_count = flow_rotation(
            args.video, args.center, args.flow_radius
        )
        tracking_method = "rotor_features"

    if len(times) < 20 or np.ptp(angles) < math.pi:
        print(
            json.dumps(
                {
                    "type": "rotor_tracking_summary",
                    "ok": False,
                    "error": "no_rotation",
                    "tracking_method": tracking_method,
                    "tracking_fraction": round(detection_fraction, 4),
                },
                separators=(",", ":"),
            )
        )
        return 1
    speeds = rolling_speed(times, angles, args.speed_window)
    finite = np.isfinite(speeds)
    significant = finite & (np.abs(speeds) >= args.moving_rpm)
    if not np.any(significant):
        print(json.dumps({"type": "rotor_tracking_summary", "ok": False, "error": "no_rotation"}))
        return 1
    direction = 1.0 if np.nanmedian(speeds[significant]) >= 0 else -1.0
    signed_speeds = speeds * direction
    moving = finite & (signed_speeds >= args.moving_rpm)
    first_moving = first_sustained_motion(moving, times)
    if first_moving is None:
        print(json.dumps({"type": "rotor_tracking_summary", "ok": False, "error": "no_rotation"}))
        return 1

    moving_indices = np.flatnonzero(moving)
    moving_indices = moving_indices[moving_indices >= first_moving]
    last_moving = moving_indices[-1]
    # The video continues through commanded coast-down. Remove its terminal one-second
    # smoothing shoulder so a normal stop is not mislabeled as a running stall.
    active_end_s = max(times[first_moving], times[last_moving] - 1.0)
    active = (np.arange(len(moving)) >= first_moving) & (times <= active_end_s)
    active_finite = active & finite
    reverse = active_finite & (signed_speeds < -args.reverse_rpm)
    stalled = active_finite & (np.abs(signed_speeds) < args.stall_rpm)

    # Judge steady running only after the startup transient and before commanded stop.
    steady_start_s = times[first_moving] + args.settle_seconds
    steady = active_finite & (times >= steady_start_s)
    steady_speeds = signed_speeds[steady]
    summary = {
        "type": "rotor_tracking_summary",
        "ok": True,
        "tracking_method": tracking_method,
        "frames": frame_count,
        "detections": len(detections),
        "tracking_fraction": round(detection_fraction, 4),
        "first_motion_s": round(float(times[first_moving]), 3),
        "last_motion_s": round(float(times[last_moving]), 3),
        "revolutions": round(float(abs(angles[last_moving] - angles[first_moving]) / (2 * math.pi)), 3),
        "reverse_frames": int(np.count_nonzero(reverse)),
        "longest_reverse_s": round(contiguous_duration(reverse, times), 3),
        "longest_stall_s": round(contiguous_duration(stalled, times), 3),
        "pre_run_excursion_deg": round(
            float(np.ptp(angles[: first_moving + 1]) * 180 / math.pi), 3
        ),
    }
    if trajectory_center is not None and trajectory_axes is not None:
        summary["trajectory_center_px"] = [round(value, 2) for value in trajectory_center]
        summary["trajectory_axes_px"] = [round(value, 2) for value in trajectory_axes]
    if len(steady_speeds) >= 10:
        summary.update(
            {
                "steady_samples": len(steady_speeds),
                "steady_mean_rpm": round(float(np.mean(steady_speeds)), 3),
                "steady_stddev_rpm": round(float(np.std(steady_speeds)), 3),
                "steady_min_rpm": round(float(np.min(steady_speeds)), 3),
                "steady_max_rpm": round(float(np.max(steady_speeds)), 3),
            }
        )
    else:
        summary["steady_samples"] = len(steady_speeds)

    steady_range = (
        float(np.ptp(steady_speeds)) if len(steady_speeds) >= 10 else math.inf
    )
    if args.profile:
        # Per-speed accuracy, direction, ripple, stalls, and reversals are qualified against
        # timestamped dwell windows by analyze_profile_plateaus.py. This pass proves the
        # physical trajectory itself was observable rather than applying one target to a
        # multi-speed or bidirectional profile.
        summary["qualified"] = bool(
            detection_fraction >= args.qualified_detection and len(times) >= 20
        )
    else:
        summary["qualified"] = bool(
            detection_fraction >= args.qualified_detection
            and np.count_nonzero(reverse) == 0
            and summary["longest_stall_s"] <= args.maximum_stall
            and len(steady_speeds) >= 10
            and abs(float(np.mean(steady_speeds)) - args.target_rpm) <= args.mean_tolerance
            and float(np.std(steady_speeds)) <= args.maximum_stddev
            and steady_range <= args.maximum_range
        )

    if args.csv is not None:
        with args.csv.open("w", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(
                (
                    "frame",
                    "t_s",
                    "x",
                    "y",
                    "area_px",
                    "angle_rad",
                    "speed_rpm",
                    "raw_angle_rad",
                    "raw_speed_rpm",
                )
            )
            rows = detections if detections else [
                Detection(index, float(time_s), math.nan, math.nan, 0)
                for index, time_s in enumerate(times)
            ]
            for detection, angle, speed in zip(rows, angles, signed_speeds, strict=True):
                writer.writerow(
                    (
                        detection.frame,
                        f"{detection.time_s:.6f}",
                        f"{detection.x:.3f}",
                        f"{detection.y:.3f}",
                        detection.area,
                        f"{angle * direction:.8f}",
                        "" if not math.isfinite(speed) else f"{speed:.5f}",
                        f"{angle:.8f}",
                        "" if not math.isfinite(speed) else f"{speed / direction:.5f}",
                    )
                )
    print(json.dumps(summary, separators=(",", ":")))
    return 0 if summary["qualified"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--center", type=parse_pair, default=(704.0, 355.0), metavar="X,Y")
    parser.add_argument("--radius", type=parse_pair, default=(110.0, 205.0), metavar="MIN,MAX")
    parser.add_argument("--flow-radius", type=parse_pair, default=(38.0, 210.0), metavar="MIN,MAX")
    parser.add_argument("--stick-radius", type=parse_pair, default=(0.0, 295.0), metavar="MIN,MAX")
    parser.add_argument("--method", choices=("auto", "green", "flow", "stick"), default="auto")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--minimum-detection", type=float, default=0.70)
    parser.add_argument("--moving-rpm", type=float, default=3.0)
    parser.add_argument("--reverse-rpm", type=float, default=2.0)
    parser.add_argument("--stall-rpm", type=float, default=2.0)
    parser.add_argument("--settle-seconds", type=float, default=12.0)
    parser.add_argument("--speed-window", type=float, default=1.0)
    parser.add_argument("--target-rpm", type=float, default=35.0)
    parser.add_argument("--qualified-detection", type=float, default=0.90)
    parser.add_argument("--maximum-stall", type=float, default=0.20)
    parser.add_argument("--mean-tolerance", type=float, default=1.50)
    parser.add_argument("--maximum-stddev", type=float, default=1.00)
    parser.add_argument("--maximum-range", type=float, default=5.00)
    parser.add_argument("--maximum-tracking-gap", type=float, default=0.20)
    parser.add_argument(
        "--profile",
        action="store_true",
        help="defer per-speed and direction qualification to timestamped plateau analysis",
    )
    return analyze(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
