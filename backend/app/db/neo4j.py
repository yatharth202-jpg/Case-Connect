import logging
from neo4j import GraphDatabase, Driver
from backend.app.config import settings

logger = logging.getLogger("case_connect.neo4j")
_driver: Driver | None = None

def get_neo4j_driver() -> Driver | None:
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                connection_timeout=2.0,
                max_connection_lifetime=60
            )
        except Exception as e:
            logger.warning(f"Could not initialize Neo4j driver: {e}")
            return None
    return _driver

def close_neo4j_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None

def get_neo4j_session():
    driver = get_neo4j_driver()
    if driver:
        try:
            return driver.session()
        except Exception:
            return None
    return None

def check_neo4j_health() -> bool:
    try:
        driver = get_neo4j_driver()
        if not driver:
            return False
        with driver.session() as session:
            result = session.run("RETURN 1 AS alive")
            record = result.single()
            return record is not None and record["alive"] == 1
    except Exception as e:
        logger.debug(f"Neo4j health check failed: {e}")
        return False

