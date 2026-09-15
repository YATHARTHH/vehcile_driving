#!/usr/bin/env python3
"""
FleetTrack Reference Data Seeder
Seeds development and integration test reference entities (tenants, fleets, vehicles, users)
without polluting schema migrations with application mock data.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from backend.database import AsyncSessionLocal, engine
from backend.models.tenant import Fleet, Tenant, Vehicle
from backend.models.user import User
from backend.utils.auth import get_password_hash


async def seed_data() -> None:
    print("[Seeder] Starting reference data seeding...")
    async with AsyncSessionLocal() as session:
        # 1. Tenants
        tenants_data = [
            {"id": "tenant_fedex_in", "name": "FedEx Express India", "tier": "enterprise"},
            {"id": "tenant_delhivery", "name": "Delhivery Freight Logistics", "tier": "enterprise"},
        ]
        for t_info in tenants_data:
            existing = await session.get(Tenant, t_info["id"])
            if not existing:
                session.add(Tenant(**t_info))
                print(f"  + Added tenant: {t_info['id']}")

        await session.flush()

        # 2. Fleets
        fleets_data = [
            {"id": "fleet_pune_north", "tenant_id": "tenant_fedex_in", "name": "Pune North Delivery Hub", "region": "Maharashtra"},
            {"id": "fleet_mumbai_metro", "tenant_id": "tenant_fedex_in", "name": "Mumbai Metro Express", "region": "Maharashtra"},
        ]
        for f_info in fleets_data:
            existing = await session.get(Fleet, f_info["id"])
            if not existing:
                session.add(Fleet(**f_info))
                print(f"  + Added fleet: {f_info['id']}")

        await session.flush()

        # 3. Vehicles
        vehicles_data = [
            {
                "id": "veh_01",
                "tenant_id": "tenant_fedex_in",
                "fleet_id": "fleet_pune_north",
                "vin": "VININD0001FEDEX01",
                "vehicle_class": "light_commercial_van",
                "powertrain": "ice_diesel",
            },
            {
                "id": "veh_02",
                "tenant_id": "tenant_fedex_in",
                "fleet_id": "fleet_pune_north",
                "vin": "VININD0002FEDEX02",
                "vehicle_class": "passenger_car",
                "powertrain": "ice_petrol",
            },
            {
                "id": "veh_03",
                "tenant_id": "tenant_fedex_in",
                "fleet_id": "fleet_mumbai_metro",
                "vin": "VININD0003FEDEX03",
                "vehicle_class": "heavy_duty_truck",
                "powertrain": "ice_diesel",
            },
        ]
        for v_info in vehicles_data:
            existing = await session.get(Vehicle, v_info["id"])
            if not existing:
                session.add(Vehicle(**v_info))
                print(f"  + Added vehicle: {v_info['id']}")

        await session.flush()

        # 4. Users
        users_data = [
            {
                "username": "admin",
                "password": get_password_hash("Admin@1234"),
                "vehicle_number": "MH12AB1001",
                "email": "admin@fleettrack.io",
            },
            {
                "username": "driver1",
                "password": get_password_hash("Driver@1234"),
                "vehicle_number": "MH12AB1002",
                "email": "driver1@fleettrack.io",
            },
        ]
        for u_info in users_data:
            stmt = select(User).where(User.username == u_info["username"])
            existing = (await session.execute(stmt)).scalars().first()
            if not existing:
                session.add(User(**u_info))
                print(f"  + Added user: {u_info['username']}")

        await session.commit()
        print("[Seeder] Reference data seeded successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
