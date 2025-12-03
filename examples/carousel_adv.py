#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-18 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK

"""
Advanced showcase of viewport and hotspot functionality with UPS battery monitoring.

Extended version of carousel.py that includes UPS Plus battery monitoring showing:
- Battery charge percentage
- Time remaining until fully charged (when charging)
- Total runtime left before shutdown (when on battery)

Requires:
- psutil (+ dependencies)
- smbus2 (for UPS communication)
- geeekpi UPS Plus hardware (https://github.com/geeekpi/upsplus)

Installation:
  $ sudo apt-get install python-dev
  $ sudo pip install psutil smbus2
"""

import time
import psutil

from demo_opts import get_device
from luma.core.virtual import viewport, snapshot

from hotspot import memory, uptime, cpu_load, clock, network, disk, ups_battery


def position(max, step=1):
    forwards = range(0, max, step)
    backwards = range(max, 0, -step)
    while True:
        for x in forwards:
            yield x
        for x in backwards:
            yield x


def pause_every(interval, generator):
    try:
        while True:
            x = next(generator)
            if x % interval == 0:
                for _ in range(20):
                    yield x
            else:
                yield x
    except StopIteration:
        pass


def intersect(a, b):
    return list(set(a) & set(b))


def first(iterable, default=None):
    if iterable:
        for item in iterable:
            return item
    return default


def main():
    # Full screen widgets - one widget at a time
    widget_width = device.width
    widget_height = device.height

    # Create hotspot widgets with faster refresh intervals
    utime = snapshot(widget_width, widget_height, uptime.render, interval=0.5)
    mem = snapshot(widget_width, widget_height, memory.render, interval=0.5)
    dsk = snapshot(widget_width, widget_height, disk.render, interval=1.0)
    cpuload = snapshot(widget_width, widget_height, cpu_load.render, interval=0.25)
    clk = snapshot(widget_width, widget_height, clock.render, interval=0.5)

    # UPS battery monitoring widget
    ups = snapshot(widget_width, widget_height, ups_battery.render, interval=1.0)

    # Network interfaces detection
    network_ifs = psutil.net_if_stats().keys()
    wlan = first(intersect(network_ifs, ["wlan0", "wl0"]), "wlan0")
    eth = first(intersect(network_ifs, ["eth0", "en0"]), "eth0")
    lo = first(intersect(network_ifs, ["lo", "lo0"]), "lo")

    net_wlan = snapshot(widget_width, widget_height, network.stats(wlan), interval=1.0)
    net_eth = snapshot(widget_width, widget_height, network.stats(eth), interval=1.0)
    net_lo = snapshot(widget_width, widget_height, network.stats(lo), interval=1.0)

    # Widget list including UPS battery
    widgets = [cpuload, ups, utime, clk, net_wlan, net_eth, net_lo, mem, dsk]

    # Target frame rate for smooth scrolling (increased to 120 FPS)
    target_fps = 120
    frame_time = 1.0 / target_fps

    # Horizontal scrolling (full screen widgets)
    virtual = viewport(device, width=widget_width * len(widgets), height=widget_height)
    for i, widget in enumerate(widgets):
        virtual.add_hotspot(widget, (i * widget_width, 0))

    scroll_speed = 2  # Pixels per frame for faster scrolling
    for x in pause_every(widget_width, position(widget_width * (len(widgets) - 1), scroll_speed)):
        frame_start = time.time()
        virtual.set_position((x, 0))

        # Sleep only for remaining frame time to maintain consistent FPS
        elapsed = time.time() - frame_start
        sleep_time = frame_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
