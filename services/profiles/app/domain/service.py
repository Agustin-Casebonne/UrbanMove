"""Lógica de negocio de profiles. Solo usa domain/model.py y ports/ports.py.

Ejemplo: services/inventory/app/domain/service.py
"""


from ..ports.ports import ProfileRepository

from ..domain.model import Profile, ProfileNotFound

from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

class ProfileService:
    def __init__(self, profile_repository: ProfileRepository):
        self.profile_repository = profile_repository

    def check_health(self):
        self.profile_repository.ping()

    def get_profile(self, user_id):
        profile = self.profile_repository.get_profile(user_id)
        if profile is None:
            raise ProfileNotFound(user_id)
        return profile

    def create_profile(self, user_id, name, email):

        existing = self.profile_repository.get_profile(user_id)
        if existing:
            return existing
    
        profile = Profile(
            user_id=user_id,
            name=name,
            email=email,
            active=True,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.profile_repository.save(profile)
        return profile

    def update_profile(self, user_id, name, phone_number, preferred_vehicle_type):
        profile = self.get_profile(user_id)
        profile.name=name
        profile.phone_number=phone_number
        profile.preferred_vehicle_type=preferred_vehicle_type
        updated_at=now_iso()
        self.profile_repository.update(profile)

        return profile

    def deactivate_profile(self, user_id):
        profile = self.get_profile(user_id)
        profile.active=False
        profile.updated_at=now_iso()

        self.profile_repository.update(profile)

        return profile

    