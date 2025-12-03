#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-18 Richard Hull and contributors
# See LICENSE.rst for details.

"""
UPS Plus battery monitoring hotspot.
Displays battery charge percentage, charging time remaining, and runtime left.
Requires geeekpi upsplus hardware and smbus2 library.
"""

try:
    import smbus2

    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False

from hotspot.common import right_text, title_text, tiny_font
import time


# UPS Plus I2C configuration
DEVICE_BUS = 1
DEVICE_ADDR = 0x17

# Cache for UPS data to reduce I2C reads
_ups_cache = None
_ups_cache_time = 0
_cache_validity = 1.5  # Cache valid for 1.5 seconds


def read_ups_data():
    """
    Read UPS battery data from I2C device.
    Returns dict with battery info or None if unavailable.
    Uses caching to reduce I2C traffic.
    """
    global _ups_cache, _ups_cache_time

    # Return cached data if still valid
    current_time = time.time()
    if _ups_cache is not None and (current_time - _ups_cache_time) < _cache_validity:
        return _ups_cache

    if not SMBUS_AVAILABLE:
        return None

    try:
        bus = smbus2.SMBus(DEVICE_BUS)

        # Only read the specific registers we need (much faster than reading all 254)
        # Registers we need: 5-6, 7-8, 9-10, 19-20, 28-31, 32-35
        def read_register_range(start, end):
            """Read a range of registers efficiently."""
            result = []
            for i in range(start, end + 1):
                result.append(bus.read_byte_data(DEVICE_ADDR, i))
            return result

        # Read only necessary registers
        bat_voltage = read_register_range(5, 6)
        charge_typec = read_register_range(7, 8)
        charge_micro = read_register_range(9, 10)
        capacity = read_register_range(19, 20)
        online_time = read_register_range(28, 31)
        full_time = read_register_range(32, 35)

        bus.close()

        # Parse battery data from registers
        data = {
            "capacity_pct": capacity[1] << 8
            | capacity[0],  # Battery remaining capacity %
            "online_time": online_time[3] << 24
            | online_time[2] << 16
            | online_time[1] << 8
            | online_time[0],  # Accumulated running time (sec)
            "full_time": full_time[3] << 24
            | full_time[2] << 16
            | full_time[1] << 8
            | full_time[0],  # Accumulated charged time (sec)
            "bat_voltage": bat_voltage[1] << 8
            | bat_voltage[0],  # Battery port voltage (mV)
            "charge_typec": charge_typec[1] << 8
            | charge_typec[0],  # Type C charging voltage (mV)
            "charge_micro": charge_micro[1] << 8
            | charge_micro[0],  # Micro USB charging voltage (mV)
        }

        # Update cache
        _ups_cache = data
        _ups_cache_time = current_time

        return data

    except Exception as e:
        # Return cached data if available, otherwise None
        return _ups_cache


def format_time(seconds):
    """Format seconds into human-readable time string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins}m"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"


def render(draw, width, height):
    """Render UPS battery information."""
    margin = 5

    data = read_ups_data()

    if data is None:
        # UPS not available
        title_text(draw, margin, width, text="UPS Battery")
        draw.text((margin, 20), text="Status:", font=tiny_font, fill="white")
        draw.text((margin, 35), text="UPS not", font=tiny_font, fill="white")
        draw.text((margin, 45), text="detected", font=tiny_font, fill="white")
        return

    # Determine charging status
    is_charging = data["charge_typec"] > 4000 or data["charge_micro"] > 4000

    # Calculate runtime estimate (rough estimate based on typical discharge)
    # Assuming ~4 hours at 100% capacity
    runtime_hours = (data["capacity_pct"] / 100.0) * 4.0
    runtime_seconds = int(runtime_hours * 3600)

    title_text(draw, margin, width, text="UPS Battery")

    # Display battery percentage
    draw.text((margin, 20), text="Charge:", font=tiny_font, fill="white")
    right_text(draw, 20, width, margin, text=f"{data['capacity_pct']}%")

    if is_charging:
        # Display charging status
        draw.text((margin, 35), text="Status:", font=tiny_font, fill="white")
        right_text(draw, 35, width, margin, text="Charging")

        # Display accumulated charging time
        draw.text((margin, 45), text="Charged:", font=tiny_font, fill="white")
        right_text(draw, 45, width, margin, text=format_time(data["full_time"]))
    else:
        # Display runtime remaining
        draw.text((margin, 35), text="Status:", font=tiny_font, fill="white")
        right_text(draw, 35, width, margin, text="On Batt")

        draw.text((margin, 45), text="Runtime:", font=tiny_font, fill="white")
        right_text(draw, 45, width, margin, text=format_time(runtime_seconds))
