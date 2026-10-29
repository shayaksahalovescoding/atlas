import logging
import threading
import pythoncom

logger = logging.getLogger("atlas.collectors.wmi")

_wmi_available = False
try:
    import wmi as wmi_module
    _wmi_available = True
except ImportError:
    wmi_module = None
    logger.warning("WMI module not available, falling back to limited hardware detection")


class WMIProvider:
    def __init__(self):
        self._local = threading.local()

    def _get_wmi(self):
        if not _wmi_available:
            return None
        if not hasattr(self._local, "wmi_conn") or self._local.wmi_conn is None:
            try:
                pythoncom.CoInitialize()
                self._local.wmi_conn = wmi_module.WMI()
            except Exception as e:
                logger.error(f"Failed to connect to WMI: {e}")
                self._local.wmi_conn = None
        return self._local.wmi_conn

    def query(self, wql):
        conn = self._get_wmi()
        if conn is None:
            return []
        try:
            return conn.query(wql)
        except Exception as e:
            logger.error(f"WMI query failed: {wql[:80]}... - {e}")
            return []

    def get_class(self, class_name):
        conn = self._get_wmi()
        if conn is None:
            return []
        try:
            return getattr(conn, class_name)()
        except Exception as e:
            logger.error(f"WMI class query failed: {class_name} - {e}")
            return []

    def get_cpu_info(self):
        results = []
        for cpu in self.get_class("Win32_Processor"):
            results.append({
                "name": getattr(cpu, "Name", "").strip(),
                "vendor": getattr(cpu, "Manufacturer", ""),
                "cores_physical": getattr(cpu, "NumberOfCores", 0),
                "cores_logical": getattr(cpu, "NumberOfLogicalProcessors", 0),
                "max_frequency_mhz": getattr(cpu, "MaxClockSpeed", 0),
                "current_frequency_mhz": getattr(cpu, "CurrentClockSpeed", 0),
                "architecture": getattr(cpu, "Architecture", 0),
                "l2_cache_kb": getattr(cpu, "L2CacheSize", 0),
                "l3_cache_kb": getattr(cpu, "L3CacheSize", 0),
                "status": getattr(cpu, "Status", ""),
            })
        return results

    def get_gpu_info(self):
        results = []
        for gpu in self.get_class("Win32_VideoController"):
            ram = getattr(gpu, "AdapterRAM", 0)
            results.append({
                "name": getattr(gpu, "Name", "").strip(),
                "vendor": getattr(gpu, "AdapterCompatibility", ""),
                "driver_version": getattr(gpu, "DriverVersion", ""),
                "memory_bytes": ram if ram and ram > 0 else 0,
                "adapter_type": getattr(gpu, "VideoProcessor", ""),
                "status": getattr(gpu, "Status", ""),
                "resolution": f"{getattr(gpu, 'CurrentHorizontalResolution', 0)}x{getattr(gpu, 'CurrentVerticalResolution', 0)}",
                "refresh_rate": getattr(gpu, "CurrentRefreshRate", 0),
            })
        return results

    def get_memory_info(self):
        results = []
        for mem in self.get_class("Win32_PhysicalMemory"):
            results.append({
                "capacity_bytes": int(getattr(mem, "Capacity", 0)),
                "speed_mhz": getattr(mem, "Speed", 0),
                "manufacturer": getattr(mem, "Manufacturer", "").strip(),
                "part_number": getattr(mem, "PartNumber", "").strip(),
                "memory_type": getattr(mem, "MemoryType", 0),
                "form_factor": getattr(mem, "FormFactor", 0),
                "bank_label": getattr(mem, "BankLabel", ""),
                "device_locator": getattr(mem, "DeviceLocator", ""),
            })
        return results

    def get_disk_info(self):
        results = []
        for disk in self.get_class("Win32_DiskDrive"):
            results.append({
                "model": getattr(disk, "Model", "").strip(),
                "serial": getattr(disk, "SerialNumber", "").strip(),
                "size_bytes": int(getattr(disk, "Size", 0)),
                "interface": getattr(disk, "InterfaceType", ""),
                "media_type": getattr(disk, "MediaType", ""),
                "firmware": getattr(disk, "FirmwareRevision", "").strip(),
                "partitions": getattr(disk, "Partitions", 0),
                "status": getattr(disk, "Status", ""),
                "device_id": getattr(disk, "DeviceID", ""),
            })
        return results

    def get_motherboard_info(self):
        boards = self.get_class("Win32_BaseBoard")
        if not boards:
            return {}
        board = boards[0]
        bios_list = self.get_class("Win32_BIOS")
        bios = bios_list[0] if bios_list else None
        return {
            "manufacturer": getattr(board, "Manufacturer", ""),
            "product": getattr(board, "Product", ""),
            "serial": getattr(board, "SerialNumber", ""),
            "bios_version": getattr(bios, "SMBIOSBIOSVersion", "") if bios else "",
            "bios_vendor": getattr(bios, "Manufacturer", "") if bios else "",
            "bios_date": getattr(bios, "ReleaseDate", "") if bios else "",
        }

    def get_network_adapters(self):
        results = []
        for adapter in self.get_class("Win32_NetworkAdapterConfiguration"):
            if not getattr(adapter, "IPEnabled", False):
                continue
            results.append({
                "description": getattr(adapter, "Description", ""),
                "mac_address": getattr(adapter, "MACAddress", ""),
                "ipv4": getattr(adapter, "IPAddress", []),
                "dns_servers": getattr(adapter, "DNSServerSearchOrder", []),
                "gateway": (getattr(adapter, "DefaultIPGateway", []) or [None])[0],
                "dhcp_enabled": getattr(adapter, "DHCPEnabled", False),
                "index": getattr(adapter, "Index", 0),
            })
        return results

    def get_os_info(self):
        os_list = self.get_class("Win32_OperatingSystem")
        if not os_list:
            return {}
        os = os_list[0]
        return {
            "name": getattr(os, "Caption", ""),
            "version": getattr(os, "Version", ""),
            "build": getattr(os, "BuildNumber", ""),
            "architecture": getattr(os, "OSArchitecture", ""),
            "install_date": getattr(os, "InstallDate", ""),
            "registered_owner": getattr(os, "RegisteredUser", ""),
            "product_id": getattr(os, "SerialNumber", ""),
            "last_boot": getattr(os, "LastBootUpTime", ""),
        }

    def get_services(self):
        results = []
        for svc in self.get_class("Win32_Service"):
            results.append({
                "name": getattr(svc, "Name", ""),
                "display_name": getattr(svc, "DisplayName", ""),
                "status": getattr(svc, "State", ""),
                "startup_type": getattr(svc, "StartMode", ""),
                "path": getattr(svc, "PathName", ""),
                "pid": getattr(svc, "ProcessId", 0),
                "description": getattr(svc, "Description", ""),
                "account": getattr(svc, "StartName", ""),
                "service_type": getattr(svc, "ServiceType", ""),
            })
        return results

    def get_installed_updates(self):
        results = []
        for update in self.get_class("Win32_QuickFixEngineering"):
            results.append({
                "kb_id": getattr(update, "HotFixID", ""),
                "description": getattr(update, "Description", ""),
                "install_date": getattr(update, "InstalledOn", ""),
            })
        return results

    def is_available(self):
        return _wmi_available and self._get_wmi() is not None
