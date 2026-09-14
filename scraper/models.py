from dataclasses import dataclass, field


@dataclass
class Lead:
    name: str = ""
    category: str = ""
    location: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    description: str = ""
    source_url: str = ""
    source_name: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "location": self.location,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "description": self.description,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "extra": self.extra,
        }
