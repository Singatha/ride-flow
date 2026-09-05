import uuid
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DriverMissingRequirements,
    DriverNotVerified,
    DriverProfileAlreadyExists,
    DriverProfileNotFound,
    DriverStateConflict,
    VehicleAlreadyExists,
    VehicleNotFound,
)
from app.domains.drivers.models import (
    DriverProfile,
    DriverStatus,
    DriverVerificationStatus,
    Vehicle,
)
from app.domains.drivers.repository import (
    DriverLocationRepository,
    DriverRepository,
    VehicleRepository,
)
from app.domains.drivers.schemas import (
    DriverLocationResponse,
    DriverLocationUpdate,
    DriverProfileCreate,
    DriverProfileUpdate,
    NearbyDriver,
    VehicleCreate,
    VehicleUpdate,
)
from app.domains.users.models import User


class DriverService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.drivers = DriverRepository(session)
        self.vehicles = VehicleRepository(session)
        self.locations = DriverLocationRepository(session)

    async def create_profile(self, user: User, data: DriverProfileCreate) -> DriverProfile:
        try:
            if await self.drivers.get_by_user_id(user.id) is not None:
                raise DriverProfileAlreadyExists("Driver profile already exists")
            profile = DriverProfile(
                user_id=user.id,
                license_number=data.license_number,
                license_expiry=data.license_expiry,
            )
            self.drivers.add(profile)
            await self.session.flush()
            await self.session.refresh(profile)
            await self.session.commit()
            return profile
        except IntegrityError as exc:
            await self.session.rollback()
            raise DriverProfileAlreadyExists(
                "Driver profile or license number already exists"
            ) from exc
        except Exception:
            await self.session.rollback()
            raise

    async def get_profile(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self.drivers.get_by_user_id(user_id)
        if profile is None:
            raise DriverProfileNotFound("Driver profile does not exist")
        return profile

    async def update_profile(self, user_id: uuid.UUID, data: DriverProfileUpdate) -> DriverProfile:
        profile = await self._locked_profile(user_id)
        if profile.status in {DriverStatus.RESERVED, DriverStatus.ON_TRIP}:
            raise DriverStateConflict("Driver credentials cannot change during an active ride")
        changes = data.model_dump(exclude_unset=True)
        try:
            for field, value in changes.items():
                setattr(profile, field, value)
            if changes:
                profile.verification_status = DriverVerificationStatus.PENDING
                profile.status = DriverStatus.OFFLINE
            await self._save_and_refresh(profile)
            return profile
        except IntegrityError as exc:
            await self.session.rollback()
            raise DriverProfileAlreadyExists("Driver license number already exists") from exc

    async def set_verification(
        self, driver_id: uuid.UUID, verification: DriverVerificationStatus
    ) -> DriverProfile:
        profile = await self.drivers.get_by_id(driver_id, for_update=True)
        if profile is None:
            raise DriverProfileNotFound("Driver profile does not exist")
        profile.verification_status = verification
        if verification is not DriverVerificationStatus.APPROVED:
            if profile.status in {DriverStatus.RESERVED, DriverStatus.ON_TRIP}:
                raise DriverStateConflict("Active-trip driver verification cannot change")
            profile.status = DriverStatus.OFFLINE
        await self._save_and_refresh(profile)
        return profile

    async def go_online(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self._locked_profile(user_id)
        if profile.status is DriverStatus.AVAILABLE:
            return profile
        if profile.status is not DriverStatus.OFFLINE:
            raise DriverStateConflict(f"Driver cannot go online from {profile.status.value}")
        if profile.verification_status is not DriverVerificationStatus.APPROVED:
            raise DriverNotVerified("Driver profile must be approved before going online")
        if profile.license_expiry <= date.today():
            raise DriverNotVerified("Driver license has expired")
        missing: list[str] = []
        if await self.vehicles.get_active_for_driver(profile.id) is None:
            missing.append("active_vehicle")
        if not await self.locations.exists_for_driver(profile.id):
            missing.append("location")
        if missing:
            raise DriverMissingRequirements(
                "Driver must complete online requirements", {"missing": missing}
            )
        profile.status = DriverStatus.AVAILABLE
        await self._save_and_refresh(profile)
        return profile

    async def go_offline(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self._locked_profile(user_id)
        if profile.status in {DriverStatus.RESERVED, DriverStatus.ON_TRIP}:
            raise DriverStateConflict("Driver cannot go offline during an active ride")
        if profile.status is DriverStatus.OFFLINE:
            return profile
        profile.status = DriverStatus.OFFLINE
        await self._save_and_refresh(profile)
        return profile

    async def update_location(
        self, user_id: uuid.UUID, data: DriverLocationUpdate
    ) -> DriverLocationResponse:
        profile = await self.get_profile(user_id)
        recorded_at = data.recorded_at or datetime.now(UTC)
        try:
            await self.locations.upsert(profile.id, data, recorded_at)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return DriverLocationResponse(
            driver_id=profile.id,
            latitude=data.latitude,
            longitude=data.longitude,
            heading=data.heading,
            speed_kph=data.speed_kph,
            accuracy_m=data.accuracy_m,
            recorded_at=recorded_at,
        )

    async def find_available_nearby(
        self,
        latitude: float,
        longitude: float,
        *,
        radius_m: float = 5_000,
        limit: int = 20,
    ) -> list[NearbyDriver]:
        return await self.locations.find_available_nearby(
            latitude, longitude, radius_m=radius_m, limit=limit
        )

    async def _locked_profile(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self.drivers.get_by_user_id(user_id, for_update=True)
        if profile is None:
            raise DriverProfileNotFound("Driver profile does not exist")
        return profile

    async def _save_and_refresh(self, profile: DriverProfile) -> None:
        try:
            await self.session.flush()
            await self.session.refresh(profile)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise


class VehicleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.drivers = DriverRepository(session)
        self.vehicles = VehicleRepository(session)

    async def create(self, user_id: uuid.UUID, data: VehicleCreate) -> Vehicle:
        profile = await self._locked_offline_profile(user_id)
        try:
            if data.is_active:
                await self.vehicles.deactivate_for_driver(profile.id)
            vehicle = Vehicle(driver_id=profile.id, **data.model_dump())
            self.vehicles.add(vehicle)
            await self.session.flush()
            await self.session.refresh(vehicle)
            await self.session.commit()
            return vehicle
        except IntegrityError as exc:
            await self.session.rollback()
            raise VehicleAlreadyExists("Vehicle license plate already exists") from exc

    async def list_for_driver(self, user_id: uuid.UUID) -> list[Vehicle]:
        profile = await self._profile(user_id)
        return list(await self.vehicles.list_for_driver(profile.id))

    async def update(
        self, user_id: uuid.UUID, vehicle_id: uuid.UUID, data: VehicleUpdate
    ) -> Vehicle:
        profile = await self._locked_offline_profile(user_id)
        vehicle = await self.vehicles.get_for_driver(vehicle_id, profile.id)
        if vehicle is None:
            raise VehicleNotFound("Vehicle does not exist")
        changes = data.model_dump(exclude_unset=True)
        try:
            if changes.get("is_active") is True:
                await self.vehicles.deactivate_for_driver(profile.id)
            for field, value in changes.items():
                setattr(vehicle, field, value)
            await self.session.flush()
            await self.session.refresh(vehicle)
            await self.session.commit()
            return vehicle
        except IntegrityError as exc:
            await self.session.rollback()
            raise VehicleAlreadyExists("Vehicle license plate already exists") from exc

    async def _profile(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self.drivers.get_by_user_id(user_id)
        if profile is None:
            raise DriverProfileNotFound("Create a driver profile first")
        return profile

    async def _locked_offline_profile(self, user_id: uuid.UUID) -> DriverProfile:
        profile = await self.drivers.get_by_user_id(user_id, for_update=True)
        if profile is None:
            raise DriverProfileNotFound("Create a driver profile first")
        if profile.status is not DriverStatus.OFFLINE:
            raise DriverStateConflict("Vehicles can only change while the driver is offline")
        return profile
