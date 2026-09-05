from sqlalchemy.orm import Session
from app import crud, schemas

def test_crud_user(db: Session):
    user_in = schemas.UserCreate(username="cruduser", password="password", role="user")
    user = crud.create_user(db, user_in)
    assert user.username == "cruduser"
    assert hasattr(user, "id")
    
    fetched = crud.get_user_by_username(db, "cruduser")
    assert fetched.id == user.id

def test_crud_persona_lifecycle(db: Session):
    # Setup user
    u = crud.create_user(db, schemas.UserCreate(username="p_owner", password="pw", role="user"))
    
    # Create
    p_in = schemas.PersonaCreate(
        name="P1", bio="Bio", theories=["T1"], stance="S1", system_prompt="SP", is_public=True
    )
    persona = crud.create_persona(db, p_in, owner_id=u.id)
    assert persona.name == "P1"
    assert persona.theories == ["T1"]
    
    # Read
    fetched = crud.get_persona(db, persona.id)
    assert fetched.name == "P1"
    assert fetched.theories == ["T1"]
    
    # Update
    update_in = schemas.PersonaUpdate(name="P1_Updated", theories=["T2"])
    updated = crud.update_persona(db, persona.id, update_in)
    assert updated.name == "P1_Updated"
    assert updated.theories == ["T2"]
    
    # Update non-existent
    assert crud.update_persona(db, 999, update_in) is None
    
    # Delete
    assert crud.delete_persona(db, persona.id) is True
    assert crud.get_persona(db, persona.id) is None
    
    # Delete non-existent
    assert crud.delete_persona(db, 999) is True

def test_crud_forum_lifecycle(db: Session):
    u = crud.create_user(db, schemas.UserCreate(username="f_creator", password="pw", role="user"))
    p = crud.create_persona(db, schemas.PersonaCreate(name="P", bio="B", theories=[], is_public=True), owner_id=u.id)
    
    # Create
    f_in = schemas.ForumCreate(topic="Topic", participant_ids=[p.id])
    forum = crud.create_forum(db, f_in, creator_id=u.id)
    assert forum.topic == "Topic"
    
    # Read
    fetched = crud.get_forum(db, forum.id)
    assert fetched.id == forum.id
    
    # Message
    m_in = schemas.MessageCreate(
        forum_id=forum.id, persona_id=p.id, speaker_name="P", content="Hello", turn_count=1
    )
    msg = crud.create_message(db, m_in)
    assert msg.content == "Hello"
    
    # Get Messages
    msgs = crud.get_forum_messages(db, forum.id)
    assert len(msgs) == 1
    assert msgs[0].content == "Hello"

def test_persona_json_parsing_edge_cases(db: Session):
    # Test internal JSON handling if manually manipulated (less critical for pure CRUD but good for coverage)
    # The CRUD function handles string -> list conversion.
    # We can simulate a DB state where theories is a string.
    u = crud.create_user(db, schemas.UserCreate(username="json_user", password="pw", role="user"))
    p_in = schemas.PersonaCreate(name="BadJSON", bio="B", theories=[], is_public=True)
    p = crud.create_persona(db, p_in, owner_id=u.id)
    
    # Manually corrupt theories to invalid JSON string
    db.execute("UPDATE personas SET theories = ? WHERE id = ?", ["invalid json", p.id])
    
    from app.crud import get_persona
    db_p = get_persona(db, p.id)
    assert db_p.theories == "invalid json"
