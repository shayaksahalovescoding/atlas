from atlas.app.twin.entities.base import Entity


class File(Entity):
    def __init__(self, name="File", **kwargs):
        super().__init__("file", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("extension", "")
        self.properties.setdefault("size_bytes", 0)
        self.properties.setdefault("created_time", "")
        self.properties.setdefault("modified_time", "")
        self.properties.setdefault("accessed_time", "")
        self.properties.setdefault("is_hidden", False)
        self.properties.setdefault("is_system", False)
        self.properties.setdefault("owner", "")
        self.properties.setdefault("mime_type", "")


class Directory(Entity):
    def __init__(self, name="Directory", **kwargs):
        super().__init__("directory", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("file_count", 0)
        self.properties.setdefault("total_size_bytes", 0)
        self.properties.setdefault("created_time", "")
        self.properties.setdefault("modified_time", "")
        self.properties.setdefault("is_watched", False)
        self.properties.setdefault("directory_type", "")


class Project(Entity):
    def __init__(self, name="Project", **kwargs):
        super().__init__("project", name, **kwargs)
        self.properties.setdefault("path", "")
        self.properties.setdefault("project_type", "")
        self.properties.setdefault("language", "")
        self.properties.setdefault("framework", "")
        self.properties.setdefault("vcs", "")
        self.properties.setdefault("last_activity", "")
        self.properties.setdefault("file_count", 0)
        self.properties.setdefault("total_size_bytes", 0)
        self.properties.setdefault("associated_applications", [])
