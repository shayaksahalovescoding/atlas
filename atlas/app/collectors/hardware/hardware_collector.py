import platform
import socket
import os
import asyncio
from datetime import datetime

import psutil

from atlas.app.collectors.base import BaseCollector
from atlas.app.collectors.windows.wmi_provider import WMIProvider
from atlas.app.core.events.event_types import EventType
from atlas.app.twin.entities.hardware import (
    Machine, CPU, GPU, MemoryModule, StorageDevice, Partition,
    NetworkAdapter, Display, Motherboard, Battery, Driver
)
from atlas.app.twin.relationships.relationship import Relationship, RelationshipType, ConfidenceLevel


class HardwareCollector(BaseCollector):
    def __init__(self, event_bus, graph):
        super().__init__("hardware_collector", event_bus, graph)
        self._wmi = WMIProvider()
        self._machine_id = None
        self._initialized = False

    async def initialize(self):
        await super().initialize()
        await self.collect()
        self._initialized = True

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        self._collect_machine()
        self._collect_cpu()
        self._collect_gpu()
        self._collect_memory()
        self._collect_storage()
        self._collect_partitions()
        self._collect_network_adapters()
        self._collect_battery()
        self._collect_motherboard()

    def _collect_machine(self):
        existing = self.graph.get_entities_by_type("machine")
        if existing:
            machine = existing[0]
            self._machine_id = machine.id
        else:
            machine = Machine(name=platform.node(), source=self.name)
            self._machine_id = machine.id
            self.graph.add_entity(machine)

        boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        uptime = int((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds())

        os_info = self._wmi.get_os_info()
        self.graph.update_entity(machine.id,
            hostname=platform.node(),
            os_version=os_info.get("version", platform.version()),
            os_build=os_info.get("build", ""),
            architecture=platform.architecture()[0],
            domain=os.environ.get("USERDOMAIN", ""),
            username=os.environ.get("USERNAME", ""),
            boot_time=boot_time,
            uptime_seconds=uptime,
        )

    def _collect_cpu(self):
        wmi_cpus = self._wmi.get_cpu_info()
        freq = psutil.cpu_freq()

        for i, wmi_cpu in enumerate(wmi_cpus):
            cpu_name = wmi_cpu.get("name", f"CPU {i}")
            existing = self.graph.find_entity("cpu", brand=cpu_name)
            if existing:
                cpu = existing[0]
            else:
                cpu = CPU(name=cpu_name, source=self.name)
                self.graph.add_entity(cpu)
                if self._machine_id:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, cpu.id, self._machine_id,
                        "cpu", "machine", evidence_source=self.name
                    )

            self.graph.update_entity(cpu.id,
                brand=cpu_name,
                vendor=wmi_cpu.get("vendor", ""),
                cores_physical=wmi_cpu.get("cores_physical", psutil.cpu_count(logical=False)),
                cores_logical=wmi_cpu.get("cores_logical", psutil.cpu_count()),
                base_frequency_mhz=freq.current if freq else 0,
                max_frequency_mhz=wmi_cpu.get("max_frequency_mhz", freq.max if freq else 0),
                current_frequency_mhz=freq.current if freq else 0,
                usage_percent=psutil.cpu_percent(interval=0),
                cache_l2_kb=wmi_cpu.get("l2_cache_kb", 0),
                cache_l3_kb=wmi_cpu.get("l3_cache_kb", 0),
            )

    def _collect_gpu(self):
        wmi_gpus = self._wmi.get_gpu_info()
        for i, wmi_gpu in enumerate(wmi_gpus):
            gpu_name = wmi_gpu.get("name", f"GPU {i}")
            existing = self.graph.find_entity("gpu", name=gpu_name)
            if existing:
                gpu_entity = existing[0]
            else:
                gpu_entity = GPU(name=gpu_name, source=self.name)
                self.graph.add_entity(gpu_entity)
                if self._machine_id:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, gpu_entity.id, self._machine_id,
                        "gpu", "machine", evidence_source=self.name
                    )

            mem_bytes = wmi_gpu.get("memory_bytes", 0)
            self.graph.update_entity(gpu_entity.id,
                vendor=wmi_gpu.get("vendor", ""),
                driver_version=wmi_gpu.get("driver_version", ""),
                memory_total_mb=mem_bytes // (1024 * 1024) if mem_bytes else 0,
                adapter_type=wmi_gpu.get("adapter_type", ""),
            )

    def _collect_memory(self):
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        existing = self.graph.get_entities_by_type("memory")
        if existing:
            mem = existing[0]
        else:
            mem = MemoryModule(name="System Memory", source=self.name)
            self.graph.add_entity(mem)
            if self._machine_id:
                self.graph.find_or_create_relationship(
                    RelationshipType.PART_OF, mem.id, self._machine_id,
                    "memory", "machine", evidence_source=self.name
                )

        wmi_mem = self._wmi.get_memory_info()
        speed = wmi_mem[0].get("speed_mhz", 0) if wmi_mem else 0
        slots_used = len(wmi_mem)

        self.graph.update_entity(mem.id,
            total_bytes=vm.total,
            available_bytes=vm.available,
            used_bytes=vm.used,
            usage_percent=vm.percent,
            swap_total_bytes=swap.total,
            swap_used_bytes=swap.used,
            swap_percent=swap.percent,
            speed_mhz=speed,
            slots_used=slots_used,
        )

    def _collect_storage(self):
        wmi_disks = self._wmi.get_disk_info()
        for disk_info in wmi_disks:
            disk_name = disk_info.get("model", "Unknown Disk")
            existing = self.graph.find_entity("storage_device", model=disk_name)
            if existing:
                disk = existing[0]
            else:
                disk = StorageDevice(name=disk_name, source=self.name)
                self.graph.add_entity(disk)
                if self._machine_id:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, disk.id, self._machine_id,
                        "storage_device", "machine", evidence_source=self.name
                    )

            media = disk_info.get("media_type", "").lower()
            device_type = "SSD" if "solid" in media or "ssd" in media else (
                "HDD" if "hard" in media or "hdd" in media else "Unknown"
            )

            self.graph.update_entity(disk.id,
                model=disk_name,
                serial=disk_info.get("serial", ""),
                size_bytes=disk_info.get("size_bytes", 0),
                interface=disk_info.get("interface", ""),
                firmware=disk_info.get("firmware", ""),
                device_type=device_type,
            )

    def _collect_partitions(self):
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue

            part_name = f"{part.mountpoint} ({part.fstype})"
            existing = self.graph.find_entity("partition", mount_point=part.mountpoint)
            if existing:
                partition = existing[0]
            else:
                partition = Partition(name=part_name, source=self.name)
                self.graph.add_entity(partition)
                if self._machine_id:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, partition.id, self._machine_id,
                        "partition", "machine", evidence_source=self.name
                    )

            self.graph.update_entity(partition.id,
                mount_point=part.mountpoint,
                filesystem=part.fstype,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                usage_percent=usage.percent,
            )

    def _collect_network_adapters(self):
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        io = psutil.net_io_counters(pernic=True)

        for name, stat in stats.items():
            if name.startswith("Loopback") or name == "lo":
                continue
            existing = self.graph.find_entity("network_adapter", name=name)
            if existing:
                adapter = existing[0]
            else:
                adapter = NetworkAdapter(name=name, source=self.name)
                self.graph.add_entity(adapter)
                if self._machine_id:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, adapter.id, self._machine_id,
                        "network_adapter", "machine", evidence_source=self.name
                    )

            ipv4 = []
            ipv6 = []
            mac = ""
            for addr in addrs.get(name, []):
                if addr.family.name == "AF_INET":
                    ipv4.append(addr.address)
                elif addr.family.name == "AF_INET6":
                    ipv6.append(addr.address)
                elif addr.family.name == "AF_LINK" or addr.family.value == -1 or addr.family.value == 17:
                    mac = addr.address

            nic_io = io.get(name)
            self.graph.update_entity(adapter.id,
                is_up=stat.isup,
                speed_mbps=stat.speed,
                ipv4_addresses=ipv4,
                ipv6_addresses=ipv6,
                mac_address=mac,
                bytes_sent=nic_io.bytes_sent if nic_io else 0,
                bytes_recv=nic_io.bytes_recv if nic_io else 0,
            )

    def _collect_battery(self):
        battery = psutil.sensors_battery()
        if battery is None:
            return
        existing = self.graph.get_entities_by_type("battery")
        if existing:
            bat = existing[0]
        else:
            bat = Battery(name="Battery", source=self.name)
            self.graph.add_entity(bat)
            if self._machine_id:
                self.graph.find_or_create_relationship(
                    RelationshipType.PART_OF, bat.id, self._machine_id,
                    "battery", "machine", evidence_source=self.name
                )
        self.graph.update_entity(bat.id,
            percent=battery.percent,
            is_charging=battery.power_plugged if battery.power_plugged is not None else False,
            power_plugged=battery.power_plugged if battery.power_plugged is not None else False,
            time_left_seconds=battery.secsleft if battery.secsleft > 0 else None,
        )

    def _collect_motherboard(self):
        mb_info = self._wmi.get_motherboard_info()
        if not mb_info:
            return
        existing = self.graph.get_entities_by_type("motherboard")
        if existing:
            mb = existing[0]
        else:
            mb = Motherboard(name=mb_info.get("product", "Motherboard"), source=self.name)
            self.graph.add_entity(mb)
            if self._machine_id:
                self.graph.find_or_create_relationship(
                    RelationshipType.PART_OF, mb.id, self._machine_id,
                    "motherboard", "machine", evidence_source=self.name
                )
        self.graph.update_entity(mb.id, **mb_info)
