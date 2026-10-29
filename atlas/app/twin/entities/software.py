from atlas.app.twin.entities.base import Entity


class OperatingSystem(Entity):
    def __init__(self, name="Windows", **kwargs):
        super().__init__("operating_system", name, **kwargs)
        self.properties.setdefault("version", "")
        self.properties.setdefault("build", "")
        self.properties.setdefault("edition", "")
        self.properties.setdefault("architecture", "")
        self.properties.setdefault("install_date", "")
        self.properties.setdefault("last_update", "")
        self.properties.setdefault("registered_owner", "")
        self.properties.setdefault("product_id", "")


class Application(Entity):
    def __init__(self, name="Application", **kwargs):
        super().__init__("application", name, **kwargs)
        self.properties.setdefault("display_name", "")
        self.properties.setdefault("version", "")
        self.properties.setdefault("publisher", "")
        self.properties.setdefault("install_date", "")
        self.properties.setdefault("install_location", "")
        self.properties.setdefault("uninstall_string", "")
        self.properties.setdefault("executable_path", "")
        self.properties.setdefault("size_bytes", 0)
        self.properties.setdefault("is_system", False)
        self.properties.setdefault("registry_key", "")
        self.properties.setdefault("last_used", "")
        self.properties.setdefault("crash_count", 0)
        self.properties.setdefault("process_count", 0)
        self.properties.setdefault("cpu_usage", 0.0)
        self.properties.setdefault("memory_usage", 0)


class Executable(Entity):
    def __init__(self, name="Executable", **kwargs):
        super().__init__("executable", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("version", "")
        self.properties.setdefault("company", "")
        self.properties.setdefault("description", "")
        self.properties.setdefault("size_bytes", 0)
        self.properties.setdefault("hash_sha256", "")
        self.properties.setdefault("signed", None)
        self.properties.setdefault("signer", "")


class Library(Entity):
    def __init__(self, name="Library", **kwargs):
        super().__init__("library", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("version", "")
        self.properties.setdefault("type", "")
        self.properties.setdefault("loaded_by", [])


class Service(Entity):
    def __init__(self, name="Service", **kwargs):
        super().__init__("service", name, **kwargs)
        self.properties.setdefault("service_name", "")
        self.properties.setdefault("display_name", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("startup_type", "")
        self.properties.setdefault("executable_path", "")
        self.properties.setdefault("pid", None)
        self.properties.setdefault("description", "")
        self.properties.setdefault("account", "")
        self.properties.setdefault("dependencies", [])
        self.properties.setdefault("dependents", [])
        self.properties.setdefault("service_type", "")
        self.properties.setdefault("last_state_change", "")
        self.properties.setdefault("failure_count", 0)


class InstalledUpdate(Entity):
    def __init__(self, name="Update", **kwargs):
        super().__init__("installed_update", name, **kwargs)
        self.properties.setdefault("kb_id", "")
        self.properties.setdefault("description", "")
        self.properties.setdefault("install_date", "")
        self.properties.setdefault("type", "")
        self.properties.setdefault("support_url", "")


class StartupEntry(Entity):
    def __init__(self, name="Startup Entry", **kwargs):
        super().__init__("startup_entry", name, **kwargs)
        self.properties.setdefault("command", "")
        self.properties.setdefault("location", "")
        self.properties.setdefault("enabled", True)
        self.properties.setdefault("user", "")
        self.properties.setdefault("type", "")


class ScheduledTask(Entity):
    def __init__(self, name="Scheduled Task", **kwargs):
        super().__init__("scheduled_task", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("status", "")
        self.properties.setdefault("last_run", "")
        self.properties.setdefault("next_run", "")
        self.properties.setdefault("triggers", [])
        self.properties.setdefault("actions", [])
        self.properties.setdefault("author", "")
