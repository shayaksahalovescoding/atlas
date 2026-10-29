from atlas.app.twin.entities.base import Entity


class Machine(Entity):
    def __init__(self, name="Local Machine", **kwargs):
        super().__init__("machine", name, **kwargs)
        self.properties.setdefault("hostname", "")
        self.properties.setdefault("os_version", "")
        self.properties.setdefault("os_build", "")
        self.properties.setdefault("architecture", "")
        self.properties.setdefault("domain", "")
        self.properties.setdefault("username", "")
        self.properties.setdefault("boot_time", "")
        self.properties.setdefault("uptime_seconds", 0)


class CPU(Entity):
    def __init__(self, name="CPU", **kwargs):
        super().__init__("cpu", name, **kwargs)
        self.properties.setdefault("brand", "")
        self.properties.setdefault("vendor", "")
        self.properties.setdefault("cores_physical", 0)
        self.properties.setdefault("cores_logical", 0)
        self.properties.setdefault("base_frequency_mhz", 0)
        self.properties.setdefault("max_frequency_mhz", 0)
        self.properties.setdefault("current_frequency_mhz", 0)
        self.properties.setdefault("usage_percent", 0.0)
        self.properties.setdefault("temperature_c", None)
        self.properties.setdefault("architecture", "")
        self.properties.setdefault("cache_l2_kb", 0)
        self.properties.setdefault("cache_l3_kb", 0)


class GPU(Entity):
    def __init__(self, name="GPU", **kwargs):
        super().__init__("gpu", name, **kwargs)
        self.properties.setdefault("vendor", "")
        self.properties.setdefault("driver_version", "")
        self.properties.setdefault("memory_total_mb", 0)
        self.properties.setdefault("memory_used_mb", 0)
        self.properties.setdefault("memory_free_mb", 0)
        self.properties.setdefault("usage_percent", 0.0)
        self.properties.setdefault("temperature_c", None)
        self.properties.setdefault("adapter_type", "")


class MemoryModule(Entity):
    def __init__(self, name="RAM", **kwargs):
        super().__init__("memory", name, **kwargs)
        self.properties.setdefault("total_bytes", 0)
        self.properties.setdefault("available_bytes", 0)
        self.properties.setdefault("used_bytes", 0)
        self.properties.setdefault("usage_percent", 0.0)
        self.properties.setdefault("swap_total_bytes", 0)
        self.properties.setdefault("swap_used_bytes", 0)
        self.properties.setdefault("swap_percent", 0.0)
        self.properties.setdefault("speed_mhz", 0)
        self.properties.setdefault("type", "")
        self.properties.setdefault("slots_used", 0)
        self.properties.setdefault("slots_total", 0)


class StorageDevice(Entity):
    def __init__(self, name="Storage", **kwargs):
        super().__init__("storage_device", name, **kwargs)
        self.properties.setdefault("device_type", "")
        self.properties.setdefault("model", "")
        self.properties.setdefault("serial", "")
        self.properties.setdefault("size_bytes", 0)
        self.properties.setdefault("interface", "")
        self.properties.setdefault("firmware", "")
        self.properties.setdefault("smart_status", "")
        self.properties.setdefault("temperature_c", None)


class Partition(Entity):
    def __init__(self, name="Partition", **kwargs):
        super().__init__("partition", name, **kwargs)
        self.properties.setdefault("mount_point", "")
        self.properties.setdefault("filesystem", "")
        self.properties.setdefault("total_bytes", 0)
        self.properties.setdefault("used_bytes", 0)
        self.properties.setdefault("free_bytes", 0)
        self.properties.setdefault("usage_percent", 0.0)
        self.properties.setdefault("device_id", "")
        self.properties.setdefault("label", "")


class NetworkAdapter(Entity):
    def __init__(self, name="Network Adapter", **kwargs):
        super().__init__("network_adapter", name, **kwargs)
        self.properties.setdefault("adapter_type", "")
        self.properties.setdefault("mac_address", "")
        self.properties.setdefault("ipv4_addresses", [])
        self.properties.setdefault("ipv6_addresses", [])
        self.properties.setdefault("speed_mbps", 0)
        self.properties.setdefault("is_up", False)
        self.properties.setdefault("bytes_sent", 0)
        self.properties.setdefault("bytes_recv", 0)
        self.properties.setdefault("dns_servers", [])
        self.properties.setdefault("gateway", "")
        self.properties.setdefault("dhcp_enabled", False)


class Display(Entity):
    def __init__(self, name="Display", **kwargs):
        super().__init__("display", name, **kwargs)
        self.properties.setdefault("resolution", "")
        self.properties.setdefault("refresh_rate_hz", 0)
        self.properties.setdefault("is_primary", False)
        self.properties.setdefault("orientation", "")
        self.properties.setdefault("bits_per_pixel", 0)
        self.properties.setdefault("adapter", "")


class Device(Entity):
    def __init__(self, name="Device", **kwargs):
        super().__init__("device", name, **kwargs)
        self.properties.setdefault("device_class", "")
        self.properties.setdefault("manufacturer", "")
        self.properties.setdefault("device_id", "")
        self.properties.setdefault("hardware_id", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("driver_name", "")


class Driver(Entity):
    def __init__(self, name="Driver", **kwargs):
        super().__init__("driver", name, **kwargs)
        self.properties.setdefault("version", "")
        self.properties.setdefault("provider", "")
        self.properties.setdefault("date", "")
        self.properties.setdefault("path", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("start_type", "")
        self.properties.setdefault("type", "")
        self.properties.setdefault("signed", None)


class Motherboard(Entity):
    def __init__(self, name="Motherboard", **kwargs):
        super().__init__("motherboard", name, **kwargs)
        self.properties.setdefault("manufacturer", "")
        self.properties.setdefault("product", "")
        self.properties.setdefault("serial", "")
        self.properties.setdefault("bios_version", "")
        self.properties.setdefault("bios_vendor", "")
        self.properties.setdefault("bios_date", "")


class Battery(Entity):
    def __init__(self, name="Battery", **kwargs):
        super().__init__("battery", name, **kwargs)
        self.properties.setdefault("percent", 0)
        self.properties.setdefault("is_charging", False)
        self.properties.setdefault("power_plugged", False)
        self.properties.setdefault("time_left_seconds", None)
        self.properties.setdefault("design_capacity_mwh", 0)
        self.properties.setdefault("full_charge_capacity_mwh", 0)
