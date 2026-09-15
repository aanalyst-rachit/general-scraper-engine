from dataclasses import dataclass, field


@dataclass
class Lead:
    # Identity
    name: str = ""
    profession: str = ""
    company_name: str = ""
    category: str = ""
    subcategory: str = ""

    # Professional / business information
    designation: str = ""
    specialization: str = ""
    services: str = ""
    description: str = ""

    # Contact information
    phone: str = ""
    alternate_phone: str = ""
    email: str = ""
    alternate_email: str = ""
    website: str = ""

    # Address information
    address: str = ""
    location: str = ""
    locality: str = ""
    city: str = ""
    district: str = ""
    state: str = ""
    country: str = ""
    pincode: str = ""

    # Public profiles
    social_profiles: dict[str, str] = field(default_factory=dict)

    # Discovery / source information
    source_url: str = ""
    source_name: str = ""
    source_id: str = ""
    search_context: str = ""

    # Flexible / future-proof data
    extra: dict[str, str] = field(default_factory=dict)
    raw_data: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "profession": self.profession,
            "company_name": self.company_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "designation": self.designation,
            "specialization": self.specialization,
            "services": self.services,
            "description": self.description,
            "phone": self.phone,
            "alternate_phone": self.alternate_phone,
            "email": self.email,
            "alternate_email": self.alternate_email,
            "website": self.website,
            "address": self.address,
            "location": self.location,
            "locality": self.locality,
            "city": self.city,
            "district": self.district,
            "state": self.state,
            "country": self.country,
            "pincode": self.pincode,
            "social_profiles": dict(self.social_profiles),
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_id": self.source_id,
            "search_context": self.search_context,
            "extra": dict(self.extra),
            "raw_data": dict(self.raw_data),
        }
