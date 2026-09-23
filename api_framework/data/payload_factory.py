"""Factories for valid, unique GoRest request payloads."""
from faker import Faker


class UserPayloadFactory:
    """Creates valid user data with unique addresses for parallel test safety."""

    _faker = Faker()

    @classmethod
    def create(cls) -> dict[str, str]:
        return {
            "name": cls._faker.name(),
            "email": cls._faker.unique.email(),
            "gender": cls._faker.random_element(elements=("male", "female")),
            "status": cls._faker.random_element(elements=("active", "inactive")),
        }

    @classmethod
    def create_update_payload(cls) -> dict[str, str]:
        return {
            "name": f"Updated {cls._faker.first_name()}",
            "status": "active",
        }
