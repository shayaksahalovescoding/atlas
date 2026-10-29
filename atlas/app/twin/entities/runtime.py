from atlas.app.twin.entities.base import Entity


class Process(Entity):
    def __init__(self, name="Process", **kwargs):
        super().__init__("process", name, **kwargs)
        self.properties.setdefault("pid", 0)
        self.properties.setdefault("ppid", 0)
        self.properties.setdefault("executable_path", "")
        self.properties.setdefault("command_line", "")
        self.properties.setdefault("username", "")
        self.properties.setdefault("start_time", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("cpu_percent", 0.0)
        self.properties.setdefault("memory_bytes", 0)
        self.properties.setdefault("memory_percent", 0.0)
        self.properties.setdefault("thread_count", 0)
        self.properties.setdefault("handle_count", 0)
        self.properties.setdefault("io_read_bytes", 0)
        self.properties.setdefault("io_write_bytes", 0)
        self.properties.setdefault("io_read_count", 0)
        self.properties.setdefault("io_write_count", 0)
        self.properties.setdefault("priority", "")
        self.properties.setdefault("application_id", None)
        self.properties.setdefault("is_system", False)
        self.properties.setdefault("window_title", "")
        self.properties.setdefault("open_files_count", 0)
        self.properties.setdefault("connection_count", 0)
        self.properties.setdefault("child_count", 0)


class Thread(Entity):
    def __init__(self, name="Thread", **kwargs):
        super().__init__("thread", name, **kwargs)
        self.properties.setdefault("thread_id", 0)
        self.properties.setdefault("process_id", 0)
        self.properties.setdefault("cpu_percent", 0.0)
        self.properties.setdefault("state", "")
        self.properties.setdefault("priority", 0)


class NetworkConnection(Entity):
    def __init__(self, name="Connection", **kwargs):
        super().__init__("network_connection", name, **kwargs)
        self.properties.setdefault("local_address", "")
        self.properties.setdefault("local_port", 0)
        self.properties.setdefault("remote_address", "")
        self.properties.setdefault("remote_port", 0)
        self.properties.setdefault("protocol", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("pid", 0)
        self.properties.setdefault("process_name", "")
        self.properties.setdefault("direction", "")
        self.properties.setdefault("family", "")


class ApplicationWindow(Entity):
    def __init__(self, name="Window", **kwargs):
        super().__init__("window", name, **kwargs)
        self.properties.setdefault("hwnd", 0)
        self.properties.setdefault("title", "")
        self.properties.setdefault("class_name", "")
        self.properties.setdefault("pid", 0)
        self.properties.setdefault("is_visible", True)
        self.properties.setdefault("is_minimized", False)
        self.properties.setdefault("rect", {})
