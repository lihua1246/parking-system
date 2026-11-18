import sqlite3

import pytest

from app.models.entities import SPACE_FREE, SPACE_OCCUPIED, SPACE_RESERVED, ParkingSpace
from app.repository.db import get_connection, init_db
from app.repository.space_repo import SpaceRepo


@pytest.fixture
def repo():
    conn = get_connection(":memory:")
    init_db(conn)
    yield SpaceRepo(conn)
    conn.close()


def _space(code: str, zone: str = "A区", status: str = SPACE_FREE) -> ParkingSpace:
    return ParkingSpace(id=None, code=code, zone=zone, status=status, fixed_vehicle_id=None)


def test_req006_add_returns_id_and_get_roundtrip(repo):
    new_id = repo.add(_space("A-001"))
    assert isinstance(new_id, int)
    assert repo.get(new_id) == ParkingSpace(
        id=new_id, code="A-001", zone="A区", status=SPACE_FREE, fixed_vehicle_id=None
    )


def test_req006_duplicate_code_rejected(repo):
    repo.add(_space("A-001"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add(_space("A-001"))
    assert len(repo.list_all()) == 1


def test_req006_list_by_zone_and_status(repo):
    repo.add(_space("A-001", "A区", SPACE_FREE))
    repo.add(_space("A-002", "A区", SPACE_OCCUPIED))
    repo.add(_space("B-001", "B区", SPACE_FREE))

    assert [s.code for s in repo.list_by("A区", SPACE_FREE)] == ["A-001"]
    assert {s.code for s in repo.list_by("A区", None)} == {"A-001", "A-002"}
    assert {s.code for s in repo.list_by(None, SPACE_FREE)} == {"A-001", "B-001"}
    assert {s.code for s in repo.list_by(None, None)} == {"A-001", "A-002", "B-001"}


def test_req006_update_changes_fields(repo):
    space_id = repo.add(_space("A-001"))
    repo.update(ParkingSpace(space_id, "A-009", "B区", SPACE_RESERVED, None))
    assert repo.get(space_id) == ParkingSpace(
        id=space_id, code="A-009", zone="B区", status=SPACE_RESERVED, fixed_vehicle_id=None
    )


def test_req006_update_to_existing_code_rejected(repo):
    first = repo.add(_space("A-001"))
    repo.add(_space("A-002"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.update(ParkingSpace(first, "A-002", "A区", SPACE_FREE, None))
    assert repo.get(first).code == "A-001"


def test_req006_delete_removes_space(repo):
    space_id = repo.add(_space("A-001"))
    repo.delete(space_id)
    assert repo.get(space_id) is None
    assert repo.list_all() == []


def test_req006_get_missing_returns_none(repo):
    assert repo.get(999) is None


def test_req006_update_without_id_rejected(repo):
    with pytest.raises(ValueError):
        repo.update(_space("A-001"))
