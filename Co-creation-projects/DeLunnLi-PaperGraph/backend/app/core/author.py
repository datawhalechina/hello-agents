
from dataclasses import dataclass
from typing import Any

@dataclass
class Author:
    name: str
    affiliation: str | None = None
    email: str | None = None
    orcid: str | None = None

    db_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "affiliation": self.affiliation,
            "email": self.email,
            "orcid": self.orcid,
        }
        if self.db_id is not None:
            d["db_id"] = int(self.db_id)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Author":
        raw_id = data.get("db_id")
        db_id: int | None = None
        if raw_id is not None:
            try:
                db_id = int(raw_id)
            except Exception:
                db_id = None
        return cls(
            name=data.get("name", ""),
            affiliation=data.get("affiliation"),
            email=data.get("email"),
            orcid=data.get("orcid"),
            db_id=db_id,
        )
