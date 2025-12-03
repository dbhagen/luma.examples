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


# UPS Plus I2C configuration
DEVICE_BUS = 1
DEVICE_ADDR = 0x17


def read_ups_data():
    """
    Read UPS battery data from I2C device.
    Returns dict with battery info or None if unavailable.
    """
    if not SMBUS_AVAILABLE:
        return None

    try:
        bus = smbus2.SMBus(DEVICE_BUS)

        # Read all registers (1-254)
        aReceiveBuf = [0x00]  # Placeholder for index 0
        for i in range(1, 255):
            aReceiveBuf.append(bus.read_byte_data(DEVICE_ADDR, i))

        bus.close()

        # Parse battery data from registers
        data = {
            "capacity_pct": aReceiveBuf[20] << 8
            | aReceiveBuf[19],  # Battery remaining capacity %
            "online_time": aReceiveBuf[31] << 24
            | aReceiveBuf[30] << 16
            | aReceiveBuf[29] << 8
            | aReceiveBuf[28],  # Accumulated running time (sec)
            "full_time": aReceiveBuf[35] << 24
            | aReceiveBuf[34] << 16
            | aReceiveBuf[33] << 8
            | aReceiveBuf[32],  # Accumulated charged time (sec)
            "bat_voltage": aReceiveBuf[6] << 8
            | aReceiveBuf[5],  # Battery port voltage (mV)
            "charge_typec": aReceiveBuf[8] << 8
            | aReceiveBuf[7],  # Type C charging voltage (mV)
            "charge_micro": aReceiveBuf[10] << 8
            | aReceiveBuf[9],  # Micro USB charging voltage (mV)
        }

        return data

    except Exception as e:
        # Return None if UPS hardware not available
        return None


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
