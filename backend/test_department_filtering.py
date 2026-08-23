"""
Unit and API integration test suite for Department-Based Grievance Filtering in SPIN Staff Portal.
"""

from __future__ import annotations

import os
import sys
import asyncio
import httpx

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from spin_agents.api import app
from spin_agents.auth import create_access_token
from spin_agents.departments import (
    normalize_department,
    get_department_for_category,
    get_categories_for_department,
    matches_department,
)


def test_canonical_department_mappings():
    print("Testing canonical department normalization and category mappings...")
    assert normalize_department("Municipality") == "Municipality"
    assert normalize_department("Water Supply & Sanitation Board") == "Water Supply"
    assert normalize_department("State Power Distribution Corp") == "Electricity"
    assert normalize_department("Municipal Infrastructure & Public Works") == "Municipality"

    assert get_department_for_category("Water Supply") == "Water Supply"
    assert get_department_for_category("Roads & Potholes") == "Municipality"
    assert get_department_for_category("Electricity") == "Electricity"

    assert "Roads & Potholes" in get_categories_for_department("Municipality")
    assert "Water Supply" in get_categories_for_department("Water Supply")
    assert "Electricity" in get_categories_for_department("Electricity")

    assert matches_department("Municipality", "Roads & Potholes", None, "Municipality") is True
    assert matches_department("Water Supply", "Water Supply", None, "Municipality") is False
    assert matches_department("Water Supply", "Water Supply", None, "Water Supply") is True
    print("✓ Canonical department taxonomy tests passed!")


async def test_async_api_flow():
    print("\nTesting async staff API endpoints and department authorization...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test staff login with Municipality
        res_muni = await client.post(
            "/api/auth/staff-login",
            json={
                "identifier": "officer.muni@pune.gov.in",
                "password": "Password123",
                "department": "Municipality",
            },
        )
        assert res_muni.status_code == 200, res_muni.text
        data_muni = res_muni.json()
        assert data_muni["status"] == "success"
        assert data_muni["user"]["department"] == "Municipality"
        assert "access_token" in data_muni
        print("✓ Staff login with Municipality department passed!")

        # 2. Test staff login with Water Supply
        res_water = await client.post(
            "/api/auth/staff-login",
            json={
                "identifier": "officer.water@pune.gov.in",
                "password": "Password123",
                "department": "Water Supply",
            },
        )
        assert res_water.status_code == 200, res_water.text
        data_water = res_water.json()
        assert data_water["user"]["department"] == "Water Supply"
        print("✓ Staff login with Water Supply department passed!")

        # 3. Test /api/staff/grievances for Municipality staff
        muni_token = data_muni["access_token"]
        res_muni_grievances = await client.get(
            "/api/staff/grievances",
            headers={"Authorization": f"Bearer {muni_token}"},
        )
        assert res_muni_grievances.status_code == 200, res_muni_grievances.text
        muni_g_data = res_muni_grievances.json()
        assert muni_g_data["status"] == "success"
        assert muni_g_data["department"] == "Municipality"
        for g in muni_g_data["grievances"]:
            assert g["department"] == "Municipality", f"Leaked non-Municipality grievance: {g}"
        print(f"✓ Municipality staff received {muni_g_data['count']} Municipality-restricted grievances!")

        # 4. Test /api/staff/grievances for Water Supply staff
        water_token = data_water["access_token"]
        res_water_grievances = await client.get(
            "/api/staff/grievances",
            headers={"Authorization": f"Bearer {water_token}"},
        )
        assert res_water_grievances.status_code == 200, res_water_grievances.text
        water_g_data = res_water_grievances.json()
        assert water_g_data["status"] == "success"
        assert water_g_data["department"] == "Water Supply"
        for g in water_g_data["grievances"]:
            assert g["department"] == "Water Supply", f"Leaked non-Water Supply grievance: {g}"
        print(f"✓ Water Supply staff received {water_g_data['count']} Water Supply-restricted grievances!")

        # 5. Test Admin role cross-department access
        admin_token = create_access_token({"sub": "admin-1", "role": "admin", "dept": None})
        res_admin = await client.get(
            "/api/staff/grievances",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_admin.status_code == 200, res_admin.text
        admin_g_data = res_admin.json()
        assert "Admin" in admin_g_data["department"]
        print(f"✓ Admin role successfully accessed cross-department queue ({admin_g_data['count']} total grievances)!")

        # 6. Test Unassigned staff account edge case
        unassigned_token = create_access_token({"sub": "unassigned-1", "role": "staff", "dept": None})
        res_unassigned = await client.get(
            "/api/staff/grievances",
            headers={"Authorization": f"Bearer {unassigned_token}"},
        )
        assert res_unassigned.status_code == 200
        unassigned_data = res_unassigned.json()
        assert unassigned_data["status"] == "error"
        assert "Department not assigned" in unassigned_data["message"]
        print("✓ Unassigned staff account properly blocked with unassigned department message!")


if __name__ == "__main__":
    print("=" * 70)
    print("       SPIN DEPARTMENT FILTERING INTEGRATION VERIFICATION")
    print("=" * 70)
    test_canonical_department_mappings()
    asyncio.run(test_async_api_flow())
    print("\n" + "=" * 70)
    print("       ALL DEPARTMENT FILTERING VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
